import logging
import os
import sys
from pathlib import Path

# Fix dla bezpośredniego uruchamiania pliku z podkatalogu
project_root = str(Path(__file__).parent.parent.parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import gradio as gr
from app.core.pipeline import VocalPipeline
from app.utils.config import load_config
from app.utils.logging import setup_logging

logger = logging.getLogger("vms.gui")


def create_ui(pipeline: VocalPipeline):
    with gr.Blocks(title="Vocal Modeling Studio") as demo:
        gr.Markdown("# 🎙️ Vocal Modeling Studio")
        gr.Markdown(
            "Wgraj swój wokal, wybierz próbkę referencyjną i pozwól AI zająć się resztą."
        )

        with gr.Row():
            with gr.Column():
                input_audio = gr.Audio(
                    label="Twój wokal (Input)", type="filepath"
                )
                reference_audio = gr.Audio(
                    label="Próbka referencyjna (opcjonalnie)", type="filepath"
                )
                
                with gr.Accordion("Zaawansowane ustawienia", open=False):
                    audacity_export = gr.Checkbox(
                        label="Eksport dla Audacity", value=False
                    )
                    use_vc = gr.Checkbox(
                        label="Włącz Voice Conversion", value=True
                    )
                
                run_btn = gr.Button("Uruchom Pipeline", variant="primary")

            with gr.Column():
                output_audio = gr.Audio(label="Wynik (Processed)")
                output_path_display = gr.Textbox(label="Ścieżka do projektu", interactive=False)
                logs = gr.Textbox(label="Status / Logi", interactive=False)

        def process(input_path, ref_path, audacity_flag, vc_flag):
            if not input_path:
                return None, "", "Błąd: Brak pliku wejściowego."
            
            try:
                # Tymczasowa zmiana konfiguracji dla danego uruchomienia, jeśli potrzebna
                # (W MVP używamy domyślnej z załadowanego pipeline)
                
                result_path = pipeline.run(
                    input_path=Path(input_path),
                    reference_path=Path(ref_path) if ref_path else None,
                    export_for_audacity=audacity_flag
                )
                
                # result_path to ścieżka do końcowego pliku WAV
                return str(result_path), str(result_path.parent), "Sukces: Przetwarzanie zakończone."
            except Exception as e:
                logger.exception("Błąd podczas pracy pipeline: %s", e)
                return None, "", f"Błąd: {str(e)}"

        run_btn.click(
            fn=process,
            inputs=[input_audio, reference_audio, audacity_export, use_vc],
            outputs=[output_audio, output_path_display, logs]
        )
        
    return demo


def launch(config_path: str = "configs/default.yaml", prevent_thread_lock: bool = False) -> None:
    config = load_config(Path(config_path))
    
    # Inicjalizacja logowania dla GUI
    log_dir = Path(config.get("paths", {}).get("logs_dir", "logs"))
    setup_logging(log_dir)
    logger.info("Uruchamianie interfejsu Gradio...")
    
    pipeline = VocalPipeline(config=config)
    ui = create_ui(pipeline)
    ui.launch(show_error=True, prevent_thread_lock=prevent_thread_lock, inbrowser=True)


if __name__ == "__main__":
    # Dodaj root projektu do PYTHONPATH, aby importy 'app.*' działały przy bezpośrednim uruchomieniu
    project_root = str(Path(__file__).parent.parent.parent.parent.absolute())
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        os.environ["PYTHONPATH"] = project_root + os.pathsep + os.environ.get("PYTHONPATH", "")

    launch()
