from pathlib import Path
import requests
from PIL import Image
from typing import List, Dict
from io import BytesIO
import base64

class ImageKeywordGenerator:
    def __init__(self, model_name: str = "llava", api_tokens: Dict[str, str] = None):
        self.model_name = model_name
        self.api_tokens = api_tokens or {}
        
        # Add supported languages dictionary
        self.supported_languages = {
            'en': 'English',
            'dk': 'Danish',
            'vi': 'Vietnamese'
        }
        
        # Configure base URL based on model provider
        if not model_name.startswith('gpt-4') and not model_name.startswith('gemini'):
            self.base_url = "http://localhost:11434/api/generate"
            self.provider = 'ollama'
        elif model_name.startswith('gpt-4'):
            self.base_url = "https://api.openai.com/v1/chat/completions"
            self.provider = 'openai'
        elif model_name.startswith('gemini'):
            self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
            self.provider = 'google'
        else:
            self.base_url = "http://localhost:11434/api/generate"
            self.provider = 'ollama'

    def get_headers(self):
        if self.provider == 'ollama':
            return {}
        elif self.provider == 'openai':
            return {"Authorization": f"Bearer {self.api_tokens['openai']}"}
        elif self.provider == 'google':
            return {"Authorization": f"Bearer {self.api_tokens['google']}"}

    def generate_keywords(self, image_path: str, languages: List[str]) -> Dict[str, List[str]]:
        """Generate keywords for an image in selected languages using Ollama LLM"""
        try:
            # Read and encode image
            with open(image_path, 'rb') as img_file:
                img_base64 = base64.b64encode(img_file.read()).decode('utf-8')

            # Initialize keywords dict only for selected languages
            keywords = {lang: [] for lang in languages}
            
            # Generate English keywords regardless of selection
            en_prompt = """Generate 5-7 relevant keywords for this image in English. Focus on describing: objects, colors, actions, emotions, settings, style.
                        Avoid generic terms like 'photograph', 'photography', 'image', 'picture' or software names.
                        Provide only single words or short phrases, separated by commas."""
            
            response_en = requests.post(
                self.base_url,
                json={
                    "model": self.model_name,
                    "prompt": en_prompt,
                    "images": [img_base64],
                    "stream": False
                }
            )
            
            english_keywords = []
            if response_en.status_code == 200:
                english_keywords = [k.strip().lower() for k in response_en.json()["response"].strip().split(',')]
                # Only save English keywords if English was selected
                if 'en' in languages:
                    keywords['en'] = english_keywords
            
            # Translate to other selected languages using English keywords
            if english_keywords:
                non_english_langs = [lang for lang in languages if lang != 'en']
                for lang in non_english_langs:
                    translate_prompt = f"""Translate these English keywords to {self.supported_languages[lang]}, keeping the same meaning and style. 
                                        Return only the translations, separated by commas: {', '.join(english_keywords)}"""
                    
                    response = requests.post(
                        self.base_url,
                        json={
                            "model": self.model_name,
                            "prompt": translate_prompt,
                            "stream": False
                        }
                    )
                    
                    if response.status_code == 200:
                        raw_translation = response.json()["response"].strip()
                        translated_keywords = []
                        for k in raw_translation.replace('\n', ',').split(','):
                            cleaned = k.replace('-', '').strip().lower()
                            if cleaned:
                                translated_keywords.append(cleaned)
                        keywords[lang] = translated_keywords
            
            return keywords
                
        except Exception as e:
            print(f"Error processing {image_path}: {str(e)}")
            return {lang: [] for lang in languages}