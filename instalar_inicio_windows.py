"""
Instala Jarvis en el inicio de Windows.
Ejecuta este script UNA SOLA VEZ y Jarvis se abrirá automáticamente
cada vez que inicies sesión en tu laptop — sin ventana visible.
"""
import os
import shutil
from pathlib import Path

JARVIS_DIR = Path(__file__).parent.resolve()
VBS_FILE = JARVIS_DIR / "iniciar_jarvis.vbs"

# Carpeta de inicio de sesión de Windows
STARTUP_FOLDER = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
DESTINO = STARTUP_FOLDER / "Jarvis.vbs"

def instalar():
    if not VBS_FILE.exists():
        print(f"❌ No encontré el archivo: {VBS_FILE}")
        return

    # Regenerar el .vbs con la ruta absoluta correcta (por si el proyecto se movió)
    python_exe = JARVIS_DIR / ".venv" / "Scripts" / "python.exe"
    main_py = JARVIS_DIR / "main.py"

    if not python_exe.exists():
        print(f"❌ No encontré el venv en: {python_exe}")
        return

    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{JARVIS_DIR}"
WshShell.Run """{python_exe}"" ""{main_py}"" --auto", 0, False
Set WshShell = Nothing
'''
    DESTINO.write_text(vbs_content, encoding="utf-8")
    
    # Eliminar el archivo .bat anterior si existe para evitar ejecuciones duplicadas
    bat_antiguo = STARTUP_FOLDER / "Jarvis.bat"
    if bat_antiguo.exists():
        try:
            bat_antiguo.unlink()
            print("[INFO] Se elimino el archivo antiguo Jarvis.bat para evitar conflictos.")
        except Exception:
            pass

    print("[OK] Jarvis instalado en el inicio de Windows.")
    print(f"   Archivo creado en: {DESTINO}")
    print()
    print("   La proxima vez que inicies sesion en Windows,")
    print("   Jarvis arrancara automaticamente en silencio (sin ventana)")
    print("   y te dara los buenos dias.")

def desinstalar():
    removed = False
    for nombre in ["Jarvis.vbs", "Jarvis.bat"]:
        target = STARTUP_FOLDER / nombre
        if target.exists():
            target.unlink()
            print(f"[OK] {nombre} eliminado del inicio de Windows.")
            removed = True
    if not removed:
        print("[INFO] Jarvis no estaba en el inicio de Windows.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--desinstalar":
        desinstalar()
    else:
        instalar()
