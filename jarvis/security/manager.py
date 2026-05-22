from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import random
import unicodedata


PUBLIC_ACTIONS = {
    "open_chrome",
    "open_vscode",
    "open_spotify",
    "open_terminal",
    "open_explorer",
    "open_github",
    "close_chrome",
    "close_vscode",
    "close_spotify",
    "close_terminal",
    "search_google",
    "open_website",
    "web_search",
    "get_time",
    "volume_up",
    "volume_down",
    "mute",
    "unmute",
    "get_volume",
    "set_volume",
    "get_battery",
    "brightness_up",
    "brightness_down",
    "set_brightness",
    "analyze_camera",
    "standby",
}

PRIVATE_ACTIONS = {
    "get_system_stats",
    "add_reminder",
    "add_alarm",
    "list_reminders",
    "cancel_reminders",
    "save_custom_macro",
    "run_custom_macro",
    "list_custom_macros",
    "delete_custom_macro",
    "edit_custom_macro",
    "analyze_screen",
    "save_learning_note",
    "summarize_today_learning",
    "reflect_today",
    "identify_user",
}

CRITICAL_ACTIONS = {
    "shutdown_pc",
    "restart_pc",
    "lock_pc",
    "cancel_shutdown",
}

OWNER_ONLY_ACTIONS = {
    "enroll_owner_face",
    "enroll_trusted_face",
    "delete_authorized_face",
    "list_authorized_faces",
    "lock_private_access",
    "set_guest_mode",
}


@dataclass(slots=True)
class SecurityDecision:
    allowed: bool
    state: str
    label: str
    response: str = ""


