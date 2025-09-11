bl_info = {
    "name"        : "SMWOS Mesh Importer",
    "author"      : "mariokart64n",
    "version"     : (1, 5, 0),
    "blender"     : (4, 0, 0),
    "location"    : "File > Import > SMWOS (.*.MESH)",
    "description" : "Imports the proprietary SMWOS split-component mesh format.",
    "category"    : "Import-Export",
}

import struct, os, bpy
from bpy_extras.io_utils import ImportHelper
from mathutils import Vector

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def read(fmt, f):
    sz = struct.calcsize(fmt)
    buf = f.read(sz)
    if len(buf) != sz:
        raise EOFError(f"Unexpected end-of-file while reading {fmt}")
    return struct.unpack(fmt, buf)

def read_half(h):
    s=(h>>15)&1; e=(h>>10)&0x1F; m=h&0x3FF
    if e==0:  return ((-1)**s)*(m/2**10)*2**-14
    if e==31: return float('nan') if m else float('inf')*((-1)**s)
    return ((-1)**s)*(1+m/2**10)*2**(e-15)

def pad16(start, cur):  # same formula as your MaxScript
    return (16 - ((cur - start) & 0xF)) & 0xF

def decode_data_by_type(fp, data_type):
    """
    Reads and decodes attribute data from the file pointer `fp` according to
    the given `data_type` (D3DDECLTYPE enum).
    
    Returns a list of 4 floats (or ints normalized to floats), padding zeros if needed.
    """
    if data_type == 0:  # FLOAT1
        vals = struct.unpack("<f", fp.read(4))
        return list(vals) + [0, 0, 0]
    elif data_type == 1:  # FLOAT2
        vals = struct.unpack("<2f", fp.read(8))
        return list(vals) + [0, 0]
    elif data_type == 2:  # FLOAT3
        vals = struct.unpack("<3f", fp.read(12))
        return list(vals) + [0]
    elif data_type == 3:  # FLOAT4
        vals = struct.unpack("<4f", fp.read(16))
        return list(vals)
    elif data_type == 4:  # D3DCOLOR (ARGB stored as 4 bytes)
        raw = fp.read(4)
        b, g, r, a = raw  # assuming BGRA order? Confirm in your data!
        # normalize color components to 0-1 floats
        return [r / 255, g / 255, b / 255, a / 255]
    elif data_type == 5:  # UBYTE4 (4 unsigned bytes)
        raw = fp.read(4)
        return list(raw)
    elif data_type == 6:  # SHORT2 (2 signed shorts)
        vals = struct.unpack("<2h", fp.read(4))
        return list(vals) + [0, 0]
    elif data_type == 7:  # SHORT4 (4 signed shorts)
        vals = struct.unpack("<4h", fp.read(8))
        return list(vals)
    elif data_type == 8:  # UBYTE4N (4 unsigned bytes normalized)
        raw = fp.read(4)
        return [float(b)/255.0 for b in raw]
    elif data_type == 9:  # SHORT2N (2 signed shorts normalized)
        vals = struct.unpack("<2h", fp.read(4))
        return [v / 32767.0 for v in vals] + [0, 0]
    elif data_type == 10:  # SHORT4N (4 signed shorts normalized)
        vals = struct.unpack("<4h", fp.read(8))
        return [v / 32767.0 for v in vals]
    elif data_type == 11:  # USHORT2N (2 unsigned shorts normalized)
        vals = struct.unpack("<2H", fp.read(4))
        return [v / 65535.0 for v in vals] + [0, 0]
    elif data_type == 12:  # USHORT4N (4 unsigned shorts normalized)
        vals = struct.unpack("<4H", fp.read(8))
        return [v / 65535.0 for v in vals]
    elif data_type == 13:  # UDEC3 (packed 10:10:10 bits, need custom decode)
        raw = fp.read(4)
        # Implement if needed; placeholder:
        return [0, 0, 0, 0]
    elif data_type == 14:  # DEC3N (packed signed 10:10:10 normalized)
        raw = fp.read(4)
        # Implement if needed; placeholder:
        return [0, 0, 0, 0]
    elif data_type == 15:  # FLOAT16_2 (2 half floats)
        raw = fp.read(4)
        h1, h2 = struct.unpack("<2H", raw)
        return [read_half(h1), read_half(h2), 0, 0]
    elif data_type == 16:  # FLOAT16_4 (4 half floats)
        raw = fp.read(8)
        h = struct.unpack("<4H", raw)
        return [read_half(x) for x in h]
    else:
        # Unknown or UNUSED, read 4 bytes raw as fallback
        raw = fp.read(4)
        padded = list(raw) + [0] * (4 - len(raw))
        return [float(b) for b in padded]
    
    
