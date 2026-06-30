import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

# Fix dla bezpośredniego uruchamiania pliku z podkatalogu
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import gradio as gr
from app.audio.cleanup import CleanupSettings
from app.core.pipeline import VocalPipeline
from app.gui.gradio.legal_search_panel import (
    RESULT_HEADERS,
    download_selected_safe_result_for_gui,
    search_legal_sources_for_gui,
)
from app.standardization.vocal_standardizer import VocalInstrumentalStandardizer
from app.utils.config import load_config
from app.utils.logging import setup_logging

logger = logging.getLogger("vms.gui")

# Zmienne globalne do monitorowania aktywności
last_heartbeat = time.time()
heartbeat_lock = threading.Lock()

def _standardizer_from_config(config: dict[str, Any], cleanup_overrides: dict[str, Any] | None = None) -> VocalInstrumentalStandardizer:
    audio_cfg = config.get("audio", {})
    paths_cfg = config.get("paths", {})
    standardization_cfg = config.get("standardization", {})
    cleanup_cfg = dict(audio_cfg.get("cleanup", {}))
    if cleanup_overrides:
        cleanup_cfg.update(cleanup_overrides)
    return VocalInstrumentalStandardizer(
        sample_rate=int(audio_cfg.get("sample_rate", 48000)),
        output_dir=Path(paths_cfg.get("standardized_output_dir", "data/output/standardized")),
        target_vocal_relative_to_instrumental_db=float(
            standardization_cfg.get("target_vocal_relative_to_instrumental_db", -6.0)
        ),
        max_gain_correction_db=float(standardization_cfg.get("max_gain_correction_db", 12.0)),
        no_instrumental_target_peak_dbfs=float(standardization_cfg.get("no_instrumental_target_peak_dbfs", -1.0)),
        preview_mix_peak_dbfs=float(standardization_cfg.get("preview_mix_peak_dbfs", -1.0)),
        cleanup_settings=CleanupSettings.from_mapping(cleanup_cfg),
    )


def _safe_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.exists() else None


def _compare_vocal_standardization(
    config: dict[str, Any],
    vocal_path: str | None,
    instrumental_path: str | None,
    cleanup_overrides: dict[str, Any] | None,
) -> tuple[dict[str, Any], str, float, str]:
    if not vocal_path:
        return {}, "", 0.0, "Błąd: wgraj ścieżkę wokalną."

    vocal = _safe_path(vocal_path)
    instrumental = _safe_path(instrumental_path)
    if vocal is None:
        return {}, "", 0.0, "Błąd: nie znaleziono pliku ścieżki wokalnej."

    try:
        standardizer = _standardizer_from_config(config, cleanup_overrides)
        report = standardizer.analyze(vocal_path=vocal, instrumental_path=instrumental)
    except Exception as exc:
        logger.exception("Standardization analyze failed: %s", exc)
        return {}, "", 0.0, f"Błąd analizy: {exc}"

    state = {
        "vocal_path": str(vocal),
        "instrumental_path": str(instrumental) if instrumental else None,
        "proposed_gain_db": report.recommendation.proposed_vocal_gain_db,
        "alternative_gain_db": report.recommendation.alternative_vocal_gain_db,
    }
    status = "Gotowe: przygotowano propozycję dopasowania wokalu."
    return state, report.to_text(), report.recommendation.proposed_vocal_gain_db, status


def _render_vocal_standardization(
    config: dict[str, Any],
    state: dict[str, Any] | None,
    action: str,
    manual_gain_db: float | int | None,
    cleanup_overrides: dict[str, Any] | None,
) -> tuple[str | None, str | None, str, str, str]:
    if not state:
        return None, None, "", "", "Najpierw kliknij PORÓWNAJ / ZAPROPONUJ."

    vocal_path = state.get("vocal_path")
    instrumental_path = state.get("instrumental_path")
    if not vocal_path:
        return None, None, "", "", "Brak ścieżki wokalnej w stanie GUI."

    try:
        standardizer = _standardizer_from_config(config, cleanup_overrides)
        result = standardizer.render(
            vocal_path=Path(vocal_path),
            instrumental_path=Path(instrumental_path) if instrumental_path else None,
            action=action,  # type: ignore[arg-type]
            manual_gain_db=float(manual_gain_db) if action == "correct" else None,
        )
    except Exception as exc:
        logger.exception("Standardization render failed: %s", exc)
        return None, None, "", "", f"Błąd renderu: {exc}"

    output_folder = str(result.report_path.parent)
    status = (
        "Gotowe: wygenerowano dopasowaną ścieżkę wokalną. "
        "Instrumental nie został zmodyfikowany; preview mix służy tylko do kontroli."
    )
    return (
        str(result.vocal_path) if result.vocal_path else None,
        str(result.preview_mix_path) if result.preview_mix_path else None,
        output_folder,
        result.report.to_text(),
        status,
    )


