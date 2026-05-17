"""
Instala Jarvis en el inicio de Windows.
Ejecuta este script UNA SOLA VEZ y Jarvis se abrirá automáticamente
cada vez que inicies sesión en tu laptop.
"""
import os
import shutil
from pathlib import Path

JARVIS_DIR = Path(__file__).parent
BAT_FILE = JARVIS_DIR / "iniciar_jarvis.bat"

# Carpeta de inicio de sesión de Windows
STARTUP_FOLDER = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
DESTINO = STARTUP_FOLDER / "Jarvis.bat"

def instalar():
    if not BAT_FILE.exists():
        print(f"❌ No encontré el archivo: {BAT_FILE}")
        return

    shutil.copy(BAT_FILE, DESTINO)
    print(f"✅ Jarvis instalado en el inicio de Windows.")
    print(f"   Archivo copiado a: {DESTINO}")
    print()
    print("   La próxima vez que inicies sesión en Windows,")
    print("   Jarvis arrancará automáticamente y te dará los buenos días.")

def desinstalar():
    if DESTINO.exists():
        DESTINO.unlink()
        print("✅ Jarvis eliminado del inicio de Windows.")
    else:
        print("ℹ️  Jarvis no estaba en el inicio de Windows.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--desinstalar":
        desinstalar()
    else:
        instalar()
