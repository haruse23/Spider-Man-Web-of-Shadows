import bpy
from bpy.types import Operator, FileHandler
from bpy.props import StringProperty

from .DDS import *
from .TEX import *
from .Convert import *

bl_info = {
    "name": "DDS/TEX Converter (WOS)",
    "author": "haru233",
    "version": (3, 0, 0),
    "blender": (4, 5, 0),
    "location": "Drag-and-Drop",
    "description": "Convert DDS to TEX and TEX to DDS via Drag-and-Drop"
}


class CONVERT_OT_DDS_TEX(Operator):
    """Drag and Drop DDS or TEX files to convert"""
    bl_idname = "import_scene.dds_tex_converter"
    bl_label = "DDS/TEX Converter (WOS)"
    bl_options = {'REGISTER', 'UNDO'}

    # Filepath property
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement)
    directory: bpy.props.StringProperty(subtype="DIR_PATH")

    def execute(self, context):
        if not self.files:
            self.report({'WARNING'}, "No files received")
            return {'CANCELLED'}

        for file in self.files:
            filepath = os.path.join(self.directory, file.name)

            try:
                Convert(filepath, DDS, TEX)
            except Exception as e:
                self.report({'ERROR'}, f"{file.name}: {e}")

        self.report({'INFO'}, f"Converted {len(self.files)} file(s)")
        return {'FINISHED'}
    


class DDS_TEX_FileHandler(FileHandler):
    bl_idname = "DDS_TEX_FILEHANDLER"
    bl_label = "Convert DDS/TEX Files (WOS)"
    bl_import_operator = "import_scene.dds_tex_converter"
    bl_file_extensions = ".dds;.tex"
    
    @classmethod
    def poll_drop(cls, context):
        return context.area and context.area.type == "VIEW_3D"
    
    @classmethod
    def can_handle(cls, context, filepath):
        return filepath.lower().endswith((".dds", ".tex"))

# Register the operator
def menu_func_import(self, context):
    self.layout.operator(CONVERT_OT_DDS_TEX.bl_idname, text="DDS/TEX Converter")

# Register the classes
def register():
    bpy.utils.register_class(CONVERT_OT_DDS_TEX)
    bpy.utils.register_class(DDS_TEX_FileHandler)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

# Unregister the classes
def unregister():
    bpy.utils.unregister_class(CONVERT_OT_DDS_TEX)
    bpy.utils.unregister_class(DDS_TEX_FileHandler)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