class SecurityManager:
    """Session-based access control for private Jarvis capabilities."""

    def __init__(
        self,
        owner_name: str | None = None,
        *,
        enabled: bool | None = None,
        session_seconds: int | None = None,
    ) -> None:
        from config import settings
        self.owner_name = (owner_name or settings.owner_name).strip() or "Diego Alexander Santos Aguilar"
        self.owner_short_name = self.owner_name.split()[0]
        self.enabled = settings.security_enabled if enabled is None else enabled
        self.session_seconds = max(30, settings.security_session_seconds if session_seconds is None else session_seconds)
        self.state = "unknown"
        self.verified_until: datetime | None = None
        self.denied_attempts = 0
        self.current_identity_name = ""
        self.current_identity_role = ""

    def authorize_action(self, action_name: str, action_input: object = "") -> SecurityDecision:
        level = self.access_level_for_action(action_name)
        return self._authorize(level)

    def authorize_text(self, text: str) -> SecurityDecision:
        if not self.looks_private_text(text):
            return self._allow()
        return self._authorize("private")

    def access_level_for_action(self, action_name: str) -> str:
        if action_name in OWNER_ONLY_ACTIONS:
            return "owner"
        if action_name in CRITICAL_ACTIONS:
            return "critical"
        if action_name in PRIVATE_ACTIONS:
            return "private"
        return "public"

    def looks_private_text(self, text: str) -> bool:
        normalized = self._normalize_text(text)
        private_phrases = [
            "que sabes de mi",
            "que recuerdas de mi",
            "mi memoria",
            "mis datos",
            "datos personales",
            "informacion personal",
            "mis rutinas",
            "mis macros",
            "mis recordatorios",
            "mis alarmas",
            "mi pantalla",
            "mis archivos",
            "mi proyecto",
            "mis preferencias",
            "quien soy",
            "como me llamo",
        ]
        return any(phrase in normalized for phrase in private_phrases)

    def verify_identity(self, name: str, role: str, method: str = "face") -> SecurityDecision:
        clean_role = role.strip().lower() or "trusted"
        self.current_identity_name = name.strip()
        self.current_identity_role = clean_role
        self.state = "verified_owner" if clean_role == "owner" else "trusted"
        self.verified_until = datetime.now() + timedelta(seconds=self.session_seconds)
        self.denied_attempts = 0
        return self._allow(label=self._label_for_state(self.state))

    def verify_owner(self, method: str = "manual") -> SecurityDecision:
        return self.verify_identity(self.owner_name, "owner", method=method)

    def set_guest(self) -> SecurityDecision:
        self.state = "guest"
        self.verified_until = None
        return SecurityDecision(True, self.state, "MODO INVITADO")

    def lock(self) -> SecurityDecision:
        self.state = "locked"
        self.verified_until = None
        return SecurityDecision(False, self.state, "BLOQUEADO")

    def status_label(self) -> str:
        return self._label_for_state(self.current_state())

    def current_state(self) -> str:
        if self.state in {"verified_owner", "trusted"} and self.verified_until is not None:
            if datetime.now() <= self.verified_until:
                return self.state
            self.state = "unknown"
            self.verified_until = None
            self.current_identity_name = ""
            self.current_identity_role = ""
        return self.state

    def _authorize(self, level: str) -> SecurityDecision:
        if level == "public":
            return self._allow()

        if not self.enabled:
            return self._allow(label="SEGURIDAD EN ESPERA")

        current_state = self.current_state()
        if current_state == "verified_owner":
            return self._allow(label="IDENTIFICADO")

        if current_state == "trusted" and level in {"private"}:
            return self._allow(label="AUTORIZADO")

        if current_state == "locked":
            return self._deny("locked")

        if current_state == "trusted" and level in {"owner", "critical"}:
            return self._deny("owner_required")

        self.denied_attempts += 1
        if self.denied_attempts >= 3:
            self.state = "security_watch"
            return self._deny("security_watch")

        self.state = "access_restricted"
        return self._deny("access_restricted")

    def _allow(self, label: str | None = None) -> SecurityDecision:
        state = self.current_state()
        return SecurityDecision(True, state, label or self._label_for_state(state))

    def _deny(self, state: str) -> SecurityDecision:
        self.state = state
        return SecurityDecision(
            False,
            state,
            self._label_for_state(state),
            self.denied_response(state),
        )

    def denied_response(self, state: str) -> str:
        if state == "locked":
            templates = [
                "Acceso bloqueado. No puedo continuar con funciones privadas hasta que el propietario se identifique.",
                "El acceso privado permanece bloqueado. Una medida estricta, si, pero bastante razonable.",
            ]
        elif state == "security_watch":
            templates = [
                f"Acceso restringido. Varios intentos privados sin autorizacion. Por favor, identifiquese o solicite a {self.owner_short_name} que autorice el acceso.",
                f"Me temo que debo activar vigilancia de seguridad. Si usted es {self.owner_short_name}, identifiquese; si no, admirable confianza, pero no puedo continuar.",
            ]
        elif state == "owner_required":
            templates = [
                f"Esa gestion requiere autorizacion directa de {self.owner_short_name}. Incluso para usuarios de confianza, conviene no entregar las llaves del reactor.",
                f"Acceso reservado al propietario. Por favor, solicite a {self.owner_short_name} que confirme esta operacion.",
            ]
        else:
            templates = [
                f"Disculpe, pero esta funcion no esta autorizada para el publico en general. Por favor, identifiquese o solicite a {self.owner_short_name} que autorice el acceso.",
                f"Me temo que no puedo revelar informacion privada sin una identificacion valida. Una precaucion aburrida, pero sensata.",
                f"Acceso restringido. Si usted es {self.owner_short_name}, por favor identifiquese. Si no lo es, admiro la confianza, pero no puedo continuar.",
            ]
        return random.choice(templates)

    def _label_for_state(self, state: str) -> str:
        labels = {
            "unknown": "SIN IDENTIFICAR",
            "verified_owner": "IDENTIFICADO",
            "trusted": "AUTORIZADO",
            "guest": "MODO INVITADO",
            "access_restricted": "ACCESO RESTRINGIDO",
            "owner_required": "REQUIERE PROPIETARIO",
            "locked": "BLOQUEADO",
            "security_watch": "VIGILANCIA",
        }
        return labels.get(state, "SIN IDENTIFICAR")

    def _normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFD", text.lower())
        return "".join(char for char in normalized if unicodedata.category(char) != "Mn")
