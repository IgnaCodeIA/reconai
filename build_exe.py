"""
Script para crear ejecutable de Windows de Recon IA usando PyInstaller.
INCLUYE FFmpeg automáticamente + FIX para metadatos de Streamlit.

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
ICON_PATH = "assets/icon.ico"  # Opcional: crear un icono

# URL de FFmpeg para Windows (build estático)
FFMPEG_DOWNLOAD_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
FFMPEG_DIR = "ffmpeg_bundle"

# Archivos y carpetas a incluir
ADDITIONAL_DATA = [
    ("db/models.py", "db"),
    ("data", "data"),
    ("core", "core"),
    ("db", "db"),
    ("ui", "ui"),
    ("reports", "reports"),
]

# ============================================================
# HIDDEN IMPORTS (AMPLIADOS)
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
        print("✅ PyInstaller instalado")
        return True
    except ImportError:
        print("❌ PyInstaller no encontrado")
        print("Instalando PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        return True


def get_package_metadata_paths():
    """
    Obtiene las rutas de metadatos de paquetes críticos.
    Esto resuelve el error: PackageNotFoundError: No package metadata was found for streamlit
    """
    site_packages = site.getsitepackages()
    if not site_packages:
        # Fallback para entornos virtuales
        site_packages = [site.getusersitepackages()]
    
    metadata_paths = []
    critical_packages = [
        "streamlit",
        "altair",
        "blinker",
        "cachetools",
        "click",
        "gitpython",
        "numpy",
        "pandas",
        "pillow",
        "protobuf",
        "pyarrow",
        "pydeck",
        "requests",
        "rich",
        "toml",
        "tornado",
        "tzlocal",
        "validators",
        "watchdog",
        "packaging",
        "importlib_metadata",
    ]
    
    for sp in site_packages:
        if not os.path.exists(sp):
            continue
        
        for pkg in critical_packages:
            # Buscar .dist-info
            for pattern in [f"{pkg}-*.dist-info", f"{pkg.replace('-', '_')}-*.dist-info"]:
                matches = list(Path(sp).glob(pattern))
                for match in matches:
                    if match.is_dir():
                        # PyInstaller espera formato (src, dst)
                        # dst es la raíz donde se copiarán los metadatos
                        metadata_paths.append((str(match), str(match.name)))
                        print(f"  📦 Metadatos encontrados: {match.name}")
    
    return metadata_paths


def download_ffmpeg():
    """Descarga FFmpeg si no existe."""
    
    if os.path.exists(FFMPEG_DIR):
        print(f"✅ FFmpeg ya descargado en {FFMPEG_DIR}/")
        return True
    
    print("\n📦 Descargando FFmpeg...")
    print(f"URL: {FFMPEG_DOWNLOAD_URL}")
    
    zip_path = "ffmpeg.zip"
    
    try:
        # Descargar con barra de progreso
        def reporthook(blocknum, blocksize, totalsize):
            readsofar = blocknum * blocksize
            if totalsize > 0:
                percent = readsofar * 100 / totalsize
                s = f"\r{percent:5.1f}% {readsofar:,} / {totalsize:,} bytes"
                sys.stderr.write(s)
                if readsofar >= totalsize:
                    sys.stderr.write("\n")
            else:
                sys.stderr.write(f"\rLeído {readsofar:,} bytes")
        
        urllib.request.urlretrieve(FFMPEG_DOWNLOAD_URL, zip_path, reporthook)
        
        print("\n📂 Extrayendo FFmpeg...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall("ffmpeg_temp")
        
        # Mover archivos a ubicación final
        extracted_dir = None
        for item in os.listdir("ffmpeg_temp"):
            if item.startswith("ffmpeg"):
                extracted_dir = os.path.join("ffmpeg_temp", item)
                break
        
        if not extracted_dir:
            raise Exception("No se encontró directorio de FFmpeg en el zip")
        
        bin_dir = os.path.join(extracted_dir, "bin")
        if not os.path.exists(bin_dir):
            raise Exception(f"No se encontró carpeta bin en {extracted_dir}")
        
        # Crear directorio de destino
        os.makedirs(FFMPEG_DIR, exist_ok=True)
        
        # Copiar solo los ejecutables necesarios
        for exe in ["ffmpeg.exe", "ffprobe.exe"]:
            src = os.path.join(bin_dir, exe)
            dst = os.path.join(FFMPEG_DIR, exe)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"  ✅ Copiado: {exe}")
        
        # Limpiar
        os.remove(zip_path)
        shutil.rmtree("ffmpeg_temp")
        
        print(f"✅ FFmpeg instalado en {FFMPEG_DIR}/")
        return True
        
    except Exception as e:
        print(f"\n❌ Error descargando FFmpeg: {e}")
        print("Puedes descargarlo manualmente de: https://ffmpeg.org/download.html")
        return False


def clean_build_dirs():
    """Limpia directorios de build anteriores con manejo de errores."""
    dirs_to_clean = ["build", "dist", "__pycache__"]
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"🧹 Limpiando {dir_name}/")
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    shutil.rmtree(dir_name)
                    break
                except PermissionError:
                    if attempt < max_retries - 1:
                        print(f"⚠️  {dir_name}/ en uso, esperando 2 segundos...")
                        print(f"    (Cierra ReconIA.exe si está corriendo)")
                        time.sleep(2)
                    else:
                        print(f"❌ No se pudo eliminar {dir_name}/")
                        print(f"    SOLUCIÓN: Cierra manualmente ReconIA.exe y el explorador")
                        print(f"    Luego presiona Enter para continuar...")
                        input()
                        shutil.rmtree(dir_name)
    
    # Limpiar archivos .spec
    for spec_file in Path(".").glob("*.spec"):
        print(f"🧹 Eliminando {spec_file}")
        spec_file.unlink()


def create_launcher_script():
    """Crea script de lanzamiento para Streamlit con FFmpeg en PATH."""
    launcher_content = """import sys