def read_vertex_attributes(fp, vertex_base_offset, stride, md_fvf, vertex_count):
    # md_fvf is list of FVF entries
    attributes = {
      'position': [],
      'normal': [],
      'tangent': [],
      'binormal': [],
      'color': [],
      'uv0': [],
      'uv1': [],
      'weights': [],
      'bone_indices': []
    }
    for v in range(vertex_count):
        base = vertex_base_offset + v * stride
        for attr in md_fvf:
            fp.seek(base + attr.pos)
            decoded = decode_data_by_type(fp, attr.data)
            usage = attr.ctype
            if usage == 0:  # POSITION
                attributes['position'].append(decoded)
            elif usage == 3:  # NORMAL
                attributes['normal'].append(decoded)
            elif usage == 5:  # TEXCOORD
                attributes['uv0'].append(decoded)
            elif usage == 6:  # TANGENT
                attributes['tangent'].append(decoded)
            elif usage == 7:  # BINORMAL
                attributes['binormal'].append(decoded)
            elif usage == 10: # COLOR
                attributes['color'].append(decoded)
            elif usage == 1:  # BLENDWEIGHT
                attributes['weights'].append(decoded)
            elif usage == 2:  # BLENDINDICES
                attributes['bone_indices'].append(decoded)
            # ... add other usages as needed
    return attributes

def read_fvf_entries(fp):
    fvf_entries = []
    while True:
        raw = fp.read(8)
        if len(raw) < 8:
            break
        
        # Sentinel check
        if raw == b'\xFF\x00\x00\x00\x11\x00\x00\x00':
            break

        # Unpack as four 2-byte unsigned shorts
        chan, pos, data, ctype = struct.unpack("<4H", raw)

        fvf_entries.append({
            "CHAN": chan,
            "POS": pos,
            "DATA": data,
            "CTYPE": ctype,
        })

    return fvf_entries

def read_vertices_dynamic(fp, md, fvf, vertex_count, hdr):
    V, N, C, UV0, UV1, W, BID, T, B = [], [], [], [], [], [], [], [], []
    base_offset = fp.tell()

    for v in range(vertex_count):
        base = base_offset + v * md.stride
        
        # Temp vars for this vertex attributes
        position = None
        normal = None
        tangent = None
        binormal = None
        color = None
        uv0 = None
        uv1 = None
        weights = [0.0, 0.0, 0.0, 0.0]
        bone_indices = [0, 0, 0, 0]

        
        for attr in fvf:
            fp.seek(base + attr.pos)
            decoded = decode_data_by_type(fp, attr.data)
            usage = attr.ctype
            
            if usage == 0:    # POSITION
                position = decoded
            elif usage == 1:  # BLENDWEIGHT
                weights = decoded
                
            elif usage == 2:  # BLENDINDICES
                bone_indices = decoded
                
            elif usage == 3:  # NORMAL
                normal = decoded
            elif usage == 4:  # PSIZE (Point size)
                # Usually used for point sprites - rarely needed in mesh vertex
                pass
            elif usage == 5:  # TEXCOORD
                uv0 = decoded
            elif usage == 6:  # TANGENT
                tangent = decoded
            elif usage == 7:  # BINORMAL
                binormal = decoded
            elif usage == 8:  # TESSFACTOR (Tessellation factor)
                # Mostly unused in vertex buffer, can ignore or store
                pass
            elif usage == 9:  # POSITIONT (Transformed position)
                # Usually pre-transformed position (screen space), rarely used
                position = decoded
            elif usage == 10: # COLOR
                color = decoded
            elif usage == 11: # FOG (Fog coordinate)
                # Optional, rarely used, can ignore or store
                pass
            elif usage == 12: # DEPTH (Depth value)
                # Optional, can ignore
                pass
            elif usage == 13: # SAMPLE (Multisample pattern)
                # Optional, usually ignored
                pass
            else:
                # Unknown usage type - optionally log or ignore
                pass

        
        # Post-process and append
        if position is not None:
            # Assuming position is SHORT4N normalized shorts [x,y,z,w]
            # Scale and reorder if needed (swap Y,Z)
            P = Vector((position[0]*hdr.bmax.x,
                        position[1]*hdr.bmax.y,
                        position[2]*hdr.bmax.z))
            V.append(P)
        else:
            V.append(Vector((0,0,0)))  # default
        
        if normal is not None:
            Nrm = Vector((normal[0], normal[1], normal[2])).normalized()
            N.append(Nrm)
        else:
            N.append(Vector((0,0,1)))
        
        if tangent is not None:
            T.append(tangent)
        else:
            T.append([0,0,0,0])
        
        if binormal is not None:
            B.append(binormal)
        else:
            B.append([0,0,0,0])
        
        if color is not None:
            C.append(color)
        else:
            C.append([1,1,1,1])
        
        if uv0 is not None:
            # Swap uv coords if needed (V,U)
            UV0.append((uv0[1], uv0[0]))
        else:
            UV0.append((0,0))
        
        if uv1 is not None:
            UV1.append((uv1[1], uv1[0]))
        else:
            UV1.append((0,0))
        
        if weights is not None:
            W.append(weights)
        else:
            W.append([0.0,0.0,0.0,0.0])
        
        if bone_indices is not None:
            BID.append(bone_indices)
        else:
            BID.append([0, 0, 0, 0])
            
       
            
   

            
            
    # After all vertices are loaded and before returning them
    print("[DEBUG] Showing first 5 vertex positions (x, y, z):")
    for i, pos in enumerate(V[:5]):
        print(f"  Vertex {i}: x={pos.x:.6f}, y={pos.y:.6f}, z={pos.z:.6f}")

    
    return V, N, C, UV0, UV1, W, BID, T, B


