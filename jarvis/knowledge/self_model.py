from __future__ import annotations


PROJECT_SELF_KNOWLEDGE = {
    "CerebroJarvis.md": "Mi cerebro principal: prompt de sistema, personalidad, reglas de decision, acciones disponibles y formato JSON.",
    "main.py": "Mi orquestador central: inicia servicios, procesa texto/voz, ejecuta acciones, wake word, rutinas, vision y UI.",
    "config.py": "Mi configuracion: carga variables de entorno, modelos, wake word, voz, limites de audio y claves API.",
    ".env": "Configuracion privada local del usuario. Contiene claves y preferencias; no debo leer ni revelar secretos.",
    ".env.example": "Plantilla publica de configuracion sin secretos reales.",
    "memory.json": "Mi memoria persistente local: datos del usuario, preferencias y rutinas guardadas.",
    "jarvis/brain/openai_brain.py": "Mi cliente de OpenAI para analizar intenciones, memoria a corto plazo y memoria a largo plazo.",
    "jarvis/speech/speech_to_text.py": "Mi modulo de escucha y transcripcion con Whisper.",
    "jarvis/speech/text_to_speech.py": "Mi voz: ElevenLabs y respaldo local.",
    "jarvis/wakeword/listener.py": "Mi detector de wake word.",
    "jarvis/ui/": "Mi interfaz visible: HUD web, overlay pywebview y fallback tkinter.",
    "jarvis/ui/index.html": "Estructura HTML de mi HUD visible.",
    "jarvis/ui/style.css": "Estilo visual de mi HUD: colores, animaciones, orbe, paneles y estados.",
    "jarvis/ui/script.js": "Logica del HUD para cambiar estado y texto visible.",
    "jarvis/ui/overlay.py": "Controlador Python que envia estados al HUD.",
    "jarvis/ui/webview_overlay.py": "Proceso separado de pywebview que muestra mi interfaz HTML.",
    "jarvis/actions/": "Mis acciones de escritorio, navegador, busqueda web y sistema.",
    "jarvis/macros/manager.py": "Mi sistema de rutinas personalizadas.",
    "jarvis/reminders/manager.py": "Mi sistema de recordatorios y alarmas.",
    "jarvis/security/manager.py": "Mi capa de seguridad: clasifica acciones publicas, privadas y criticas, mantiene sesion de confianza y bloquea acceso privado si no hay autorizacion.",
    "jarvis/security/face_auth.py": "Mi reconocimiento facial local: registra rostros autorizados y verifica identidades con OpenCV sin enviar biometria a la nube.",
    "jarvis/vision/screen_vision.py": "Mi vision de pantalla: captura el monitor y lo analiza con un modelo de vision.",
    "jarvis/vision/camera_vision.py": "Mi vision por camara: captura una imagen puntual de la webcam y la analiza con un modelo de vision.",
    "requirements.txt": "Dependencias principales del proyecto.",
    "requirements-ui.txt": "Dependencias opcionales de interfaz web con pywebview.",
    "EstadoActual.md": "Documento humano que resume mi estado actual.",
    "MejorasFuturas.md": "Roadmap humano de mejoras futuras.",
}


def render_project_self_knowledge() -> str:
    lines = [
        "Jarvis Project Self-Knowledge:",
        "If the user shows or mentions these files, recognize them as parts of yourself.",
        "Be honest: you know their role from this map, but you only know exact current contents if they are visible, loaded, or explicitly read.",
        "",
    ]
    for path, description in PROJECT_SELF_KNOWLEDGE.items():
        lines.append(f"- {path}: {description}")
    return "\n".join(lines)
