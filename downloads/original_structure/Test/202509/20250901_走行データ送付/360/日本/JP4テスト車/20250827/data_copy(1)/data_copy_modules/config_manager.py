"""
Configuration manager for Data Copy Tool
Handles loading and validation of configuration settings
"""

import configparser
import os
import sys
from typing import Dict, Any, Optional


class ConfigManager:
    """Manages configuration settings for the data copy tool"""
    
    def __init__(self, config_file: str = "copy_config.ini"):
        """
        Initialize configuration manager
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file"""
        try:
            if not os.path.exists(self.config_file):
                self._create_default_config()
            
            self.config.read(self.config_file, encoding='utf-8')
            self._validate_config()
            
        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)
    
    def _create_default_config(self):
        """Create default configuration file if it doesn't exist"""
        default_config = """[PERFORMANCE]
# Copy performance mode: fast, balanced, safe
performance_mode = balanced
max_concurrent_threads = 4
file_buffer_size = 1048576
progress_update_interval = 30
verification_tolerance = 1024

[VEHICLE]
# Expected vehicle model (e.g., RV1, RV2, RV3, etc.)
expected_vehicle_model = RV1
strict_vehicle_validation = true

[LOGGING]
log_level = INFO
detailed_progress_logging = true
file_copy_logging = false

[COPY_OPTIONS]
skip_existing_files = false
verify_file_integrity = false
max_retry_attempts = 3
retry_delay = 5

[ADVANCED]
enable_experimental_features = false
large_file_buffer_size = 16777216
file_operation_timeout = 300
"""
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(default_config)
            print(f"Created default configuration file: {self.config_file}")
        except Exception as e:
            print(f"Error creating default configuration: {e}")
            sys.exit(1)
    
    def _validate_config(self):
        """Validate configuration values"""
        # Validate performance mode
        valid_modes = ['fast', 'balanced', 'safe']
        mode = self.get_performance_mode()
        if mode not in valid_modes:
            print(f"Warning: Invalid performance mode '{mode}', using 'balanced'")
            self.config.set('PERFORMANCE', 'performance_mode', 'balanced')
        
        # Validate numeric values
        try:
            self.get_max_concurrent_threads()
            self.get_file_buffer_size()
            self.get_progress_update_interval()
            self.get_verification_tolerance()
        except ValueError as e:
            print(f"Configuration validation error: {e}")
            sys.exit(1)
    
    def get_performance_mode(self) -> str:
        """Get performance mode setting"""
        return self.config.get('PERFORMANCE', 'performance_mode', fallback='balanced').lower()
    
    def get_max_concurrent_threads(self) -> int:
        """Get maximum concurrent threads"""
        return self.config.getint('PERFORMANCE', 'max_concurrent_threads', fallback=4)
    
    def get_file_buffer_size(self) -> int:
        """Get file buffer size in bytes"""
        return self.config.getint('PERFORMANCE', 'file_buffer_size', fallback=1048576)
    
    def get_progress_update_interval(self) -> int:
        """Get progress update interval in seconds"""
        return self.config.getint('PERFORMANCE', 'progress_update_interval', fallback=30)
    
    def get_verification_tolerance(self) -> int:
        """Get verification tolerance in bytes"""
        return self.config.getint('PERFORMANCE', 'verification_tolerance', fallback=1024)
    
    def get_expected_vehicle_model(self) -> str:
        """Get expected vehicle model"""
        return self.config.get('VEHICLE', 'expected_vehicle_model', fallback='RV1').upper()
    
    def is_strict_vehicle_validation_enabled(self) -> bool:
        """Check if strict vehicle validation is enabled"""
        return self.config.getboolean('VEHICLE', 'strict_vehicle_validation', fallback=True)
    
    def get_log_level(self) -> str:
        """Get log level"""
        return self.config.get('LOGGING', 'log_level', fallback='INFO').upper()
    
    def is_detailed_progress_logging_enabled(self) -> bool:
        """Check if detailed progress logging is enabled"""
        return self.config.getboolean('LOGGING', 'detailed_progress_logging', fallback=True)
    
    def is_file_copy_logging_enabled(self) -> bool:
        """Check if file copy logging is enabled"""
        return self.config.getboolean('LOGGING', 'file_copy_logging', fallback=False)
    
    def should_skip_existing_files(self) -> bool:
        """Check if existing files should be skipped"""
        return self.config.getboolean('COPY_OPTIONS', 'skip_existing_files', fallback=False)
    
    def should_verify_file_integrity(self) -> bool:
        """Check if file integrity verification is enabled"""
        return self.config.getboolean('COPY_OPTIONS', 'verify_file_integrity', fallback=False)
    
    def get_max_retry_attempts(self) -> int:
        """Get maximum retry attempts"""
        return self.config.getint('COPY_OPTIONS', 'max_retry_attempts', fallback=3)
    
    def get_retry_delay(self) -> int:
        """Get retry delay in seconds"""
        return self.config.getint('COPY_OPTIONS', 'retry_delay', fallback=5)
    
    def is_experimental_features_enabled(self) -> bool:
        """Check if experimental features are enabled"""
        return self.config.getboolean('ADVANCED', 'enable_experimental_features', fallback=False)
    
    def get_large_file_buffer_size(self) -> int:
        """Get large file buffer size in bytes"""
        return self.config.getint('ADVANCED', 'large_file_buffer_size', fallback=16777216)
    
    def get_file_operation_timeout(self) -> int:
        """Get file operation timeout in seconds"""
        return self.config.getint('ADVANCED', 'file_operation_timeout', fallback=300)
    
    def get_performance_settings(self) -> Dict[str, Any]:
        """Get all performance-related settings as a dictionary"""
        return {
            'mode': self.get_performance_mode(),
            'max_threads': self.get_max_concurrent_threads(),
            'buffer_size': self.get_file_buffer_size(),
            'update_interval': self.get_progress_update_interval(),
            'verification_tolerance': self.get_verification_tolerance()
        }
    
    def validate_vehicle_model(self, detected_model: str) -> bool:
        """
        Validate detected vehicle model against expected model
        
        Args:
            detected_model: Vehicle model detected from Vector drive
            
        Returns:
            True if validation passes, False otherwise
        """
        expected = self.get_expected_vehicle_model()
        detected = detected_model.upper() if detected_model else ""
        
        if not self.is_strict_vehicle_validation_enabled():
            return True
        
        return expected == detected
    
    def get_vehicle_validation_message(self, detected_model: str) -> str:
        """
        Get vehicle validation message
        
        Args:
            detected_model: Vehicle model detected from Vector drive
            
        Returns:
            Validation message
        """
        expected = self.get_expected_vehicle_model()
        detected = detected_model.upper() if detected_model else "UNKNOWN"
        
        if self.validate_vehicle_model(detected_model):
            return f"SUCCESS: Vehicle model validation passed: {detected} matches expected {expected}"
        else:
            return f"ERROR: VEHICLE MODEL MISMATCH: Detected '{detected}' but expected '{expected}'"
    
    def reload_config(self):
        """Reload configuration from file"""
        self._load_config()
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
        except Exception as e:
            print(f"Error saving configuration: {e}")


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def reload_config():
    """Reload global configuration"""
    global _config_manager
    if _config_manager:
        _config_manager.reload_config()