import os

# CRÍTICO: Configurar metadatos ANTES de importar streamlit
if getattr(sys, 'frozen', False):
    # Ejecutando como ejecutable empaquetado
    application_path = sys._MEIPASS
    
    # Añadir ruta de metadatos al path de importlib
    sys.path.insert(0, application_path)
    
    # Variable de entorno para importlib_metadata
    os.environ['IMPORTLIB_METADATA_PATH'] = application_path
else:
    # Ejecutando como script normal
    application_path = os.path.dirname(os.path.abspath(__file__))

# IMPORTANTE: Añadir FFmpeg al PATH
ffmpeg_path = os.path.join(application_path, 'ffmpeg_bundle')
if os.path.exists(ffmpeg_path):
    os.environ['PATH'] = ffmpeg_path + os.pathsep + os.environ.get('PATH', '')
    print(f"✅ FFmpeg añadido al PATH: {ffmpeg_path}")
else:
    print(f"⚠️  FFmpeg no encontrado en: {ffmpeg_path}")

os.chdir(application_path)

# Ahora sí, importar streamlit
import streamlit.web.cli as stcli

if __name__ == '__main__':
    # Lanzar Streamlit
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
"""
    
    with open("launcher.py", "w", encoding="utf-8") as f:
        f.write(launcher_content)
    
    print("✅ Launcher script creado (con fix de metadatos + developmentMode)")
    return "launcher.py"


def build_executable(launcher_script):
    """Construye el ejecutable con PyInstaller."""
    
    print("\n🔍 Buscando metadatos de paquetes...")
    metadata_paths = get_package_metadata_paths()
    
    if not metadata_paths:
        print("⚠️  No se encontraron metadatos (puede causar problemas)")
    
    # Construir comando
    cmd = [
        "pyinstaller",
        "--name", APP_NAME,
        "--onefile",
        "--console", 
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
    
    # CRÍTICO: Añadir metadatos de paquetes
    for src, dst in metadata_paths:
        cmd.extend(["--add-data", f"{src}{os.pathsep}{dst}"])
    
    # CRÍTICO: Añadir FFmpeg
    if os.path.exists(FFMPEG_DIR):
        cmd.extend(["--add-data", f"{FFMPEG_DIR}{os.pathsep}ffmpeg_bundle"])
        print(f"✅ FFmpeg incluido en el ejecutable")
    
    # Script principal
    cmd.append(launcher_script)
    
    print("\n🔨 Construyendo ejecutable...")
    print(f"Comando: {' '.join(cmd[:10])}... (truncado)")
    print(f"Total de argumentos: {len(cmd)}")
    
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

{APP_NAME}.exe

pause
"""
    
    bat_path = f"dist/{APP_NAME}_Launcher.bat"
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
    
    print(f"✅ Launcher batch creado: {bat_path}")


