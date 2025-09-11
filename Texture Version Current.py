import os
import struct
import io
from tkinter import Tk, Canvas, Scrollbar, filedialog, messagebox, StringVar
from tkinter import ttk
from PIL import Image, ImageTk, ImageFile

# DDS constants
DDS_MAGIC = b'DDS '
DDS_HEADER_SIZE = 124
DDS_FLAGS = 0x00021007
DDS_CAPS = 0x1000
DDS_PIXELFORMAT_SIZE = 32
DDS_PF_FLAGS = 0x00000004

FOURCC = {
    'DXT1': b'DXT1',
    'DXT3': b'DXT3',
    'DXT5': b'DXT5',
}

def parse_header_bytes(header):
    width = struct.unpack_from('<I', header, 0x18)[0]
    height = struct.unpack_from('<I', header, 0x1C)[0]
    fmt = header[0x28:0x2C].decode('ascii', errors='ignore').strip('\x00')
    return width, height, fmt

def build_dds(width, height, fmt, raw_data):
    fourcc = FOURCC[fmt]

    block_size = 8 if fmt == 'DXT1' else 16
    expected_size = ((width + 3) // 4) * ((height + 3) // 4) * block_size

    # If raw data is longer or shorter, trim or pad it
    if len(raw_data) < expected_size:
        print(f"[!] Warning: raw data too small. Padding with {expected_size - len(raw_data)} bytes.")
        raw_data += b'\x00' * (expected_size - len(raw_data))
    elif len(raw_data) > expected_size:
        print(f"[!] Warning: raw data too large. Trimming to {expected_size} bytes.")
        raw_data = raw_data[:expected_size]

    # Correct DDS pitchOrLinearSize is the size of top mipmap level
    pitch_or_linear_size = ((width + 3) // 4) * block_size

    header = struct.pack(
        '<I'     # dwSize
        'I'      # dwFlags
        'I'      # dwHeight
        'I'      # dwWidth
        'I'      # dwPitchOrLinearSize
        'I'      # dwDepth
        'I'      # dwMipMapCount
        '11I'    # dwReserved1[11]
        'I'      # ddspf.dwSize
        'I'      # ddspf.dwFlags
        '4s'     # ddspf.dwFourCC
        '5I'     # ddspf.dwRGBBitCount + dwRBitMask + dwGBitMask + dwBBitMask + dwABitMask
        'I'      # dwCaps
        'I'      # dwCaps2
        'I'      # dwCaps3
        'I'      # dwCaps4
        'I'      # dwReserved2
        ,
        124,             # dwSize
        DDS_FLAGS,       # dwFlags
        height,          # dwHeight
        width,           # dwWidth
        pitch_or_linear_size,  # dwPitchOrLinearSize
        0,               # dwDepth
        0,               # dwMipMapCount
        *(0,) * 11,      # dwReserved1
        DDS_PIXELFORMAT_SIZE,  # ddspf.dwSize
        DDS_PF_FLAGS,          # ddspf.dwFlags
        fourcc,                # ddspf.dwFourCC
        0, 0, 0, 0, 0,         # RGBBitCount and masks (unused)
        DDS_CAPS,              # dwCaps
        0, 0, 0, 0             # dwCaps2,3,4,reserved2
    )

    return DDS_MAGIC + header + raw_data

def match_header_and_raw(selected_path, all_tex_files):
    selected_size = os.path.getsize(selected_path)
    selected_name = os.path.basename(selected_path)

    # Take everything before the last ".0" or ".1"
    if selected_name.endswith(".0.tex") or selected_name.endswith(".1.tex"):
        base_prefix = selected_name.rsplit(".", 2)[0]  # split from right, max 2 split
    else:
        raise Exception("Invalid TEX filename")


    if "0" in selected_name and selected_size == 68:
        header = open(selected_path, "rb").read()
        # Look for matching component1
        for f in all_tex_files:
            if f != selected_path and f"{base_prefix}.1.tex" in f:
                raw = open(f, "rb").read()
                return header, raw
        raise Exception("No matching raw file found for component0.")

    elif "1" in selected_name and selected_size > 68:
        raw = open(selected_path, "rb").read()
        # Look for matching component0
        for f in all_tex_files:
            if f != selected_path and f"{base_prefix}.0.tex" in f:
                header = open(f, "rb").read()
                return header, raw
        raise Exception("No matching header file found for component1.")

    raise Exception("Invalid TEX file size or naming.")




def load_tex_pair(path):
    selected_size = os.path.getsize(path)
    folder = os.path.dirname(path)
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".tex")]

    if selected_size == 68:
        header = open(path, "rb").read()
        for f in files:
            if f != path and os.path.getsize(f) > 68:
                raw = open(f, "rb").read()
                break
        else:
            raise Exception("No matching raw file found.")
    elif selected_size > 68:
        raw = open(path, "rb").read()
        for f in files:
            if f != path and os.path.getsize(f) == 68:
                header = open(f, "rb").read()
                break
        else:
            raise Exception("No matching header file found.")
    else:
        raise Exception("Invalid TEX file size.")

    width, height, fmt = parse_header_bytes(header)
    dds = build_dds(width, height, fmt, raw)
    return Image.open(io.BytesIO(dds)), fmt, width, height


