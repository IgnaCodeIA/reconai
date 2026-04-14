"""
Script para crear ejecutable de Windows de Recon IA usando PyInstaller.
INCLUYE:
  - FFmpeg automáticamente
  - FIX archivos estáticos de Streamlit (index.html, JS, CSS)
  - FIX componentes frontend de streamlit-webrtc
  - FIX modelos .binarypb de MediaPipe
  - FIX metadatos de paquetes (PackageNotFoundError)

Uso:
    python build_exe.py
"""

import os
import sys
import subprocess
import shutil
import urllib.request
import zipfile
from pathlib import Path
import site
import time

# ============================================================
# CONFIGURACIÓN
# ============================================================

APP_NAME = "ReconIA"
MAIN_SCRIPT = "ui/app.py"
ICON_PATH = "assets/icon.ico"

# URL de FFmpeg para Windows (build estático)
FFMPEG_DOWNLOAD_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)
FFMPEG_DIR = "ffmpeg_bundle"

# Archivos y carpetas de la aplicación a incluir
ADDITIONAL_DATA = [
    ("data", "data"),
    ("core", "core"),
    ("db", "db"),
    ("ui", "ui"),
    ("reports", "reports"),
]

# ============================================================
# HIDDEN IMPORTS
# ============================================================

HIDDEN_IMPORTS = [
    "streamlit",
    "streamlit.runtime",
    "streamlit.runtime.scriptrunner",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "streamlit.web",
    "streamlit.web.cli",
    "streamlit.web.bootstrap",
    "streamlit_webrtc",
    "av",
    "av.audio",
    "av.video",
    "mediapipe",
    "cv2",
    "numpy",
    "pandas",
    "matplotlib",
    "matplotlib.backends",
    "matplotlib.backends.backend_pdf",
    "reportlab",
    "reportlab.pdfgen",
    "reportlab.lib",
    "PIL",
    "PIL.Image",
    "sqlite3",
    "altair",
    "pyarrow",
    "pydeck",
    "tornado",
    "tornado.web",
    "tornado.ioloop",
    "watchdog",
    "watchdog.observers",
    "click",
    "validators",
    "packaging",
    "packaging.version",
    "packaging.specifiers",
]

# ============================================================
# FUNCIONES
# ============================================================

