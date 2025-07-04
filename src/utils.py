import os
import sys
import platform
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import tempfile
import shutil

logger = logging.getLogger(__name__)

def get_launcher_dir() -> Path:
    """
    Get the launcher directory based on the operating system.
    Now supports Windows, macOS, and Linux.
    """
    system = platform.system().lower()
    
    if system == 'windows':
        appdata = os.environ.get('APPDATA')
        if not appdata:
            raise EnvironmentError('APPDATA environment variable not found.')
        return Path(appdata) / 'InnLab3Launcher'
    
    elif system == 'darwin':  # macOS
        home = Path.home()
        return home / 'Library' / 'Application Support' / 'InnLab3Launcher'
    
    elif system == 'linux':
        # Follow XDG Base Directory Specification
        xdg_data_home = os.environ.get('XDG_DATA_HOME')
        if xdg_data_home:
            return Path(xdg_data_home) / 'InnLab3Launcher'
        else:
            return Path.home() / '.local' / 'share' / 'InnLab3Launcher'
    
    else:
        raise NotImplementedError(f'Unsupported operating system: {system}')

def get_minecraft_dir() -> Path:
    """Get the default Minecraft directory for the current OS."""
    system = platform.system().lower()
    
    if system == 'windows':
        appdata = os.environ.get('APPDATA')
        if appdata:
            return Path(appdata) / '.minecraft'
    elif system == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'minecraft'
    elif system == 'linux':
        return Path.home() / '.minecraft'
    
    # Fallback to current directory
    return Path.cwd() / 'minecraft'

def get_java_executable() -> Optional[str]:
    """Find Java executable on the system."""
    # Try java command first
    try:
        result = subprocess.run(['java', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return 'java'
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Try common Java installation paths
    system = platform.system().lower()
    java_paths = []
    
    if system == 'windows':
        java_paths = [
            r'C:\Program Files\Java\jre*\bin\java.exe',
            r'C:\Program Files (x86)\Java\jre*\bin\java.exe',
            r'C:\Program Files\Eclipse Adoptium\jdk*\bin\java.exe',
            r'C:\Program Files\OpenJDK\jdk*\bin\java.exe'
        ]
    elif system == 'darwin':
        java_paths = [
            '/usr/bin/java',
            '/Library/Java/JavaVirtualMachines/*/Contents/Home/bin/java',
            '/System/Library/Java/JavaVirtualMachines/*/Contents/Home/bin/java'
        ]
    elif system == 'linux':
        java_paths = [
            '/usr/bin/java',
            '/usr/lib/jvm/*/bin/java',
            '/opt/java/*/bin/java'
        ]
    
    import glob
    for pattern in java_paths:
        matches = glob.glob(pattern)
        if matches:
            # Test the first match
            java_path = matches[0]
            try:
                result = subprocess.run([java_path, '-version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return java_path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
    
    return None

def get_system_info() -> Dict[str, Any]:
    """Get comprehensive system information."""
    return {
        'platform': platform.platform(),
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'python_version': platform.python_version(),
        'java_path': get_java_executable(),
        'launcher_dir': str(get_launcher_dir()),
        'minecraft_dir': str(get_minecraft_dir())
    }

def ensure_directory(path: Path) -> bool:
    """Ensure a directory exists, create if it doesn't."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False

def safe_file_operation(operation: callable, *args, **kwargs) -> bool:
    """Safely perform file operations with error handling."""
    try:
        operation(*args, **kwargs)
        return True
    except Exception as e:
        logger.error(f"File operation failed: {e}")
        return False

def get_available_memory() -> int:
    """Get available system memory in GB."""
    try:
        import psutil
        memory = psutil.virtual_memory()
        return int(memory.total / (1024**3))  # Convert to GB
    except ImportError:
        logger.warning("psutil not available, using fallback memory detection")
        # Fallback method
        system = platform.system().lower()
        if system == 'windows':
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                c_ulong = ctypes.c_ulong
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ('dwLength', c_ulong),
                        ('dwMemoryLoad', c_ulong),
                        ('ullTotalPhys', ctypes.c_ulonglong),
                        ('ullAvailPhys', ctypes.c_ulonglong),
                        ('ullTotalPageFile', ctypes.c_ulonglong),
                        ('ullAvailPageFile', ctypes.c_ulonglong),
                        ('ullTotalVirtual', ctypes.c_ulonglong),
                        ('ullAvailVirtual', ctypes.c_ulonglong),
                        ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
                    ]
                
                memoryStatus = MEMORYSTATUSEX()
                memoryStatus.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                kernel32.GlobalMemoryStatusEx(ctypes.byref(memoryStatus))
                return int(memoryStatus.ullTotalPhys / (1024**3))
            except Exception:
                pass
        
        # Default fallback
        return 8

def validate_minecraft_version(version: str) -> bool:
    """Validate if a Minecraft version string is properly formatted."""
    import re
    # Pattern for Minecraft versions like 1.20.1, 1.19.4, etc.
    pattern = r'^\d+\.\d+(\.\d+)?

    return bool(re.match(pattern, version))

def clean_filename(filename: str) -> str:
    """Clean a filename to be safe for the filesystem."""
    import re
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    return filename

def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def is_admin() -> bool:
    """Check if the current process has administrator privileges."""
    system = platform.system().lower()
    
    if system == 'windows':
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.geteuid() == 0

def open_file_manager(path: Path):
    """Open the file manager at the specified path."""
    system = platform.system().lower()
    
    try:
        if system == 'windows':
            os.startfile(str(path))
        elif system == 'darwin':
            subprocess.run(['open', str(path)])
        elif system == 'linux':
            subprocess.run(['xdg-open', str(path)])
        else:
            logger.warning(f"Cannot open file manager on {system}")
    except Exception as e:
        logger.error(f"Failed to open file manager: {e}")

def create_backup(source: Path, backup_dir: Path, name: str = None) -> Optional[Path]:
    """Create a backup of a file or directory."""
    try:
        if not source.exists():
            logger.error(f"Source path does not exist: {source}")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = name or f"{source.name}_{timestamp}"
        backup_path = backup_dir / backup_name
        
        ensure_directory(backup_dir)
        
        if source.is_file():
            shutil.copy2(source, backup_path)
        else:
            shutil.copytree(source, backup_path)
        
        logger.info(f"Backup created: {backup_path}")
        return backup_path
        
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return None

# Legacy function for backward compatibility
def get_launcher_dir_legacy():
    """Legacy function that returns string path."""
    return str(get_launcher_dir())
