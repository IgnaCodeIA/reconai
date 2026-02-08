"""
Validador de archivos multimedia para Recon IA.
Verifica que videos e imágenes sean procesables antes de subirlos.
"""

import cv2
import hashlib
from pathlib import Path
from typing import Tuple, Dict, Any
import mimetypes


class FileValidator:
    
    ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mpeg', '.mpg', '.m4v', '.mkv'}
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    
    MAX_VIDEO_SIZE_MB = 500
    MAX_IMAGE_SIZE_MB = 10
    
    MIN_VIDEO_WIDTH = 320
    MIN_VIDEO_HEIGHT = 240
    MIN_IMAGE_WIDTH = 320
    MIN_IMAGE_HEIGHT = 240
    
    @staticmethod
    def validate_video(file_path: str | Path) -> Tuple[bool, str, Dict[str, Any]]:
        path = Path(file_path)
        
        if not path.exists():
            return False, f"Archivo no encontrado: {path}", {}
        
        if path.suffix.lower() not in FileValidator.ALLOWED_VIDEO_EXTENSIONS:
            return False, f"Extensión no permitida: {path.suffix}. Permitidas: {', '.join(FileValidator.ALLOWED_VIDEO_EXTENSIONS)}", {}
        
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > FileValidator.MAX_VIDEO_SIZE_MB:
            return False, f"Archivo muy grande: {size_mb:.1f}MB (máximo: {FileValidator.MAX_VIDEO_SIZE_MB}MB)", {}
        
        if size_mb == 0:
            return False, "Archivo vacío (0 bytes)", {}
        
        try:
            cap = cv2.VideoCapture(str(path))
            
            if not cap.isOpened():
                return False, "No se puede abrir el archivo como video. Puede estar corrupto o usar un codec no soportado.", {}
            
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            duration_sec = 0
            if fps > 0 and frame_count > 0:
                duration_sec = int(frame_count / fps)
            
            fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
            codec = "unknown"
            if fourcc_int > 0:
                codec = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)])
            
            cap.release()
            
            metadata = {
                'width': width,
                'height': height,
                'fps': round(fps, 2),
                'frame_count': frame_count,
                'duration_sec': duration_sec,
                'size_mb': round(size_mb, 2),
                'codec': codec
            }
            
            if width == 0 or height == 0:
                return False, "Video sin dimensiones válidas", metadata
            
            if width < FileValidator.MIN_VIDEO_WIDTH or height < FileValidator.MIN_VIDEO_HEIGHT:
                return False, f"Resolución muy baja: {width}x{height} (mínimo: {FileValidator.MIN_VIDEO_WIDTH}x{FileValidator.MIN_VIDEO_HEIGHT})", metadata
            
            if fps == 0 or fps > 1000:
                return False, f"FPS inválidos: {fps}", metadata
            
            if frame_count == 0:
                return False, "Video sin frames", metadata
            
            if duration_sec == 0:
                return False, "Video con duración 0 segundos", metadata
            
            return True, "Video válido", metadata
            
        except Exception as e:
            return False, f"Error al procesar video: {str(e)}", {}
    
    @staticmethod
    def validate_image(file_path: str | Path) -> Tuple[bool, str, Dict[str, Any]]:
        path = Path(file_path)
        
        if not path.exists():
            return False, f"Archivo no encontrado: {path}", {}
        
        if path.suffix.lower() not in FileValidator.ALLOWED_IMAGE_EXTENSIONS:
            return False, f"Extensión no permitida: {path.suffix}. Permitidas: {', '.join(FileValidator.ALLOWED_IMAGE_EXTENSIONS)}", {}
        
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > FileValidator.MAX_IMAGE_SIZE_MB:
            return False, f"Archivo muy grande: {size_mb:.1f}MB (máximo: {FileValidator.MAX_IMAGE_SIZE_MB}MB)", {}
        
        if size_mb == 0:
            return False, "Archivo vacío (0 bytes)", {}
        
        try:
            img = cv2.imread(str(path))
            
            if img is None:
                return False, "No se puede leer el archivo como imagen. Puede estar corrupto.", {}
            
            height, width = img.shape[:2]
            channels = img.shape[2] if len(img.shape) == 3 else 1
            
            mime_type, _ = mimetypes.guess_type(str(path))
            img_format = mime_type.split('/')[-1] if mime_type else path.suffix[1:]
            
            metadata = {
                'width': width,
                'height': height,
                'channels': channels,
                'size_mb': round(size_mb, 2),
                'format': img_format
            }
            
            if width == 0 or height == 0:
                return False, "Imagen sin dimensiones válidas", metadata
            
            if width < FileValidator.MIN_IMAGE_WIDTH or height < FileValidator.MIN_IMAGE_HEIGHT:
                return False, f"Resolución muy baja: {width}x{height} (mínimo: {FileValidator.MIN_IMAGE_WIDTH}x{FileValidator.MIN_IMAGE_HEIGHT})", metadata
            
            if channels not in [1, 3, 4]:
                return False, f"Número de canales inválido: {channels}", metadata
            
            return True, "Imagen válida", metadata
            
        except Exception as e:
            return False, f"Error al procesar imagen: {str(e)}", {}
    
    @staticmethod
    def calculate_hash(file_path: str | Path) -> str:
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    @staticmethod
    def get_file_type(file_path: str | Path) -> str:
        path = Path(file_path)
        ext = path.suffix.lower()
        
        if ext in FileValidator.ALLOWED_VIDEO_EXTENSIONS:
            return 'video'
        elif ext in FileValidator.ALLOWED_IMAGE_EXTENSIONS:
            return 'image'
        else:
            return 'unknown'