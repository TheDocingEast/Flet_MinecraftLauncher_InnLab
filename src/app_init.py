"""
Application initialization module for InnLab³ Launcher.
Handles initial setup, directory creation, and environment validation.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from utils import get_launcher_dir, ensure_directory, get_system_info, get_java_executable
from updater import UpdateManager

logger = logging.getLogger(__name__)

class LauncherInitializer:
    """Handles launcher initialization and setup."""
    
    def __init__(self):
        self.launcher_dir = get_launcher_dir()
        self.required_dirs = [
            'minecraft',
            'modpacks',
            'backups',
            'cache',
            'logs'
        ]
        self.system_info = get_system_info()
    
    def ensure_launcher_directories(self) -> bool:
        """Create all required launcher directories."""
        try:
            # Create main launcher directory
            if not ensure_directory(self.launcher_dir):
                logger.error(f"Failed to create launcher directory: {self.launcher_dir}")
                return False
            
            logger.info(f"Launcher directory: {self.launcher_dir}")
            
            # Create subdirectories
            for dir_name in self.required_dirs:
                dir_path = self.launcher_dir / dir_name
                if not ensure_directory(dir_path):
                    logger.error(f"Failed to create directory: {dir_path}")
                    return False
                logger.debug(f"Directory ensured: {dir_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating launcher directories: {e}")
            return False
    
    def validate_system_requirements(self) -> Dict[str, Any]:
        """Validate system requirements for running the launcher."""
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'info': {}
        }
        
        try:
            # Check Python version
            python_version = sys.version_info
            if python_version < (3, 8):
                validation_result['errors'].append(
                    f"Python 3.8+ required, found {python_version.major}.{python_version.minor}"
                )
                validation_result['valid'] = False
            else:
                validation_result['info']['python_version'] = f"{python_version.major}.{python_version.minor}.{python_version.micro}"
            
            # Check Java installation
            java_path = get_java_executable()
            if not java_path:
                validation_result['warnings'].append(
                    "Java not found. Please install Java 8+ for Minecraft to work."
                )
            else:
                validation_result['info']['java_path'] = java_path
            
            # Check available disk space
            try:
                import shutil
                total, used, free = shutil.disk_usage(self.launcher_dir)
                free_gb = free // (1024**3)
                
                if free_gb < 2:
                    validation_result['errors'].append(
                        f"Insufficient disk space. At least 2GB required, {free_gb}GB available."
                    )
                    validation_result['valid'] = False
                elif free_gb < 5:
                    validation_result['warnings'].append(
                        f"Low disk space: {free_gb}GB available. Consider freeing up space."
                    )
                
                validation_result['info']['free_space_gb'] = free_gb
                
            except Exception as e:
                logger.warning(f"Could not check disk space: {e}")
            
            # Check memory
            try:
                from utils import get_available_memory
                total_memory = get_available_memory()
                
                if total_memory < 4:
                    validation_result['warnings'].append(
                        f"Low system memory: {total_memory}GB. 8GB+ recommended for modded Minecraft."
                    )
                
                validation_result['info']['total_memory_gb'] = total_memory
                
            except Exception as e:
                logger.warning(f"Could not check system memory: {e}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating system requirements: {e}")
            validation_result['valid'] = False
            validation_result['errors'].append(f"System validation failed: {e}")
            return validation_result
    
    def create_default_config(self) -> bool:
        """Create default configuration file if it doesn't exist."""
        try:
            config_path = Path('config.json')
            
            if config_path.exists():
                logger.info("Configuration file already exists")
                return True
            
            from main import ConfigManager
            default_config = ConfigManager.DEFAULT_CONFIG.copy()
            
            # Adjust defaults based on system
            try:
                from utils import get_available_memory
                system_memory = get_available_memory()
                # Allocate 50% of system memory, but not more than 16GB or less than 2GB
                recommended_ram = max(2, min(16, system_memory // 2))
                default_config['ram'] = recommended_ram
            except Exception:
                pass
            
            # Save default config
            success = ConfigManager.save_config(str(config_path), default_config)
            if success:
                logger.info(f"Default configuration created: {config_path}")
            else:
                logger.error("Failed to create default configuration")
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating default config: {e}")
            return False
    
    def check_for_updates(self) -> Optional[Dict]:
        """Check for launcher and modpack updates."""
        try:
            update_manager = UpdateManager(launcher_dir=str(self.launcher_dir))
            result = update_manager.check_for_updates()
            
            if result.get('updates_available'):
                logger.info("Updates are available")
            else:
                logger.info("No updates available")
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return None
    
    def initialize(self) -> Dict[str, Any]:
        """Perform complete launcher initialization."""
        logger.info("Starting launcher initialization...")
        
        init_result = {
            'success': True,
            'directories_created': False,
            'config_created': False,
            'system_validation': None,
            'updates_checked': False,
            'errors': []
        }
        
        try:
            # Create directories
            if self.ensure_launcher_directories():
                init_result['directories_created'] = True
                logger.info("Launcher directories created successfully")
            else:
                init_result['success'] = False
                init_result['errors'].append("Failed to create launcher directories")
            
            # Validate system
            validation = self.validate_system_requirements()
            init_result['system_validation'] = validation
            
            if not validation['valid']:
                init_result['success'] = False
                init_result['errors'].extend(validation['errors'])
                logger.error("System validation failed")
            
            # Log warnings
            for warning in validation.get('warnings', []):
                logger.warning(warning)
            
            # Create default config
            if self.create_default_config():
                init_result['config_created'] = True
            else:
                init_result['errors'].append("Failed to create default configuration")
            
            # Check for updates (non-critical)
            try:
                update_result = self.check_for_updates()
                if update_result:
                    init_result['updates_checked'] = True
                    init_result['update_info'] = update_result
            except Exception as e:
                logger.warning(f"Update check failed: {e}")
            
            if init_result['success']:
                logger.info("Launcher initialization completed successfully")
            else:
                logger.error("Launcher initialization completed with errors")
            
            return init_result
            
        except Exception as e:
            logger.error(f"Critical error during initialization: {e}")
            init_result['success'] = False
            init_result['errors'].append(f"Critical initialization error: {e}")
            return init_result

def ensure_launcher_dir():
    """Legacy function for backward compatibility."""
    initializer = LauncherInitializer()
    initializer.ensure_launcher_directories()
    return str(initializer.launcher_dir)

def main():
    """Main initialization function."""
    # Configure logging for initialization
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    initializer = LauncherInitializer()
    result = initializer.initialize()
    
    if result['success']:
        print("✅ Launcher initialization successful!")
        
        # Print system info
        validation = result.get('system_validation', {})
        info = validation.get('info', {})
        
        if info:
            print("\n📊 System Information:")
            for key, value in info.items():
                print(f"  {key}: {value}")
        
        # Print warnings
        warnings = validation.get('warnings', [])
        if warnings:
            print("\n⚠️  Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        
        # Print update info
        if result.get('updates_checked') and result.get('update_info', {}).get('updates_available'):
            print("\n🔄 Updates available! Check the launcher for details.")
        
    else:
        print("❌ Launcher initialization failed!")
        print("\n🔍 Errors:")
        for error in result.get('errors', []):
            print(f"  - {error}")
        
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