def _run_legacy_pipeline(
    pipeline: VocalPipeline,
    input_path: str | None,
    reference_path: str | None,
    export_for_audacity: bool,
) -> tuple[str | None, str, str]:
    if not input_path:
        return None, "", "Błąd: najpierw wgraj plik audio z wokalem."

    try:
        result_path = pipeline.run(
            input_path=Path(input_path),
            reference_path=Path(reference_path) if reference_path else None,
            export_for_audacity=bool(export_for_audacity),
        )
    except Exception as exc:  # GUI should display a readable error instead of crashing
        logger.exception("Legacy pipeline failed: %s", exc)
        return None, "", f"Błąd pipeline: {exc}"

    return str(result_path), str(result_path.parent), "Sukces: przetwarzanie zakończone."

def create_ui(config: dict[str, Any], pipeline: VocalPipeline):
    theme = gr.themes.Soft()
    css = """
    .vms-small-note {font-size: 0.92rem; opacity: 0.82;}
    .vms-warning {border-left: 4px solid #d97706; padding-left: 0.8rem;}
    """
    with gr.Blocks(title="Vocal Modeling Studio 1.0.4", theme=theme, css=css) as demo:
        gr.Markdown("# 🎙️ Vocal Modeling Studio — 1.0.4")
        gr.Markdown(
            "**Standaryzator wokalu względem instrumentalu.** "
            "VMS zwraca dopasowaną ścieżkę wokalną; instrumental jest tylko referencją."
        )

        # Skrypt JavaScript do ostrzegania i bicia serca (heartbeat)
        demo.load(None, None, None, js="""
            () => {
                // Ostrzeżenie przed zamknięciem
                window.addEventListener('beforeunload', function (e) {
                    // Standardowe wymuszenie alertu w nowoczesnych przeglądarkach
                    e.preventDefault();
                    e.returnValue = '';
                    return "Czy na pewno chcesz opuścić stronę? Procesy w tle mogą zostać przerwane.";
                });

                // Funkcja bicia serca informująca serwer, że karta jest otwarta
                function sendHeartbeat() {
                    const btn = document.getElementById('heartbeat_btn');
                    if (btn) btn.click();
                }

                setInterval(sendHeartbeat, 5000); // Co 5 sekund
            }
        """)

        with gr.Tabs():
            with gr.Tab("Standaryzacja wokalu"):
                gr.Markdown(
                    "Główny workflow: wgraj ścieżkę wokalną i opcjonalnie instrumental jako referencję. "
                    "VMS zaproponuje korektę wokalu, a po akceptacji wygeneruje `vocal_processed.wav`. "
                    "`preview_mix.wav` zawiera 20-sekundowy fragment wokół najgłośniejszego momentu wokalu do szybkiej weryfikacji."
                )
                proposal_state = gr.State({})
                with gr.Row():
                    with gr.Column(scale=1):
                        vocal_audio = gr.Audio(label="Ścieżka wokalna", type="filepath")
                        instrumental_audio = gr.Audio(label="Instrumental / referencja (opcjonalnie)", type="filepath")
                        process_button = gr.Button("PROCESS", variant="primary")
                        
                        manual_mode = gr.Checkbox(label="MANUAL: ręczna korekta gain wokalu [dB]", value=False)
                        with gr.Column(visible=False) as manual_container:
                            manual_gain = gr.Slider(
                                label="Korekta gain [dB]",
                                minimum=-18,
                                maximum=18,
                                value=0,
                                step=0.25,
                            )
                        
                        with gr.Row():
                            accept_button = gr.Button("ACCEPT")
                            try_again_button = gr.Button("TRY AGAIN")
                        with gr.Accordion("Cleanup wokalu", open=False):
                            cleanup_enabled = gr.Checkbox(label="Włącz lekki cleanup", value=True)
                            cleanup_dc = gr.Checkbox(label="Usuń DC offset", value=True)
                            cleanup_hp_enabled = gr.Checkbox(label="High-pass dla wokalu", value=True)
                            cleanup_hp_hz = gr.Slider(label="High-pass [Hz]", minimum=40, maximum=180, value=80, step=1)
                            cleanup_fade_ms = gr.Slider(label="Fade safety [ms]", minimum=0, maximum=20, value=5, step=0.5)
                            cleanup_trim = gr.Checkbox(label="Trim ciszy", value=False)
                            cleanup_gate = gr.Checkbox(label="Noise gate", value=False)

                    with gr.Column(scale=1):
                        proposed_gain = gr.Number(label="Proponowany gain wokalu [dB]", interactive=False)
                        vocal_output = gr.Audio(label="Wynik główny: vocal_processed.wav")
                        preview_output = gr.Audio(label="Preview mix — tylko kontrolnie")
                        output_folder = gr.Textbox(label="Folder wyniku", interactive=False)
                        status = gr.Textbox(label="Status", lines=4, interactive=False)
                report_text = gr.Textbox(label="Raport / rekomendacje", lines=18, interactive=False)

                manual_mode.change(
                    fn=lambda x: gr.update(visible=x),
                    inputs=[manual_mode],
                    outputs=[manual_container]
                )

                process_button.click(
                    fn=lambda vocal_path, inst_path, enabled, dc, hp, hp_hz, fade, trim, gate: _compare_vocal_standardization(
                        config,
                        vocal_path,
                        inst_path,
                        {
                            "enabled": enabled,
                            "remove_dc_offset": dc,
                            "high_pass_enabled": hp,
                            "high_pass_hz": hp_hz,
                            "fade_ms": fade,
                            "trim_silence_enabled": trim,
                            "noise_gate_enabled": gate,
                        },
                    ),
                    inputs=[
                        vocal_audio,
                        instrumental_audio,
                        cleanup_enabled,
                        cleanup_dc,
                        cleanup_hp_enabled,
                        cleanup_hp_hz,
                        cleanup_fade_ms,
                        cleanup_trim,
                        cleanup_gate,
                    ],
                    outputs=[proposal_state, report_text, proposed_gain, status],
                )
                accept_button.click(
                    fn=lambda state, mode, gain, enabled, dc, hp, hp_hz, fade, trim, gate: _render_vocal_standardization(
                        config,
                        state,
                        "correct" if mode else "accept",
                        gain,
                        {
                            "enabled": enabled,
                            "remove_dc_offset": dc,
                            "high_pass_enabled": hp,
                            "high_pass_hz": hp_hz,
                            "fade_ms": fade,
                            "trim_silence_enabled": trim,
                            "noise_gate_enabled": gate,
                        },
                    ),
                    inputs=[
                        proposal_state,
                        manual_mode,
                        manual_gain,
                        cleanup_enabled,
                        cleanup_dc,
                        cleanup_hp_enabled,
                        cleanup_hp_hz,
                        cleanup_fade_ms,
                        cleanup_trim,
                        cleanup_gate,
                    ],
                    outputs=[vocal_output, preview_output, output_folder, report_text, status],
                )
                try_again_button.click(
                    fn=lambda vocal_path, inst_path, enabled, dc, hp, hp_hz, fade, trim, gate: _compare_vocal_standardization(
                        config,
                        vocal_path,
                        inst_path,
                        {
                            "enabled": enabled,
                            "remove_dc_offset": dc,
                            "high_pass_enabled": hp,
                            "high_pass_hz": hp_hz,
                            "fade_ms": fade,
                            "trim_silence_enabled": trim,
                            "noise_gate_enabled": gate,
                        },
                    ),
                    inputs=[
                        vocal_audio,
                        instrumental_audio,
                        cleanup_enabled,
                        cleanup_dc,
                        cleanup_hp_enabled,
                        cleanup_hp_hz,
                        cleanup_fade_ms,
                        cleanup_trim,
                        cleanup_gate,
                    ],
                    outputs=[proposal_state, report_text, proposed_gain, status],
                )

                with gr.Accordion("Klasyczny pipeline VMS / tryb zaawansowany", open=False):
                    gr.Markdown(
                        "Ten tryb uruchamia starszy pipeline analizy/czyszczenia/masteringu. "
                        "Nie jest głównym workflow standaryzacji względem instrumentalu."
                    )
                    with gr.Row():
                        legacy_input = gr.Audio(label="Input audio", type="filepath")
                        reference_audio = gr.Audio(label="Próbka referencyjna głosu (opcjonalnie)", type="filepath")
                    export_for_audacity = gr.Checkbox(label="Eksport pliku roboczego dla Audacity", value=False)
                    legacy_run_button = gr.Button("Uruchom klasyczny pipeline")
                    legacy_output = gr.Audio(label="Wynik klasycznego pipeline")
                    legacy_output_path = gr.Textbox(label="Folder wyniku / sesji", interactive=False)
                    legacy_status = gr.Textbox(label="Status", lines=4, interactive=False)
                    legacy_run_button.click(
                        fn=lambda input_path, ref_path, audacity_flag: _run_legacy_pipeline(
                            pipeline,
                            input_path,
                            ref_path,
                            audacity_flag,
                        ),
                        inputs=[legacy_input, reference_audio, export_for_audacity],
                        outputs=[legacy_output, legacy_output_path, legacy_status],
                    )

            with gr.Tab("Applio / Voice Changer"):
                gr.Markdown(
                    "### Applio backend\n"
                    "Applio pozostaje osobnym backendem dla **Voice Changer / Voice Conversion / Voice Blender**. "
                    "VMS nie implementuje własnego RVC i nie próbuje zastępować Applio. "
                    "Docelowo ten panel powinien służyć do sprawdzenia statusu Applio i wysłania/odebrania pliku wokalu."
                )

            with gr.Tab("Legal Search"):
                gr.Markdown(
                    "### Wyszukiwanie legalnych źródeł audio\n"
                    "Szukaj dostępnych legalnych źródeł audio po wykonawcy, tytule, gatunku, licencji lub metadanych. "
                    "Automatyczne pobieranie jest ograniczone do wyników sklasyfikowanych jako `safe`."
                )
                with gr.Row():
                    with gr.Column(scale=1):
                        search_title = gr.Textbox(label="Tytuł / fraza", placeholder="np. acapella vocal, public domain vocals")
                        search_artist = gr.Textbox(label="Wykonawca / autor", placeholder="opcjonalnie")
                        search_genre = gr.Textbox(label="Gatunek / styl", placeholder="np. pop, soul, ambient")
                        search_license = gr.Textbox(label="Licencja / typ źródła", placeholder="np. CC0, CC-BY, public domain")
                        search_isrc = gr.Textbox(label="ISRC", placeholder="opcjonalnie")
                        with gr.Accordion("Źródła i filtry", open=True):
                            use_local_catalog = gr.Checkbox(label="Katalog lokalny + sugestie źródeł", value=True)
                            use_musicbrainz = gr.Checkbox(label="MusicBrainz metadata", value=False)
                            use_archive = gr.Checkbox(label="Archive.org", value=False)
                            use_freesound = gr.Checkbox(label="Freesound API", value=False)
                            freesound_key = gr.Textbox(label="Freesound API key", type="password", placeholder="wymagany tylko dla Freesound")
                            safe_only = gr.Checkbox(label="Pokaż tylko wyniki safe", value=True)
                            limit = gr.Slider(label="Limit wyników API", minimum=1, maximum=50, step=1, value=10)
                        search_button = gr.Button("Szukaj", variant="primary")
                    with gr.Column(scale=2):
                        search_summary = gr.Markdown("Wyniki pojawią się po uruchomieniu wyszukiwania.")
                        search_table = gr.Dataframe(
                            headers=RESULT_HEADERS,
                            datatype=["str"] * len(RESULT_HEADERS),
                            label="Wyniki",
                            interactive=False,
                            wrap=True,
                        )
                        search_state = gr.State([])

                with gr.Accordion("Pobieranie bezpiecznego wyniku", open=False):
                    gr.Markdown(
                        "Podaj numer wyniku z tabeli. Pobieranie działa tylko wtedy, gdy status licencji to `safe` "
                        "i wynik ma bezpośredni URL do pliku/preview."
                    )
                    with gr.Row():
                        selected_result_number = gr.Number(label="Numer wyniku", precision=0, value=1)
                        download_dir = gr.Textbox(label="Folder pobrań", value="data/search_cache/downloads")
                    download_button = gr.Button("Pobierz wybrany safe wynik")
                    download_status = gr.Textbox(label="Status pobierania", lines=3, interactive=False)

                search_button.click(
                    fn=search_legal_sources_for_gui,
                    inputs=[
                        search_title,
                        search_artist,
                        search_isrc,
                        search_genre,
                        search_license,
                        use_local_catalog,
                        use_musicbrainz,
                        use_freesound,
                        freesound_key,
                        use_archive,
                        safe_only,
                        limit,
                    ],
                    outputs=[search_table, search_state, search_summary],
                )
                download_button.click(
                    fn=download_selected_safe_result_for_gui,
                    inputs=[search_state, selected_result_number, download_dir],
                    outputs=[download_status],
                )

            with gr.Tab("Narzędzia / Ustawienia"):
                gr.Markdown(
                    "### Narzędzia / Ustawienia\n"
                    "Ta sekcja nie jest głównym workflow. Służy do ustawień technicznych i przyszłych narzędzi pomocniczych:\n\n"
                    "- lista urządzeń audio / ASIO / WASAPI / sounddevice,\n"
                    "- status backendów, np. Applio,\n"
                    "- ścieżki do narzędzi zewnętrznych, np. ffmpeg,\n"
                    "- rekomendowany host zewnętrzny: REAPER (render/batch),\n"
                    "- informacje o środowisku.\n\n"
                    "Główny workflow znajduje się w zakładce **Standaryzacja wokalu**."
                )

                # Ukryty komponent do heartbeat
                heartbeat_btn = gr.Button("HB", elem_id="heartbeat_btn", visible=False)

                def heartbeat():
                    global last_heartbeat
                    with heartbeat_lock:
                        last_heartbeat = time.time()
                    return None

                heartbeat_btn.click(fn=heartbeat, inputs=[], outputs=[])

    return demo


