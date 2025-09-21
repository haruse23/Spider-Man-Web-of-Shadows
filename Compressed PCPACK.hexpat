import std.io;
import std.mem;

struct CompressedBlock {
    char magic[4]; // NCH\x00
    u32 CompressedDataSize;
    std::print(CompressedDataSize);
    u32 unknown1;
    u32 UncompressedDataSize;
    u32 unknown2;
    u32 unknown3;
    u32 CompressedEnd; // Header size (0x20) + CompressedDataSize (this offset is relative to the current chunk)
    u32 IsCompressedFlag; // 1 is Compressed
    u8 Data[CompressedDataSize];
    
    if (CompressedDataSize < 0x7FFE0) {
        u32 size_of_padding = 0x7FFE0 - CompressedDataSize;
        
        if ($ + size_of_padding < std::mem::size()) {
            std::mem::AlignTo<0x80000>;
        }
        
        else {
            size_of_padding = std::mem::size() - $;
            padding[size_of_padding];
        }
        
    }
    
    // Rest is Padding (A1)
    
    // Compression Method is LZO1X
    // Max Block Size is 0x80000
};





CompressedBlock CompressedBlock[while(!std::mem::eof())] @0x00;


