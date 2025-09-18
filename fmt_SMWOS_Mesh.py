# author: haru233 (haruse31/haruse#31)

from inc_noesis import *
import struct


def registerNoesisTypes():
    handle = noesis.register("Spider-Man: Web of Shadows", ".standalone_mesh")
    noesis.setHandlerTypeCheck(handle, checkType)
    noesis.setHandlerLoadModel(handle, LoadModel)
    # noesis.setHandlerWriteModel(handle, WriteModel)
    return 1

def checkType(data):
    return 1


class D3D9_DATATYPE:
    FLOAT1     = 0,
    FLOAT2     = 1,
    FLOAT3     = 2,
    FLOAT4     = 3,
    D3DCOLOR   = 4,
    UBYTE4     = 5,
    SHORT2     = 6,
    SHORT4     = 7,
    UBYTE4N    = 8,
    SHORT2N    = 9,
    SHORT4N    = 10,
    USHORT2N   = 11,
    USHORT4N   = 12,
    UDEC3      = 13,
    DEC3N      = 14,
    FLOAT16_2  = 15,
    FLOAT16_4  = 16,
    UNUSED     = 17

D3D9_ELEMENTTYPE = {
    0: "POSITION",
    1: "BLENDWEIGHT",
    2: "BLENDINDICES",
    3: "NORMAL",
    4: "PSIZE",
    5: "TEXCOORD",
    6: "TANGENT",
    7: "BINORMAL",
    8: "TESSFACTOR",
    9: "POSITIONT",
    10: "COLOR",
    11: "FOG",
    12: "DEPTH",
    13: "SAMPLE"
}

def half_to_float(h):
    s = (h >> 15) & 1
    e = (h >> 10) & 0x1F
    m = h & 0x3FF
    if e == 0:
        return ((-1)**s) * (m / 2**10) * 2**-14
    if e == 31:
        return float('inf') * ((-1)**s) if m == 0 else float('nan')
    return ((-1)**s) * (1 + m / 2**10) * 2**(e-15)


# Map datatype to size (bytes) and struct format for unpacking
def Get_DataType(dt):
    if dt == 0:      # FLOAT1
        return (4, "<f")
    elif dt == 1:    # FLOAT2
        return (8, "<2f")
    elif dt == 2:    # FLOAT3
        return (12, "<3f")
    elif dt == 3:    # FLOAT4
        return (16, "<4f")
    elif dt == 4:    # D3DCOLOR (ARGB)
        return (4, "<4B")
    elif dt == 5:    # UBYTE4
        return (4, "<4B")
    elif dt == 6:    # SHORT2
        return (4, "<2h")
    elif dt == 7:    # SHORT4
        return (8, "<4h")
    elif dt == 8:    # UBYTE4N (normalized 0-1)
        return (4, "<4B")
    elif dt == 9:    # SHORT2N (normalized -1..1)
        return (4, "<2h")
    elif dt == 10:   # SHORT4N (normalized -1..1)
        return (8, "<4h")
    elif dt == 11:   # USHORT2N (normalized 0..1)
        return (4, "<2H")
    elif dt == 12:   # USHORT4N (normalized 0..1)
        return (8, "<4H")
    elif dt == 13:   # UDEC3 (10:10:10 unsigned packed)
        return (4, "<I")
    elif dt == 14:   # DEC3N (10:10:10 signed normalized)
        return (4, "<I")
    elif dt == 15:   # FLOAT16_2 (half 2 floats)
        return (4, "<2H")
    elif dt == 16:   # FLOAT16_4 (half 4 floats)
        return (8, "<4H")
    elif dt == 17:   # UNUSED
        return (0, "")
    else:
        return (0, "")
    