from collections import namedtuple

# Define the FVFEntry structure
FVFEntry = namedtuple('FVFEntry', ['chan', 'pos', 'data', 'ctype'])

# Define how many bytes each data type consumes
TYPE_SIZES = {
    0: 4,   # FLOAT1
    1: 8,   # FLOAT2
    2: 12,  # FLOAT3
    3: 16,  # FLOAT4
    4: 4,   # D3DCOLOR
    5: 4,   # UBYTE4
    6: 4,   # SHORT2
    7: 8,   # SHORT4
    8: 4,   # UBYTE4N
    9: 4,   # SHORT2N
    10: 8,  # SHORT4N
    11: 4,  # USHORT2N
    12: 8,  # USHORT4N
    13: 4,  # UDEC3
    14: 4,  # DEC3N
    15: 4,  # FLOAT16_2
    16: 8,  # FLOAT16_4
    17: 0,  # UNUSED
}

def extract_fvf_from_importer_metadata(mesh_decl):
    """Reads vertex declaration metadata from your imported MeshDecl object"""
    fvf = []
    pos = 0

    if not hasattr(mesh_decl, 'vertex_declaration'):
        raise ValueError(f"'{mesh_decl}' has no 'vertex_declaration' to extract from")

    for attr in mesh_decl.vertex_declaration:
        usage = attr.usage                    # e.g. 0=POSITION, 3=NORMAL, etc.
        usage_index = getattr(attr, 'usage_index', 0)
        data_type = attr.data_type            # e.g. 2=FLOAT3, etc.
        offset = getattr(attr, 'offset', None)

        if offset is None:
            offset = pos

        fvf.append(FVFEntry(
            chan=usage_index,
            pos=offset,
            data=data_type,
            ctype=usage
        ))

        # Only bump the offset if we're assigning automatically
        if getattr(attr, 'offset', None) is None:
            pos += TYPE_SIZES.get(data_type, 0)

    return fvf


def convert_fvf_list_to_entries(fvf_list):
    from collections import namedtuple
    FVFEntry = namedtuple('FVFEntry', ['chan', 'pos', 'data', 'ctype'])

    entries = []
    for attr in fvf_list:
        entries.append(FVFEntry(
            chan=getattr(attr, 'chan', 0),       # or 'usage_index' depending on your FVF object
            pos=getattr(attr, 'offset', 0),
            data=getattr(attr, 'data_type', 0),
            ctype=getattr(attr, 'usage', 0)
        ))
    return entries


# ---------------------------------------------------------------------------
# classes
# ---------------------------------------------------------------------------

