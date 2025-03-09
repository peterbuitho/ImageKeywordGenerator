import json
from pathlib import Path
from typing import Dict, Optional

class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / '.imagekeywordgenerator'
        self.config_file = self.config_dir / 'config.json'
        self.config_dir.mkdir(exist_ok=True)
        self.load_config()

    def load_config(self):
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                'api_tokens': {
                    'openai': '',                 
                    'google': ''
                }
            }
            self.save_config()

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def get_api_token(self, provider: str) -> str:
        return self.config['api_tokens'].get(provider, '')

    def set_api_token(self, provider: str, token: str):
        if 'api_tokens' not in self.config:
            self.config['api_tokens'] = {}
        self.config['api_tokens'][provider] = token
        self.save_config()