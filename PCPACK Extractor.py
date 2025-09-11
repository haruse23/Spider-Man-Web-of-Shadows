import tkinter as tk
from tkinter import filedialog, messagebox

import os
import sys
import types
import lzo

# Import your CLI functions directly
sys.path.append(r"f:\Web of Shadows\image\pc\WebOfShadowsTools-master\python")

import wos.cli as cli
from wos.cli import extract_pcpack, list_pcpack, scan_pcpack_files


def select_file():
    path = filedialog.askopenfilename(filetypes=[("PCPACK files", "*.pcpack")])
    if path:
        entry_input.delete(0, tk.END)
        entry_input.insert(0, path)

def select_folder():
    path = filedialog.askdirectory()
    if path:
        entry_output.delete(0, tk.END)
        entry_output.insert(0, path)

def run_extract():
    infile = entry_input.get()
    outdir = entry_output.get()

    cli.args = types.SimpleNamespace(
        prepend_file_index=prepend_var.get(),
        with_pcapk=pcapk_var.get(),
        quiet=quiet_var.get(),
        force=force_var.get()
    )

    if not infile or not outdir:
        messagebox.showerror("Error", "Please select input file and output folder.")
        return

    try:
        for pack in scan_pcpack_files(infile):
            extract_pcpack(
                pack,
                outdir,
                force=force_var.get(),
                quiet=quiet_var.get(),
                with_pcapk=pcapk_var.get()
            )
        messagebox.showinfo("Success", f"Extracted files to {outdir}")
    except Exception as e:
        messagebox.showerror("Error", str(e))


def run_list():
    infile = entry_input.get()

    cli.args = types.SimpleNamespace(
        prepend_file_index=prepend_var.get(),
        with_pcapk=pcapk_var.get(),
        quiet=quiet_var.get(),
        force=force_var.get()
    )
    
    if not infile:
        messagebox.showerror("Error", "Please select a PCPACK file.")
        return

    try:
        result = []
        for pack in scan_pcpack_files(infile):
            from io import StringIO
            import sys

            mystdout = StringIO()
            mystderr = StringIO()

            old_stdout, old_stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = mystdout, mystderr

            try:
                list_pcpack(pack, quiet=quiet_var.get(), with_pcapk=pcapk_var.get())
            except Exception as e:
                # if list_pcpack itself fails
                result.append(f"[ERROR] {e}")
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr

            output = mystdout.getvalue()
            errors = mystderr.getvalue()
            if output:
                result.append(output)
            if errors:
                result.append(f"[stderr] {errors}")

        # Put into GUI
        output_text.delete("1.0", tk.END)
        output_text.insert(tk.END, "\n".join(result))

    except Exception as e:
        messagebox.showerror("Error", str(e))


# --- GUI Layout ---
root = tk.Tk()
root.title("Spider-Man: Web of Shadows PCPACK Extractor")

# User-configurable options
force_var = tk.BooleanVar(value=True)       # overwrite existing files
quiet_var = tk.BooleanVar(value=False)      # suppress output
prepend_var = tk.BooleanVar(value=False)    # prepend index in names
pcapk_var = tk.BooleanVar(value=True)       # extract nested .pcapk


tk.Label(root, text="Input PCPACK File / Folder:").grid(row=0, column=0, sticky="w")
entry_input = tk.Entry(root, width=50)
entry_input.grid(row=0, column=1)
tk.Button(root, text="Browse", command=select_file).grid(row=0, column=2)

tk.Label(root, text="Output Folder:").grid(row=1, column=0, sticky="w")
entry_output = tk.Entry(root, width=50)
entry_output.grid(row=1, column=1)
tk.Button(root, text="Browse", command=select_folder).grid(row=1, column=2)

# Buttons row (row=2 stays for checkboxes, row=3 for buttons)
tk.Button(root, text="Extract", command=run_extract).grid(row=3, column=1, pady=5)
tk.Button(root, text="List Contents", command=run_list).grid(row=3, column=2, pady=5)

# Option checkboxes (keep them in row=2)
tk.Checkbutton(root, text="Overwrite existing files", variable=force_var).grid(row=2, column=0, sticky="w", padx=5)
tk.Checkbutton(root, text="Quiet mode", variable=quiet_var).grid(row=2, column=1, sticky="w", padx=5)
tk.Checkbutton(root, text="Prepend file index", variable=prepend_var).grid(row=2, column=2, sticky="w", padx=5)
tk.Checkbutton(root, text="Extract nested .pcapk", variable=pcapk_var).grid(row=2, column=3, sticky="w", padx=5)

# Output frame moves to row=4 instead of 3
output_frame = tk.Frame(root)
output_frame.grid(row=4, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")

# Make frame expand
root.grid_rowconfigure(4, weight=1)
root.grid_columnconfigure(1, weight=1)


# Text widget
output_text = tk.Text(output_frame, wrap="none")
output_text.pack(side="left", fill="both", expand=True)

# Vertical scrollbar
scrollbar_y = tk.Scrollbar(output_frame, orient="vertical", command=output_text.yview)
scrollbar_y.pack(side="right", fill="y")
output_text.configure(yscrollcommand=scrollbar_y.set)

# (Optional) Horizontal scrollbar
scrollbar_x = tk.Scrollbar(output_frame, orient="horizontal", command=output_text.xview)
scrollbar_x.pack(side="bottom", fill="x")
output_text.configure(xscrollcommand=scrollbar_x.set)


if __name__ == "__main__":
    try:
        root.mainloop()
    except Exception as e:
        import traceback
        with open("fatal_error.log", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        import tkinter.messagebox as mb
        mb.showerror("Fatal Error", f"The app crashed!\n\nSee fatal_error.log for details.")
        raise