def check_dependencies():
    """Verifica que PyInstaller esté instalado."""
    try:
        import PyInstaller
        print("OK PyInstaller instalado")
        return True
    except ImportError:
        print("PyInstaller no encontrado, instalando...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        return True


def get_streamlit_data_paths():
    """
    CRITICO: Localiza los archivos estaticos y componentes de Streamlit.
    Sin esto el ejecutable falla con:
      FileNotFoundError: streamlit\\static\\index.html
    Devuelve lista de tuplas (src, dst) para --add-data.
    """
    try:
        import streamlit
        streamlit_dir = Path(streamlit.__file__).parent
    except ImportError:
        print("ADVERTENCIA: No se puede importar streamlit para localizar assets")
        return []

    paths = []

    # 1. Archivos estaticos del frontend (index.html, JS, CSS, media)
    static_dir = streamlit_dir / "static"
    if static_dir.exists():
        paths.append((str(static_dir), "streamlit/static"))
        print(f"  OK Streamlit static: {static_dir}")
    else:
        print(f"  ADVERTENCIA: No se encontro streamlit/static en {streamlit_dir}")

    # 2. Componentes internos de Streamlit (algunos builds los necesitan)
    components_dir = streamlit_dir / "components"
    if components_dir.exists():
        paths.append((str(components_dir), "streamlit/components"))
        print(f"  OK Streamlit components: {components_dir}")

    # 3. Directorio runtime completo (por si hay assets adicionales)
    runtime_dir = streamlit_dir / "runtime"
    if runtime_dir.exists():
        paths.append((str(runtime_dir), "streamlit/runtime"))
        print(f"  OK Streamlit runtime: {runtime_dir}")

    return paths


def get_streamlit_webrtc_data_paths():
    """
    Localiza los assets del frontend de streamlit-webrtc.
    Sin esto el componente WebRTC no carga en el ejecutable.
    Devuelve lista de tuplas (src, dst) para --add-data.
    """
    try:
        import streamlit_webrtc
        webrtc_dir = Path(streamlit_webrtc.__file__).parent
    except ImportError:
        print("  ADVERTENCIA: streamlit_webrtc no disponible")
        return []

    paths = []

    # Buscar carpetas de frontend: frontend/, static/, component/
    for subdir_name in ["frontend", "static", "component"]:
        subdir = webrtc_dir / subdir_name
        if subdir.exists():
            paths.append((str(subdir), f"streamlit_webrtc/{subdir_name}"))
            print(f"  OK streamlit_webrtc/{subdir_name}: {subdir}")

    # Incluir el paquete completo como fallback
    paths.append((str(webrtc_dir), "streamlit_webrtc"))
    print(f"  OK streamlit_webrtc (paquete completo): {webrtc_dir}")

    return paths


def get_mediapipe_data_paths():
    """
    Localiza los modelos .binarypb y .tflite de MediaPipe.
    Sin esto MediaPipe falla al inicializar en el ejecutable.
    Devuelve lista de tuplas (src, dst) para --add-data.
    """
    try:
        import mediapipe
        mediapipe_dir = Path(mediapipe.__file__).parent
    except ImportError:
        print("  ADVERTENCIA: mediapipe no disponible")
        return []

    paths = []

    # Modelos de pose y otros modelos necesarios
    modules_dir = mediapipe_dir / "modules"
    if modules_dir.exists():
        paths.append((str(modules_dir), "mediapipe/modules"))
        print(f"  OK MediaPipe modules: {modules_dir}")

    # Python package completo (incluye .binarypb y datos)
    for subdir_name in ["python", "tasks"]:
        subdir = mediapipe_dir / subdir_name
        if subdir.exists():
            paths.append((str(subdir), f"mediapipe/{subdir_name}"))
            print(f"  OK MediaPipe {subdir_name}: {subdir}")

    return paths


def get_package_metadata_paths():
    """
    Obtiene rutas de metadatos de paquetes criticos.
    Resuelve: PackageNotFoundError: No package metadata was found for streamlit
    """
    site_packages = site.getsitepackages() or []
    try:
        site_packages.append(site.getusersitepackages())
    except Exception:
        pass

    critical_packages = [
        "streamlit", "altair", "blinker", "cachetools", "click",
        "gitpython", "numpy", "pandas", "pillow", "protobuf",
        "pyarrow", "pydeck", "requests", "rich", "toml", "tornado",
        "tzlocal", "validators", "watchdog", "packaging",
        "importlib_metadata", "streamlit_webrtc", "av", "mediapipe",
        "opencv-python", "reportlab", "matplotlib",
    ]

    metadata_paths = []
    for sp in site_packages:
        if not os.path.exists(sp):
            continue
        for pkg in critical_packages:
            for pattern in [
                f"{pkg}-*.dist-info",
                f"{pkg.replace('-', '_')}-*.dist-info",
            ]:
                for match in Path(sp).glob(pattern):
                    if match.is_dir():
                        metadata_paths.append((str(match), str(match.name)))
                        print(f"  OK Metadatos: {match.name}")

    return metadata_paths


def download_ffmpeg():
    """Descarga FFmpeg si no existe."""
    if os.path.exists(FFMPEG_DIR):
        ffmpeg_exe = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
        if os.path.exists(ffmpeg_exe):
            print(f"OK FFmpeg ya disponible en {FFMPEG_DIR}/")
            return True

    print("\nDescargando FFmpeg para Windows...")
    print(f"URL: {FFMPEG_DOWNLOAD_URL}")

    zip_path = "ffmpeg_temp.zip"

    try:
        def reporthook(blocknum, blocksize, totalsize):
            readsofar = blocknum * blocksize
            if totalsize > 0:
                percent = min(readsofar * 100 / totalsize, 100)
                sys.stderr.write(f"\r  {percent:5.1f}% ({readsofar:,} / {totalsize:,} bytes)")
                if readsofar >= totalsize:
                    sys.stderr.write("\n")

        urllib.request.urlretrieve(FFMPEG_DOWNLOAD_URL, zip_path, reporthook)

        print("Extrayendo FFmpeg...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall("ffmpeg_extract_temp")

        # Localizar carpeta bin dentro del zip extraido
        extracted_dir = None
        for item in os.listdir("ffmpeg_extract_temp"):
            if item.lower().startswith("ffmpeg"):
                extracted_dir = os.path.join("ffmpeg_extract_temp", item)
                break

        if not extracted_dir:
            raise RuntimeError("No se encontro directorio ffmpeg en el zip")

        bin_dir = os.path.join(extracted_dir, "bin")
        if not os.path.exists(bin_dir):
            raise RuntimeError(f"No se encontro carpeta bin en {extracted_dir}")

        os.makedirs(FFMPEG_DIR, exist_ok=True)
        for exe in ["ffmpeg.exe", "ffprobe.exe"]:
            src = os.path.join(bin_dir, exe)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(FFMPEG_DIR, exe))
                print(f"  OK Copiado: {exe}")

        os.remove(zip_path)
        shutil.rmtree("ffmpeg_extract_temp")

        print(f"OK FFmpeg instalado en {FFMPEG_DIR}/")
        return True

    except Exception as e:
        print(f"\nError descargando FFmpeg: {e}")
        print("Descarga manual: https://ffmpeg.org/download.html")
        # Limpiar restos
        for path in [zip_path, "ffmpeg_extract_temp"]:
            if os.path.exists(path):
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                    else:
                        shutil.rmtree(path)
                except Exception:
                    pass
        return False


def clean_build_dirs():
    """Limpia directorios de build anteriores."""
    for dir_name in ["build", "dist", "__pycache__"]:
        if os.path.exists(dir_name):
            print(f"Limpiando {dir_name}/")
            for attempt in range(3):
                try:
                    shutil.rmtree(dir_name)
                    break
                except PermissionError:
                    if attempt < 2:
                        print(f"  {dir_name}/ en uso, esperando... (cierra ReconIA.exe si esta corriendo)")
                        time.sleep(2)
                    else:
                        print(f"No se pudo eliminar {dir_name}/ automaticamente.")
                        print("Cierra ReconIA.exe manualmente y presiona Enter...")
                        input()
                        shutil.rmtree(dir_name)

    for spec_file in Path(".").glob("*.spec"):
        print(f"Eliminando {spec_file}")
        spec_file.unlink()


def create_launcher_script():
    """
    Crea el script de entrada para PyInstaller.
    Configura PATH de FFmpeg, directorio de trabajo y lanza Streamlit.
    """
    launcher_content = '''import sys
import os

if getattr(sys, "frozen", False):
    # _MEIPASS: carpeta temporal donde PyInstaller extrae TODO el bundle
    # Aqui viven ui/app.py, streamlit, mediapipe, ffmpeg_bundle, etc.
    application_path = sys._MEIPASS
    # exe_dir: carpeta donde esta el .exe fisicamente
    # Aqui deben guardarse BD, videos grabados y exports (datos persistentes)
    exe_dir = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
    exe_dir = application_path

# Exponer exe_dir para que init_db.py y session_manager.py
# sepan donde guardar la BD y los videos (junto al .exe, no en _MEIPASS)
os.environ["RECON_IA_DATA_DIR"] = exe_dir

# CRITICO: chdir a _MEIPASS para que "ui/app.py" sea una ruta relativa valida.
# Streamlit run acepta rutas relativas al CWD.
os.chdir(application_path)

# Anadir FFmpeg al PATH
ffmpeg_path = os.path.join(application_path, "ffmpeg_bundle")
if os.path.exists(ffmpeg_path):
    os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ.get("PATH", "")

if application_path not in sys.path:
    sys.path.insert(0, application_path)

import streamlit.web.cli as stcli

if __name__ == "__main__":
    # Ruta relativa al CWD (= application_path = _MEIPASS): funciona correctamente
    sys.argv = [
        "streamlit",
        "run",
        "ui/app.py",
        "--server.headless=true",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())
'''

    with open("launcher.py", "w", encoding="utf-8") as f:
        f.write(launcher_content)

    print("OK Launcher script creado")
    return "launcher.py"


def build_executable(launcher_script):
    """Construye el ejecutable con PyInstaller."""

    # ---- Recopilar todos los --add-data ----
    print("\nLocalizando assets de Streamlit...")
    streamlit_paths = get_streamlit_data_paths()

    print("\nLocalizando assets de streamlit-webrtc...")
    webrtc_paths = get_streamlit_webrtc_data_paths()

    print("\nLocalizando modelos de MediaPipe...")
    mediapipe_paths = get_mediapipe_data_paths()

    print("\nLocalizando metadatos de paquetes...")
    metadata_paths = get_package_metadata_paths()

    if not streamlit_paths:
        print("\nERROR: No se encontraron archivos estaticos de Streamlit.")
        print("Asegurate de que streamlit esta instalado en este entorno Python.")
        return False

    # ---- Construir comando ----
    cmd = [
        "pyinstaller",
        "--name", APP_NAME,
        "--onefile",
        "--console",
        "--clean",
        "--noconfirm",
    ]

    if os.path.exists(ICON_PATH):
        cmd.extend(["--icon", ICON_PATH])

    for imp in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", imp])

    # Datos de la aplicacion
    for src, dst in ADDITIONAL_DATA:
        if os.path.exists(src):
            cmd.extend(["--add-data", f"{src}{os.pathsep}{dst}"])
        else:
            print(f"  ADVERTENCIA: No existe {src}, se omite")

    # Assets criticos
    for src, dst in streamlit_paths:
        cmd.extend(["--add-data", f"{src}{os.pathsep}{dst}"])

    for src, dst in webrtc_paths:
        cmd.extend(["--add-data", f"{src}{os.pathsep}{dst}"])

    for src, dst in mediapipe_paths:
        cmd.extend(["--add-data", f"{src}{os.pathsep}{dst}"])

    for src, dst in metadata_paths:
        cmd.extend(["--add-data", f"{src}{os.pathsep}{dst}"])

    # FFmpeg
    if os.path.exists(FFMPEG_DIR):
        cmd.extend(["--add-data", f"{FFMPEG_DIR}{os.pathsep}ffmpeg_bundle"])
        print(f"\nOK FFmpeg incluido desde {FFMPEG_DIR}/")
    else:
        print("\nADVERTENCIA: FFmpeg no encontrado, el video puede no funcionar")

    cmd.append(launcher_script)

    print(f"\nConstruyendo ejecutable ({len(cmd)} argumentos)...")

    try:
        subprocess.check_call(cmd)
        print("\nOK Ejecutable creado exitosamente!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\nError al crear ejecutable: {e}")
        return False


def create_launcher_bat():
    """Crea script .bat para lanzar el ejecutable sin consola visible."""
    # Script .vbs para lanzar sin ventana de consola (solucion anterior ya aplicada)
    vbs_content = f"""Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "{APP_NAME}.exe", 0, False
WScript.Sleep 3000
WshShell.Run "http://localhost:8501"
"""
    vbs_path = f"dist/{APP_NAME}_Launcher.vbs"
    with open(vbs_path, "w", encoding="utf-8") as f:
        f.write(vbs_content)
    print(f"OK Launcher VBS creado: {vbs_path}")

    # .bat como alternativa (muestra consola)
    bat_content = f"""@echo off
echo Iniciando Recon IA...
start http://localhost:8501
{APP_NAME}.exe
pause
"""
    bat_path = f"dist/{APP_NAME}_Launcher.bat"
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
    print(f"OK Launcher BAT creado: {bat_path}")


def create_readme():
    """Crea README con instrucciones."""
    readme_content = """RECON IA - INSTRUCCIONES DE USO
================================

CONTENIDO DEL PAQUETE:
  ReconIA.exe                Aplicacion principal
  ReconIA_Launcher.vbs       Lanzador sin consola (recomendado)
  ReconIA_Launcher.bat       Lanzador con consola (para diagnostico)
  data/                      Base de datos y exportaciones

INSTALACION:
  1. Copia toda la carpeta a tu disco (ej: C:\\ReconIA)
  2. No separes los archivos del ejecutable

USO NORMAL:
  - Doble clic en ReconIA_Launcher.vbs
  - Se abrira el navegador en http://localhost:8501 automaticamente

PRIMERA EJECUCION:
  - Puede tardar 15-30 segundos en cargar
  - Windows puede mostrar aviso de seguridad -> clic en "Ejecutar de todas formas"
  - Si el navegador no abre: escribe manualmente http://localhost:8501

REQUISITOS:
  - Windows 10 / 11  (64-bit)
  - Webcam (para captura en directo)
  - Permisos de camara habilitados en el navegador
  - 2 GB RAM minimo

PROBLEMAS COMUNES:
  - Puerto ocupado: cierra otras instancias de la app
  - Error de camara: verifica permisos en Configuracion de Windows
  - Para diagnostico: usa ReconIA_Launcher.bat (muestra errores en consola)

FFmpeg: incluido
"""
    with open("dist/README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("OK README creado: dist/README.txt")


def main():
    print("=" * 60)
    print("  RECON IA - BUILD EJECUTABLE WINDOWS")
    print("  Fix: Streamlit static + WebRTC + MediaPipe + FFmpeg")
    print("=" * 60)
    print()

    if not check_dependencies():
        return

    if not download_ffmpeg():
        print("\nADVERTENCIA: Sin FFmpeg. Presiona Enter para continuar o Ctrl+C para cancelar.")
        input()

    clean_build_dirs()

    launcher = create_launcher_script()

    if not build_executable(launcher):
        return

    create_launcher_bat()
    create_readme()

    print()
    print("=" * 60)
    print("  BUILD COMPLETADO")
    print("=" * 60)
    print(f"  Ejecutable : dist/{APP_NAME}.exe")
    print(f"  Launcher   : dist/{APP_NAME}_Launcher.vbs")
    print(f"  README     : dist/README.txt")
    print()
    print("Para distribuir: copia la carpeta dist/ completa al cliente")
    print()


if __name__ == "__main__":
    main()