class Header:
    __slots__ = ("mesh_count", "bmin", "bmax")

    def __init__(self, f):
        f.seek(12, 1)  # skip fixed bytes
        self.mesh_count, = read("<I", f)
        f.seek(20, 1)  # skip unknown
        self.bmin = Vector(read("<3f", f))
        self.bmax = Vector(read("<3f", f))
        print(f"[DEBUG] Header BMin: ({self.bmin.x:.6f}, {self.bmin.y:.6f}, {self.bmin.z:.6f})")
        print(f"[DEBUG] Header BMax: ({self.bmax.x:.6f}, {self.bmax.y:.6f}, {self.bmax.z:.6f})")

        f.seek(20, 1)  # additional unknown chunk

        table_bytes = self.mesh_count * 8
        f.seek(table_bytes, 1)
        
        # Align to next 16-byte boundary
        offset = f.tell()
        aligned = (offset + 15) & ~15
        pad = aligned - offset
        if pad:
            print(f"[DEBUG] Aligning {pad} bytes after mesh table")
            f.seek(pad, 1)



class MeshDecl:
    __slots__=("unk1","unk2","bone_palette_count","unk3","unk4","vertex_count","unk5",
               "unk6","unk7","index_count","unk8","unk9","unk10","unk11",
               "bone_palette","stride","mag1","mag2")
    def __init__(self,f):
        
        print(f"\n[DEBUG] MeshDecl starts at offset 0x{f.tell():X}")

        blk=f.tell(); f.seek(32,1)
        
        print(f"[DEBUG] Reading 14I at offset 0x{f.tell():X}")

        (self.unk1,self.unk2,self.bone_palette_count,
         self.unk3,self.unk4,self.vertex_count,self.unk5,
         self.unk6,self.unk7,self.index_count,self.unk8,
         self.unk9,self.unk10,self.unk11)=read("<14I",f)
         
        print(f"[DEBUG] bone_palette_count = {self.bone_palette_count}")
        
        print(f"[DEBUG] Reading bone palette at offset 0x{f.tell():X}")

        self.bone_palette=list(read(f"<{self.bone_palette_count}H",f))
        if (self.bone_palette_count*2)&3: f.seek((4-((self.bone_palette_count*2)&3))&3,1)
        
        print(f"[DEBUG] Finished bone palette at offset 0x{f.tell():X}")

        print(f"[DEBUG] Reading stride/mag1/mag2 at offset 0x{f.tell():X}")

        self.stride,self.mag1,self.mag2=read("<3I",f)


class FVFDecl:
    __slots__ = ("chan", "pos", "data", "ctype")

    def __init__(self, t):
        self.chan, self.pos, self.data, self.ctype = t

    @staticmethod
    def read_block(f, stride, fvf_start):
        entries = []

        while True:
            blob = f.read(8)
            if len(blob) < 8:
                break

            tup = struct.unpack("<HHHH", blob)
            print(f"[DEBUG] Raw FVF tuple: {tup}")

            if tup == (0x00FF, 0x0000, 0x0011, 0x0000):
                print("[INFO] D3DDECL_END sentinel found.")
                break

            if tup[1] > stride or tup[1] > 0x100:
                f.seek(-8, 1)
                break

            entries.append(FVFDecl(tup))

        # Align to 16 bytes after FVF block
        fvf_end = f.tell()
        aligned = (f.tell() + 15) & ~15
        pad = aligned - f.tell()
        if pad:
            print(f"[DEBUG] Aligning FVF block to 16 bytes: skipping {pad} bytes")
            f.seek(pad, 1)


        return entries



class Model:
    def __init__(self, filepath):
        with open(filepath, "rb") as f:
            self.header = Header(f)

            self.meshes = []
            self.fvfs = []

            for i in range(self.header.mesh_count):
                mesh = MeshDecl(f)
                fvf_start = f.tell()
                fvf = FVFDecl.read_block(f, mesh.stride, fvf_start)
                self.meshes.append(mesh)
                self.fvfs.append(fvf)
                print(f"[DEBUG] Finished MeshDecl {i} at offset 0x{f.tell():X}")





           

        




