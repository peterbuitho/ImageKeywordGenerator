import tkinter as tk
import base64
import os
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk
from pathlib import Path
from typing import Dict, List, Optional, Any
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
import requests
from ..utils.metadata import save_keywords, embed_keywords_in_image
from ..models.generator import ImageKeywordGenerator
from ..utils.config_manager import ConfigManager

class ImageKeywordGeneratorGUI:
    def wrap_text(self, text, width=40):
        """Wrap text to fit within column width"""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= width:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(' '.join(current_line))
            
        return '\n'.join(lines)

    def __init__(self, root):
        self.root = root
        self.root.title("Image Keyword Generator")
        
        # Configure root window
        self.setup_window()
        
        # Create main layout
        self.create_main_frame()
        
        # Create UI sections
        self.create_directory_section()
        self.create_model_section()
        self.create_language_section()
        self.create_options_section()
        self.create_button_section()
        self.create_results_section()
        self.create_status_section()
        
        # Initialize other components
        self.initialize_components()
        
        # Log initialization
        self.log("Application initialized successfully")
    
    def setup_window(self):
        """Configure the main window size and position"""
        window_width = 2048
        window_height = 1200
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        self.root.resizable(True, True)
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
    
    def create_main_frame(self):
        """Create and configure the main frame"""
        self.main_frame = ttk.Frame(self.root, padding="5")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        for i in range(3):  # Columns
            self.main_frame.columnconfigure(i, weight=1)
        for i in range(9):  # Rows
            weight = 3 if i == 6 else 1  # Row 6 (Treeview) gets more weight
            self.main_frame.rowconfigure(i, weight=weight)
    
    def create_status_section(self):
        """Create the status area"""
        self.status_area = ScrolledText(
            self.main_frame, 
            height=10, 
            wrap=tk.WORD,
            background='white',
            font=('Consolas', 9)
        )
        self.status_area.grid(
            row=8, 
            column=0, 
            columnspan=3, 
            pady=5, 
            sticky=(tk.W, tk.E, tk.N, tk.S)
        )
    
    def log(self, message: str):
        """Add message to status area with timestamp"""
        if hasattr(self, 'status_area'):
            from datetime import datetime
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.status_area.insert(tk.END, f"[{timestamp}] {message}\n")
            self.status_area.see(tk.END)
            self.root.update_idletasks()

    def generate_key(self, password: str) -> bytes:
        """Generate encryption key from password"""
        salt = b'fixed_salt_for_api_keys'  # In production, use a secure random salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def show_api_config(self):
        """Show API configuration dialog with show/hide functionality"""
        api_window = tk.Toplevel(self.root)
        api_window.title("API Configuration")
        api_window.geometry("500x250")
        
        # Create frames for each API provider
        providers = {
            'openai': 'OpenAI API Key',
            'google': 'Google AI API Key'
        }
        
        row = 0
        api_vars = {}
        show_vars = {}
        entries = {}
        
        # Create a function factory to handle closure properly
        def make_toggle_show(entry, show_var):
            return lambda: entry.configure(show='' if show_var.get() else '*')
        
        for provider, label in providers.items():
            ttk.Label(api_window, text=label).grid(row=row, column=0, padx=5, pady=5)
            
            # Create a frame for entry and show/hide button
            entry_frame = ttk.Frame(api_window)
            entry_frame.grid(row=row, column=1, padx=5, pady=5, sticky='ew')
            
            # Get decrypted value from config manager
            current_value = self.config_manager.get_api_token(provider) or ''
            
            var = tk.StringVar(value=current_value)
            api_vars[provider] = var
            show_vars[provider] = tk.BooleanVar(value=False)
            
            # Create entry widget
            entry = ttk.Entry(entry_frame, textvariable=var, show='*', width=40)
            entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
            entries[provider] = entry
            
            # Create show/hide toggle button with proper closure
            toggle_cmd = make_toggle_show(entry, show_vars[provider])
            ttk.Checkbutton(
                entry_frame, 
                text="Show", 
                variable=show_vars[provider],
                command=toggle_cmd
            ).pack(side=tk.RIGHT, padx=5)
            
            row += 1
        
        def save_api_keys():
            try:
                # Generate encryption key
                key = self.generate_key("fixed_encryption_password")
                f = Fernet(key)
                
                for provider, var in api_vars.items():
                    api_key = var.get()
                    if (api_key):
                        # Encrypt and save the API key
                        encrypted_key = f.encrypt(api_key.encode()).decode()
                        self.config_manager.set_api_token(provider, encrypted_key)
                
                api_window.destroy()
                self.log("API keys saved successfully")
            except Exception as e:
                self.log(f"Error saving API keys: {str(e)}")
        
        # Add save button
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
            
    def add_result_to_tree(self, file_path: str, keywords: Dict[str, List[str]]):
        """Add a result row to the treeview with wrapped text"""
        try:
            # Load and resize image
            with Image.open(file_path) as img:
                aspect_ratio = img.width / img.height
                if (aspect_ratio > 1):
                    # Landscape image
                    target_width = 75
                    target_height = int(target_width / aspect_ratio)
                else:
                    # Portrait image   
                    target_height = 75
                    target_width = int(target_height * aspect_ratio)
                
                img_resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img_resized)
                self.thumbnail_cache[file_path] = photo
            
            # Prepare values with wrapped text
            values = [
                Path(file_path).name,  # filename
                self.wrap_text(', '.join(keywords.get('en', [])), 30),  # english keywords
                self.wrap_text(', '.join(keywords.get('dk', [])), 30),  # danish keywords
                self.wrap_text(', '.join(keywords.get('vi', [])), 30)   # vietnamese keywords
            ]
            
            # Insert into tree with thumbnail in the icon column (#0)
            iid = self.log_tree.insert('', tk.END, text='', values=values, image=photo)
            
            # Store the mapping
            self.file_to_iid[file_path] = iid
            
        except Exception as e:
            self.log(f"Error processing thumbnail for {file_path}: {str(e)}")
            # Insert without thumbnail if there's an error
            values = [
                Path(file_path).name,
                self.wrap_text(', '.join(keywords.get('en', [])), 30),
                self.wrap_text(', '.join(keywords.get('dk', [])), 30),
                self.wrap_text(', '.join(keywords.get('vi', [])), 30)
            ]
            iid = self.log_tree.insert('', tk.END, text='', values=values)
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
        """Process selected images with the chosen model"""
        if not self.generator:
            self.log("Error: No model selected")
            return
            
        input_dir = self.input_dir.get()
        output_dir = self.output_dir.get()
        
        if not input_dir or not output_dir:
            messagebox.showerror("Error", "Please select both input and output directories")
            return
        
        # Get selected languages using self.languages instead of self.lang_vars
        selected_langs = [lang for lang, (_, var) in self.languages.items() if var.get()]
        if not selected_langs:
            messagebox.showerror("Error", "Please select at least one language")
            return
        
        try:
            # Clear previous results
            self.log_tree.delete(*self.log_tree.get_children())
            self.last_processed_keywords = {}
            self.last_processed_files = set()
            
            # Process images
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
            found_files = False
            
            for file_path in Path(input_dir).rglob('*'):
                if file_path.suffix.lower() in image_extensions:
                    found_files = True
                    self.log(f"Processing: {file_path}")
                    try:
                        keywords = self.generator.generate_keywords(str(file_path), selected_langs)
                        if keywords:
                            self.last_processed_keywords[str(file_path)] = keywords
                            self.last_processed_files.add(str(file_path))
                            self.add_result_to_tree(str(file_path), keywords)
                            save_keywords(str(file_path), keywords, output_dir, self.append_mode.get())
                            for lang in selected_langs:
                                self.log(f"Generated keywords ({lang}): {', '.join(keywords[lang])}")
                    except Exception as e:
                        self.log(f"Error processing {file_path}: {str(e)}")
            
            if not found_files:
                self.log("No image files found in the selected directory")
                
        except Exception as e:
            self.log(f"Error during processing: {str(e)}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def get_ollama_models(self):
        """Get list of available models and update combobox"""
        try:
            # Get Ollama models
            response = requests.get('http://localhost:11434/api/tags')
            if response.status_code == 200:
                data = response.json()
                # Extract model names that contain 'llava' or 'vision'
                ollama_models = [
                    model['name'] for model in data['models'] 
                    if 'llava' in model['name'].lower() or 'vision' in model['name'].lower()
                ]
            else:
                ollama_models = []
                self.log("Failed to get Ollama models")
        except Exception as e:
            ollama_models = []
            self.log(f"Error getting Ollama models: {str(e)}")

        # Add cloud vision models
        all_models = ollama_models + ['gpt-4-vision-preview', 'gemini-pro-vision']
        
        # Update model combobox if it exists
        if hasattr(self, 'model') and self.model:
            current = self.model.get()
            self.model['values'] = all_models
            if current in all_models:
                self.model.set(current)
            elif all_models:
                self.model.set(all_models[0])
        
        self.log(f"Available models: {', '.join(all_models)}")
        return all_models

    def on_model_changed(self, event=None):
        """Handle model selection change"""
        selected_model = self.model.get()
        if selected_model:
            self.config_manager.set_last_model(selected_model)
            # Update generator with new model
            self.generator = ImageKeywordGenerator(model_name=selected_model)
            self.log(f"Selected model: {selected_model}")

    def create_directory_section(self):
        """Create the directory selection section"""
        # Create directory selection frame
        dir_frame = ttk.LabelFrame(self.main_frame, text="Directory Selection", padding="5")
        dir_frame.grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Configure grid weights for directory frame
        dir_frame.columnconfigure(1, weight=1)  # Entry column expands
        dir_frame.columnconfigure(3, weight=1)  # Entry column expands
        
        # Initialize StringVar for directory paths
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        
        # Input directory row
        ttk.Label(dir_frame, text="Input Directory:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(dir_frame, textvariable=self.input_dir).grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(dir_frame, text="Browse", command=self.browse_input).grid(row=0, column=2, padx=5, pady=5)
        
        # Output directory row
        ttk.Label(dir_frame, text="Output Directory:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(dir_frame, textvariable=self.output_dir).grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(dir_frame, text="Browse", command=self.browse_output).grid(row=1, column=2, padx=5, pady=5)

    def create_model_section(self):
        """Create the model selection section"""
        model_frame = ttk.LabelFrame(self.main_frame, text="Model Selection", padding="5")
        model_frame.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Model selection combobox
        ttk.Label(model_frame, text="Model:").grid(row=0, column=0, padx=5, pady=5)
        self.model = ttk.Combobox(model_frame, state='readonly')
        self.model.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        self.model.bind('<<ComboboxSelected>>', self.on_model_changed)
        
        # API Config button
        ttk.Button(model_frame, text="API Config", command=self.show_api_config).grid(row=0, column=2, padx=5, pady=5)
        
        # Get available models
        self.get_ollama_models()

    def create_language_section(self):
        """Create the language selection section"""
        lang_frame = ttk.LabelFrame(self.main_frame, text="Languages", padding="5")
        lang_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Initialize language checkboxes
        self.languages = {}
        languages = {
            'en': 'English',
            'dk': 'Danish',
            'vi': 'Vietnamese'
        }
        
        for i, (code, name) in enumerate(languages.items()):
            var = tk.BooleanVar(value=True if code == 'en' else False)
            cb = ttk.Checkbutton(lang_frame, text=name, variable=var)
            cb.grid(row=0, column=i, padx=10, pady=5)
            self.languages[code] = (cb, var)

    def create_options_section(self):
        """Create the options section"""
        options_frame = ttk.LabelFrame(self.main_frame, text="Options", padding="5")
        options_frame.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Append mode checkbox
        self.append_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame, 
            text="Append to existing keyword files", 
            variable=self.append_mode
        ).grid(row=0, column=0, padx=5, pady=5)

    def create_button_section(self):
        """Create the main action buttons section"""
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        ttk.Button(
            button_frame,
            text="Process Images",
            command=self.process_images
        ).grid(row=0, column=0, padx=5)
        
        ttk.Button(
            button_frame,
            text="Embed Keywords",
            command=self.embed_keywords
        ).grid(row=0, column=1, padx=5)

    def create_results_section(self):
        """Create the results treeview section"""
        # Create treeview with scrollbar
        tree_frame = ttk.Frame(self.main_frame)
        tree_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create treeview
        self.log_tree = ttk.Treeview(
            tree_frame,
            columns=('File', 'English', 'Danish', 'Vietnamese'),
            selectmode='extended'
        )
        
        # Configure columns
        self.log_tree.column('#0', width=100)  # Icon column
        self.log_tree.column('File', width=200)
        self.log_tree.column('English', width=300)
        self.log_tree.column('Danish', width=300)
        self.log_tree.column('Vietnamese', width=300)
        
        # Configure headers
        self.log_tree.heading('File', text='File')
        self.log_tree.heading('English', text='English Keywords')
        self.log_tree.heading('Danish', text='Danish Keywords')
        self.log_tree.heading('Vietnamese', text='Vietnamese Keywords')
        
        # Configure scrollbar
        self.log_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.configure(command=self.log_tree.yview)
        
        # Pack treeview
        self.log_tree.pack(expand=True, fill=tk.BOTH)
        
        # Initialize storage for thumbnails and file mappings
        self.thumbnail_cache = {}
        self.file_to_iid = {}

    def initialize_components(self):
        """Initialize additional components"""
        self.config_manager = ConfigManager()
        self.generator = None  # Will be set when model is selected