# ---------------- GUI ----------------
root = Tk()
root.geometry("1000x600")
root.title("TEX File Browser")

# ---------------- Left Frame ----------------
left_frame = ttk.Frame(root)
left_frame.pack(side="left", fill="y")

# Search entry at top
search_entry = ttk.Entry(left_frame)
search_var = StringVar(search_entry, "")
search_entry.config(textvariable = search_var)
search_entry.pack(side="top", fill="x", padx=5, pady=5)


# Frame for treeview + scrollbar
tree_frame = ttk.Frame(left_frame)
tree_frame.pack(side="top", fill="both", expand=True)

# Treeview
tree = ttk.Treeview(tree_frame)
tree.pack(side="left", fill="both", expand=True)
tree["columns"] = ("fullpath",)
tree.column("#0", width=250)
tree.heading("#0", text="Files")

# Scrollbar
scroll = Scrollbar(tree_frame, command=tree.yview)
scroll.pack(side="right", fill="y")
tree.configure(yscrollcommand=scroll.set)

# Store all files for filtering
all_files = []

def populate_tree(dir_path, parent=""):
    global all_files
    try:
        entries = sorted(os.listdir(dir_path))
        for entry in entries:
            full_path = os.path.join(dir_path, entry)
            is_dir = os.path.isdir(full_path)
            oid = tree.insert(parent, "end", text=entry, open=False)
            tree.set(oid, "fullpath", full_path)
            if not is_dir:
                all_files.append((oid, entry, full_path))
            if is_dir:
                populate_tree(full_path, oid)
    except Exception:
        pass

# Filter function
def filter_tree(*args):
    query = search_var.get().lower()
    for oid, name, full_path in all_files:
        if query in name.lower():
            parent = tree.parent(oid)
            tree.reattach(oid, parent, "end")  # reattach to its parent
        else:
            tree.detach(oid)  # hide item

search_var.trace_add("write", filter_tree)
# ---------------- Right Frame ----------------
preview_canvas = Canvas(root, bg="gray")
preview_canvas.pack(side="right", fill="both", expand=True)
preview_canvas.image_ref = None


def show_image_on_canvas(img, label):
    preview_canvas.delete("all")
    canvas_width = preview_canvas.winfo_width()
    canvas_height = preview_canvas.winfo_height()

    # Optional: resize image to fit canvas if it's too large
    max_width = min(canvas_width, 800)
    max_height = min(canvas_height, 800)

    img.thumbnail((max_width, max_height), Image.LANCZOS)
    tk_img = ImageTk.PhotoImage(img)
    preview_canvas.create_image(canvas_width // 2, canvas_height // 2, anchor="center", image=tk_img)
    preview_canvas.image_ref = tk_img
    root.title(f"TEX Viewer - {label}")


def populate_tree(folder, parent=""):
    global all_files
    if parent == "":  # top-level call, clear tree
        tree.delete(*tree.get_children())
        all_files = []

    for entry in sorted(os.listdir(folder)):
        full_path = os.path.join(folder, entry)
        is_dir = os.path.isdir(full_path)
        oid = tree.insert(parent, "end", text=entry, open=False)
        tree.set(oid, "fullpath", full_path)
        if not is_dir:
            all_files.append((oid, entry, full_path))
        if is_dir:
            populate_tree(full_path, oid)
            

def on_select(event):
    item = tree.selection()[0]
    path = tree.item(item, "values")[0]

    if not path.lower().endswith(".tex") or not os.path.isfile(path):
        return

    try:
        folder = os.path.dirname(path)
        files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".tex")]

        # Use the new smart matching logic
        header, raw = match_header_and_raw(path, files)

        width, height, fmt = parse_header_bytes(header)
        if fmt not in FOURCC:
            raise Exception(f"Unsupported format: {fmt}")

        # Compute expected size for safety
        expected_size = ((width + 3) // 4) * ((height + 3) // 4)
        if fmt == 'DXT1':
            expected_size *= 8
        else:
            expected_size *= 16

        # Pad raw data if too small
        if len(raw) < expected_size:
            raw += b'\x00' * (expected_size - len(raw))

        dds = build_dds(width, height, fmt, raw)
        img = Image.open(io.BytesIO(dds))
        show_image_on_canvas(img, f"{fmt} {width}x{height}")


    except Exception as e:
        messagebox.showerror("Error", str(e))



tree.bind("<<TreeviewSelect>>", on_select)

def browse_folder():
    global all_files
    folder_path = filedialog.askdirectory(title="Select a folder to browse")
    if folder_path:
        # Clear tree and file list
        for item in tree.get_children():
            tree.delete(item)
        all_files = []
        populate_tree(folder_path)
        filter_tree()
        root.title(f"TEX Viewer - {folder_path}")

# Button above the search bar
browse_btn = ttk.Button(left_frame, text="Open Folder", command=browse_folder)
browse_btn.pack(fill="x", padx=5, pady=5)


root.mainloop()