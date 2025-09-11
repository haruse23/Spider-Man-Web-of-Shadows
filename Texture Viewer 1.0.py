import struct
from tkinter import Tk, Button, filedialog, messagebox, Canvas, Label
from tkinter import ttk
from PIL import Image, ImageTk
import os
import io

# DDS file wrapper constants
DDS_MAGIC = b'DDS '
DDS_HEADER_SIZE = 124
DDS_FLAGS = 0x00021007
DDS_CAPS = 0x1000
DDS_PIXELFORMAT_SIZE = 32
DDS_PF_FLAGS = 0x00000004  # DDPF_FOURCC

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
    
    # DDS header layout (124 bytes total)
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
        0,               # dwPitchOrLinearSize (can be 0)
        0,               # dwDepth
        0,               # dwMipMapCount
        *(0,) * 11,      # dwReserved1
        DDS_PIXELFORMAT_SIZE,  # ddspf.dwSize
        DDS_PF_FLAGS,          # ddspf.dwFlags
        fourcc,                # ddspf.dwFourCC
        0, 0, 0, 0, 0,         # ddspf.dwRGBBitCount and masks (0 for compressed)
        DDS_CAPS,              # dwCaps
        0, 0, 0, 0,            # dwCaps2,3,4 and reserved2
    )

    return DDS_MAGIC + header + raw_data


def open_tex():
    filetypes = [("TEX Files", "*.TEX"), ("All Files", "*.*")]
    
    paths = filedialog.askopenfilenames(title="Select 2 TEX files", filetypes=filetypes)
    
    if len(paths) != 2:
        messagebox.showerror("Error", "Choose exactly two files.")
        return

    print(f"File 0 size: {os.path.getsize(paths[0])} bytes")
    print(f"File 1 size: {os.path.getsize(paths[1])} bytes")

    b1, b2 = open(paths[0], "rb").read(), open(paths[1], "rb").read()

    if len(b1) == 68:
        header, raw = b1, b2
    elif len(b2) == 68:
        header, raw = b2, b1
    else:
        messagebox.showerror("Error", "Neither file appears to be a valid header (68 bytes).")
        return

    width, height, fmt = parse_header_bytes(header)
    if fmt not in FOURCC:
        messagebox.showerror("Error", f"Unsupported format: {fmt}")
        return

    try:
        dds = build_dds(width, height, fmt, raw)
        img = Image.open(io.BytesIO(dds))
        show(img, f"{fmt} {width}x{height}")
    except Exception as e:
        messagebox.showerror("Failed to load:", str(e))

from tkinter import Toplevel

def show(img, title):
    win = Toplevel()
    win.title(title)
    canvas = Canvas(win, width=img.width, height=img.height)
    canvas.pack()
    tk_img = ImageTk.PhotoImage(img)
    canvas.create_image(0, 0, anchor='nw', image=tk_img)
    canvas.image = tk_img  # keep a reference so it doesn’t get GC’d


root = Tk()
root.geometry("800x640")
root.title("TEX Texture Viewer")

Button(root, text="Open TEX components", command=open_tex).pack(pady=20)

root.mainloop()
