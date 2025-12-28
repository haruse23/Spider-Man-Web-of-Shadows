import os
from .Hash import *

def Convert(Filepath, DDS, TEX):
    File = os.path.basename(Filepath)
    Filename = os.path.splitext(File)[0]
    DirectoryPath = os.path.dirname(Filepath)
    Extension = Filepath.lower().split('.')[-1].lower()
    hash = hex(Hash(Filename))
    
    Path = os.path.join(DirectoryPath, Filename)
    
    PathOutputTEX = os.path.join(DirectoryPath, "0x" + hash[2:].upper() + "." + Filename)
    PathInputTEX = os.path.join(DirectoryPath, Filename.split(".")[0] + "." + Filename.split(".")[1])
    if Extension == 'dds':
        with open(Path + ".dds", 'rb') as f:
            dds = DDS()
            dds.ReadDDSHeader(f) # Read DDS
            dds.ReadDDSData(f)

            
        with open(PathOutputTEX + ".0.tex", 'wb') as f: 
            tex = TEX() # Construct TEX
            tex.ConvertToTEX0(dds, Filename) # Convert to TEX0
            tex.ConvertToTEX1(dds) # Convert to TEX1
            
            tex.WriteTEX0(f) # Write *.0.tex
            
        with open(PathOutputTEX + ".1.tex", 'wb') as f:
            tex.WriteTEX1(f) # Write *.1.tex
            
            
    if Extension == 'tex':
        with open(PathInputTEX + ".0.tex", 'rb') as f:
            tex = TEX()
            tex.ReadTEX0(f) # Read TEX0
            
        with open(PathInputTEX + ".1.tex", 'rb') as f:
            tex.ReadTEX1(f) # Read TEX1
            
        with open(Path + ".dds", 'wb') as f:
            dds = DDS() # Construct DDS
            dds.ConvertToDDS(tex) # Convert to DDS
            
            dds.WriteDDSHeader(f) # Write DDS Header
            dds.WriteDDSData(f) # Write DDS Data
            
            
    else:
        print(f"Unsupported file type: {Extension}")