from __future__ import annotations

from pathlib import Path

from config import settings
from jarvis.actions.app_actions import AppActions
from jarvis.actions.browser_actions import BrowserActions
from jarvis.actions.system_actions import SystemActions
from jarvis.brain.gemini_brain import GeminiBrain
from jarvis.speech.speech_to_text import SpeechToTextService
from jarvis.speech.text_to_speech import TextToSpeechService
from jarvis.ui.overlay import OverlayUI
from jarvis.wakeword.listener import WakeWordListener


class JarvisApp:
    def __init__(self) -> None:
        self.ui = OverlayUI()
        self.wake_word = WakeWordListener(
            settings.wake_word,
            model_name=settings.wake_word_model,
            threshold=settings.wake_word_threshold,
            debug=settings.wake_word_debug,
        )
        self.speech_to_text = SpeechToTextService(
            settings.whisper_model,
            settings.language,
            settings.whisper_prompt,
        )
        self.text_to_speech = TextToSpeechService(
            language=settings.language,
            rate=settings.tts_rate,
            voice_hint=settings.tts_voice_hint,
            elevenlabs_api_key=settings.elevenlabs_api_key,
            elevenlabs_voice_id=settings.elevenlabs_voice_id,
        )
        self.brain = GeminiBrain(settings.gemini_api_key, settings.gemini_model)
        self.app_actions = AppActions()
        self.browser_actions = BrowserActions()
        self.system_actions = SystemActions()

    def run(self) -> None:
        self.ui.start()
        self.ui.set_detail("Jarvis iniciado")
        self.ui.activate("thinking", "Interfaz lista")
        self.ui.hide(delay_ms=1800)
        self.ui.set_detail("En espera de activacion")
        self.ui.set_state("idle")
        print("Jarvis listo.")
        print(
            "Escribe un comando, usa '/voz' para grabar hasta silencio, "
            "usa '/wake' para escuchar 'hey jarvis', o 'salir' para terminar."
        )

        while True:
            user_text = input("Tu> ").strip()
            if user_text.lower() in {"salir", "exit", "quit"}:
                print("Cerrando Jarvis.")
                break

            if not user_text:
                continue

            if user_text.lower() == "/voz":
                try:
                    transcribed = self.capture_voice_command()
                except Exception as exc:
                    print(f"Jarvis> No pude grabar o transcribir audio: {exc}")
                    continue

                if not transcribed:
                    print("Jarvis> No detecte texto en el audio.")
                    continue

                print(f"Transcrito> {transcribed}")
                response = self.process_text(transcribed)
                print(f"Jarvis> {response}")
                continue

            if user_text.lower() == "/wake":
                self.run_wake_mode()
                continue

            response = self.process_text(user_text)
            print(f"Jarvis> {response}")

    def process_text(self, text: str) -> str:
        self.ui.show()
        self.ui.set_detail(f'Tu dijiste: "{text}"')
        self.ui.set_state("thinking")
        analysis = self.brain.analyze(text)

        if analysis.get("intent") == "action":
            action_name = analysis.get("action", "")
            action_input = analysis.get("action_input", "")
            self.ui.set_detail(self.describe_action(action_name, action_input))
            self.ui.set_state("speaking")
            response = self.execute_action(action_name, action_input)
            self.ui.set_detail(response)
            self.text_to_speech.speak(response)
            self.ui.set_state("idle")
            self.ui.set_detail("En espera de activacion")
            return response

        response = analysis.get("response", "No tengo una respuesta para eso todavia.")
        self.ui.set_state("speaking")
        self.ui.set_detail(response)
        self.text_to_speech.speak(response)
        self.ui.set_state("idle")
        self.ui.set_detail("En espera de activacion")
        return response

    def capture_voice_command(self) -> str:
        temp_audio = Path("temp_command.wav")
        self.ui.show()
        self.ui.set_detail("Habla despues del tono de voz")
        self.ui.set_state("listening")
        print("Jarvis> Escuchando... habla ahora.")
        self.speech_to_text.record_until_silence(
            str(temp_audio),
            max_duration_seconds=settings.voice_max_seconds,
            silence_duration_seconds=settings.voice_silence_seconds,
            min_speech_seconds=settings.voice_min_speech_seconds,
            energy_threshold=settings.voice_energy_threshold,
        )
        self.ui.set_state("thinking")
        self.ui.set_detail("Procesando tu voz...")
        return self.speech_to_text.transcribe_file(str(temp_audio))

    def run_wake_mode(self) -> None:
        print(f"Jarvis> Modo wake word activo. Di '{settings.wake_word}' para comenzar. Escribe Ctrl+C para salir.")
        try:
            while True:
                self.ui.set_state("idle")
                detection = self.wake_word.wait_for_wake_word()
                if not detection.detected:
                    continue

                self.ui.show()
                self.ui.set_detail("Wake word detectada")
                print(f"Jarvis> Wake word detectada con score {detection.score:.2f}")
                self.text_to_speech.speak("Sí, señor?")
                
                # Bucle continuo de conversación
                while True:
                    transcribed = self.capture_voice_command()
                    if not transcribed:
                        print("Jarvis> No detecte texto. Cerrando flujo de conversacion.")
                        self.ui.set_state("idle")
                        self.ui.set_detail("En espera de activacion")
                        break # Rompe el bucle interno, vuelve a esperar wake word

                    self.ui.set_detail(f'Transcrito: "{transcribed}"')
                    print(f"Transcrito> {transcribed}")
                    response = self.process_text(transcribed)
                    print(f"Jarvis> {response}")

        except KeyboardInterrupt:
            self.ui.set_state("idle")
            self.ui.set_detail("En espera de activacion")
            print("\nJarvis> Saliendo del modo wake word.")

    def execute_action(self, action_name: str, action_input: str = "") -> str:
        if action_name in {
            "open_chrome",
            "open_vscode",
            "open_spotify",
            "open_terminal",
            "open_explorer",
        }:
            return self.app_actions.execute(action_name)

        if action_name == "open_github":
            return self.browser_actions.open_github()

        if action_name == "search_google":
            query = action_input.strip()
            if not query:
                return "Necesito saber que quieres buscar en Google."
            return self.browser_actions.search_google(query)

        if action_name == "open_website":
            url = action_input.strip()
            if not url:
                return "Necesito una direccion web para abrirla."
            return self.browser_actions.open_url(url)

        if action_name == "get_time":
            return self.system_actions.get_current_time()

        return "No reconozco esa accion todavia."

    def describe_action(self, action_name: str, action_input: str = "") -> str:
        descriptions = {
            "open_chrome": "Preparando Google Chrome",
            "open_vscode": "Preparando Visual Studio Code",
            "open_spotify": "Preparando Spotify",
            "open_terminal": "Preparando la terminal",
            "open_explorer": "Preparando el Explorador de archivos",
            "open_github": "Preparando GitHub",
            "get_time": "Consultando la hora actual",
        }
        if action_name == "search_google" and action_input:
            return f'Buscando en Google: "{action_input}"'
        if action_name == "open_website" and action_input:
            return f"Abriendo sitio: {action_input}"
        return descriptions.get(action_name, f"Accion: {action_name}")


if __name__ == "__main__":
    JarvisApp().run()
