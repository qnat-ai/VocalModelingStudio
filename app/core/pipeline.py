from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np

from app.analysis.key_detector import detect_key
from app.analysis.quality_diff import compare_quality_reports
from app.analysis.quality_guardrails import GuardrailSettings, evaluate_guardrails
from app.analysis.quality_report import analyze_audio, analyze_quality
from app.audio.cleanup import CleanupSettings, peak_normalize, process_cleanup
from app.audio.io import load_audio, save_audio
from app.audio.pitch import estimate_f0_mono, pitch_frame_to_note, placeholder_pitch_correction
from app.core.session import SessionPaths
from app.integration.audacity_bridge import AudacityBridge
from app.integration.vst_bridge import ExternalFxBridge
from app.mastering.chain import MasteringChain, MasteringSettings
from app.models.voice_conversion import VoiceConversionEngine
from app.plugins.demucs.plugin import DemucsPlugin
from app.utils.logging import setup_logging


class VocalPipeline:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.audio_cfg = config.get("audio", {})
        self.processing_cfg = config.get("processing", {})
        self.paths_cfg = config.get("paths", {})
        self.mastering_cfg = config.get("mastering", {})
        self.integration_cfg = config.get("integration", {})
        self.guardrails_cfg = config.get("quality_guardrails", {})

    def run(
        self,
        input_path: Path,
        reference_path: Path | None = None,
        export_for_audacity: bool = False,
        output_path: Path | None = None,
    ) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        projects_dir = Path(self.paths_cfg.get("projects_dir", "data/projects"))
        session = SessionPaths.create(projects_dir, stamp=stamp, input_name=input_path.stem)
        logger = setup_logging(Path(self.paths_cfg.get("logs_dir", "logs")), session_id=session.session_id)
        logger.info("Start render session: %s", session.session_id)

        source_copy = session.input_dir / input_path.name
        shutil.copy2(input_path, source_copy)
        if reference_path is not None and reference_path.exists():
            shutil.copy2(reference_path, session.input_dir / reference_path.name)

        sr = int(self.audio_cfg.get("sample_rate", 48000))
        mono = bool(self.audio_cfg.get("mono", False))
        normalize_peak_db = self.audio_cfg.get("normalize_peak_db")

        processing_input_path = input_path
        demucs_used = False
        if self.processing_cfg.get("split_vocals_enabled", False):
            demucs = DemucsPlugin(binary_name=str(self.processing_cfg.get("demucs_binary", "demucs")))
            demucs_strict = bool(self.processing_cfg.get("demucs_strict", False))
            try:
                if not demucs.check_available():
                    raise RuntimeError("demucs CLI is not available in PATH.")
                processing_input_path = demucs.separate_vocals(
                    input_path,
                    session.work_dir / "demucs",
                    model_name=str(self.processing_cfg.get("demucs_model", "htdemucs")),
                )
                demucs_used = True
                logger.info("Demucs separation completed: %s", processing_input_path)
            except Exception as exc:
                if demucs_strict:
                    logger.exception("Demucs strict mode failure")
                    raise
                logger.warning("Demucs unavailable or failed, continuing without split: %s", exc)

        input_report = analyze_quality(processing_input_path)
        input_report_path = session.reports_dir / f"quality_before_{input_path.stem}.json"
        input_report_path.write_text(input_report.to_json(), encoding="utf-8")

        audio, sr = load_audio(processing_input_path, sample_rate=sr, mono=mono)
        audio = process_cleanup(audio, sr, CleanupSettings.from_mapping(self.audio_cfg.get("cleanup", {})))
        if normalize_peak_db is not None:
            audio = peak_normalize(audio, target_db=float(normalize_peak_db))

        detected_key = "unknown"
        key_report_path = session.reports_dir / f"key_report_{input_path.stem}.txt"
        if self.processing_cfg.get("key_detection_enabled", True):
            detected_key = detect_key(processing_input_path)
            key_report_path.write_text(detected_key + "\n", encoding="utf-8")
            logger.info("Detected key: %s", detected_key)

        times, f0 = estimate_f0_mono(audio, sr)
        pitch_csv_path = session.reports_dir / f"pitch_report_{input_path.stem}.csv"
        voiced_frames = 0
        with pitch_csv_path.open("w", encoding="utf-8") as handle:
            handle.write("time_sec,f0_hz,midi,note_name,cents_off\n")
            for time_sec, hz in zip(times, f0):
                midi, note_name, cents_off = pitch_frame_to_note(float(hz) if hz == hz else float("nan"))
                if midi is not None:
                    voiced_frames += 1
                handle.write(
                    f"{time_sec:.6f},"
                    f"{'' if hz != hz else f'{hz:.3f}'},"
                    f"{'' if midi is None else f'{midi:.3f}'},"
                    f"{note_name},"
                    f"{'' if cents_off is None else f'{cents_off:.3f}'}\n"
                )
        pitch_summary = {
            "frames": int(len(times)),
            "voiced_frames": int(voiced_frames),
            "unvoiced_frames": int(len(times) - voiced_frames),
            "detected_key": detected_key,
            "pitch_correction_is_placeholder": bool(self.processing_cfg.get("pitch_correction_enabled", True)),
        }
        pitch_summary_path = session.reports_dir / f"pitch_report_{input_path.stem}.json"
        pitch_summary_path.write_text(json.dumps(pitch_summary, ensure_ascii=False, indent=2), encoding="utf-8")

        if self.processing_cfg.get("pitch_correction_enabled", True):
            logger.info("Pitch correction enabled in config; current stage is placeholder/non-destructive.")
            audio = placeholder_pitch_correction(
                audio,
                sr,
                strength=float(self.processing_cfg.get("pitch_strength", 0.65)),
            )

        vc = VoiceConversionEngine(
            enabled=bool(self.processing_cfg.get("voice_conversion_enabled", False)),
            config=self.processing_cfg.get("voice_conversion", {}),
        )
        audio = vc.convert(audio, sr, reference_path=reference_path)
        pre_master_audio = np.asarray(audio, dtype=np.float64).copy()

        mastering = MasteringChain.from_config(self.mastering_cfg)
        audio = mastering.process_audio(audio, sr)
        mastering_profile = mastering.get_last_profile()

        default_output_path = session.output_dir / f"{input_path.stem}_processed_{stamp}.wav"
        out_path = Path(output_path) if output_path else default_output_path
        save_audio(out_path, audio, sr)

        external_fx = ExternalFxBridge.from_config(self.integration_cfg.get("external_fx", {}))
        external_fx_applied = False
        if external_fx.settings.enabled:
            fx_output_path = session.work_dir / f"external_fx_{input_path.stem}_{stamp}.wav"
            try:
                out_path = external_fx.process_file(out_path, fx_output_path)
                audio, _ = load_audio(out_path, sample_rate=sr, mono=mono)
                external_fx_applied = True
                logger.info("External FX processed output using preset '%s'.", external_fx.settings.preset)
            except Exception as exc:
                if external_fx.settings.strict:
                    logger.exception("External FX strict mode failure")
                    raise
                logger.warning("External FX failed, keeping pre-FX output: %s", exc)
                out_path = default_output_path if output_path is None else Path(output_path)
                save_audio(out_path, audio, sr)

        output_report = analyze_audio(audio, sr, source=str(out_path))
        output_report_path = session.reports_dir / f"quality_after_{input_path.stem}.json"

        guardrail_settings = GuardrailSettings.from_mapping(self.guardrails_cfg)
        fail_safe_enabled = bool(self.guardrails_cfg.get("fail_safe_enabled", True))
        guardrail_result = evaluate_guardrails(output_report, guardrail_settings)
        guardrail_issues_before_fail_safe = tuple(guardrail_result.issues)
        fail_safe_activated = False
        if not guardrail_result.passed and fail_safe_enabled:
            fail_safe_activated = True
            neutral_cfg = self.guardrails_cfg.get("neutral_mastering", {})
            neutral_settings = MasteringSettings.neutral_preset(neutral_cfg)
            fallback_mastering = MasteringChain(neutral_settings)
            audio = fallback_mastering.process_audio(pre_master_audio, sr)
            mastering_profile = fallback_mastering.get_last_profile()
            out_path = Path(output_path) if output_path else default_output_path
            save_audio(out_path, audio, sr)
            output_report = analyze_audio(audio, sr, source=str(out_path))
            guardrail_result = evaluate_guardrails(output_report, guardrail_settings)
            external_fx_applied = False
            logger.warning("Fail-safe activated; neutral mastering preset replaced previous output.")

        output_report_path.write_text(output_report.to_json(), encoding="utf-8")

        quality_delta_report = compare_quality_reports(input_report, output_report)
        quality_delta_path = session.reports_dir / f"quality_delta_{input_path.stem}.json"
        quality_delta_path.write_text(quality_delta_report.to_json(), encoding="utf-8")

        guardrail_report_path = session.reports_dir / f"quality_guardrails_{input_path.stem}.json"
        guardrail_report_path.write_text(guardrail_result.to_json(), encoding="utf-8")

        mastering_profile_path = session.metadata_dir / "mastering_profile.json"
        mastering_profile_path.write_text(json.dumps(mastering_profile, ensure_ascii=False, indent=2), encoding="utf-8")

        run_metadata = {
            "session_id": session.session_id,
            "run_at": stamp,
            "input_path": str(input_path),
            "session_input_copy": str(source_copy),
            "processing_input_path": str(processing_input_path),
            "input_sha256": self._hash_file_sha256(input_path),
            "output_path": str(out_path),
            "sample_rate": int(sr),
            "mono": mono,
            "detected_key": detected_key,
            "demucs_used": demucs_used,
            "external_fx_applied": external_fx_applied,
            "guardrails_passed": guardrail_result.passed,
            "guardrail_issues_before_fail_safe": list(guardrail_issues_before_fail_safe),
            "fail_safe_enabled": fail_safe_enabled,
            "fail_safe_activated": fail_safe_activated,
            "mastering_profile": mastering_profile,
            "session_paths": session.to_dict(),
            "config": self.config,
        }
        run_metadata_path = session.metadata_dir / f"render_metadata_{input_path.stem}_{stamp}.json"
        run_metadata_path.write_text(json.dumps(run_metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        session_manifest_path = session.write_session_manifest(
            {
                "session_id": session.session_id,
                "input_path": str(input_path),
                "reference_path": str(reference_path) if reference_path else None,
                "output_path": str(out_path),
                "reports": {
                    "quality_before": str(input_report_path),
                    "quality_after": str(output_report_path),
                    "quality_delta": str(quality_delta_path),
                    "guardrails": str(guardrail_report_path),
                    "pitch_csv": str(pitch_csv_path),
                    "pitch_json": str(pitch_summary_path),
                    "key": str(key_report_path),
                },
            }
        )

        if export_for_audacity:
            bridge = AudacityBridge(
                in_dir=Path(self.paths_cfg.get("audacity_in_dir", str(session.work_dir / "audacity_in"))),
                out_dir=Path(self.paths_cfg.get("audacity_out_dir", str(session.work_dir / "audacity_out"))),
            )
            audacity_path = bridge.export_for_audacity(out_path)
            logger.info("Plik dla Audacity: %s", audacity_path)

        logger.info("Raport jakości wejścia: %s", input_report_path)
        logger.info("Raport pitch/F0: %s", pitch_csv_path)
        logger.info("Raport jakości wyjścia: %s", output_report_path)
        logger.info("Raport before/after: %s", quality_delta_path)
        logger.info("Raport guardrails: %s", guardrail_report_path)
        logger.info("Metadane renderu: %s", run_metadata_path)
        logger.info("Session manifest: %s", session_manifest_path)
        if fail_safe_activated:
            logger.warning("Aktywowano fail-safe: zastosowano neutralny preset masteringu.")
        if not guardrail_result.passed:
            logger.warning("Guardrails wykryly problemy jakościowe: %s", list(guardrail_result.issues))
        return out_path

    @staticmethod
    def _hash_file_sha256(path: Path) -> str:
        hasher = hashlib.sha256()
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

