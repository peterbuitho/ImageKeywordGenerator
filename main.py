import os
from pathlib import Path
import argparse
from PIL import Image
from PIL import TiffImagePlugin  # Add this import
from PIL import Image, PngImagePlugin
import piexif  # Add this import - you'll need to install it: pip install piexif
import json
from typing import List, Dict
import requests
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import sys
from config_manager import ConfigManager  # Add this import

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
        if model_name.startswith('llava') or model_name.startswith('llama'):
            self.base_url = "http://localhost:11434/api/generate"
            self.provider = 'ollama'
        elif model_name.startswith('gpt-4'):
            self.base_url = "https://api.openai.com/v1/chat/completions"
            self.provider = 'openai'
        elif model_name.startswith('gemini'):
            self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
            self.provider = 'google'

    def get_headers(self):
        if self.provider == 'ollama':
            return {}
        elif self.provider == 'openai':
            return {"Authorization": f"Bearer {self.api_tokens['openai']}"}
        elif self.provider == 'google':
            return {"Authorization": f"Bearer {self.api_tokens['google']}"}

    def generate_keywords(self, image_path: str, languages: List[str], include_english: bool = False) -> Dict[str, List[str]]:
        """Generate keywords for an image in selected languages using Ollama LLM"""
        try:
            # Convert image to base64
            with Image.open(image_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                import base64
                from io import BytesIO
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode()

            keywords = {lang: [] for lang in languages}
            
            # Always get English keywords first (even if not selected)
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
                if 'en' in languages:  # Only save English if selected
                    keywords['en'] = english_keywords
            
            # Translate to other languages using English keywords
            if english_keywords:
                for lang in languages:
                    if lang != 'en':
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

def save_keywords(image_path: str, keywords: Dict[str, List[str]], output_dir: str, append: bool = False) -> None:
    """Save keywords to separate JSON files for each language"""
    image_name = Path(image_path).stem
    
    for lang, kw_list in keywords.items():
        output_path = Path(output_dir) / f"{image_name}_keywords_{lang}.json"
        
        if append and output_path.exists():
            # Load existing keywords
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                existing_keywords = existing_data.get('keywords', [])
                
                # Merge keywords without duplicates
                merged_keywords = list(set(existing_keywords + kw_list))
                kw_list = merged_keywords
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'image': image_path,
                'language': lang,
                'keywords': kw_list
            }, f, indent=2, ensure_ascii=False)

def embed_keywords_in_image(image_path: str, keywords: Dict[str, List[str]], selected_languages: List[str]) -> bool:
    """Embed keywords into image metadata for selected languages only"""
    try:
        with Image.open(image_path) as img:
            # Create combined keyword string for all selected languages with UTF-8 encoding
            combined_keywords = []
            for lang in selected_languages:
                if lang in keywords and keywords[lang]:
                    lang_keywords = keywords[lang]
                    # Ensure proper UTF-8 encoding for each keyword
                    combined_keywords.extend([f"{lang}:{kw}".encode('utf-8').decode('utf-8') 
                                           for kw in lang_keywords])
            
            # Convert to string format with proper encoding
            keyword_string = ", ".join(combined_keywords)
            
            if img.format == 'JPEG':
                try:
                    exif_dict = piexif.load(img.info.get('exif', b''))
                except:
                    exif_dict = {'0th': {}, '1st': {}, 'Exif': {}, 'GPS': {}, 'Interop': {}}
                
                # Store all keywords in one UserComment tag with UTF-8 encoding
                exif_dict['Exif'][piexif.ExifIFD.UserComment] = keyword_string.encode('utf-8')
                
                # Convert back to bytes
                exif_bytes = piexif.dump(exif_dict)
                
                # Save with new metadata
                img.save(image_path, 'JPEG', exif=exif_bytes, quality='keep')
            
            elif img.format == 'PNG':
                # Create new image with metadata
                new_img = Image.new(img.mode, img.size)
                new_img.putdata(list(img.getdata()))
                
                # Add metadata (PNG text chunks are UTF-8 by default)
                info = PngImagePlugin.PngInfo()
                info.add_text("Keywords", keyword_string)
                
                # Save with metadata
                new_img.save(image_path, 'PNG', pnginfo=info)
            
            else:
                raise ValueError(f"Unsupported image format: {img.format}")
            
        return True
    except Exception as e:
        print(f"Error embedding keywords in {image_path}: {str(e)}")
        return False

class ImageKeywordGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Keyword Generator")
        self.root.geometry("800x600")
        
        # Configure root to resize
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure main frame grid
        self.main_frame.columnconfigure(1, weight=1)  # Make column 1 (middle) expandable
        self.main_frame.rowconfigure(6, weight=3)  # Make Treeview row expandable
        self.main_frame.rowconfigure(7, weight=1)  # Make status area row expandable

        # Input directory selection
        ttk.Label(self.main_frame, text="Input Directory:").grid(row=0, column=0, sticky=tk.W)
        self.input_dir = tk.StringVar()
        ttk.Entry(self.main_frame, textvariable=self.input_dir, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(self.main_frame, text="Browse", command=self.browse_input).grid(row=0, column=2)
        
        # Output directory selection
        ttk.Label(self.main_frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W)
        self.output_dir = tk.StringVar()
        ttk.Entry(self.main_frame, textvariable=self.output_dir, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(self.main_frame, text="Browse", command=self.browse_output).grid(row=1, column=2)
        
        # Model selection frame and API button in the same row
        model_frame = ttk.LabelFrame(self.main_frame, text="Model Selection", padding="5")
        model_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # API configuration button next to model frame
        api_button = ttk.Button(
            self.main_frame,
            text="Configure API Keys",
            command=self.show_api_config
        )
        api_button.grid(row=2, column=2, pady=5, padx=5, sticky=tk.E)
        
        # Available models
        self.models = [
            "llava",
            "llava:13b",
            "llama3.2-vision",
            "llava-llama3:8b-v1.1-fp16",
            "llava-llama3:8b",
            "gpt-4-vision-preview",
            "gemini-pro-vision"
        ]
        
        # Model radio buttons
        self.model = tk.StringVar(value="llava")
        for i, model_name in enumerate(self.models):
            ttk.Radiobutton(
                model_frame, 
                text=model_name,
                variable=self.model,
                value=model_name
            ).grid(row=i//3, column=i%3, padx=10, sticky=tk.W)
        
        # Language selection frame
        lang_frame = ttk.LabelFrame(self.main_frame, text="Languages", padding="5")
        lang_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Language checkboxes
        self.languages = {
            'en': ('English', tk.BooleanVar(value=True)),
            'dk': ('Danish', tk.BooleanVar(value=False)),
            'vi': ('Vietnamese', tk.BooleanVar(value=False))
        }
        
        for i, (lang_code, (lang_name, var)) in enumerate(self.languages.items()):
            ttk.Checkbutton(
                lang_frame,
                text=lang_name,
                variable=var
            ).grid(row=0, column=i, padx=10, sticky=tk.W)
        
        # Add append/overwrite option frame
        append_frame = ttk.LabelFrame(self.main_frame, text="Options", padding="5")
        append_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.append_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            append_frame,
            text="Append to existing keywords (if file exists)",
            variable=self.append_mode
        ).pack(side=tk.LEFT, padx=5)
        
        # Add Process and Embed buttons to the right of append frame
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=4, column=2, pady=5, padx=5, sticky=tk.E)
        
        # Process button
        ttk.Button(
            button_frame,
            text="Process Images",
            command=self.process_images
        ).pack(side=tk.LEFT, padx=2)
        
        # Embed button
        self.embed_button = ttk.Button(
            button_frame,
            text="Embed Keywords",
            command=self.embed_keywords,
            state=tk.DISABLED  # Initially disabled
        )
        self.embed_button.pack(side=tk.LEFT, padx=2)
        
        # Replace ScrolledText with Treeview for structured display
        columns = ('filename', 'english', 'danish', 'vietnamese')
        self.log_tree = ttk.Treeview(self.main_frame, columns=columns, show='headings', height=20, selectmode='extended')
        
        # Configure columns
        self.log_tree.heading('filename', text='Filename')
        self.log_tree.heading('english', text='English Keywords')
        self.log_tree.heading('danish', text='Danish Keywords')
        self.log_tree.heading('vietnamese', text='Vietnamese Keywords')
        
        # Add iid and values mapping for tracking
        self.file_to_iid = {}  # Maps file paths to tree item IDs
        
        # Add scrollbar
        tree_scroll = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=tree_scroll.set)
        
        # Grid the treeview and scrollbar with sticky options
        self.log_tree.grid(row=6, column=0, columnspan=3, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scroll.grid(row=6, column=3, pady=5, sticky=(tk.N, tk.S))
        
        # Status text area for messages with expanded sticky options
        self.status_area = ScrolledText(self.main_frame, height=5)  # Remove fixed width
        self.status_area.grid(row=7, column=0, columnspan=3, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Store processed keywords
        self.last_processed_keywords = {}
        self.last_processed_files = []

        # Extended model list including API models
        self.models.extend([
            "gpt-4-vision-preview",
            "gemini-pro-vision"
        ])

        # Load configuration
        self.config_manager = ConfigManager()
        
    def show_api_config(self):
        """Show API configuration dialog"""
        api_window = tk.Toplevel(self.root)
        api_window.title("API Configuration")
        api_window.geometry("400x200")
        
        # Create frames for each API provider
        providers = {
            'openai': 'OpenAI API Key',
            'google': 'Google AI API Key'
        }
        
        row = 0
        api_vars = {}
        for provider, label in providers.items():
            ttk.Label(api_window, text=label).grid(row=row, column=0, padx=5, pady=5)
            var = tk.StringVar(value=self.config_manager.get_api_token(provider))
            api_vars[provider] = var
            entry = ttk.Entry(api_window, textvariable=var, show='*', width=40)
            entry.grid(row=row, column=1, padx=5, pady=5)
            row += 1
        
        def save_api_keys():
            for provider, var in api_vars.items():
                self.config_manager.set_api_token(provider, var.get())
            api_window.destroy()
            self.log("API keys saved successfully")
        
        ttk.Button(
            api_window,
            text="Save",
            command=save_api_keys
        ).grid(row=row, column=0, columnspan=2, pady=20)

    def browse_input(self):
        directory = filedialog.askdirectory()
        if directory:
            self.input_dir.set(directory)
            # Set output directory to same as input directory by default
            if not self.output_dir.get():  # Only set if output dir is empty
                self.output_dir.set(directory)
            
    def browse_output(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir.set(directory)
            
    def log(self, message):
        """Log status messages"""
        self.status_area.insert(tk.END, message + "\n")
        self.status_area.see(tk.END)
        self.root.update()
    
    def add_result_to_tree(self, file_path: str, keywords: Dict[str, List[str]]):
        """Add a processed file's results to the treeview"""
        values = [Path(file_path).name]  # Start with filename
        
        # Add keywords for each language, or empty string if not available
        for lang in ['en', 'dk', 'vi']:
            kw_list = keywords.get(lang, [])
            values.append(', '.join(kw_list) if kw_list else '')
        
        # Insert and store the item ID
        iid = self.log_tree.insert('', tk.END, values=values)
        self.file_to_iid[file_path] = iid

    def embed_keywords(self):
        """Embed keywords into selected image files"""
        selected_items = self.log_tree.selection()
        if not selected_items:
            self.log("Please select one or more images first")
            return
        
        # Get selected languages
        selected_languages = [lang for lang, (_, var) in self.languages.items() if var.get()]
        if not selected_languages:
            self.log("Please select at least one language")
            return
        
        # Get file paths for selected items
        selected_files = []
        for iid in selected_items:
            filename = self.log_tree.item(iid)['values'][0]  # Get filename from first column
            # Find the full path from last_processed_keywords
            full_path = next((path for path in self.last_processed_keywords.keys() 
                            if Path(path).name == filename), None)
            if full_path:
                selected_files.append(full_path)
        
        if not selected_files:
            self.log("No valid files selected")
            return
            
        if messagebox.askyesno("Confirm Embed", 
                              f"This will embed keywords for {len(selected_languages)} language(s) "
                              f"into {len(selected_files)} image file(s). Continue?"):
            for image_path in selected_files:
                self.log(f"Embedding keywords in: {image_path}")
                if embed_keywords_in_image(image_path, 
                                         self.last_processed_keywords[image_path],
                                         selected_languages):
                    self.log(f"Keywords embedded successfully for languages: {', '.join(selected_languages)}")
                    # Highlight the processed item in the tree
                    self.log_tree.item(self.file_to_iid[image_path], tags=('embedded',))
                else:
                    self.log("Failed to embed keywords")
            
            # Add visual feedback for embedded items
            self.log_tree.tag_configure('embedded', background='#e6ffe6')
            self.log("Embedding complete!")

    def process_images(self):
        # Clear tracking dictionaries
        self.file_to_iid.clear()
        self.last_processed_keywords.clear()
        self.last_processed_files.clear()
        
        # Clear the treeview
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)
        
        input_dir = self.input_dir.get()
        output_dir = self.output_dir.get()
        model = self.model.get()
        append = self.append_mode.get()
        
        # Get selected languages
        selected_languages = [lang for lang, (_, var) in self.languages.items() if var.get()]
        
        if not selected_languages:
            self.log("Please select at least one language")
            return
        
        if not input_dir or not output_dir:
            self.log("Please select both input and output directories")
            return
            
        try:
            os.makedirs(output_dir, exist_ok=True)
            generator = ImageKeywordGenerator(
                model_name=model,
                api_tokens={
                    'openai': self.config_manager.get_api_token('openai'),               
                    'google': self.config_manager.get_api_token('google')
                }
            )
            
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
            for file_path in Path(input_dir).rglob('*'):
                if file_path.suffix.lower() in image_extensions:
                    self.log(f"Processing: {file_path}")
                    keywords = generator.generate_keywords(str(file_path), selected_languages)
                    
                    if any(keywords.values()):
                        # Store keywords for embedding
                        self.last_processed_keywords[str(file_path)] = keywords
                        self.last_processed_files.append(str(file_path))
                        
                        save_keywords(str(file_path), keywords, output_dir, append=append)
                        # Add results to treeview
                        self.add_result_to_tree(str(file_path), keywords)
            
            # Enable embed button if files were processed
            if self.last_processed_files:
                self.embed_button['state'] = tk.NORMAL
            
            self.log("Processing complete!")
        except Exception as e:
            self.log(f"Error: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Generate keywords for images using LLM vision model')
    parser.add_argument('--gui', action='store_true', help='Launch GUI mode')
    parser.add_argument('--input_dir', type=str, help='Directory containing images')
    parser.add_argument('--output_dir', type=str, help='Directory to save keyword files')
    parser.add_argument('--model', type=str, default='llava', help='LLM model to use')
    parser.add_argument('--append', action='store_true', help='Append to existing keyword files')
    parser.add_argument('--languages', type=str, nargs='+', default=['en'], help='Languages for keyword generation (e.g., en dk vi)')
    parser.add_argument('--openai-key', type=str, help='OpenAI API key')    
    parser.add_argument('--google-key', type=str, help='Google AI API key')
    
    args = parser.parse_args()
    
    # Load configuration
    config_manager = ConfigManager()
    
    # Update API tokens from command line if provided
    if args.openai_key:
        config_manager.set_api_token('openai', args.openai_key)
    
    if args.google_key:
        config_manager.set_api_token('google', args.google_key)
    
    # If no arguments provided, default to GUI mode
    if len(sys.argv) == 1:
        args.gui = True
    
    if args.gui:
        root = tk.Tk()
        app = ImageKeywordGeneratorGUI(root)
        root.mainloop()
    else:
        if not args.input_dir:
            parser.error("--input_dir is required when not using GUI mode")
        if not args.output_dir:
            parser.error("--output_dir is required when not using GUI mode")
            
        # Original CLI code
        os.makedirs(args.output_dir, exist_ok=True)
        generator = ImageKeywordGenerator(model_name=args.model)
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
        for file_path in Path(args.input_dir).rglob('*'):
            if file_path.suffix.lower() in image_extensions:
                print(f"Processing: {file_path}")
                keywords = generator.generate_keywords(str(file_path), args.languages)
                if keywords:
                    save_keywords(str(file_path), keywords, args.output_dir, append=args.append)
                    for lang in args.languages:
                        print(f"Generated keywords ({lang}): {', '.join(keywords[lang])}")

if __name__ == "__main__":
    main()