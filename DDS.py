import struct

def read_uint(f):
    return struct.unpack("<I", f.read(4))[0]


def write_uint(f, data):
    f.write(struct.pack("<I", data))



class DDS:
    def __init__(self):
        self.Magic = b''
        
        self.dwSize = 0
        self.dwFlags = 0
        self.dwHeight = 0
        self.dwWidth = 0
        self.dwPitchOrLinearSize = 0
        self.dwDepth = 0
        self.dwMipMapCount = 0
        self.dwReserved = b''
        
        #Pixel Format
        self.dwSizePF = 0
        self.dwFlagsPF = 0
        self.dwFourCC = b''
        self.dwRGBBitCount = 0
        self.dwRBitMask = 0
        self.dwGBitMask = 0
        self.dwBBitMask = 0
        self.dwABitMask = 0
        
        self.dwCaps = 0
        self.dwCaps2 = 0
        self.dwCaps3 = 0
        self.dwCaps4 = 0
        self.dwReserved2 = 0
        
        self.dataDDS = b''
    
    def ReadDDSHeader(self, f):
        self.Magic = f.read(4)
        
        self.dwSize = read_uint(f)
        self.dwFlags = read_uint(f)
        self.dwHeight = read_uint(f)
        self.dwWidth = read_uint(f)
        self.dwPitchOrLinearSize = read_uint(f)
        self.dwDepth = read_uint(f)
        self.dwMipMapCount = read_uint(f)
        self.dwReserved = f.read(11 * 4)
        self.ReadDDSPixelFormat(f)
        self.dwCaps = read_uint(f)
        self.dwCaps2 = read_uint(f)
        self.dwCaps3 = read_uint(f)
        self.dwCaps4 = read_uint(f)
        self.dwReserved2 = read_uint(f)
        
        
        
        
        
        
    def ReadDDSPixelFormat(self, f):
        self.dwSizePF = read_uint(f)
        self.dwFlagsPF = read_uint(f)
        self.dwFourCC = f.read(4)
        self.dwRGBBitCount = read_uint(f)
        self.dwRBitMask = read_uint(f)
        self.dwGBitMask = read_uint(f)
        self.dwBBitMask = read_uint(f)
        self.dwABitMask = read_uint(f)
        
        
        
    def ReadDDSData(self, f):
        self.dataDDS = f.read()
        
        
    def ConvertToDDS(self, TEX):
        self.Magic = b'DDS '
        
        self.dwSize = 124
        self.dwFlags = 135175
        self.dwHeight = TEX.dwHeight
        self.dwWidth = TEX.dwWidth
        self.dwPitchOrLinearSize = 0
        self.dwDepth = 0
        self.dwMipMapCount = TEX.dwMipMapCount
        self.dwReserved = b'\x00' * 11 * 4
        
        #Pixel Format
        if TEX.dwFourCC == b'DXT1' or TEX.dwFourCC == b'DXT3' or TEX.dwFourCC == b'DXT5':
            self.dwSizePF = 32
            self.dwFlagsPF = 4
            self.dwFourCC = TEX.dwFourCC
            self.dwRGBBitCount = 32
            self.dwRBitMask = 16711680
            self.dwGBitMask = 65280
            self.dwBBitMask = 255
            self.dwABitMask = 4278190080


        elif TEX.dwFourCC == b'\x15\x00\x00\x00':
            self.dwSizePF = 32
            self.dwFlagsPF = 65
            self.dwFourCC = b'\x00' * 4
            self.dwRGBBitCount = 32
            self.dwRBitMask = 16711680
            self.dwGBitMask = 65280
            self.dwBBitMask = 255
            self.dwABitMask = 4278190080
            
        
        elif TEX.dwFourCC == b'\x16\x00\x00\x00':
            self.dwSizePF = 32
            self.dwFlagsPF = 64
            self.dwFourCC = b'\x00' * 4
            self.dwRGBBitCount = 32
            self.dwRBitMask = 16711680
            self.dwGBitMask = 65280
            self.dwBBitMask = 255
            self.dwABitMask = 0
            
        elif TEX.dwFourCC == b'\x32\x00\x00\x00':
            self.dwSizePF = 32
            self.dwFlagsPF = 131072
            self.dwFourCC = b'\x00' * 4
            self.dwRGBBitCount = 8                     
            self.dwRBitMask = 255
            self.dwGBitMask = 0
            self.dwBBitMask = 0
            self.dwABitMask = 0
            
            
            
                
        self.dwCaps = 4198408
        self.dwCaps2 = 0
        self.dwCaps3 = 0
        self.dwCaps4 = 0
        self.dwReserved2 = 0
            
        self.dataDDS = TEX.dataTEX
        
    
    def WriteDDSHeader(self, f):
        f.write(self.Magic)
        
        write_uint(f, self.dwSize)
        write_uint(f, self.dwFlags)
        write_uint(f, self.dwHeight)
        write_uint(f, self.dwWidth)
        write_uint(f, self.dwPitchOrLinearSize)
        write_uint(f, self.dwDepth)
        write_uint(f, self.dwMipMapCount)
        f.write(self.dwReserved)
        self.WriteDDSPixelFormat(f)
        write_uint(f, self.dwCaps)
        write_uint(f, self.dwCaps2)
        write_uint(f, self.dwCaps3)
        write_uint(f, self.dwCaps4)
        write_uint(f, self.dwReserved2)
    
    
    
    def WriteDDSPixelFormat(self, f):
        write_uint(f, self.dwSizePF)
        write_uint(f, self.dwFlagsPF)
        f.write(self.dwFourCC)
        write_uint(f, self.dwRGBBitCount)
        write_uint(f, self.dwRBitMask)
        write_uint(f, self.dwGBitMask)
        write_uint(f, self.dwBBitMask)
        write_uint(f, self.dwABitMask)
        
        
    def WriteDDSData(self, f):
        f.write(self.dataDDS)

