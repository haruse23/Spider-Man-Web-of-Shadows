import bpy
import struct
from mathutils import Matrix
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator
import os

bl_info = {
    "name": "Import SKEL Skeleton (.SKEL)",
    "author": "haru233",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "File > Import > Spider-Man: Web of Shadows (.SKEL)",
    "description": "Import SKEL skeleton files from Spider-Man: Web of Shadows",
    "category": "Import-Export",
}

class ImportSKELSkeleton(Operator, ImportHelper):
    bl_idname = "import_scene.skel"
    bl_label = "Import SKEL Skeleton"
    filename_ext = ".SKEL"
    
    filter_glob: bpy.props.StringProperty(
    default="*.skel",
    options={'HIDDEN'},
    maxlen=255,
)

    
    def execute(self, context):
        filepath = self.filepath
        with open(filepath, "rb") as f:
            data = f.read()
            
        offset = 0x8
        boneCount = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        
        arm_data = bpy.data.armatures.new("SKEL_Armature")
        arm_object = bpy.data.objects.new("SKEL_Armature", arm_data)
        bpy.context.collection.objects.link(arm_object)
        bpy.context.view_layer.objects.active = arm_object
        bpy.ops.object.mode_set(mode='EDIT')

        edit_bones = []
        parent_indices = []
        matrices = []

        for i in range(boneCount):
            base_offset = offset + i * 0x90

            base_offset += 0x4
            

            
            rot11 = struct.unpack_from("<f", data, base_offset + 0x40)[0]
            rot12 = struct.unpack_from("<f", data, base_offset + 0x44)[0]
            rot13 = struct.unpack_from("<f", data, base_offset + 0x48)[0]

            rot21 = struct.unpack_from("<f", data, base_offset + 0x50)[0]
            rot22 = struct.unpack_from("<f", data, base_offset + 0x54)[0]
            rot23 = struct.unpack_from("<f", data, base_offset + 0x58)[0]

            rot31 = struct.unpack_from("<f", data, base_offset + 0x60)[0]
            rot32 = struct.unpack_from("<f", data, base_offset + 0x64)[0]
            rot33 = struct.unpack_from("<f", data, base_offset + 0x68)[0]

            pos_x = struct.unpack_from("<f", data, base_offset + 0x70)[0]
            pos_y = struct.unpack_from("<f", data, base_offset + 0x74)[0]
            pos_z = struct.unpack_from("<f", data, base_offset + 0x78)[0]



            M = Matrix((
                (rot11, rot12, rot13, 0.0),
                (rot21, rot22, rot23, 0.0),
                (rot31, rot32, rot33, 0.0),
                (pos_x, pos_y, pos_z, 1.0)
            ))
            
            M = M.inverted()
            matrices.append(M)
            
            

            parent_index = struct.unpack_from("<i", data, base_offset + 0x88)[0]
            parent_indices.append(parent_index)

            
        
        for i in range(boneCount):
            bone = arm_data.edit_bones.new(f"bone_{i}")
            edit_bones.append(bone)

        
        for i in range(boneCount):
            bone = edit_bones[i]
            bone_matrix = matrices[i]
            parent_index = parent_indices[i]

            if 0 <= parent_index < boneCount:
                bone.parent = edit_bones[parent_index]

            head = bone_matrix[3].to_3d()
            tail = head + bone_matrix.col[1].to_3d().normalized() * 0.1
            bone.head = head
            bone.tail = tail

        







                
       
                    
        bpy.ops.object.mode_set(mode='OBJECT')            
            
        self.report({'INFO'}, f"Read {boneCount} bones.")
        return {'FINISHED'}
                

         
            
    
    
    

def menu_func_import(self, context):
    self.layout.operator(ImportSKELSkeleton.bl_idname, text="Spider-Man: Web of Shadows (.SKEL)")

def register():
    bpy.utils.register_class(ImportSKELSkeleton)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(ImportSKELSkeleton)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
