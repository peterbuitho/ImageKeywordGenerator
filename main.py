import os
from pathlib import Path
import argparse
from PIL import Image
import json
from typing import List, Dict
import requests
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter.scrolledtext import ScrolledText
import sys

class ImageKeywordGenerator:
    def __init__(self, model_name: str = "llava"):
        self.model_name = model_name
        self.base_url = "http://localhost:11434/api/generate"
        
    def generate_keywords(self, image_path: str) -> Dict[str, List[str]]:
        """Generate keywords for an image in English and Danish using Ollama LLM vision model"""
        try:
            # Convert image to base64
            with Image.open(image_path) as img:
                # Ensure image is in RGB mode
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                # Convert to base64
                import base64
                from io import BytesIO
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode()

            # Prepare prompts for both languages
            en_prompt = """Generate 5-7 relevant keywords for this image in English. Focus on describing: objects, colors, actions, emotions, settings, style.
            Avoid generic terms like 'photograph', 'photography', 'image', 'picture' or software names.
            Provide only single words or short phrases, separated by commas."""

            dk_prompt = """Generér 5-7 relevante keywords for dette billede på Dansk. 
Focusér på det beskrivende: objekter, farver, aktioner, følelser, omgivelser, stil.
Undgå generiske termer som 'fotografi', 'foto', 'billede' or softwarenavne.
VIGTIGT: Giv KUN enkelte nøgleord eller korte udtryk, adskilt af kommaer.
BRUG IKKE linjeskift, bindestreg eller bulletpunkter."""
            
            # Get English keywords
            response_en = requests.post(
                self.base_url,
                json={
                    "model": self.model_name,
                    "prompt": en_prompt,
                    "images": [img_base64],
                    "stream": False
                }
            )
            
            # Get Danish keywords
            response_dk = requests.post(
                self.base_url,
                json={
                    "model": self.model_name,
                    "prompt": dk_prompt,
                    "images": [img_base64],
                    "stream": False
                }
            )
            
            # Parse responses and extract keywords
            keywords = {
                'en': [],
                'dk': []
            }
            
            if response_en.status_code == 200:
                keywords['en'] = [k.strip().lower() for k in response_en.json()["response"].strip().split(',')]
            if response_dk.status_code == 200:
                # Clean up Danish keywords by:
                # 1. Split by commas or newlines
                # 2. Remove hyphens and extra whitespace
                # 3. Remove empty strings
                raw_dk = response_dk.json()["response"].strip()
                dk_keywords = []
                for k in raw_dk.replace('\n', ',').split(','):
                    cleaned = k.replace('-', '').strip().lower()
                    if cleaned:
                        dk_keywords.append(cleaned)
                keywords['dk'] = dk_keywords
                
            return keywords
                
        except Exception as e:
            print(f"Error processing {image_path}: {str(e)}")
            return {'en': [], 'dk': []}

    # Alternative implementation for OpenAI
    """
    import openai

    def generate_keywords(self, image_path: str) -> List[str]:
        with open(image_path, "rb") as image_file:
            response = openai.ChatCompletion.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Generate 5-7 keywords for this image"},
                            {"type": "image_url", "image_url": {"url": image_file}}
                        ]
                    }
                ]
            )
            keywords = response.choices[0].message.content.strip().split(',')
            return [k.strip().lower() for k in keywords]
    """

def save_keywords(image_path: str, keywords: Dict[str, List[str]], output_dir: str):
    """Save keywords to a JSON file next to the image"""
    image_name = Path(image_path).stem
    output_path = Path(output_dir) / f"{image_name}_keywords.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'image': image_path,
            'keywords': keywords
        }, f, indent=2, ensure_ascii=False)

class ImageKeywordGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Keyword Generator")
        self.root.geometry("800x600")
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
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
        
        # Model selection
        ttk.Label(self.main_frame, text="Model:").grid(row=2, column=0, sticky=tk.W)
        self.model = tk.StringVar(value="llava")
        ttk.Entry(self.main_frame, textvariable=self.model, width=50).grid(row=2, column=1, padx=5)
        
        # Process button
        ttk.Button(self.main_frame, text="Process Images", command=self.process_images).grid(row=3, column=0, columnspan=3, pady=10)
        
        # Log area
        self.log_area = ScrolledText(self.main_frame, height=20, width=80)
        self.log_area.grid(row=4, column=0, columnspan=3, pady=5)
        
    def browse_input(self):
        directory = filedialog.askdirectory()
        if directory:
            self.input_dir.set(directory)
            
    def browse_output(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir.set(directory)
            
    def log(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.root.update()
        
    def process_images(self):
        input_dir = self.input_dir.get()
        output_dir = self.output_dir.get()
        model = self.model.get()
        
        if not input_dir or not output_dir:
            self.log("Please select both input and output directories")
            return
            
        try:
            os.makedirs(output_dir, exist_ok=True)
            generator = ImageKeywordGenerator(model_name=model)
            
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
            for file_path in Path(input_dir).rglob('*'):
                if file_path.suffix.lower() in image_extensions:
                    self.log(f"Processing: {file_path}")
                    keywords = generator.generate_keywords(str(file_path))
                    if keywords['en'] or keywords['dk']:
                        save_keywords(str(file_path), keywords, output_dir)
                        self.log("Generated keywords:")
                        self.log(f"English: {', '.join(keywords['en'])}")
                        self.log(f"Danish:  {', '.join(keywords['dk'])}\n")
                        
            self.log("Processing complete!")
        except Exception as e:
            self.log(f"Error: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Generate keywords for images using LLM vision model')
    parser.add_argument('--gui', action='store_true', help='Launch GUI mode')
    parser.add_argument('--input_dir', type=str, help='Directory containing images')
    parser.add_argument('--output_dir', type=str, help='Directory to save keyword files')
    parser.add_argument('--model', type=str, default='llava', help='LLM model to use')
    
    args = parser.parse_args()
    
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
                keywords = generator.generate_keywords(str(file_path))
                if keywords:
                    save_keywords(str(file_path), keywords, args.output_dir)
                    print(f"Generated keywords: {', '.join(keywords['en'])} (English), {', '.join(keywords['dk'])} (Danish)")

if __name__ == "__main__":
    main()