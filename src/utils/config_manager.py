from pathlib import Path
import json
from cryptography.fernet import Fernet
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class ConfigManager:
    def __init__(self):
        self.config_file = Path.home() / '.imagekeywordgenerator' / 'config.json'
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.key = self.generate_key("fixed_encryption_password")
        self.f = Fernet(self.key)
        
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                'api_tokens': {},
                'last_model': 'llava'  # Default model
            }
            self._save_config()

    def generate_key(self, password: str) -> bytes:
        salt = b'fixed_salt_for_api_keys'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def get_api_token(self, provider: str) -> str:
        encrypted_token = self.config.get('api_tokens', {}).get(provider)
        if encrypted_token:
            try:
                return self.f.decrypt(encrypted_token.encode()).decode()
            except Exception:
                return ""
        return ""

    def set_api_token(self, provider: str, token: str):
        if token:
            try:
                self.f.decrypt(token.encode())
                encrypted_token = token
            except Exception:
                encrypted_token = self.f.encrypt(token.encode()).decode()
            
            if 'api_tokens' not in self.config:
                self.config['api_tokens'] = {}
            self.config['api_tokens'][provider] = encrypted_token
            self._save_config()

    def get_last_model(self) -> str:
        """Get the last used model name"""
        return self.config.get('last_model', 'llava')

    def set_last_model(self, model_name: str):
        """Save the last used model name"""
        self.config['last_model'] = model_name
        self._save_config()

    def _save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)