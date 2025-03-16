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
import tkinter.font as tkFont

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
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="5")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure main frame grid weights
        self.main_frame.columnconfigure(1, weight=1)  # Middle column expands
        self.main_frame.rowconfigure(6, weight=2)     # TreeView row expands more
        self.main_frame.rowconfigure(8, weight=1, minsize=150)  # Increased minimum height for status
        
        
        # Create UI sections in correct order
        self.create_directory_section()    # Row 0-1
        self.create_model_section()        # Row 2
        self.create_language_section()     # Row 3
        self.create_options_section()      # Row 4
        self.create_button_section()       # Row 5
        self.create_results_section()      # Row 6-7
        self.create_status_section()       # Row 8
        
        # Initialize other components
        self.initialize_components()
        
        # Log initialization
        self.log("Application initialized successfully")
    
    def setup_window(self):
        """Configure the main window size and position"""
        window_width = 1600
        window_height = 900
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        self.root.minsize(800, 700)  # Prevent window from being too small
        self.root.resizable(True, True)
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
    
    def create_status_section(self):
        """Create the status/log area"""
        # Create a labeled frame for the status area with toggle button
        self.status_frame = ttk.LabelFrame(self.main_frame, padding="5")
        self.status_frame.grid(row=8, column=0, columnspan=3, padx=5, pady=(5,0), sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create custom label widget with toggle button
        label_frame = ttk.Frame(self.status_frame)
        ttk.Label(label_frame, text="Process Log").pack(side=tk.LEFT, padx=5)
        self.toggle_status_button = ttk.Button(label_frame, text="Hide", command=self.toggle_status_visibility, width=5)
        self.toggle_status_button.pack(side=tk.RIGHT, padx=5)
        self.status_frame['labelwidget'] = label_frame
        
        # Configure grid weights for status frame
        self.status_frame.columnconfigure(0, weight=1)
        self.status_frame.rowconfigure(0, weight=1)
        
        # Create scrolled text widget for status messages
        self.status_area = ScrolledText(
            self.status_frame,
            height=12,
            wrap=tk.WORD,
            background='white',
            font=('Consolas', 9)
        )
        self.status_area.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def toggle_status_visibility(self):
        """Toggle visibility of the status area"""
        if self.status_area.winfo_ismapped():
            self.status_area.grid_remove()
            self.toggle_status_button.config(text="Show")
        else:
            self.status_area.grid()
            self.toggle_status_button.config(text="Hide")

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
                    target_width = 50
                    target_height = int(target_width / aspect_ratio)
                else:
                    # Portrait image   
                    target_height = 50
                    target_width = int(target_height * aspect_ratio)
                
                img_resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img_resized)
                self.thumbnail_cache[file_path] = photo
            
           # Get column widths
            english_width = self.log_tree.column('english', 'width')
            danish_width = self.log_tree.column('danish', 'width')
            vietnamese_width = self.log_tree.column('vietnamese', 'width')
            
            # Prepare values with wrapped text
            values = [
                Path(file_path).name,  # filename
                self.wrap_text(', '.join(keywords.get('en', [])), english_width // 8),  # english keywords
                self.wrap_text(', '.join(keywords.get('dk', [])), danish_width // 8),  # danish keywords
                self.wrap_text(', '.join(keywords.get('vi', [])), vietnamese_width // 8)   # vietnamese keywords
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
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
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

    def get_lm_studio_models(self):
        """Get list of available models from LM-studio server"""
        try:
            # Get LM-studio models
            response = requests.get('http://localhost:1234/v1/models')
            if response.status_code == 200:
                data = response.json()
                # Extract model names
                lm_studio_models = [model['id'] for model in data['data']]
            else:
                lm_studio_models = []
                self.log("Failed to get LM-studio models")
        except Exception as e:
            lm_studio_models = []
            self.log(f"Error getting LM-studio models: {str(e)}")
            
        return lm_studio_models

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

        # Get LM-studio models
        lm_studio_models = self.get_lm_studio_models()
        if lm_studio_models:
            # Add 'lmstudio:' prefix to differentiate from Ollama models
            lm_studio_models = [f"lmstudio:{model}" for model in lm_studio_models]
            self.log(f"Found {len(lm_studio_models)} LM-studio models")

        # Add cloud vision models
        all_models = ollama_models + lm_studio_models + ['gpt-4-vision-preview', 'gemini-pro-vision']
        
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
        button_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        # Process Images button
        process_button = ttk.Button(
            button_frame,
            text="Process Images",
            command=self.process_images
        )
        process_button.grid(row=0, column=0, padx=5)
        
        # Embed Keywords button
        embed_button = ttk.Button(
            button_frame,
            text="Embed Keywords",
            command=self.embed_keywords
        )
        embed_button.grid(row=0, column=1, padx=5)
        
        # Highlight buttons
        process_button.configure(style='Highlight.TButton')
        embed_button.configure(style='Highlight.TButton')

        # Add style configuration for highlighted buttons
        style = ttk.Style()
        bold_font = tkFont.Font(weight='bold')
        style.configure('Highlight.TButton', font=bold_font)

    def create_results_section(self):
        """Create the results treeview section"""
        # Create treeview with scrollbars
        tree_frame = ttk.Frame(self.main_frame)
        tree_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for tree_frame
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        # Configure style for fixed row height
        style = ttk.Style()
        style.configure('Treeview', rowheight=75)
        
        # Create treeview
        columns = ('filename', 'english', 'danish', 'vietnamese')
        self.log_tree = ttk.Treeview(
            tree_frame,  # Changed parent to tree_frame
            columns=columns,
            show='tree headings',
            height=20,
            selectmode='extended',
            style="Treeview"
        )
        
        # Create scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.log_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.log_tree.xview)
        
        # Configure treeview scrolling
        self.log_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout for treeview and scrollbars
        self.log_tree.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.E, tk.W))
        
        # Configure columns
        self.log_tree.column('#0', width=100)  # Icon column
        self.log_tree.column('filename', width=200)
        self.log_tree.column('english', width=300)
        self.log_tree.column('danish', width=300)
        self.log_tree.column('vietnamese', width=300)
        
        # Configure headers
        self.log_tree.heading('#0', text='Preview')
        self.log_tree.heading('filename', text='File')
        self.log_tree.heading('english', text='English Keywords')
        self.log_tree.heading('danish', text='Danish Keywords')
        self.log_tree.heading('vietnamese', text='Vietnamese Keywords')
        
        # Initialize storage for thumbnails and file mappings
        self.thumbnail_cache = {}
        self.file_to_iid = {}

    def initialize_components(self):
        """Initialize additional components"""
        self.config_manager = ConfigManager()
        self.generator = None  # Will be set when model is selected