def launch(config_path: str = "configs/default.yaml", prevent_thread_lock: bool = False) -> None:
    config = load_config(Path(config_path))
    
    # Inicjalizacja logowania dla GUI
    log_dir = Path(config.get("paths", {}).get("logs_dir", "logs"))
    setup_logging(log_dir)
    logger.info("Uruchamianie interfejsu Gradio...")
    
    pipeline = VocalPipeline(config=config)
    ui = create_ui(config=config, pipeline=pipeline)
    
    # Wątek monitorujący aktywność klientów
    def monitor_activity():
        # Dajemy czas na start i otwarcie przeglądarki
        time.sleep(15)
        while True:
            time.sleep(5)
            with heartbeat_lock:
                # Jeśli ostatni heartbeat był dawniej niż 15 sekund temu, zamykamy
                if time.time() - last_heartbeat > 15:
                    logger.warning("Brak aktywnych kart przeglądarki. Zamykanie serwera...")
                    os._exit(0) # Brutalne ale skuteczne zamknięcie procesu

    monitor_thread = threading.Thread(target=monitor_activity, daemon=True)
    monitor_thread.start()

    ui.launch(show_error=True, prevent_thread_lock=prevent_thread_lock, inbrowser=True)


if __name__ == "__main__":
    # Dodaj root projektu do PYTHONPATH, aby importy 'app.*' działały przy bezpośrednim uruchomieniu
    project_root = str(Path(__file__).parent.parent.parent.parent.absolute())
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        os.environ["PYTHONPATH"] = project_root + os.pathsep + os.environ.get("PYTHONPATH", "")

    launch()