def create_readme():
    """Crea README con instrucciones."""
    readme_content = """
RECON IA - INSTRUCCIONES DE USO
================================

CONTENIDO DEL PAQUETE:
- ReconIA.exe          (Aplicación principal)
- ReconIA_Launcher.bat (Lanzador recomendado)
- data/                (Base de datos)

INSTALACIÓN:
1. Copia toda la carpeta a tu disco (ej: C:\\ReconIA)
2. NO separes los archivos

USO:
- Doble clic en "ReconIA_Launcher.bat"
- O ejecuta directamente "ReconIA.exe"
- Se abrirá el navegador automáticamente en http://localhost:8501

PRIMERA EJECUCIÓN:
- Puede tardar 10-30 segundos en cargar
- Windows puede mostrar advertencia de seguridad (es normal)
- Click en "Más información" → "Ejecutar de todas formas"

PROBLEMAS COMUNES:
- Si no se abre el navegador: abre manualmente http://localhost:8501
- Si sale error de puerto ocupado: cierra otras instancias de la app
- Si no carga el video: verifica permisos de cámara en Windows

REQUISITOS:
- Windows 10/11 64-bit
- Webcam (para captura en vivo)
- 2GB RAM mínimo
- Permisos de cámara habilitados

SOPORTE:
- Email: [tu-email]
- Logs: ver ventana de consola si ejecutas el .exe directamente

FFmpeg incluido: ✅
Versión: [fecha de build]
"""
    
    readme_path = "dist/README.txt"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print(f"✅ README creado: {readme_path}")


def main():
    """Función principal."""
    print("=" * 60)
    print("  RECON IA - BUILD EJECUTABLE WINDOWS CON FFMPEG")
    print("  + FIX METADATOS STREAMLIT")
    print("=" * 60)
    print()
    
    # 1. Verificar dependencias
    if not check_dependencies():
        return
    
    # 2. Descargar FFmpeg
    if not download_ffmpeg():
        print("\n⚠️  Continuando sin FFmpeg (puede haber problemas de video)")
        input("Presiona Enter para continuar o Ctrl+C para cancelar...")
    
    # 3. Limpiar builds anteriores
    clean_build_dirs()
    
    # 4. Crear launcher
    launcher = create_launcher_script()
    
    # 5. Construir ejecutable
    if not build_executable(launcher):
        return
    
    # 6. Crear launcher batch y README
    create_installer_script()
    create_readme()
    
    # 7. Resumen
    print("\n" + "=" * 60)
    print("✅ BUILD COMPLETADO CON FFMPEG + FIX METADATOS")
    print("=" * 60)
    print(f"\n📦 Ejecutable: dist/{APP_NAME}.exe")
    print(f"🚀 Launcher: dist/{APP_NAME}_Launcher.bat")
    print(f"📄 README: dist/README.txt")
    print(f"🎬 FFmpeg: Incluido en el ejecutable")
    print(f"📋 Metadatos: Incluidos (fix para Streamlit)")
    print("\nPara distribuir:")
    print("  1. Copia la carpeta 'dist/' completa")
    print("  2. Ejecuta el .bat o el .exe directamente")
    print("\n⚠️  IMPORTANTE:")
    print("  - Primera ejecución: 10-30 segundos")
    print("  - FFmpeg está incluido y configurado")
    print("  - Navegador se abre automáticamente")
    print()

    
if __name__ == "__main__":
    main()