# ---------------------------------------------------------------------------
# Read Triangle Strips then Convert to Triangles
# ---------------------------------------------------------------------------
def read_faces(f, index_count):
    expected_bytes = index_count * 2
    raw = f.read(expected_bytes)
    if len(raw) < expected_bytes:
        raise EOFError(f"Not enough index data: wanted {expected_bytes}, got {len(raw)}")
    idx = list(struct.unpack(f"<{index_count}H", raw))

    faces, strip = [], []
    skipped = 0

    for ix in idx:
        if ix == 0xFFFF:
            strip.clear()
            continue
        strip.append(ix)
        if len(strip) >= 3:
            i = len(strip) - 3
            if i & 1:
                tri = (strip[i+1], strip[i], strip[i+2])
            else:
                tri = (strip[i], strip[i+1], strip[i+2])

            # Detect degenerate triangles
            if tri[0] != tri[1] and tri[1] != tri[2] and tri[2] != tri[0]:
                faces.append(tri)
            else:
                skipped += 1
                
    
    if skipped:
        print(f"[IMPORT DEBUG] Skipped {skipped} degenerate triangles out of {len(idx)-2} possible tris")
        
    if (index_count * 2) & 3:
        f.seek((4 - ((index_count * 2) & 3)) & 3, 1)
        

    return faces


def assign_vertex_groups(obj, BID, W, bone_palette):
    mesh = obj.data

    # Map all bone IDs through the palette
    all_bones = set()
    for vertex_bones in BID:
        real_bones = [bone_palette[b] for b in vertex_bones]
        all_bones.update(real_bones)

    print(f"[DEBUG] Unique real bone IDs in BID via palette: {sorted(all_bones)}")
    print(f"[DEBUG] Total unique real bone IDs found: {len(all_bones)}")

    # Create vertex groups with real bone indices
    vgroups = {}
    for bone_id in sorted(all_bones):
        vgroups[bone_id] = obj.vertex_groups.new(name=f"bone_{bone_id}")

    # Assign weights per vertex per bone (mapping palette → real bone)
    for v_idx, (bones, weights) in enumerate(zip(BID, W)):
        for palette_idx, weight in zip(bones, weights):
            if weight > 0:
                real_bone_idx = bone_palette[palette_idx]
                vgroups[real_bone_idx].add([v_idx], weight, 'REPLACE')

                