def LoadModel(data, mdlList):
    bs = NoeBitStream(data)
    
    # Mesh Header
    bs.seek(4, 0)
    Filename_Hash = bs.readUInt()
    bs.seek(4, 1)
    Submesh_Count = bs.readUInt()
    MeshTableOffset = bs.readUInt()
    bs.seek(12, 1) # Unknown
    
    BoundingBoxSphere = bs.readBytes(16)

    BoundingBoxMax_X = bs.readFloat()
    BoundingBoxMax_Y = bs.readFloat()
    BoundingBoxMax_Z = bs.readFloat()
    BoundingBoxMax_W = bs.readFloat() # Always 0
    
    bs.seek(MeshTableOffset, 0)
    
    Mesh_Table = bs.readBytes(8 * Submesh_Count)

    MeshInfoOffsets = []
    for i in range(Submesh_Count):
        entry_offset = i*8 + 4

        MeshInfoOffset = struct.unpack_from("<I", Mesh_Table, entry_offset)[0]
        
        MeshInfoOffsets.append(MeshInfoOffset)

    # Mesh Declaration
    Submeshes = []
    for i in range(Submesh_Count):
        bs.seek(MeshInfoOffsets[i], 0)

        bs.seek(32, 1)

        bs.seek(4, 1) # Unknown

        bonepaletteoffset = bs.readUInt()

        bone_palette_count = bs.readUInt()

        bs.seek(8, 1) # Unknown
        Vertices_Count = bs.readUInt()
  

        bs.seek(12, 1) #Unknown
        Indices_Count = bs.readUInt()

        Index_Size = bs.readUInt() # How many bytes each index takes

        VertexStrideOffset = bs.readUInt()

        bs.seek(8, 1)

        bs.seek(bonepaletteoffset, 0)

        bone_palette = []
        for j in range(bone_palette_count):
            bone_palette_index = bs.readUShort()

            bone_palette.append(bone_palette_index)

        bs.seek(VertexStrideOffset, 0)
        Vertex_Stride = bs.readUInt()

        FVFOffset = bs.readUInt()

        bs.seek(FVFOffset, 0)

        # FVF (Flexible Vertex Format) Layout // Vertex Declarations
        VertexLayout = []

        while True:
            next8 = bs.readBytes(8)

            if next8 == b'\xFF\x00\x00\x00\x11\x00\x00\x00':
                # Already consumed the sentinel
                break

            # Unpack 4 ushorts from next8
            chan, pos, data, etype = struct.unpack("<4H", next8)
            VertexLayout.append({
                "Offset": pos,
                "DataType": data,
                "ElementType": etype
            })

        Submeshes.append((Vertices_Count, Indices_Count, Vertex_Stride, VertexLayout))

    bs.seek(4, 1) # PHYS

    # # === Find the companion .1.mesh file ===
    # component0_path = rapi.getInputName()
    # baseName = component0_path.replace(".0.wosmesh", "")
    # component1_path = baseName + ".1.wosmesh"

    # if not os.path.exists(component1_path):
    #     print("ERROR: Companion .1.wosmesh file not found:", component1_path)
    #     return 0

    # # === Load pixel data ===
    # ModelData = rapi.loadIntoByteArray(component1_path)
    # Model_BS = NoeBitStream(ModelData)

    submesh_buffers = []

    for sm_index, submesh in enumerate(Submeshes):
        Vertices_Count, Indices_Count, Vertex_Stride, VertexLayout = submesh
        print(Vertices_Count)
        print(Indices_Count)
        
        # --- Read vertex and index buffers ---
        vertex_data_offset = bs.tell()
        Vertex_Bytes = bs.readBytes(Vertices_Count * Vertex_Stride)

        index_data_offset = bs.tell()
        if Index_Size == 2:
            IndexData = [bs.readUShort() for _ in range(Indices_Count)]
        elif Index_Size == 4:
            IndexData = [bs.readUInt() for _ in range(Indices_Count)]


        current_pos = bs.tell()
        padding = (4 - (current_pos % 4)) % 4

        file_length = len(bs.getBuffer())

        if padding and current_pos < file_length:
            bs.seek(padding, 1)

        # SAVE all info for later rendering
        submesh_buffers.append((Vertex_Bytes, IndexData, Vertex_Stride, VertexLayout, Vertices_Count, Index_Size))
    
    submesh_vertices = []
    for v in range(Vertices_Count):
        vertex_base = v * Vertex_Stride
        vertex_dict = {}

        for elem in VertexLayout:
            dt = elem['DataType']
            offset = elem['Offset']
            size, fmt = Get_DataType(dt)
            start = vertex_base + offset
            end = start + size
            raw = Vertex_Bytes[start:end]
            value = struct.unpack(fmt, raw)

            # Normalize as needed
            if dt == 8:  # UBYTE4N
                value = tuple(x / 255.0 for x in value)
            elif dt in (9, 10):  # SHORT2N / SHORT4N
                # Normalize to [-1, 1]
                value = [x / 32767.0 for x in value[:3]]
            elif dt in (11, 12):
                value = tuple(x / 65535.0 for x in value)
            elif dt in (15, 16):  # HALF precision
                value = tuple(half_to_float(x) for x in value)

            vertex_dict[D3D9_ELEMENTTYPE.get(elem['ElementType'], "UNKNOWN")] = value

        submesh_vertices.append(vertex_dict)
    
    # Creating RPG Context for Model
    ctx = rapi.rpgCreateContext()

    for i, (Vertex_Bytes, IndexData, Vertex_Stride, VertexLayout, Vertices_Count, Index_Size) in enumerate(submesh_buffers):
        # ----------------------------
        # Build buffers
        # ----------------------------

        # Submesh Name
        rapi.rpgSetName("Submesh_{}".format(i))

        D3D_TO_RPG = {
        0: (noesis.RPGEODATA_FLOAT, 4),       # FLOAT1
        1: (noesis.RPGEODATA_FLOAT, 8),       # FLOAT2
        2: (noesis.RPGEODATA_FLOAT, 12),      # FLOAT3
        3: (noesis.RPGEODATA_FLOAT, 16),      # FLOAT4
        5: (noesis.RPGEODATA_UBYTE, 4),       # UBYTE4
        6: (noesis.RPGEODATA_SHORT, 4),       # SHORT2
        7: (noesis.RPGEODATA_SHORT, 8),       # SHORT4
        8: (noesis.RPGEODATA_UBYTE, 4),       # UBYTE4N
        9: (noesis.RPGEODATA_SHORT, 4),       # SHORT2N
        10:(noesis.RPGEODATA_SHORT, 8),       # SHORT4N
        11:(noesis.RPGEODATA_USHORT, 4),      # USHORT2N
        12:(noesis.RPGEODATA_USHORT, 8),      # USHORT4N
        15:(noesis.RPGEODATA_HALFFLOAT, 4),   # FLOAT16_2
        16:(noesis.RPGEODATA_HALFFLOAT, 8)    # FLOAT16_4
    }

        stride = Vertex_Stride
        for elem in VertexLayout:
            dtype = elem['DataType']      # D3DDECLTYPE
            usage = elem['ElementType']   # D3DDECLUSAGE
            offset = elem['Offset']

            rpg_type, size = D3D_TO_RPG.get(dtype, (noesis.RPGEODATA_FLOAT, 4))
            usage_name = D3D9_ELEMENTTYPE.get(usage, None)

            # Bind based on usage
            if usage_name == 'BINORMAL':
                continue
            elif usage_name == 'POSITION':
                rapi.rpgBindPositionBufferOfs(Vertex_Bytes, rpg_type, stride, offset)
            elif usage_name == 'NORMAL':
                rapi.rpgBindNormalBufferOfs(Vertex_Bytes, rpg_type, stride, offset)
            elif usage_name == 'TEXCOORD':
                rapi.rpgBindUV1BufferOfs(Vertex_Bytes, rpg_type, stride, offset)
            elif usage_name == 'COLOR':
                continue
            elif usage_name == 'TANGENT':
                continue
            elif usage_name == 'BLENDWEIGHT':
                continue
            elif usage_name == 'BLENDINDICES':
                continue
        

        # Commit indices once
        if Index_Size == 2:
            sx = BoundingBoxMax_X
            sy = BoundingBoxMax_Y
            sz = BoundingBoxMax_Z

            # Build a 4x3 scale matrix (three axes vectors + translation)
            scaleMat = NoeMat43((
                NoeVec3((sx, 0.0, 0.0)),  # X axis
                NoeVec3((0.0, sy, 0.0)),  # Y axis
                NoeVec3((0.0, 0.0, sz)),  # Z axis
                NoeVec3((0.0, 0.0, 0.0))  # Translation
            ))

            # Apply it
            rapi.rpgSetTransform(scaleMat)

            indexBuffer = struct.pack("<%dH" % len(IndexData), *IndexData)
            rapi.rpgCommitTriangles(indexBuffer, noesis.RPGEODATA_USHORT, len(IndexData), noesis.RPGEO_TRIANGLE_STRIP)
        
        elif Index_Size == 4:
            sx = BoundingBoxMax_X
            sy = BoundingBoxMax_Y
            sz = BoundingBoxMax_Z

            # Build a 4x3 scale matrix (three axes vectors + translation)
            scaleMat = NoeMat43((
                NoeVec3((sx, 0.0, 0.0)),  # X axis
                NoeVec3((0.0, sy, 0.0)),  # Y axis
                NoeVec3((0.0, 0.0, sz)),  # Z axis
                NoeVec3((0.0, 0.0, 0.0))  # Translation
            ))

            # Apply it
            rapi.rpgSetTransform(scaleMat)

            # Build a scale matrix from your bounding box
            scaleMat = noesis.buildMat43Scale((BoundingBoxMax_X, BoundingBoxMax_Y, BoundingBoxMax_Z))
            rapi.rpgSetTransform(scaleMat)

            indexBuffer = struct.pack("<%dI" % len(IndexData), *IndexData)
            rapi.rpgCommitTriangles(indexBuffer, noesis.RPGEODATA_UINT, len(IndexData), noesis.RPGEO_TRIANGLE_STRIP)
       

            # --- Clear binds so they don’t leak to the next submesh ---
            rapi.rpgClearBufferBinds()

    # Build model and append
    mdl = rapi.rpgConstructModel()
    mdlList.append(mdl)



    return 1


