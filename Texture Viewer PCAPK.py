import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import io
import struct
from pcapk import APKFArchive
import os
import tempfile
import subprocess
import os
import shutil
from tkinter import filedialog, messagebox
import zipfile


class TextureViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("PCAPK Texture Viewer")

        self.archive = None
        self.textures = []

        # UI layout
        self.setup_ui()

    def setup_ui(self):
        frame = ttk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True)

        # Left panel for search + listbox
        left_panel = ttk.Frame(frame)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)

        # Search Bar
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.update_file_list_from_search)
        search_entry = ttk.Entry(left_panel, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, padx=5, pady=5)

        # Frame for listbox + scrollbar
        listbox_frame = ttk.Frame(left_panel)
        listbox_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # File List with scrollbar
        self.file_listbox = tk.Listbox(listbox_frame, width=40, yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.file_listbox.yview)

        self.file_listbox.bind('<<ListboxSelect>>', self.on_texture_select)



        # Image Display
        self.image_label = tk.Label(frame, text="No texture loaded")
        self.image_label.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Info
        self.info_label = tk.Label(frame, text="", justify=tk.LEFT, anchor="nw")
        self.info_label.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)


        # Menu
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open PCAPK...", command=self.open_file)
        filemenu.add_separator()
        filemenu.add_command(label="Export Selected to TEX...", command=self.export_selected_tex)
        filemenu.add_command(label="Export Selected to DDS...", command=self.export_selected_dds)
        filemenu.add_command(label="Export Selected to PNG...", command=self.export_selected_png)
        filemenu.add_command(label="Export All to TEX...", command=self.export_all_tex)
        filemenu.add_command(label="Export All to DDS...", command=self.export_all_dds)
        filemenu.add_command(label="Export All to PNG...", command=self.export_all_png)

        filemenu.add_separator()
        filemenu.add_command(label="Replace Selected with DDS...", command=self.replace_selected_with_dds)
        filemenu.add_separator()
        filemenu.add_command(label="Save As/Export PCAPK...", command=self.save_archive)

        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[("PCAPK files", "*.pcapk"), ("All files", "*.*")])
        if not path:
            return

        try:
            with open(path, 'rb') as f:
                data = f.read()

            self.archive = APKFArchive(data)
            self.textures = [f for f in self.archive.files("TEX")]
            self.filtered_textures = self.textures.copy()  # Add this line

            self.file_listbox.delete(0, tk.END)
            for tex in self.filtered_textures:
                self.file_listbox.insert(tk.END, tex.filename)


        except Exception as e:
            messagebox.showerror("Error", f"Failed to load PCAPK:\n{e}")


    def update_file_list_from_search(self, *args):
        query = self.search_var.get().lower()
        self.file_listbox.delete(0, tk.END)
        self.filtered_textures = [tex for tex in self.textures if query in tex.filename.lower()]  # Filter

        for tex in self.filtered_textures:
            self.file_listbox.insert(tk.END, tex.filename)


    def on_texture_select(self, event):
        selection = self.file_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        tex_file = self.filtered_textures[index]  # Use filtered list

        try:
            header = tex_file.components[0]
            data = tex_file.components[1]

            width = struct.unpack_from("<I", header, 0x18)[0]
            height = struct.unpack_from("<I", header, 0x1C)[0]
            mipMapCount = struct.unpack_from("<I", header, 0x24)[0]
            fourCC_bytes = header[0x28:0x2C]
            fourCC_int = struct.unpack_from("<I", header, 0x28)[0]

            if fourCC_bytes == b'DXT1':
                img = decode_dxt1(width, height, data)
            elif fourCC_bytes == b'DXT3':
                img = decode_dxt3(width, height, data)
            elif fourCC_bytes == b'DXT5':
                img = decode_dxt5(width, height, data)
            elif fourCC_int == 21:
                img = decode_a8r8g8b8(width, height, data)
            elif fourCC_int == 22:
                img = decode_x8r8g8b8(width, height, data)
            elif fourCC_int == 50:
                img = decode_l8(width, height, data)
            else:
                raise NotImplementedError(f"Format {fourCC_bytes} not supported yet")



            img_tk = ImageTk.PhotoImage(img)
            self.image_label.config(image=img_tk)
            self.image_label.image = img_tk

        except Exception as e:
            messagebox.showerror("Error", f"Failed to render texture:\n{e}")


        info_text = (
                        f"Filename: {tex_file.filename}\n"
                        f"Width: {width}\n"
                        f"Height: {height}\n"
                        f"Format: {fourCC_bytes.decode('ascii')}\n"
                        f"Mipmaps: {mipMapCount}\n"
                        f"Data Size: {len(data)} bytes"
                    )
        self.info_label.config(text=info_text)




    def export_selected_dds(self):
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("No selection", "Please select a texture.")
            return

        tex_file = self.filtered_textures[selection[0]]
        try:
            dds_bytes = convertTEXtoDDS(tex_file)
            out_path = filedialog.asksaveasfilename(defaultextension=".dds", filetypes=[("DDS Files", "*.dds")])
            if out_path:
                with open(out_path, "wb") as f:
                    f.write(dds_bytes)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export DDS:\n{e}")

    def export_selected_png(self):
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("No selection", "Please select a texture.")
            return

        tex_file = self.filtered_textures[selection[0]]
        try:
            img = decode_tex_to_image(tex_file)
            out_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Files", "*.png")])
            if out_path:
                img.save(out_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export PNG:\n{e}")


    def export_all_dds(self):
        dir_path = filedialog.askdirectory()
        if not dir_path:
            return

        for tex in self.textures:
            try:
                dds_bytes = convertTEXtoDDS(tex)
                safe_name = os.path.splitext(tex.filename)[0]
                out_path = os.path.join(dir_path, safe_name + ".dds")
                with open(out_path, "wb") as f:
                    f.write(dds_bytes)
            except Exception as e:
                print(f"Failed to export {tex.filename} to DDS: {e}")

    def export_all_png(self):
        dir_path = filedialog.askdirectory()
        if not dir_path:
            return

        for tex in self.textures:
            try:
                img = decode_tex_to_image(tex)
                safe_name = os.path.splitext(tex.filename)[0]
                out_path = os.path.join(dir_path, safe_name + ".png")
                img.save(out_path)
            except Exception as e:
                print(f"Failed to export {tex.filename} to PNG: {e}")


    def load_dds_as_image(self, dds_bytes):
        # Skip the 4-byte magic ('DDS ') and 124-byte header
        header = dds_bytes[4:128]
        data = dds_bytes[128:]

        height, width = struct.unpack_from("<II", header, 8)
        fourCC_bytes = header[84:88]
        fourCC_int = struct.unpack_from("<I", header, 0x54)[0]

        if fourCC_bytes == b'DXT1':
            return decode_dxt1(width, height, data)
        elif fourCC_bytes == b'DXT3':
            return decode_dxt3(width, height, data)
        elif fourCC_bytes == b'DXT5':
            return decode_dxt5(width, height, data)
        elif fourCC_int == 21:
            return decode_a8r8g8b8(width, height, data)
        elif fourCC_int == 22:
            return decode_x8r8g8b8(width, height, data)
        elif fourCC_int == 50:
            return decode_l8(width, height, data)
        else:
            raise NotImplementedError(f"Unsupported DDS format: {fourCC}")
        

    
    def replace_selected_with_dds(self):
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("No selection", "Please select a texture to replace.")
            return

        tex_file = self.filtered_textures[selection[0]]

        # Open DDS file dialog
        dds_path = filedialog.askopenfilename(filetypes=[("DDS files", "*.dds")])
        if not dds_path:
            return

        try:
            with open(dds_path, "rb") as f:
                dds_bytes = f.read()

            if len(dds_bytes) < 128:
                raise ValueError("DDS file too small or corrupted")

            dds_header = dds_bytes[:128]
            dds_image_data = dds_bytes[128:]

            # Your TEX header as bytes, unchanged
            tex_header = tex_file.components[0]

            # Optionally, patch TEX header with new image size fields
            # For example, if your TEX header at offset 8-11 stores image size, update it:
            import struct
            image_size = len(dds_image_data)
            # Assuming offset 8 in header is a 4-byte uint image size field
            tex_header = bytearray(tex_header)
            struct.pack_into("<I", tex_header, 8, image_size)  # patch image size in header
            tex_header = bytes(tex_header)

            # Replace image data in components
            tex_file.components[0] = tex_header
            tex_file.components[1] = dds_image_data

            # Refresh viewer (assuming your viewer method handles reading components)
            self.on_texture_select(None)

            messagebox.showinfo("Success", "Texture replaced with DDS successfully.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to replace texture:\n{e}")


    def convert_dds_to_tex(self, dds_bytes):
        # Validate DDS header
        if not dds_bytes.startswith(b"DDS "):
            raise ValueError("Not a valid DDS file")

        header = dds_bytes[4:128]
        data = dds_bytes[128:]

        # Extract width, height, format etc.
        width, height = struct.unpack_from("<II", header, 8)
        fourCC = header[84:88]

        # Build your TEX header accordingly (this depends on TEX specs)
        # For now, let's assume you can copy DDS header directly for TEX header
        tex_header = bytearray(128)
        # Fill tex_header with your format specifics, e.g. width, height, format etc.
        # This is just a placeholder and needs your actual TEX format details

        # For now, let's reuse the DDS header (adjust if your TEX header is different)
        tex_header[:] = header

        return bytes(tex_header), data
    

    def convert_png_to_tex(self, pil_img, tex_file):
        width, height = pil_img.size

        # You must pick a format to convert to; here we just do raw BGRA
        raw_data = pil_img.tobytes("raw", "BGRA")

        # Create your TEX header (modify fields accordingly)
        header = bytearray(tex_file.components[0])  # copy existing header to preserve format

        # Update header width and height (offsets depend on your TEX spec)
        struct.pack_into("<I", header, 0x18, width)
        struct.pack_into("<I", header, 0x1C, height)

        # Update other header fields if needed (format, mipmaps, etc)

        # For uncompressed formats, raw_data can be used directly
        # For compressed formats, you need to compress raw_data first (which is non-trivial)

        return bytes(header), raw_data


    def export_selected_tex(self):
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("No selection", "Please select a texture.")
            return

        tex_file = self.filtered_textures[selection[0]]
        base_name = os.path.splitext(tex_file.filename)[0]

        dir_path = filedialog.askdirectory()
        if not dir_path:
            return

        try:
            # Export header
            header_path = os.path.join(dir_path, base_name + ".0.tex")
            with open(header_path, "wb") as f:
                f.write(tex_file.components[0])

            # Export image data
            data_path = os.path.join(dir_path, base_name + ".1.tex")
            with open(data_path, "wb") as f:
                f.write(tex_file.components[1])

            messagebox.showinfo(
                "Success",
                f"Exported header and data separately:\n{header_path}\n{data_path}"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to export TEX components:\n{e}")

    def export_all_tex(self):
        dir_path = filedialog.askdirectory()
        if not dir_path:
            return

        for tex in self.textures:
            base_name = os.path.splitext(tex.filename)[0]
            try:
                header_path = os.path.join(dir_path, base_name + ".0.tex")
                data_path = os.path.join(dir_path, base_name + ".1.tex")

                with open(header_path, "wb") as f:
                    f.write(tex.components[0])

                with open(data_path, "wb") as f:
                    f.write(tex.components[1])

            except Exception as e:
                print(f"Failed to export {tex.filename} components: {e}")

        messagebox.showinfo(
            "Success",
            f"Exported {len(self.textures)} textures as separate header/data files to:\n{dir_path}"
        )




    def save_archive(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".pcapk", filetypes=[("PCAPK files", "*.pcapk")])
        if not save_path:
            return

        with open(save_path, "wb") as f:
            f.write(self.archive.serialize())

                        



    
def decode_dxt1(width, height, data):
    def _rgb565_to_rgb888(c):
        r = ((c >> 11) & 0x1f) << 3
        g = ((c >> 5) & 0x3f) << 2
        b = (c & 0x1f) << 3
        return (r, g, b)

    img = Image.new("RGBA", (width, height))
    pixels = img.load()

    block_width = (width + 3) // 4
    block_height = (height + 3) // 4
    i = 0

    for by in range(block_height):
        for bx in range(block_width):
            c0, c1 = struct.unpack_from("<HH", data, i)
            i += 4
            bits = struct.unpack_from("<I", data, i)[0]
            i += 4

            colors = []
            c0_rgb = _rgb565_to_rgb888(c0)
            c1_rgb = _rgb565_to_rgb888(c1)
            colors.append(c0_rgb + (255,))
            colors.append(c1_rgb + (255,))

            if c0 > c1:
                colors.append(tuple((2 * a + b) // 3 for a, b in zip(c0_rgb, c1_rgb)) + (255,))
                colors.append(tuple((a + 2 * b) // 3 for a, b in zip(c0_rgb, c1_rgb)) + (255,))
            else:
                colors.append(tuple(((a + b) // 2) for a, b in zip(c0_rgb, c1_rgb)) + (255,))
                colors.append((0, 0, 0, 0))  # Transparent

            for row in range(4):
                for col in range(4):
                    if (4 * by + row) >= height or (4 * bx + col) >= width:
                        continue
                    index = (bits >> 2 * (4 * row + col)) & 0x03
                    pixels[4 * bx + col, 4 * by + row] = colors[index]
    return img

def decode_dxt3(width, height, data):
    img = Image.new("RGBA", (width, height))
    pixels = img.load()

    block_width = (width + 3) // 4
    block_height = (height + 3) // 4
    i = 0

    for by in range(block_height):
        for bx in range(block_width):
            # Read alpha data (64 bits = 8 bytes)
            alpha = struct.unpack_from("<Q", data, i)[0]
            i += 8

            # Read color block
            c0, c1 = struct.unpack_from("<HH", data, i)
            i += 4
            bits = struct.unpack_from("<I", data, i)[0]
            i += 4

            def _rgb565_to_rgb888(c):
                r = ((c >> 11) & 0x1f) << 3
                g = ((c >> 5) & 0x3f) << 2
                b = (c & 0x1f) << 3
                return (r, g, b)

            colors = []
            c0_rgb = _rgb565_to_rgb888(c0)
            c1_rgb = _rgb565_to_rgb888(c1)
            colors.append(c0_rgb)
            colors.append(c1_rgb)
            colors.append(tuple((2 * a + b) // 3 for a, b in zip(c0_rgb, c1_rgb)))
            colors.append(tuple((a + 2 * b) // 3 for a, b in zip(c0_rgb, c1_rgb)))

            for row in range(4):
                for col in range(4):
                    alpha_4bit = (alpha >> (4 * (4 * row + col))) & 0xF
                    alpha_8bit = (alpha_4bit << 4) | alpha_4bit  # Expand 4 bits to 8
                    idx = (bits >> (2 * (4 * row + col))) & 0x03
                    rgb = colors[idx]
                    x = 4 * bx + col
                    y = 4 * by + row
                    if x < width and y < height:
                        pixels[x, y] = (*rgb, alpha_8bit)

    return img

def decode_dxt5(width, height, data):
    img = Image.new("RGBA", (width, height))
    pixels = img.load()

    block_width = (width + 3) // 4
    block_height = (height + 3) // 4
    i = 0

    for by in range(block_height):
        for bx in range(block_width):
            a0 = data[i]
            a1 = data[i + 1]
            a_bits = data[i + 2:i + 8]
            a_bits_val = int.from_bytes(a_bits, 'little')
            i += 8

            # Decode alpha values
            alphas = [a0, a1]
            if a0 > a1:
                for j in range(1, 7):
                    alphas.append(((7 - j) * a0 + j * a1) // 7)
            else:
                for j in range(1, 5):
                    alphas.append(((5 - j) * a0 + j * a1) // 5)
                alphas += [0, 255]

            # Decode alpha indices
            alpha_indices = []
            for j in range(16):
                index = (a_bits_val >> (3 * j)) & 0x07
                alpha_indices.append(alphas[index])

            # Read color block
            c0, c1 = struct.unpack_from("<HH", data, i)
            i += 4
            bits = struct.unpack_from("<I", data, i)[0]
            i += 4

            def _rgb565_to_rgb888(c):
                r = ((c >> 11) & 0x1f) << 3
                g = ((c >> 5) & 0x3f) << 2
                b = (c & 0x1f) << 3
                return (r, g, b)

            colors = []
            c0_rgb = _rgb565_to_rgb888(c0)
            c1_rgb = _rgb565_to_rgb888(c1)
            colors.append(c0_rgb)
            colors.append(c1_rgb)
            colors.append(tuple((2 * a + b) // 3 for a, b in zip(c0_rgb, c1_rgb)))
            colors.append(tuple((a + 2 * b) // 3 for a, b in zip(c0_rgb, c1_rgb)))

            for row in range(4):
                for col in range(4):
                    color_index = (bits >> (2 * (4 * row + col))) & 0x03
                    alpha_index = 4 * row + col
                    alpha = alpha_indices[alpha_index]
                    rgb = colors[color_index]
                    x = 4 * bx + col
                    y = 4 * by + row
                    if x < width and y < height:
                        pixels[x, y] = (*rgb, alpha)

    return img

def decode_a8r8g8b8(width, height, data):
    # BGRA format: byte order is Blue, Green, Red, Alpha
    return Image.frombytes("RGBA", (width, height), data, "raw", "BGRA")


def decode_x8r8g8b8(width, height, data):
    # Same as A8R8G8B8 but alpha is ignored and should be set to 255
    return Image.frombytes("RGBA", (width, height), data, "raw", "BGRA")


def decode_l8(width, height, data):
    # Luminance (grayscale), 1 byte per pixel
    img = Image.frombytes("L", (width, height), data)
    return img.convert("RGBA")


def decode_tex_to_image(tex_file):
    header = tex_file.components[0]
    data = tex_file.components[1]

    width = struct.unpack_from("<I", header, 0x18)[0]
    height = struct.unpack_from("<I", header, 0x1C)[0]
    fourCC_bytes = header[0x28:0x2C]
    fourCC_int = struct.unpack_from("<I", header, 0x28)[0]

    if fourCC_bytes == b'DXT1':
        return decode_dxt1(width, height, data)
    elif fourCC_bytes == b'DXT3':
        return decode_dxt3(width, height, data)
    elif fourCC_bytes == b'DXT5':
        return decode_dxt5(width, height, data)
    elif fourCC_int == 21:
        return decode_a8r8g8b8(width, height, data)
    elif fourCC_int == 22:
        return decode_x8r8g8b8(width, height, data)
    elif fourCC_int == 50:
        return decode_l8(width, height, data)
    else:
        raise NotImplementedError(f"Format {fourCC_bytes} not supported yet")



def convertTEXtoDDS(tex_file):
    header = tex_file.components[0]
    data = tex_file.components[1]

    # Extract values from the header
    width = struct.unpack_from("<I", header, 0x18)[0]
    height = struct.unpack_from("<I", header, 0x1C)[0]
    depth = struct.unpack_from("<I", header, 0x20)[0]
    mipMapCount = struct.unpack_from("<I", header, 0x24)[0]
    fourCC = header[0x28:0x2C]
    print(f"Width: {width}, Height: {height}, Mips: {mipMapCount}, FourCC: {fourCC}")

    if fourCC not in [b'DXT1', b'DXT3', b'DXT5']:
        raise ValueError(f"Unsupported texture format: {fourCC}")

    # DDS magic
    dds_magic = b'DDS '

    # DDS flags
    flags = 0x00021007  # DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_LINEARSIZE
    pitch_or_linear_size = len(data)  # for compressed textures, this is the total size

    # Reserved 44 bytes
    reserved1 = b'\x00' * 44

    # Pixel format (ddspf)
    ddspf = struct.pack(
        "<I I 4s I I I I I",
        32,             # dwSize
        0x00000004,     # dwFlags = DDPF_FOURCC
        fourCC,         # dwFourCC
        0, 0, 0, 0, 0   # dwRGBBitCount + masks (unused with FOURCC)
    )

    # Caps
    caps = 0x00001000 | 0x00000008 | 0x00400000  # DDSCAPS_TEXTURE | DDSCAPS_MIPMAP | DDSCAPS_COMPLEX
    caps2 = 0
    caps3 = 0
    caps4 = 0
    reserved2 = 0

    # Build the DDS header (124 bytes)
    dds_header = struct.pack(
        "<I I I I I I I 44s 32s I I I I I",
        124,                # dwSize
        flags,
        height,
        width,
        pitch_or_linear_size,
        depth,
        mipMapCount,
        reserved1,
        ddspf,
        caps,
        caps2,
        caps3,
        caps4,
        reserved2
    )

    return dds_magic + dds_header + data


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1000x640")
    viewer = TextureViewer(root)
    root.mainloop()