# ---------------------------------------------------------------------------
# importer
# ---------------------------------------------------------------------------
def import_smwos(path):
    root=os.path.splitext(os.path.splitext(path)[0])[0]
    head, payl = root+".0.MESH", root+".1.MESH"
    if not (os.path.exists(head) and os.path.exists(payl)):
        raise FileNotFoundError

    with open(head,"rb") as fh:
        model = Model(head)
        hdr = model.header

    bscale=Vector((hdr.bmax.x,hdr.bmax.z,hdr.bmax.y))

    with open(payl,"rb") as fp:
        print(f"[IMPORT] Total meshes in model: {len(model.meshes)}")

        for i, (md, fvf) in enumerate(zip(model.meshes, model.fvfs)):
            print(f"\n[IMPORT] Mesh {i}")
            print(f"  Stride: {md.stride}")
            print(f"  Vertex Count (unk03): {md.vertex_count}")
            print(f"  Index Count (unk07): {md.index_count}")
            print(f"  Bone Palette Length: {len(md.bone_palette)}")

            print(f"Mesh {i} FVF entries:")
            for j, entry in enumerate(fvf):
                print(f"  Entry {i}: chan={entry.chan}, pos={entry.pos}, data={entry.data}, ctype={entry.ctype}")
            # Debug: print mesh index and stride value
            print(f"DEBUG: Mesh {i} offset = 0x{fp.tell():X}, stride = {md.stride}, bone_palette_count = {md.bone_palette_count}, vertex_count = {md.vertex_count}, index_count = {md.index_count}")
            vbase = fp.tell()
            V, N, C, UV0, UV1, W, BID, T, B = read_vertices_dynamic(fp, md, fvf, md.vertex_count, hdr)
            # Immediately after you define vbase, and before any other fp.seek:
            fp.seek(vbase)
            vb_bytes = fp.read(md.vertex_count* md.stride)

            ib_bytes = fp.read(md.index_count * 2)

            
        
            fp.seek(vbase + md.vertex_count * md.stride)
            print(f"[IMPORT] File size: {os.path.getsize(fp.name)} bytes")
            print(f"[IMPORT] Position before reading indices: 0x{fp.tell():X}")
            print(f"[IMPORT] Expecting {md.index_count * 2} bytes of index data")
            
            expected = md.index_count * 2
            remaining = os.path.getsize(fp.name) - fp.tell()
            if expected > remaining:
                raise EOFError(f"[IMPORT ERROR] Mesh {i}: trying to read {expected} bytes of indices, but only {remaining} left in file")

            faces = read_faces(fp, md.index_count)
            
            def half_to_float(h):
                s=(h>>15)&1; e=(h>>10)&0x1F; m=h&0x3FF
                if e==0:  return ((-1)**s)*(m/2**10)*2**-14
                if e==31: return float('nan') if m else float('inf')*((-1)**s)
                return ((-1)**s)*(1+m/2**10)*2**(e-15)

            def decode_half4(data):
                hvals = struct.unpack("<4H", data)
                return [half_to_float(h) for h in hvals]

            def decode_short4n(data):
                svals = struct.unpack("<4h", data)
                return [v / 32767.0 for v in svals]

            def decode_ubyte4n(data):
                bvals = struct.unpack("<4B", data)
                return [v / 255.0 for v in bvals]

            def decode_ubyte4(data):
                return struct.unpack("<4B", data)

            # inside the import_smwos function, replacing the old loop:
            for v in range(md.vertex_count):
                base = vbase + v * md.stride
                vertex_attrs = {}
                for attr in fvf:
                    fp.seek(base + attr.pos)
                    vals = decode_data_by_type(fp, attr.data)
                    vertex_attrs[(attr.chan, attr.ctype)] = vals
                # Then assign vertex_attrs values to V, N, UV0, etc. based on usage



            fp.seek(vbase+md.vertex_count*md.stride)
            faces=read_faces(fp,md.index_count)



            me=bpy.data.meshes.new(f"SMWOS_{i}")
            me.from_pydata(V,[],faces)
            me.validate(); me.update()
            for p in me.polygons: p.flip()
            
            for poly in me.polygons:
                    poly.use_smooth = True
                    
            if N:
                loop_normals = []
                for poly in me.polygons:
                    for li in poly.loop_indices:
                        vi = me.loops[li].vertex_index
                        loop_normals.append(N[vi])

                me.normals_split_custom_set(loop_normals) 
    
    
            if UV0:
                uv=me.uv_layers.new(name="UV0")
                for li,l in enumerate(me.loops): uv.data[li].uv=UV0[l.vertex_index]
            if any(UV1):
                uv1=me.uv_layers.new(name="UV1")
                for li,l in enumerate(me.loops): uv1.data[li].uv=UV1[l.vertex_index]
            if any(C):
                cl=me.color_attributes.new(name="Col",type='BYTE_COLOR',domain='POINT')
                for i,c in enumerate(C): cl.data[i].color=(*c[:3],c[3])
                
            # Suppose BID is like: [[0, 1, 2, 3], [1, 2, 3, 0], ..., [3, 0, 1, 2]]
            vertex_count = len(BID)

            for i in range(4):
                attr = me.attributes.new(name=f"bone_id{i}", type='INT', domain='POINT')
                
                # Extract just the i-th bone index for each vertex
                values = [int(b[i]) for b in BID]  # Flatten and ensure int
                
                if len(values) != vertex_count:
                    raise ValueError(f"Length mismatch: expected {vertex_count}, got {len(values)}")

                attr.data.foreach_set("value", values)


            for i in range(4):
                attr = me.attributes.new(name=f"bone_weight{i}", type='FLOAT', domain='POINT')
                values = [float(w[i]) for w in W]
                attr.data.foreach_set("value", values)


        

            obj=bpy.data.objects.new(me.name,me)
            bpy.context.collection.objects.link(obj)
            
            assign_vertex_groups(obj, BID, W, md.bone_palette)
            
            # 🔽 Store original header bounds as custom properties for reuse later
            obj["bmax_original"] = list(hdr.bmax)
            print(obj["bmax_original"])
            obj["bmin_original"] = list(hdr.bmin)
            print(obj["bmin_original"])





# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
class IMPORT_OT_smwos(bpy.types.Operator,ImportHelper):
    bl_idname="import_mesh.smwos"; bl_label="Import SMWOS mesh"
    filename_ext=".MESH"
    filter_glob:bpy.props.StringProperty(default="*.0.MESH;*.1.MESH;*.MESH",options={'HIDDEN'})
    def execute(self,ctx):
        try: import_smwos(self.filepath); return {'FINISHED'}
        except Exception as e: self.report({'ERROR'},str(e)); return {'CANCELLED'}

def menu_fn(self,ctx):
    self.layout.operator(IMPORT_OT_smwos.bl_idname,text="SMWOS mesh (.MESH)")

def register():
    bpy.utils.register_class(IMPORT_OT_smwos)
    bpy.types.TOPBAR_MT_file_import.append(menu_fn)
def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_fn)
    bpy.utils.unregister_class(IMPORT_OT_smwos)
if __name__=="__main__": register()