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
        if model_name.startswith('lmstudio:'):
            self.base_url = "http://localhost:1234/v1/chat/completions"
            self.provider = 'lmstudio'
            # Remove prefix from model name for API calls
            self.api_model_name = model_name.replace('lmstudio:', '')
        elif not model_name.startswith('gpt-4') and not model_name.startswith('gemini'):
            self.base_url = "http://localhost:11434/api/generate"
            self.provider = 'ollama'
            self.api_model_name = model_name
        elif model_name.startswith('gpt-4'):
            self.base_url = "https://api.openai.com/v1/chat/completions"
            self.provider = 'openai'
            self.api_model_name = model_name
        elif model_name.startswith('gemini'):
            self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
            self.provider = 'google'
            self.api_model_name = model_name
        else:
            self.base_url = "http://localhost:11434/api/generate"
            self.provider = 'ollama'
            self.api_model_name = model_name

    def get_headers(self):
        if self.provider in ['ollama', 'lmstudio']:
            return {}
        elif self.provider == 'openai':
            return {"Authorization": f"Bearer {self.api_tokens['openai']}"}
        elif self.provider == 'google':
            return {"Authorization": f"Bearer {self.api_tokens['google']}"}

    def generate_keywords(self, image_path: str, languages: List[str]) -> Dict[str, List[str]]:
        """Generate keywords for an image in selected languages using selected model"""
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
            
            # Handle different API formats for different providers
            english_keywords = []
            
            if self.provider == 'ollama':
                response_en = requests.post(
                    self.base_url,
                    json={
                        "model": self.api_model_name,
                        "prompt": en_prompt,
                        "images": [img_base64],
                        "stream": False
                    }
                )
                
                if response_en.status_code == 200:
                    english_keywords = [k.strip().lower() for k in response_en.json()["response"].strip().split(',')]
                    # Only save English keywords if English was selected
                    if 'en' in languages:
                        keywords['en'] = english_keywords
            
            elif self.provider == 'lmstudio':
                # Format for LM-studio API which uses OpenAI-compatible interface
                response_en = requests.post(
                    self.base_url,
                    headers=self.get_headers(),
                    json={
                        "model": self.api_model_name,
                        "messages": [
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": [
                                {"type": "text", "text": en_prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                            ]}
                        ],
                        "max_tokens": 300
                    }
                )
                
                if response_en.status_code == 200:
                    response_content = response_en.json()["choices"][0]["message"]["content"].strip()
                    english_keywords = [k.strip().lower() for k in response_content.split(',')]
                    # Only save English keywords if English was selected
                    if 'en' in languages:
                        keywords['en'] = english_keywords
            
            # Handle non-English languages
            if english_keywords:
                non_english_langs = [lang for lang in languages if lang != 'en']
                for lang in non_english_langs:
                    translate_prompt = f"""Translate these English keywords to {self.supported_languages[lang]}, keeping the same meaning and style. 
                                        Return only the translations, separated by commas: {', '.join(english_keywords)}"""
                    
                    if self.provider == 'ollama':
                        response = requests.post(
                            self.base_url,
                            json={
                                "model": self.api_model_name,
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
                    
                    elif self.provider == 'lmstudio':
                        response = requests.post(
                            self.base_url,
                            headers=self.get_headers(),
                            json={
                                "model": self.api_model_name,
                                "messages": [
                                    {"role": "system", "content": "You are a helpful assistant."},
                                    {"role": "user", "content": translate_prompt}
                                ],
                                "max_tokens": 300
                            }
                        )
                        
                        if response.status_code == 200:
                            raw_translation = response.json()["choices"][0]["message"]["content"].strip()
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