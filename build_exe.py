"""
Script para crear ejecutable de Windows de Recon IA usando PyInstaller.

Uso:
    python build_exe.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# ============================================================
# CONFIGURACIÓN
# ============================================================

APP_NAME = "ReconIA"
MAIN_SCRIPT = "ui/app.py"
ICON_PATH = "assets/icon.ico"  # Opcional: crear un icono

# Archivos y carpetas a incluir
ADDITIONAL_DATA = [
    ("db/models.py", "db"),
    ("data", "data"),  # Base de datos vacía
    ("core", "core"),
    ("db", "db"),
    ("ui", "ui"),
    ("reports", "reports"),
]

# ============================================================
# HIDDEN IMPORTS (librerías que PyInstaller no detecta)
# ============================================================

HIDDEN_IMPORTS = [
    "streamlit",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "streamlit_webrtc",
    "av",
    "mediapipe",
    "cv2",
    "numpy",
    "pandas",
    "matplotlib",
    "reportlab",
    "PIL",
    "sqlite3",
]

# ============================================================
# FUNCIONES
# ============================================================

def check_dependencies():
    """Verifica que PyInstaller esté instalado."""
    try:
        import PyInstaller
        print("✅ PyInstaller instalado")
        return True
    except ImportError:
        print("❌ PyInstaller no encontrado")
        print("Instalando PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        return True


def clean_build_dirs():
    """Limpia directorios de build anteriores."""
    dirs_to_clean = ["build", "dist", "__pycache__"]
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"🧹 Limpiando {dir_name}/")
            shutil.rmtree(dir_name)
    
    # Limpiar archivos .spec
    for spec_file in Path(".").glob("*.spec"):
        print(f"🧹 Eliminando {spec_file}")
        spec_file.unlink()


def create_launcher_script():
    """Crea script de lanzamiento para Streamlit."""
    launcher_content = """
import sys
import os
import streamlit.web.cli as stcli

if __name__ == '__main__':
    # Configurar rutas
    if getattr(sys, 'frozen', False):
        # Ejecutando como ejecutable
        application_path = sys._MEIPASS
    else:
        # Ejecutando como script
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    os.chdir(application_path)
    
    # Lanzar Streamlit
    sys.argv = [
        "streamlit",
        "run",
        "ui/app.py",
        "--server.headless=true",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
    ]
    
    sys.exit(stcli.main())
"""
    
    with open("launcher.py", "w", encoding="utf-8") as f:
        f.write(launcher_content)
    
    print("✅ Launcher script creado")
    return "launcher.py"


def build_executable(launcher_script):
    """Construye el ejecutable con PyInstaller."""
    
    # Construir comando
    cmd = [
        "pyinstaller",
        "--name", APP_NAME,
        "--onefile",  # Un solo archivo
        "--windowed",  # Sin consola (comentar si quieres ver logs)
        "--clean",
        "--noconfirm",
    ]
    
    # Añadir icono si existe
    if os.path.exists(ICON_PATH):
        cmd.extend(["--icon", ICON_PATH])
    
    # Añadir hidden imports
    for imp in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", imp])
    
    # Añadir datos adicionales
    for src, dst in ADDITIONAL_DATA:
        if os.path.exists(src):
            cmd.extend(["--add-data", f"{src}{os.pathsep}{dst}"])
    
    # Script principal
    cmd.append(launcher_script)
    
    print("\n🔨 Construyendo ejecutable...")
    print(f"Comando: {' '.join(cmd)}\n")
    
    try:
        subprocess.check_call(cmd)
        print("\n✅ Ejecutable creado exitosamente!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error al crear ejecutable: {e}")
        return False


def create_installer_script():
    """Crea script .bat para lanzar el ejecutable."""
    bat_content = f"""@echo off
echo ================================================
echo        Iniciando Recon IA
echo ================================================
echo.
echo Abriendo navegador en http://localhost:8501
echo Presione Ctrl+C para cerrar la aplicacion
echo.

start http://localhost:8501

"{APP_NAME}.exe"

pause
"""
    
    bat_path = f"dist/{APP_NAME}_Launcher.bat"
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
    
    print(f"✅ Launcher batch creado: {bat_path}")


def main():
    """Función principal."""
    print("=" * 60)
    print("  RECON IA - BUILD EJECUTABLE WINDOWS")
    print("=" * 60)
    print()
    
    # 1. Verificar dependencias
    if not check_dependencies():
        return
    
    # 2. Limpiar builds anteriores
    clean_build_dirs()
    
    # 3. Crear launcher
    launcher = create_launcher_script()
    
    # 4. Construir ejecutable
    if not build_executable(launcher):
        return
    
    # 5. Crear launcher batch
    create_installer_script()
    
    # 6. Resumen
    print("\n" + "=" * 60)
    print("✅ BUILD COMPLETADO")
    print("=" * 60)
    print(f"\n📦 Ejecutable: dist/{APP_NAME}.exe")
    print(f"🚀 Launcher: dist/{APP_NAME}_Launcher.bat")
    print("\nPara distribuir:")
    print("  1. Copia la carpeta 'dist/' completa")
    print("  2. Ejecuta el .bat o el .exe directamente")
    print("\n⚠️  IMPORTANTE:")
    print("  - Primera ejecución puede tardar 10-30 segundos")
    print("  - Se abrirá el navegador automáticamente")
    print("  - La aplicación corre en http://localhost:8501")
    print()


if __name__ == "__main__":
    main()