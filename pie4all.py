import os
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import importlib.util
import subprocess
import logging
import re
import asyncio

logging.basicConfig(level=logging.DEBUG)

# Function to check if a module is installed
def is_module_installed(module_name):
    return importlib.util.find_spec(module_name) is not None

# Function to find imports in a file
def find_imports_in_files(file_path):
    imports_found = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                if line.startswith("import ") or line.startswith("from "):
                    parts = line.split()
                    if "import" in parts:
                        module = parts[1].split('.')[0]
                        imports_found.add(module)
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
    return imports_found

# Function to scan files and update progress
def scan_files_with_progress(directory, progress_callback):
    imports_to_install = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                imports_found = find_imports_in_files(file_path)
                new_imports = [imp for imp in imports_found if not is_module_installed(imp)]
                imports_to_install.extend(new_imports)
                progress_callback(file, new_imports)
    return imports_to_install

# Function to check if the module name is valid (skip module names with "_")
def is_valid_module_name(name):
    return re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name) is not None and not name.startswith("_")

# Function to install a module using pip from a specific directory
def install_module_from_directory(module_name, install_directory):
    try:
        result = subprocess.check_output(
            [sys.executable, "-m", "pip", "install", module_name],
            stderr=subprocess.STDOUT,
            cwd=install_directory,  # Set the working directory
            text=True
        )
        return f"Installed {module_name}\n{result}"
    except subprocess.CalledProcessError as e:
        return f"Failed to install {module_name}: {e.output}"

# Function to generate pip commands for missing modules
def generate_pip_commands(modules, install_directory):
    return [
        f"pip install {module} || echo Failed to install {module}"
        for module in modules
    ]

# Main GUI class
class ModuleScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PY4ALL")

        # Set the background color for the window (enterprise blue)
        self.root.configure(bg='#2A4D8B')

        # GUI elements
        self.label = tk.Label(root, text="Select a directory to scan:", bg='#2A4D8B', fg='white', font=('Arial', 12))
        self.label.pack(pady=5)

        self.directory_entry = tk.Entry(root, width=50)
        self.directory_entry.pack(pady=5)

        self.browse_button = tk.Button(root, text="Browse", command=self.browse_directory, bg='#0A2463', fg='white', font=('Arial', 10))
        self.browse_button.pack(pady=5)

        self.scan_button = tk.Button(root, text="Scan", command=self.start_scan, bg='#0A2463', fg='white', font=('Arial', 10))
        self.scan_button.pack(pady=5)

        self.output_text = tk.Text(root, height=10, width=60, state=tk.DISABLED)
        self.output_text.pack(pady=10)

        self.listbox = tk.Listbox(root, height=10, width=50)
        self.listbox.pack(pady=5)

        self.install_button = tk.Button(root, text="Install All Missing Modules", command=self.install_all_modules, bg='#0A2463', fg='white', font=('Arial', 10))
        self.install_button.pack(pady=5)

        self.progress_label = tk.Label(root, text="", bg='#2A4D8B', fg='white', font=('Arial', 10))
        self.progress_label.pack(pady=5)

        # About button
        self.about_button = tk.Button(root, text="About", command=self.show_about, bg='#0A2463', fg='white', font=('Arial', 10))
        self.about_button.pack(pady=5)

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.directory_entry.delete(0, tk.END)
            self.directory_entry.insert(0, directory)

    def start_scan(self):
        directory = self.directory_entry.get()
        if not directory:
            messagebox.showerror("Error", "Please select a directory to scan.")
            return

        self.output_text.configure(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.listbox.delete(0, tk.END)
        self.progress_label.config(text="Scanning...")

        # Run the scan in a separate thread
        scan_thread = threading.Thread(target=self.scan_directory, args=(directory,))
        scan_thread.start()

    def scan_directory(self, directory):
        def update_progress(file, new_imports):
            self.root.after(0, lambda: self.output_text.insert(tk.END, f"Scanned: {file}\n"))
            if new_imports:
                self.root.after(0, lambda: self.output_text.insert(tk.END, f"Missing: {', '.join(new_imports)}\n"))

        imports_to_install = scan_files_with_progress(directory, update_progress)
        self.root.after(0, self.display_results, imports_to_install)

    def display_results(self, imports_to_install):
        self.output_text.insert(tk.END, "\nScan completed.\n")
        if imports_to_install:
            for module in set(imports_to_install):
                if is_valid_module_name(module):  # Only show valid modules
                    self.listbox.insert(tk.END, module)
            self.output_text.insert(tk.END, "Missing modules listed in the box below.\n")
        else:
            self.output_text.insert(tk.END, "No missing modules found.\n")

        self.output_text.configure(state=tk.DISABLED)
        self.progress_label.config(text="Scan completed.")

    def install_all_modules(self):
        # Create the second window for showing installation results
        install_window = tk.Toplevel(self.root)
        install_window.title("Installation Results")
        
        # Set the window size to cover almost the whole screen
        screen_width = install_window.winfo_screenwidth()
        screen_height = install_window.winfo_screenheight()
        install_window.geometry(f"{int(screen_width * 0.8)}x{int(screen_height * 0.8)}")  # 80% of screen width/height

        install_text = tk.Text(install_window, height=10, width=60, state=tk.NORMAL)
        install_text.pack(pady=10)
        install_text.config(width=screen_width, height=screen_height)

        # Get all the modules from the listbox
        selected_modules = [self.listbox.get(i) for i in range(self.listbox.size())]

        if not selected_modules:
            messagebox.showinfo("Info", "No modules to install.")
            return

        self.progress_label.config(text="Installing modules...")

        # Set the directory where pip will run
        install_directory = r"enter your dir here"

        # Generate pip commands for the missing modules
        pip_commands = generate_pip_commands(selected_modules, install_directory)

        # Run installations asynchronously and show results in the second window
        asyncio.run(self.run_pip_commands(pip_commands, install_text, install_directory))

        self.progress_label.config(text="Installation completed.")

    async def run_pip_commands(self, pip_commands, install_text, install_directory):
        for command in pip_commands:
            result = await asyncio.to_thread(self.run_command, command, install_directory)
            install_text.insert(tk.END, f"{result}\n")
            install_text.yview(tk.END)

    def run_command(self, command, install_directory):
        """Run a pip install command in the background from the specified directory"""
        try:
            result = subprocess.check_output(
                command,
                stderr=subprocess.STDOUT,
                shell=True,
                cwd=install_directory,  # Set the working directory
                text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            return f"Error: {e.output}"

    def show_about(self):
        about_message = "© 2024 SIG Labs Peter De Ceuster\nv7.1 PY4ALL\n\nAll rights reserved."
        messagebox.showinfo("About", about_message)

# Initialize the app
if __name__ == "__main__":
    root = tk.Tk()
    app = ModuleScannerApp(root)
    root.mainloop()
