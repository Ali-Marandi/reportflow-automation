import customtkinter
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import json
import subprocess
import sys

# Import CustomTkinter and tkdnd2 (assuming it's installed)
# For drag and drop, we'll integrate it with CustomTkinter widgets

class ReportFlowGUI(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("ReportFlow Automation")
        self.geometry("800x600")
        self.config_path = None
        self.output_dir = "reportflow_output"

        # Configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        # Sidebar Frame
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="ReportFlow", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=20)

        self.config_button = customtkinter.CTkButton(self.sidebar_frame, text="Load Config", command=self.load_config_file)
        self.config_button.grid(row=1, column=0, padx=20, pady=10)
        self.run_button = customtkinter.CTkButton(self.sidebar_frame, text="Generate Report", command=self.generate_report, state="disabled")
        self.run_button.grid(row=2, column=0, padx=20, pady=10)
        self.output_button = customtkinter.CTkButton(self.sidebar_frame, text="Open Output Folder", command=self.open_output_folder)
        self.output_button.grid(row=3, column=0, padx=20, pady=10)

        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(
            self.sidebar_frame, values=["Light", "Dark", "System"], command=self.change_appearance_mode_event
        )
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))

        # Main Frame for Content
        self.main_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, rowspan=4, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=0)
        self.main_frame.grid_rowconfigure(1, weight=1)

        self.title_label = customtkinter.CTkLabel(self.main_frame, text="ReportFlow Dashboard", font=customtkinter.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        self.config_info_frame = customtkinter.CTkFrame(self.main_frame)
        self.config_info_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.config_info_frame.grid_columnconfigure(0, weight=1)
        self.config_info_frame.grid_rowconfigure(0, weight=0)
        self.config_info_frame.grid_rowconfigure(1, weight=1)

        self.config_label = customtkinter.CTkLabel(self.config_info_frame, text="No config loaded.", font=customtkinter.CTkFont(size=16, weight="bold"))
        self.config_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.config_text = customtkinter.CTkTextbox(self.config_info_frame, wrap="word")
        self.config_text.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.config_text.insert("end", "Drag and drop your config.json file here or click 'Load Config'.")
        self.config_text.configure(state="disabled")

        self.output_log_frame = customtkinter.CTkFrame(self.main_frame)
        self.output_log_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.output_log_frame.grid_columnconfigure(0, weight=1)
        self.output_log_frame.grid_rowconfigure(0, weight=1)

        self.output_log_label = customtkinter.CTkLabel(self.output_log_frame, text="Output Log:", font=customtkinter.CTkFont(size=16, weight="bold"))
        self.output_log_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.output_log_text = customtkinter.CTkTextbox(self.output_log_frame, wrap="word")
        self.output_log_text.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.output_log_text.configure(state="disabled")

        # Drag and Drop functionality (TkDND integration)
        self.config_text.drop_target_register(tk.DND_FILES)
        self.config_text.dnd_bind('<<Drop>>', self.drop_config_file)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def load_config_file(self):
        file_path = filedialog.askopenfilename(
            title="Select ReportFlow Configuration File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            self.config_path = file_path
            self.display_config()

    def drop_config_file(self, event):
        # TkDND returns paths with {} around them if they contain spaces
        file_path = event.data.strip('{}')
        if file_path.endswith('.json'):
            self.config_path = file_path
            self.display_config()
        else:
            messagebox.showerror("Invalid File", "Please drop a .json configuration file.")

    def display_config(self):
        if self.config_path:
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                self.config_text.configure(state="normal")
                self.config_text.delete("1.0", "end")
                self.config_text.insert("end", json.dumps(config_data, indent=2))
                self.config_text.configure(state="disabled")
                self.config_label.configure(text=f"Config Loaded: {os.path.basename(self.config_path)}")
                self.run_button.configure(state="normal")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load config file: {e}")
                self.config_path = None
                self.run_button.configure(state="disabled")
        else:
            self.config_label.configure(text="No config loaded.")
            self.config_text.configure(state="normal")
            self.config_text.delete("1.0", "end")
            self.config_text.insert("end", "Drag and drop your config.json file here or click 'Load Config'.")
            self.config_text.configure(state="disabled")
            self.run_button.configure(state="disabled")

    def generate_report(self):
        if not self.config_path:
            messagebox.showerror("Error", "Please load a configuration file first.")
            return

        self.output_log_text.configure(state="normal")
        self.output_log_text.delete("1.0", "end")
        self.output_log_text.insert("end", f"Generating report using config: {os.path.basename(self.config_path)}\n")
        self.output_log_text.configure(state="disabled")
        self.update_idletasks()

        try:
            # Ensure the output directory exists
            os.makedirs(self.output_dir, exist_ok=True)

            # Run the reportflow CLI command
            # We need to find the executable path correctly
            # For simplicity, assuming 'reportflow' is in PATH or using direct path
            # In a real .exe, reportflow would be the main executable
            
            # If running from source, need to ensure reportflow is installed -e .
            # Or directly import run_pipeline if this GUI is part of the package
            
            # For this prototype, we'll simulate the CLI call
            # In a real scenario, if this GUI is part of the PyInstaller bundle,
            # it would directly call run_pipeline from the embedded package.
            
            # Find the root of the project to correctly reference the CLI
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(script_dir, '..'))
            
            # Assuming 'reportflow' command is available in PATH after 'pip install .'
            # Or, if this is a PyInstaller bundle, the CLI logic would be integrated.
            
            # For demonstration, let's use a subprocess call to the installed CLI
            command = [sys.executable, "-m", "reportflow.cli", self.config_path, "--output", self.output_dir]
            
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()

            self.output_log_text.configure(state="normal")
            self.output_log_text.insert("end", stdout)
            if stderr:
                self.output_log_text.insert("end", f"Error:\n{stderr}", "error_tag")
            self.output_log_text.configure(state="disabled")
            
            if process.returncode == 0:
                messagebox.showinfo("Success", "Report generated successfully!")
            else:
                messagebox.showerror("Error", "Report generation failed. Check log for details.")

        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            self.output_log_text.configure(state="normal")
            self.output_log_text.insert("end", f"Unexpected Error: {e}\n", "error_tag")
            self.output_log_text.configure(state="disabled")

    def open_output_folder(self):
        if os.path.exists(self.output_dir):
            try:
                if sys.platform == "win32":
                    os.startfile(self.output_dir)
                elif sys.platform == "darwin":
                    subprocess.run(["open", self.output_dir])
                else:
                    subprocess.run(["xdg-open", self.output_dir])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open output folder: {e}")
        else:
            messagebox.showinfo("Info", "Output folder does not exist yet.")

if __name__ == "__main__":
    # Set default appearance mode
    customtkinter.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
    customtkinter.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

    app = ReportFlowGUI()
    app.mainloop()