def getBoundingBox(mesh):
    if not hasattr(mesh, 'positions') or not mesh.positions:
        return None
    first = mesh.positions[0]
    max_x, max_y, max_z = first
    for v in mesh.positions:
        x, y, z = v
        max_x = max(max_x, x)
        max_y = max(max_y, y)
        max_z = max(max_z, z)
    return (max_x, max_y, max_z)

def has_skinning(mesh):
    return len(mesh.boneWeights) > 0 if hasattr(mesh, "boneWeights") else False

def build_bone_palette(mesh):
    """
    Returns a list of unique bone indices that influence this mesh.
    If the mesh is not skinned, returns an empty list.
    """
    bone_palette = set()
    
    if hasattr(mesh, "boneIndices") and mesh.boneIndices:
        for v_bone_indices in mesh.boneIndices:
            bone_palette.update(v_bone_indices)  # add all indices from this vertex

    return list(bone_palette)

import struct


def float_to_half(f):
    # convert float to 16-bit half float
    # returns unsigned short
    s = struct.pack('>f', f)
    i = struct.unpack('>I', s)[0]
    sign = (i >> 16) & 0x8000
    exponent = ((i >> 23) & 0xff) - 127 + 15
    mantissa = (i >> 13) & 0x3ff
    if exponent <= 0:
        exponent = 0
        mantissa = 0
    elif exponent >= 31:
        exponent = 31
        mantissa = 0
    return sign | (exponent << 10) | mantissa


