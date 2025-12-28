import struct
from .Hash import *

def read_uint(f):
    return struct.unpack("<I", f.read(4))[0]


def write_uint(f, data):
    f.write(struct.pack("<I", data))


class TEX:
    def __init__(self):
        self.dwUnused1 = b''
        self.dwFilenamePointer = 0
        self.dwFilenameHash = 0
        self.dwUnused2 = b''
        self.dwWidth = 0
        self.dwHeight = 0
        self.dwDepth = 0
        self.dwMipMapCount = 0
        self.dwFourCC = b''
        self.dwUnused3 = b''
        self.dataTEX = b''
        
        
    def ReadTEX0(self, f):
        self.dwUnused1 = f.read(2 * 4)
        self.dwFilenamePointer = read_uint(f)
        self.dwFilenameHash = read_uint(f)
        self.dwUnused2 = f.read(2 * 4)
        self.dwWidth = read_uint(f)
        self.dwHeight = read_uint(f)
        self.dwDepth = read_uint(f)
        self.dwMipMapCount = read_uint(f)
        self.dwFourCC = f.read(4)
        self.dwUnused3 = f.read(6 * 4)
        
        
    def ReadTEX1(self, f):
        self.dataTEX = f.read()
        
    
    def ConvertToTEX0(self, DDS, Filename):
        self.dwUnused1 = b'\x00' * 2 * 4
        self.dwFilenamePointer = 0
        self.dwFilenameHash = Hash(Filename)
        self.dwUnused2 = b'\x00' * 2 * 4
        self.dwWidth = DDS.dwWidth
        self.dwHeight = DDS.dwHeight
        self.dwDepth = DDS.dwDepth
        self.dwMipMapCount = DDS.dwMipMapCount
        self.dwFourCC = DDS.dwFourCC
        self.dwUnused3 = b'\x00' * 6 * 4
        
        
    def ConvertToTEX1(self, DDS):
        self.dataTEX = DDS.dataDDS
        
    
    def WriteTEX0(self, f):
        f.write(self.dwUnused1)
        write_uint(f, self.dwFilenamePointer)
        write_uint(f, self.dwFilenameHash)
        f.write(self.dwUnused2)
        write_uint(f, self.dwWidth)
        write_uint(f, self.dwHeight)
        write_uint(f, self.dwDepth)
        write_uint(f, self.dwMipMapCount)
        f.write(self.dwFourCC)
        f.write(self.dwUnused3)
        
        
    def WriteTEX1(self, f):
        f.write(self.dataTEX)
        
        
        
    
        
        
        
    