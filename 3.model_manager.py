import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os

CONFIG_FILE = "model_config.json"

def save_config():
    gguf_path = gguf_var.get().strip()
    mmproj_path = mmproj_var.get().strip()
    
    if not gguf_path or not mmproj_path:
        messagebox.showerror("Error", "Both file paths must be selected!")
        return
        
    config_data = {
        "gguf": gguf_path,
        "mmproj": mmproj_path
    }
    
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
        messagebox.showinfo("Success", f"Paths successfully saved to {CONFIG_FILE}!\nYou can now launch the main OCR app.")
        root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save configuration:\n{e}")

# --- Tkinter UI Setup ---
root = tk.Tk()
root.title("Vision Model Manager")
root.geometry("600x200")
root.attributes("-topmost", True)

gguf_var = tk.StringVar()
mmproj_var = tk.StringVar()

# Load existing config if it exists
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            gguf_var.set(data.get("gguf", ""))
            mmproj_var.set(data.get("mmproj", ""))
    except Exception:
        pass

tk.Label(root, text="Select Local Vision Models (GGUF & MMPROJ)", font=("Arial", 12, "bold")).pack(pady=10)

# GGUF Row
f1 = tk.Frame(root)
f1.pack(fill="x", padx=20, pady=5)
tk.Label(f1, text="GGUF Model:", width=12, anchor="w").pack(side="left")
tk.Entry(f1, textvariable=gguf_var, width=50).pack(side="left", padx=5)
tk.Button(f1, text="Browse...", command=lambda: gguf_var.set(filedialog.askopenfilename(filetypes=[("GGUF Files", "*.gguf")]))).pack(side="left")

# MMPROJ Row
f2 = tk.Frame(root)
f2.pack(fill="x", padx=20, pady=5)
tk.Label(f2, text="MMPROJ File:", width=12, anchor="w").pack(side="left")
tk.Entry(f2, textvariable=mmproj_var, width=50).pack(side="left", padx=5)
tk.Button(f2, text="Browse...", command=lambda: mmproj_var.set(filedialog.askopenfilename(filetypes=[("GGUF Files", "*.gguf")]))).pack(side="left")

# Save Button
tk.Button(root, text="Save Configuration", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), command=save_config).pack(pady=15)

root.mainloop()