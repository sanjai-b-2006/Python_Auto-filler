import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import os
from datetime import datetime

# Import our existing logic
from form_filler.data_loader import load_data
from form_filler.config_handler import load_mapping_config
from form_filler.filler import FormFiller

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Automated Form Filler")
        self.geometry("700x550")

        # Variables
        self.data_file_path = tk.StringVar()
        self.config_file_path = tk.StringVar()
        self.headless_mode = tk.BooleanVar(value=False)
        self.disable_delay = tk.BooleanVar(value=False)
        
        # Queue for thread communication
        self.log_queue = queue.Queue()

        # Create UI
        self.create_widgets()
        self.after(100, self.process_log_queue)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # File Selection Frame
        file_frame = ttk.LabelFrame(main_frame, text="1. Select Files", padding="10")
        file_frame.pack(fill=tk.X, pady=5)

        ttk.Button(file_frame, text="Select Data File...", command=self.select_data_file).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(file_frame, textvariable=self.data_file_path).grid(row=0, column=1, padx=5, sticky="w")

        ttk.Button(file_frame, text="Select Config File...", command=self.select_config_file).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(file_frame, textvariable=self.config_file_path).grid(row=1, column=1, padx=5, sticky="w")

        # Options Frame
        options_frame = ttk.LabelFrame(main_frame, text="2. Set Options", padding="10")
        options_frame.pack(fill=tk.X, pady=5)
        
        ttk.Checkbutton(options_frame, text="Run in Headless Mode (no browser window)", variable=self.headless_mode).pack(anchor="w")
        ttk.Checkbutton(options_frame, text="Disable Random Delays (faster)", variable=self.disable_delay).pack(anchor="w")
        
        # Control Frame
        control_frame = ttk.LabelFrame(main_frame, text="3. Run Automation", padding="10")
        control_frame.pack(fill=tk.X, pady=5)
        
        self.run_button = ttk.Button(control_frame, text="Start Filling Forms", command=self.start_automation_thread)
        self.run_button.pack(pady=5)

        # Log Frame
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.configure(state='disabled')

    def log(self, message):
        """Puts a message into the queue for the GUI to display."""
        self.log_queue.put(message)

    def process_log_queue(self):
        """Processes messages from the queue and updates the log display."""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.configure(state='normal')
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
                self.log_text.configure(state='disabled')
        except queue.Empty:
            self.after(100, self.process_log_queue)

    def select_data_file(self):
        path = filedialog.askopenfilename(title="Select Data File", filetypes=[("All data files", "*.csv *.json *.xlsx *.xls"), ("CSV files", "*.csv"), ("JSON files", "*.json"), ("Excel files", "*.xlsx;*.xls")])
        if path:
            self.data_file_path.set(os.path.basename(path))
            self._data_full_path = path

    def select_config_file(self):
        path = filedialog.askopenfilename(title="Select Config File", filetypes=[("JSON config files", "*.json")])
        if path:
            self.config_file_path.set(os.path.basename(path))
            self._config_full_path = path

    def start_automation_thread(self):
        if not hasattr(self, '_data_full_path') or not hasattr(self, '_config_full_path'):
            messagebox.showerror("Error", "Please select both a data file and a config file.")
            return
            
        self.run_button.config(state="disabled")
        self.log("--- Starting Automation ---")
        
        # Run the core logic in a separate thread to avoid freezing the GUI
        thread = threading.Thread(target=self.run_automation, daemon=True)
        thread.start()

    def run_automation(self):
        """The core logic that runs in a separate thread."""
        filler = None
        try:
            self.log("Loading data...")
            data_rows = load_data(self._data_full_path)
            self.log(f"Loaded {len(data_rows)} rows of data.")

            self.log("Loading form configuration...")
            config = load_mapping_config(self._config_full_path)
            self.log(f"Configuration loaded for form: {config['form_url']}")

            filler = FormFiller(
                config, 
                randomize_delay=not self.disable_delay.get(), 
                headless=self.headless_mode.get()
            )
            
            total = len(data_rows)
            for i, row in enumerate(data_rows):
                self.log(f"[{i+1}/{total}] Processing row for: {row.get('full_name', 'N/A')}")
                result = filler.fill_form_for_row(row)
                self.log(f"  -> Status: {result['status']} | Reason: {result['reason']}")

        except Exception as e:
            self.log(f"FATAL ERROR: {e}")
            messagebox.showerror("Fatal Error", f"An unexpected error occurred:\n{e}")
        finally:
            if filler:
                filler.close()
            self.log("--- Automation Finished ---")
            # Re-enable the button from the main thread
            self.after(0, lambda: self.run_button.config(state="normal"))

if __name__ == "__main__":
    app = App()
    app.mainloop()