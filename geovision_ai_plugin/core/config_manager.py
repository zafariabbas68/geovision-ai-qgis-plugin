"""
Configuration management for GeoVision AI
"""
import os
import json
from pathlib import Path


class ConfigManager:
    """Manage plugin configuration and settings"""

    def __init__(self):
        self.plugin_dir = Path(__file__).parent.parent
        self.config_file = self.plugin_dir / 'config.json'
        self.config = self.load_config()

    def load_config(self):
        """Load configuration from file or create default"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            default_config = self.get_default_config()
            self.save_config(default_config)
            return default_config

    def get_default_config(self):
        """Return default configuration"""
        return {
            'model_dir': str(self.plugin_dir / 'models' / 'weights'),
            'venv_dir': str(self.plugin_dir / 'venv'),
            'cache_size': 2,
            'default_model': 'sam2_tiny',
            'confidence_threshold': 0.5,
            'simplify_tolerance': 0.5,
            'min_area': 0.0,
            'auto_load_models': True,
            'use_gpu': True
        }

    def save_config(self, config=None):
        """Save configuration to file"""
        if config is None:
            config = self.config
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)

    def get_model_dir(self):
        """Get model directory path"""
        return Path(self.config.get('model_dir', str(self.plugin_dir / 'models' / 'weights')))

    def get_venv_dir(self):
        """Get virtual environment directory path"""
        return Path(self.config.get('venv_dir', str(self.plugin_dir / 'venv')))

    def get_setting(self, key, default=None):
        """Get a specific setting"""
        return self.config.get(key, default)

    def set_setting(self, key, value):
        """Set a specific setting and save"""
        self.config[key] = value
        self.save_config()
