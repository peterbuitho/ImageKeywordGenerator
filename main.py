import argparse
import sys
import tkinter as tk
from src.gui.main_window import ImageKeywordGeneratorGUI
from src.models.generator import ImageKeywordGenerator
from src.utils.config_manager import ConfigManager
from src.utils.metadata import save_keywords
from pathlib import Path
import os

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
    
        input_path = Path(args.input_dir)
           
        if not input_path.exists():
            parser.error(f"Input directory does not exist: {args.input_dir}")
    
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        image_files = [file_path for file_path in input_path.rglob('*') if file_path.suffix.lower() in image_extensions]
        
        if not image_files:
            print("No image files found in the input directory.")
            sys.exit()

        # Original CLI code
        os.makedirs(args.output_dir, exist_ok=True)
        generator = ImageKeywordGenerator(model_name=args.model)

        for file_path in image_files:
            print(f"Processing: {file_path}")
            keywords = generator.generate_keywords(str(file_path), args.languages)
            if keywords:
                save_keywords(str(file_path), keywords, args.output_dir, append=args.append)
                for lang in args.languages:
                    print(f"Generated keywords ({lang}): {', '.join(keywords[lang])}")

if __name__ == "__main__":
    main()