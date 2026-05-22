from __future__ import annotations

import argparse
from datetime import datetime
import random
from pathlib import Path
import re
import time
import unicodedata

from config import settings
from jarvis.actions.app_actions import AppActions
from jarvis.actions.browser_actions import BrowserActions
from jarvis.actions.search_actions import SearchActions
from jarvis.actions.system_actions import SystemActions
from jarvis.brain.openai_brain import OpenAIBrain
from jarvis.conversation.logger import ConversationLogger
from jarvis.macros.manager import MacroManager
from jarvis.reminders.manager import ReminderManager
from jarvis.security.face_auth import FaceAuthService
from jarvis.security.manager import SecurityManager
from jarvis.speech.speech_to_text import SpeechToTextService
from jarvis.speech.text_to_speech import TextToSpeechService
from jarvis.ui.overlay import OverlayUI
from jarvis.vision.camera_vision import CameraVisionService
from jarvis.vision.screen_vision import ScreenVisionService
from jarvis.wakeword.listener import WakeWordListener


class JarvisApp:
    def __init__(self, auto_mode: bool = False) -> None:
        self.auto_mode = auto_mode
        self.ui = OverlayUI()
        self.wake_word = WakeWordListener(
            settings.wake_word,
            model_name=settings.wake_word_model,
            threshold=settings.wake_word_threshold,
            debug=False if auto_mode else settings.wake_word_debug,
        )
        self.speech_to_text = SpeechToTextService()
        self.text_to_speech = TextToSpeechService()
        self.brain = OpenAIBrain()
        self.app_actions = AppActions()
        self.browser_actions = BrowserActions()
        self.search_actions = SearchActions()
        self.system_actions = SystemActions()
        self.reminders = ReminderManager(speak_callback=self.text_to_speech.speak)
        self.macros = MacroManager(self.brain.memory)
        self.screen_vision = ScreenVisionService()
        self.camera_vision = CameraVisionService()
        self.conversation_logger = ConversationLogger()
        self.security = SecurityManager()
        self._last_identity_notice = ""
        self.face_auth = FaceAuthService()
        self._standby_triggered = False
        self._ensure_owner_memory()

    def run(self) -> None:
        self.ui.start()
        self._sync_security_ui()
        self.ui.set_detail("Jarvis iniciado")
        self.ui.activate("thinking", "Interfaz lista")
        self.ui.hide(delay_ms=1800)
        self.ui.set_detail("En espera de activacion")
        self.ui.set_state("idle")
        self.reminders.start()  # Arrancar hilo de recordatorios
        print("Jarvis listo.")
        print(
            "Escribe un comando, usa '/voz' para grabar hasta silencio, "
            "usa '/wake' para escuchar 'hey jarvis', o 'salir' para terminar."
        )

        while True:
            try:
                user_text = input("Tu> ").strip()
            except EOFError:
                break
            if user_text.lower() in {"salir", "exit", "quit"}:
                print("Jarvis> Consolidando aprendizaje del dia...")
                reflection = self.reflect_today(reason="shutdown")
                if reflection:
                    print(f"Jarvis> {reflection}")
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
        self._standby_triggered = False
        self.ui.show()
        self._sync_security_ui()
        self.ui.set_detail(f'Tu dijeste: "{text}"')
        self.ui.set_state("thinking")

        denied = self._deny_if_private_text(text)
        if denied:
            return self._speak_and_log_denial(text, denied, action="private_text")

        # Intentar coincidir una rutina local directamente primero antes de ir al cerebro LLM
        matched_macro = self.macros.match_in_text(text)
        if matched_macro:
            denied = self._deny_if_unauthorized("run_custom_macro")
            if denied:
                return self._speak_and_log_denial(text, denied, action="run_custom_macro")
            self.ui.set_detail(f"Ejecutando rutina: {matched_macro}")
            self.ui.set_state("speaking")
            response = self.run_custom_macro(matched_macro)
            self.ui.set_detail(response)
            self.text_to_speech.speak(response)
            self.ui.set_state("idle")
            self.ui.set_detail("En espera de activacion")
            return self._log_and_return(text, response, intent="action", action="run_custom_macro")

        analysis = self.brain.analyze(text)

        if analysis.get("intent") == "sequence":
            steps = analysis.get("steps", [])
            self.ui.set_detail("Ejecutando secuencia")
            self.ui.set_state("speaking")
            response = self.execute_sequence(steps, analysis.get("response", "Enseguida, señor."))
            self.ui.set_detail(response)
            self.text_to_speech.speak(response)
            self.ui.set_state("idle")
            if self._standby_triggered:
                self.ui.set_detail("En reposo")
            else:
                self.ui.set_detail("En espera de activacion")
            return self._log_and_return(text, response, intent="sequence", action="execute_sequence", action_input=steps)

        if analysis.get("intent") == "action":
            action_name = analysis.get("action", "")
            action_input = analysis.get("action_input", "")
            if not action_name:
                response = analysis.get("response", "No pude identificar la accion solicitada.")
                self.ui.set_state("speaking")
                self.ui.set_detail(response)
                self.text_to_speech.speak(response)
                self.ui.set_state("idle")
                self.ui.set_detail("En espera de activacion")
                return self._log_and_return(text, response, intent="action")

            detail_input = action_input if isinstance(action_input, str) else ""
            self.ui.set_detail(self.describe_action(action_name, detail_input))
            self.ui.set_state("speaking")
            response = self.execute_action(action_name, action_input)
            self.ui.set_detail(response)
            self.text_to_speech.speak(response)
            self.ui.set_state("idle")
            if self._standby_triggered:
                self.ui.set_detail("En reposo")
            else:
                self.ui.set_detail("En espera de activacion")
            return self._log_and_return(text, response, intent="action", action=action_name, action_input=action_input)

        response = analysis.get("response", "No tengo una respuesta para eso todavia.")
        self.ui.set_state("speaking")
        self.ui.set_detail(response)
        self.text_to_speech.speak(response)
        self.ui.set_state("idle")
        self.ui.set_detail("En espera de activacion")
        return self._log_and_return(text, response, intent="chat")

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

                    if self._standby_triggered:
                        break

        except KeyboardInterrupt:
            self.ui.set_state("idle")
            self.ui.set_detail("En espera de activacion")
            print("\nJarvis> Saliendo del modo wake word.")

    def execute_action(self, action_name: str, action_input: object = "") -> str:
        action_text = str(action_input).strip() if not isinstance(action_input, dict) else ""
        denied = self._deny_if_unauthorized(action_name, action_input)
        if denied:
            return denied

        if action_name in {
            "open_chrome", "open_vscode", "open_spotify",
            "open_terminal", "open_explorer",
            "close_chrome", "close_vscode", "close_spotify", "close_terminal",
        }:
            return self.app_actions.execute(action_name)

        if action_name == "open_github":
            return self.browser_actions.open_github()

        if action_name == "search_google":
            query = action_text
            if not query:
                return "Necesito saber que quieres buscar en Google."
            return self.browser_actions.search_google(query)

        if action_name == "open_website":
            url = action_text
            if not url:
                return "Necesito una direccion web para abrirla."
            return self.browser_actions.open_url(url)

        if action_name == "web_search":
            query = action_text
            if not query:
                return "Necesito saber qué quieres que busque."
            self.ui.set_detail(f'Buscando: "{query}"')
            return self.search_actions.search_and_summarize(query)

        # Todas las acciones de sistema van por el dispatcher central
        system_actions = {
            "get_time", "shutdown_pc", "restart_pc", "lock_pc", "cancel_shutdown",
            "volume_up", "volume_down", "mute", "unmute", "get_volume", "set_volume",
            "get_battery", "get_system_stats",
            "brightness_up", "brightness_down", "set_brightness",
        }
        if action_name in system_actions:
            return self.system_actions.execute(action_name, action_text)

        if action_name == "add_reminder":
            # action_input formato: "30|Tomar el medicamento"
            try:
                parts = action_text.split("|", 1)
                minutes = int(parts[0].strip())
                message = parts[1].strip() if len(parts) > 1 else "Recordatorio"
                return self.reminders.add(minutes, message)
            except Exception:
                return "No pude interpretar el recordatorio. Dime: 'recuérdame X en N minutos'."

        if action_name == "add_alarm":
            # action_input formato: "07:30|Despertar"
            try:
                parts = action_text.split("|", 1)
                h, m = parts[0].strip().split(":")
                message = parts[1].strip() if len(parts) > 1 else "Alarma"
                return self.reminders.add_alarm(int(h), int(m), message)
            except Exception:
                return "No pude interpretar la alarma. Dime: 'pon una alarma a las X para Y'."

        if action_name == "list_reminders":
            pending = self.reminders.list_pending()
            if not pending:
                return "No tiene recordatorios pendientes."
            lines = [f"- {r['message']} a las {r['trigger_at'].strftime('%H:%M')}" for r in pending]
            return "Sus recordatorios pendientes: " + "; ".join(lines) + "."

        if action_name == "cancel_reminders":
            return self.reminders.cancel_all()

        if action_name == "save_custom_macro":
            return self.save_custom_macro(action_input)

        if action_name == "run_custom_macro":
            return self.run_custom_macro(action_text)

        if action_name == "list_custom_macros":
            return self.list_custom_macros()

        if action_name == "delete_custom_macro":
            return self.macros.delete(action_text)

        if action_name == "edit_custom_macro":
            return self.edit_custom_macro(action_input)

        if action_name == "analyze_screen":
            return self.analyze_screen(action_text)

        if action_name == "analyze_camera":
            return self.analyze_camera(action_text, inspect=self._looks_like_object_inspection(action_text))

        if action_name == "standby":
            self._standby_triggered = True
            return self.standby_response(self.reflect_today(reason="standby"))

        if action_name == "identify_user":
            return self.identify_user()

        if action_name == "enroll_owner_face":
            return self.enroll_owner_face()

        if action_name == "enroll_trusted_face":
            return self.enroll_trusted_face(action_text)

        if action_name == "delete_authorized_face":
            return self.delete_authorized_face(action_text)

        if action_name == "list_authorized_faces":
            return self.list_authorized_faces()

        if action_name == "lock_private_access":
            return self.lock_private_access()

        if action_name == "set_guest_mode":
            return self.activate_guest_mode()

        if action_name == "save_learning_note":
            return self.save_learning_note(action_text)

        if action_name == "summarize_today_learning":
            return self.summarize_today_learning()

        if action_name == "reflect_today":
            return self.reflect_today(reason="manual")

        return "No reconozco esa accion todavia."

    def execute_sequence(self, steps: object, intro_response: str = "", summarize: bool = True) -> str:
        if not isinstance(steps, list) or not steps:
            return "No pude interpretar la secuencia de acciones."

        # Upfront authorization check for all sequence steps
        for step in steps:
            if not isinstance(step, dict):
                continue
            action_name = str(step.get("action", "")).strip()
            action_input = step.get("action_input", "")
            if not action_name:
                continue
            denied = self._deny_if_unauthorized(action_name, action_input)
            if denied:
                return denied

        results: list[str] = []
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                results.append(f"Paso {index}: no pude interpretarlo.")
                continue

            action_name = str(step.get("action", "")).strip()
            action_input = str(step.get("action_input", "")).strip()
            if not action_name:
                results.append(f"Paso {index}: falta la accion.")
                continue

            self.ui.set_detail(self.describe_action(action_name, action_input))
            result = self.execute_action(action_name, action_input)
            results.append(result)

        successful_results = [result for result in results if result]
        if not successful_results:
            return "No pude completar la secuencia."

        prefix = intro_response.strip()
        if not summarize:
            return prefix or "Secuencia completada."

        summary = " ".join(successful_results)
        return f"{prefix} {summary}".strip() if prefix else summary

    def save_custom_macro(self, action_input: object) -> str:
        if not isinstance(action_input, dict):
            return "No pude interpretar la rutina que desea guardar."

        name = str(action_input.get("name", "")).strip()
        steps = action_input.get("steps", [])
        if not isinstance(steps, list):
            return "La rutina no contiene una lista valida de acciones."

        return self.macros.save(name, steps)

    def save_learning_note(self, text: str) -> str:
        note = self._extract_learning_note(text)
        if not note:
            return "No identifique con claridad que debo recordar."

        if self._looks_sensitive(note):
            return "Prefiero no guardar eso en memoria permanente, señor."

        learned_notes = self.brain.memory.get("learned_notes", [])
        if not isinstance(learned_notes, list):
            learned_notes = []

        learned_notes.append({
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "note": note,
        })
        self.brain.memory.set("learned_notes", learned_notes[-200:])
        return "Lo recordaré, señor."

    def summarize_today_learning(self) -> str:
        log_text = self.conversation_logger.get_today_text()
        return self.brain.summarize_conversation_log(log_text)

    def reflect_today(self, reason: str = "manual") -> str:
        log_text = self.conversation_logger.get_today_text()
        if len(log_text.strip()) < 220:
            if reason == "standby":
                return self._stored_reflection_summary()
            return ""

        reflection = self.brain.reflect_on_conversation_log(log_text)
        summary = str(reflection.get("summary", "")).strip()
        durable_lessons = reflection.get("durable_lessons", [])
        followups = reflection.get("followups", [])

        if not summary and not durable_lessons and not followups:
            if reason == "standby":
                return self._stored_reflection_summary()
            return ""

        today = datetime.now().strftime("%Y-%m-%d")
        daily_reflections = self.brain.memory.get("daily_reflections", {})
        if not isinstance(daily_reflections, dict):
            daily_reflections = {}

        daily_reflections[today] = {
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "reason": reason,
            "summary": summary,
            "durable_lessons": durable_lessons if isinstance(durable_lessons, list) else [],
            "followups": followups if isinstance(followups, list) else [],
        }
        self.brain.memory.set("daily_reflections", daily_reflections)

        if reason == "manual":
            return "He consolidado el aprendizaje de hoy, señor."
        if reason == "standby":
            return self._spoken_reflection_summary(summary, durable_lessons, followups)
        return self._spoken_reflection_summary(summary, durable_lessons, followups)

    def _stored_reflection_summary(self) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        daily_reflections = self.brain.memory.get("daily_reflections", {})
        if not isinstance(daily_reflections, dict):
            return ""

        reflection = daily_reflections.get(today, {})
        if not isinstance(reflection, dict):
            return ""

        return self._spoken_reflection_summary(
            str(reflection.get("summary", "")).strip(),
            reflection.get("durable_lessons", []),
            reflection.get("followups", []),
        )

    def _spoken_reflection_summary(
        self,
        summary: str,
        durable_lessons: object,
        followups: object,
    ) -> str:
        lessons = self._clean_reflection_items(durable_lessons)
        pending_items = self._clean_reflection_items(followups)

        if self._reflection_is_large(summary, lessons, pending_items):
            response = random.choice([
                "Senor, hoy fue un dia productivo. Aprendi bastante y deje lo importante consolidado.",
                "Hoy fue una buena sesion, senor. Aprendi bastante, asi que guarde lo esencial para retomarlo luego.",
                "Senor, aprendi mucho hoy. Lo importante ya quedo consolidado para la proxima vez.",
            ])
            if pending_items:
                response += " Tambien deje pendientes registrados."
            return response

        parts: list[str] = []
        if lessons:
            first_lesson = self._shorten_spoken_fragment(lessons[0], max_chars=155)
            if first_lesson:
                parts.append(f"Hoy aprendi que {first_lesson}.")
        elif summary:
            clean_summary = self._shorten_spoken_fragment(summary, max_chars=175)
            if clean_summary:
                parts.append(f"Hoy consolide esto: {clean_summary}.")

        if pending_items:
            first_pending = self._shorten_spoken_fragment(pending_items[0], max_chars=120)
            if first_pending:
                parts.append(f"Queda pendiente: {first_pending}.")

        return " ".join(parts)

    def _clean_reflection_items(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip(" .") for item in value if str(item).strip(" .")]

    def _reflection_is_large(self, summary: str, lessons: list[str], pending_items: list[str]) -> bool:
        item_count = len(lessons) + len(pending_items)
        total_chars = len(summary) + sum(len(item) for item in lessons + pending_items)
        return item_count >= 4 or total_chars > 420

    def _shorten_spoken_fragment(self, text: str, max_chars: int) -> str:
        clean_text = " ".join(text.strip(" .").split())
        if len(clean_text) <= max_chars:
            return clean_text
        shortened = clean_text[:max_chars].rsplit(" ", 1)[0].strip(" ,.;:")
        return f"{shortened}..."

    def analyze_screen(self, user_request: str = "") -> str:
        try:
            self.ui.set_detail("Tomando captura de pantalla")
            self.ui.hide(delay_ms=0)
            time.sleep(0.35)
            result = self.screen_vision.analyze_screen(user_request)
            self.ui.show()
            return result
        except Exception as exc:
            self.ui.show()
            print(f"Jarvis> Error en vision de pantalla: {exc}")
            return "No pude analizar la pantalla en este momento."

    def analyze_camera(self, user_request: str = "", inspect: bool = False) -> str:
        try:
            self.ui.set_detail("Inspeccionando objeto" if inspect else "Mirando por la camara")
            analysis = self.camera_vision.analyze_camera_with_preview(user_request, inspect=inspect)
            label = "OBJECT SCAN" if inspect else "VISION FEED"
            self.ui.set_camera_preview(analysis.preview_data_url, f"{label} {analysis.sharpness_score:.0f}")
            return analysis.answer
        except Exception as exc:
            print(f"Jarvis> Error en vision por camara: {exc}")
            return "No pude acceder a la camara en este momento."

    def identify_user(self) -> str:
        try:
            self.ui.set_detail("Verificando identidad")
            result = self.face_auth.identify()
            if result.preview_data_url:
                self.ui.set_camera_preview(result.preview_data_url, "ESCANEO FACIAL")

            if result.total_faces == 0:
                self._last_identity_notice = ""
                decision = self.security.set_guest()
                self._sync_security_ui(decision.state, decision.label)
                return "No detecto un rostro claro frente a la camara. Acceso privado no confirmado."

            owner = self._first_identity_by_role(result.identities, "owner")
            trusted = self._first_identity_by_role(result.identities, "trusted")
            identity = owner or trusted
            if identity is None:
                self._last_identity_notice = ""
                decision = self.security.set_guest()
                self._sync_security_ui(decision.state, decision.label)
                return "No reconozco a la persona frente a la camara. Mantengo el acceso privado restringido."

            decision = self.security.verify_identity(identity.name, identity.role, method="face")
            self._sync_security_ui(decision.state, decision.label)
            guest_note = ""
            if result.unknown_faces > 0:
                guest_note = " Parece que tenemos un invitado con nosotros."
            self._last_identity_notice = guest_note.strip()

            if identity.role == "owner":
                return f"Identificado, señor {identity.name}.{guest_note}"
            return f"He identificado a {identity.name}, registrado como {identity.relation}. Acceso autorizado limitado.{guest_note}"
        except Exception as exc:
            print(f"Jarvis> Error en identificacion facial: {exc}")
            return "No pude completar la identificacion facial en este momento."

    def enroll_owner_face(self) -> str:
        if self.face_auth.has_profiles() and not self._owner_is_verified():
            return self.security.denied_response("owner_required")

        try:
            self.ui.set_detail("Registrando rostro del propietario")
            name = self.face_auth.enroll(
                settings.owner_name,
                relation="propietario",
                role="owner",
                samples=settings.face_enrollment_samples,
            )
            decision = self.security.verify_owner(method="face_enrollment")
            self._sync_security_ui(decision.state, decision.label)
            return f"Rostro registrado correctamente. Identificado como {name}."
        except Exception as exc:
            print(f"Jarvis> Error registrando propietario: {exc}")
            return "No pude registrar el rostro del propietario. Intente con buena luz y mirando a la camara."

    def enroll_trusted_face(self, text: str) -> str:
        if not self._owner_is_verified():
            return self.security.denied_response("owner_required")

        name, relation = self._extract_trusted_person(text)
        if not name:
            cleaned_text = text.strip()
            if cleaned_text and len(cleaned_text.split()) <= 3:
                name = cleaned_text
                relation = "persona autorizada"
            else:
                return "Necesito el nombre de la persona autorizada. Por ejemplo: Jarvis, él es mi padre, se llama Carlos."

        try:
            self.ui.set_detail(f"Registrando autorizado: {name}")
            registered_name = self.face_auth.enroll(
                name,
                relation=relation or "persona autorizada",
                role="trusted",
                samples=settings.face_enrollment_samples,
            )
            return f"{registered_name} ha quedado registrado como {relation or 'persona autorizada'}. Tendrá acceso privado autorizado, pero no permisos de propietario."
        except Exception as exc:
            print(f"Jarvis> Error registrando autorizado: {exc}")
            return "No pude registrar ese rostro. Necesito que solo esa persona mire a la camara, con buena luz."

    def list_authorized_faces(self) -> str:
        if not self._owner_is_verified():
            return self.security.denied_response("owner_required")

        profiles = self.face_auth.list_profiles()
        if not profiles:
            return "No hay rostros autorizados registrados."

        formatted = []
        for profile in profiles:
            role = "propietario" if profile.role == "owner" else "autorizado"
            formatted.append(f"{profile.name}, {profile.relation}, {role}")
        return "Personas autorizadas: " + "; ".join(formatted) + "."

    def delete_authorized_face(self, text: str) -> str:
        if not self._owner_is_verified():
            return self.security.denied_response("owner_required")

        name = self._extract_delete_authorized_name(text)
        if not name:
            cleaned_text = text.strip()
            if cleaned_text and len(cleaned_text.split()) <= 3:
                name = cleaned_text
            else:
                return "Necesito saber a quien debo retirar de autorizados."

        if self._normalize_text(name) in self._normalize_text(settings.owner_name):
            return "No retiraré el rostro del propietario desde este comando. Ese tipo de cirugía administrativa merece una confirmación mucho más explícita."

        if self.face_auth.delete_profile(name):
            return f"{name} ha sido retirado de personas autorizadas."
        return f"No encontré un autorizado llamado {name}."

    def lock_private_access(self) -> str:
        if not self._owner_is_verified():
            return self.security.denied_response("owner_required")

        decision = self.security.lock()
        self._sync_security_ui(decision.state, decision.label)
        return "Acceso privado bloqueado. Ninguna función sensible se ejecutará sin identificación del propietario."

    def activate_guest_mode(self) -> str:
        if not self._owner_is_verified():
            return self.security.denied_response("owner_required")

        decision = self.security.set_guest()
        self._sync_security_ui(decision.state, decision.label)
        return "Modo invitado activado. El acceso privado queda restringido, como debe ser."

    def _first_identity_by_role(self, identities: list[object], role: str):
        for identity in identities:
            if getattr(identity, "role", "") == role:
                return identity
        return None

    def _owner_is_verified(self) -> bool:
        return self.security.current_state() == "verified_owner"

    def standby_response(self, reflection_summary: str = "") -> str:
        templates = [
            "Entendido, señor. Entrando en reposo.",
            "De acuerdo. Quedo en espera.",
            "Por supuesto, señor. Descansaré hasta que me necesite.",
            "Hecho. Vuelvo al modo de espera.",
        ]
        response = random.choice(templates)
        if reflection_summary:
            return f"{reflection_summary} {response}"
        return response

    def edit_custom_macro(self, action_input: object) -> str:
        if not isinstance(action_input, dict):
            return "No pude interpretar el cambio de la rutina."

        name = str(action_input.get("name", "")).strip()
        operation = str(action_input.get("operation", "")).lower().strip()
        steps = action_input.get("steps", [])
        if not isinstance(steps, list):
            return "El cambio no contiene una lista valida de acciones."

        if operation in {"add", "agregar", "append"}:
            return self.macros.add_steps(name, steps)
        if operation in {"remove", "quitar", "delete", "borrar"}:
            return self.macros.remove_steps(name, steps)

        return "No pude saber si desea agregar o quitar acciones de la rutina."

    def run_custom_macro(self, macro_name: str) -> str:
        steps = self.macros.get(macro_name)
        if steps is None:
            return f"No encontre una rutina llamada '{macro_name}'."

        spoken_response = self._macro_activation_response(macro_name)
        return self.execute_sequence(steps, spoken_response, summarize=False)

    def list_custom_macros(self) -> str:
        names = self.macros.list_names()
        if not names:
            return "No tiene rutinas personalizadas guardadas."

        if len(names) == 1:
            formatted_names = names[0]
        else:
            formatted_names = ", ".join(names[:-1]) + f" y {names[-1]}"
        return f"Las rutinas guardadas que tiene son: {formatted_names}. ¿Desea modificar o activar alguna, señor?"

    def _macro_activation_response(self, macro_name: str) -> str:
        clean_name = macro_name.strip()
        if clean_name.startswith("modo "):
            mode_name = clean_name
        else:
            mode_name = f"modo {clean_name}"

        templates = [
            f"Ahora estamos en {mode_name}, señor.",
            f"{mode_name.capitalize()} activado, señor.",
            f"Entendido. Activando {mode_name}.",
            f"Listo, señor. {mode_name.capitalize()} está en marcha.",
        ]
        return random.choice(templates)

    def _extract_delete_authorized_name(self, text: str) -> str:
        cleaned = " ".join(text.strip().split())
        patterns = [
            r"(?:elimina|quita|retira|borra)\s+a\s+(.+?)(?:\s+de\s+(?:autorizados|personas autorizadas|rostros registrados))?$",
            r"(?:elimina|quita|retira|borra)\s+(?:el\s+)?(?:autorizado|rostro)\s+de\s+([^,.;]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip(" ,.;")
        return ""

    def _extract_trusted_person(self, text: str) -> tuple[str, str]:
        cleaned = " ".join(text.strip().split())
        patterns = [
            r"(?:el|él|ella)\s+es\s+mi\s+([^,.;]+)[,.;]?\s+se\s+llama\s+([^,.;]+)",
            r"se\s+llama\s+([^,.;]+)[,.;]?\s+(?:y\s+)?(?:es|es\s+mi)\s+([^,.;]+)",
            r"autoriza\s+a\s+([^,.;]+)\s+como\s+([^,.;]+)",
            r"registra\s+a\s+([^,.;]+)\s+como\s+([^,.;]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE)
            if not match:
                continue

            first = match.group(1).strip(" ,.;")
            second = match.group(2).strip(" ,.;")
            if "autoriza" in pattern or "registra" in pattern:
                return first, second
            if "se\\s+llama" in pattern and pattern.startswith("se"):
                return first, second
            return second, first
        return "", ""

    def _extract_learning_note(self, text: str) -> str:
        cleaned = " ".join(text.strip().split())
        cleaned = re.sub(r"^jarvis[,\s]+", "", cleaned, flags=re.IGNORECASE)
        normalized = self._normalize_text(cleaned)
        prefixes = [
            "jarvis recuerda que",
            "recuerda que",
            "jarvis aprende que",
            "aprende que",
            "jarvis memoriza que",
            "memoriza que",
            "jarvis no olvides que",
            "no olvides que",
            "jarvis ten en cuenta que",
            "ten en cuenta que",
            "quiero que recuerdes que",
            "quiero que recuerdes",
            "quiero que aprendas que",
            "quiero que aprendas",
            "guarda en memoria que",
        ]
        for prefix in prefixes:
            if normalized.startswith(prefix):
                return cleaned[len(prefix):].strip(" ,.:;")
        return cleaned

    def _looks_sensitive(self, text: str) -> bool:
        normalized = self._normalize_text(text)
        sensitive_words = [
            "api key",
            "apikey",
            "clave api",
            "password",
            "contrasena",
            "contraseña",
            "token",
            "secret",
            "secreto",
        ]
        return any(word in normalized for word in sensitive_words)

    def _looks_like_object_inspection(self, text: str) -> bool:
        normalized = self._normalize_text(text)
        triggers = [
            "inspecciona",
            "inspeccionar",
            "identifica",
            "identificar",
            "que es esto",
            "que objeto es",
            "este objeto",
            "este juguete",
            "esto que tengo",
            "mira este objeto",
            "analiza este objeto",
            "revisa este objeto",
        ]
        return any(trigger in normalized for trigger in triggers)

    def _normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFD", text.lower())
        return "".join(char for char in normalized if unicodedata.category(char) != "Mn")

    def _log_and_return(
        self,
        user_text: str,
        response: str,
        *,
        intent: str = "",
        action: str = "",
        action_input: object = "",
    ) -> str:
        try:
            self.conversation_logger.log_interaction(
                user_text,
                response,
                intent=intent,
                action=action,
                action_input=action_input,
            )
        except Exception as exc:
            print(f"Jarvis> [Log] No pude guardar la conversacion: {exc}")
        return response

    def _deny_if_unauthorized(self, action_name: str, action_input: object = "") -> str:
        decision = self.security.authorize_action(action_name, action_input)
        self._sync_security_ui(decision.state, decision.label)
        if decision.allowed:
            return ""

        if self._should_attempt_face_authorization(action_name):
            self.ui.set_detail("Verificando identidad")
            self.identify_user()
            decision = self.security.authorize_action(action_name, action_input)
            self._sync_security_ui(decision.state, decision.label)
            if decision.allowed:
                self._announce_identity_notice_if_any()
                return ""

        return decision.response

    def _deny_if_private_text(self, text: str) -> str:
        decision = self.security.authorize_text(text)
        self._sync_security_ui(decision.state, decision.label)
        if decision.allowed:
            return ""

        if self._should_attempt_face_authorization("private_text"):
            self.ui.set_detail("Verificando identidad")
            self.identify_user()
            decision = self.security.authorize_text(text)
            self._sync_security_ui(decision.state, decision.label)
            if decision.allowed:
                self._announce_identity_notice_if_any()
                return ""

        return decision.response

    def _should_attempt_face_authorization(self, action_name: str) -> bool:
        if not self.security.enabled:
            return False
        if self.security.current_state() in {"verified_owner", "trusted", "locked", "security_watch"}:
            return False
        if not self.face_auth.has_profiles():
            return False
        return True

    def _announce_identity_notice_if_any(self) -> None:
        if not self._last_identity_notice:
            return
        notice = f"Señor, {self._last_identity_notice[0].lower()}{self._last_identity_notice[1:]}"
        self.ui.set_state("speaking")
        self.ui.set_detail(notice)
        self.text_to_speech.speak(notice)
        self.ui.set_state("thinking")
        self._last_identity_notice = ""

    def _speak_and_log_denial(self, user_text: str, response: str, action: str = "") -> str:
        self.ui.set_state("speaking")
        self.ui.set_detail(response)
        self.text_to_speech.speak(response)
        self.ui.set_state("idle")
        self.ui.set_detail("Acceso restringido")
        return self._log_and_return(user_text, response, intent="security", action=action)

    def _sync_security_ui(self, state: str | None = None, label: str | None = None) -> None:
        current_state = state or self.security.current_state()
        current_label = label or self.security.status_label()
        try:
            self.ui.set_security_status(current_state, current_label)
        except Exception:
            pass

    def _ensure_owner_memory(self) -> None:
        try:
            if not self.brain.memory.get("owner_name"):
                self.brain.memory.set("owner_name", self.security.owner_name)
            if not self.brain.memory.get("nombre_usuario"):
                self.brain.memory.set("nombre_usuario", self.security.owner_short_name)
        except Exception as exc:
            print(f"Jarvis> [Seguridad] No pude guardar propietario en memoria: {exc}")

    def describe_action(self, action_name: str, action_input: str = "") -> str:
        descriptions = {
            "open_chrome": "Preparando Google Chrome",
            "open_vscode": "Preparando Visual Studio Code",
            "open_spotify": "Preparando Spotify",
            "open_terminal": "Preparando la terminal",
            "open_explorer": "Preparando el Explorador de archivos",
            "open_github": "Preparando GitHub",
            "close_chrome": "Cerrando Google Chrome",
            "close_vscode": "Cerrando Visual Studio Code",
            "close_spotify": "Cerrando Spotify",
            "close_terminal": "Cerrando la terminal",
            "web_search": "Buscando en internet...",
            "get_time": "Consultando la hora",
            "shutdown_pc": "Apagando el equipo",
            "restart_pc": "Reiniciando el equipo",
            "lock_pc": "Bloqueando el equipo",
            "cancel_shutdown": "Cancelando el apagado",
            "volume_up": "Subiendo el volumen",
            "volume_down": "Bajando el volumen",
            "mute": "Silenciando el sistema",
            "unmute": "Restaurando el sonido",
            "get_volume": "Consultando el volumen",
            "set_volume": "Ajustando el volumen",
            "get_battery": "Consultando la batería",
            "get_system_stats": "Consultando el estado del sistema",
            "brightness_up": "Subiendo el brillo",
            "brightness_down": "Bajando el brillo",
            "set_brightness": "Ajustando el brillo",
            "add_reminder": "Registrando recordatorio",
            "add_alarm": "Programando alarma",
            "list_reminders": "Consultando recordatorios pendientes",
            "cancel_reminders": "Cancelando todos los recordatorios",
            "save_custom_macro": "Guardando rutina personalizada",
            "run_custom_macro": "Ejecutando rutina personalizada",
            "list_custom_macros": "Consultando rutinas guardadas",
            "delete_custom_macro": "Eliminando rutina personalizada",
            "edit_custom_macro": "Modificando rutina personalizada",
            "analyze_screen": "Analizando la pantalla",
            "analyze_camera": "Analizando la camara",
            "standby": "Entrando en reposo",
        }
        if action_name == "search_google" and action_input:
            return f'Buscando en Google: "{action_input}"'
        if action_name == "open_website" and action_input:
            return f"Abriendo sitio: {action_input}"
        return descriptions.get(action_name, f"Accion: {action_name}")

    def startup_briefing(self) -> None:
        """
        Saludo de arranque personalizado.
        Habla segun la hora del dia, da el tiempo y el clima, luego entra en modo wake.
        """
        now = datetime.now()
        hour = now.hour
        time_str = now.strftime("%H:%M")

        if 5 <= hour < 12:
            saludo = "Buenos días"
        elif 12 <= hour < 19:
            saludo = "Buenas tardes"
        else:
            saludo = "Buenas noches"

        # Leer nombre del usuario si lo tiene guardado en memoria
        nombre = self.brain.memory.get("nombre_usuario", "")
        tratamiento = f", {nombre}" if nombre else ", señor"

        # Obtener ciudad de la memoria si está guardada
        ciudad = self.brain.memory.get("ciudad", "")
        query_clima = f"clima hoy en {ciudad}" if ciudad else "clima hoy"

        print("Jarvis> [Obteniendo briefing de arranque...]")
        try:
            clima = self.search_actions.search_and_summarize(query_clima)
        except Exception:
            clima = "No pude obtener el clima en este momento."

        mensaje = (
            f"{saludo}{tratamiento}. Son las {time_str}. "
            f"{clima} "
            f"Estoy listo y en escucha activa. ¿En qué puedo asistirle hoy?"
        )

        print(f"Jarvis> {mensaje}")
        self.ui.show()
        self.ui.set_state("speaking")
        self.text_to_speech.speak(mensaje)
        self.ui.set_state("idle")
        self.ui.hide(delay_ms=1000)

    def run_auto(self) -> None:
        """
        Modo automatico: briefing de arranque + wake word permanente.
        No termina hasta que se cierre el proceso. Ideal para inicio de Windows.
        """
        import time
        self.ui.start()
        self.ui.activate("thinking", "Iniciando Jarvis...")
        self.reminders.start()  # Arrancar hilo de recordatorios
        self.startup_briefing()

        # Esperar a que termine el audio del briefing antes de escuchar
        time.sleep(1.0)

        # Bucle infinito: si el wake word sale (Ctrl+C interno), vuelve a escuchar
        print("Jarvis> Modo automatico activo. Di 'hey jarvis' en cualquier momento.")
        while True:
            try:
                self.run_wake_mode()
            except KeyboardInterrupt:
                print("\nJarvis> Cerrando.")
                break
            except Exception as e:
                print(f"Jarvis> [Error en wake mode]: {e}. Reiniciando escucha...")
                time.sleep(2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jarvis AI Assistant")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Arranque automatico: briefing + modo wake word directo (ideal para inicio de Windows)"
    )
    args = parser.parse_args()

    app = JarvisApp(auto_mode=args.auto)
    if args.auto:
        app.run_auto()
    else:
        app.run()