def simple_stripify(triangles):
    """
    Convert a list of triangles into a single triangle strip with minimal degenerates.
    triangles: list of tuples/lists of 3 vertex indices
    Returns: flat list of indices
    """
    if not triangles:
        return []

    strip = list(triangles[0])  # start with first triangle

    for tri in triangles[1:]:
        tri_list = list(tri)  # convert tuple to list
        last2 = strip[-2:]

        if len(set(last2 + tri_list)) < 5:
            # Triangles share vertices, no degenerate needed
            strip.extend(tri_list)
        else:
            # Insert minimal degenerate bridge
            strip.append(strip[-1])  # repeat last vertex
            strip.append(tri_list[0])  # start new triangle
            strip.extend(tri_list)  # add the new triangle

    return strip


def is_degenerate(tri):
    return len(set(tri)) < 3

def remove_degenerates(triangle_strip):
    cleaned = []
    # Walk the strip and convert to triangles
    for i in range(len(triangle_strip) - 2):
        tri = [triangle_strip[i], triangle_strip[i+1], triangle_strip[i+2]]
        if not is_degenerate(tri):
            cleaned.extend(tri)
    return cleaned


def WriteModel(mdl, bs):
    with open("D://Testing SMWOS Exporter//HEARTNOESIS.0.wosmesh", "wb") as out:
            # Mesh Header
            out.write(b'\x00' * 4)
            out.write(b'\x00' * 4)
            out.write(b'\x00' * 4)
            out.write(struct.pack("<I", len(mdl.meshes)))
            
            out.write(b'\x00' * 20)

            out.write(b'\x00' * 12)

            bmax = getBoundingBox(mdl.meshes[0])
            out.write(struct.pack("<3f", bmax[0], bmax[1], bmax[2]))
            out.write(b'\x00'* 20)

            out.write(b'\x00' * 8 * len(mdl.meshes))

            current_pos = out.tell()            # current position in the stream
            padding = (16 - (current_pos % 16)) % 16  # compute how many bytes to pad

            if padding:
                out.write(b'\x00' * padding)

            # Mesh Declaration
            for i, mesh in enumerate(mdl.meshes):
                out.write(b'\x00' * 32) # Unknown

                out.write(b'\x00' * 8) # Unknown

                # For a submesh
                mesh = mdl.meshes[i]

                unique_bones = set()
                if hasattr(mesh, "boneIndices") and mesh.boneIndices:
                    for bone_index in mesh.boneIndices:
                        if bone_index != -1:
                            unique_bones.add(bone_index)

                palette = build_bone_palette(mesh)
                bone_palette_count = len(palette)

                out.write(struct.pack("<I", bone_palette_count))

                out.write(b'\x00' * 8)  # Unknown
                out.write(struct.pack("<I", len(mesh.positions)))
        
                triangle_list = [mesh.indices[i:i+3] for i in range(0, len(mesh.indices), 3)]
                triangle_strip = simple_stripify(triangle_list)

                cleaned_strip = remove_degenerates(triangle_strip)

                mesh._cleaned_strip = cleaned_strip

                out.write(b'\x00' * 12)  #Unknown
                out.write(struct.pack("<I", len(cleaned_strip)))

                out.write(b'\x00' * 16) #Unknown

                for j in range(bone_palette_count):
                    out.write(struct.pack("<H", palette[j]))


                current_pos = out.tell()             # current position in the stream
                padding = (4 - (current_pos % 4)) % 4  # compute how many bytes to pad
                if padding:
                    out.write(b'\x00' * padding) 

                if has_skinning(mesh):
                    Stride = 44
                    out.write(struct.pack("<I", Stride))
                
                else:
                    Stride = 24
                    out.write(struct.pack("<I", Stride))
        
                out.write(b'\x00' * 8) # Unknown



                # FVF (Flexible Vertex Format) Layout // Vertex Declarations
                if has_skinning(mesh):
                    vertex_layout = [
                        (0, 0, 15, 5),
                        (0, 4, 16, 6),
                        (0, 12, 10, 0),
                        (0, 20, 16, 3),
                        (0, 28, 8, 1),
                        (0, 32, 5, 2),
                        (0, 36, 16, 7)
                    ]

                    for entry in vertex_layout:
                        chan, pos, data, ctype = entry
                        out.write(struct.pack("<4H", chan, pos, data, ctype))
                    out.write(b'\xFF\x00\x00\x00\x11\x00\x00\x00')
                    current_pos = out.tell()             # current position in the stream
                    padding = (16 - (current_pos % 16)) % 16  # compute how many bytes to pad
                    if padding:
                        out.write(b'\x00' * padding) 

                else:
                    vertex_layout_non_skinned = [
                        (0, 0, 15, 5),
                        (0, 4, 2, 0),
                        (0, 12, 16, 3)
                    ]

                    for entry in vertex_layout_non_skinned:
                        chan, pos, data, ctype = entry
                        out.write(struct.pack("<4H", chan, pos, data, ctype))
                    out.write(b'\xFF\x00\x00\x00\x11\x00\x00\x00')
                    current_pos = out.tell()             # current position in the stream
                    padding = (16 - (current_pos % 16)) % 16  # compute how many bytes to pad
                    if padding:
                        out.write(b'\x00' * padding) 



    with open("D://Testing SMWOS Exporter//HEARTNOESIS.1.wosmesh", "wb") as out:
        for mesh in mdl.meshes:
            if not has_skinning(mesh):
                for i, pos in enumerate(mesh.positions):
                    # UV as FLOAT16_2
                    u, v = mesh.uvs[i][:2]
                    out.write(struct.pack("<H", float_to_half(u)))
                    out.write(struct.pack("<H", float_to_half(v)))
                            
                    x, y, z = pos
                    out.write(struct.pack("<3f", x, y, z))  # position (FLOAT3)

                    nx, ny, nz = mesh.normals[i]
                    w = 0.0  # padding
                    out.write(struct.pack("<H", float_to_half(nx)))
                    out.write(struct.pack("<H", float_to_half(ny)))
                    out.write(struct.pack("<H", float_to_half(nz)))
                    out.write(struct.pack("<H", float_to_half(w)))

                
              

                for idx in mesh._cleaned_strip:
                    out.write(struct.pack("<H", idx))

    return 1