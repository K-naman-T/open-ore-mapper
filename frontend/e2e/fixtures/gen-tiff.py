import os
import struct

def make_tiff(width=1, height=1, fill=128):
    # Minimal valid TIFF: 1-pixel grayscale
    buf = bytearray()
    # Header: little-endian
    buf += b'II'  # byte order
    buf += struct.pack('<H', 42)  # magic
    buf += struct.pack('<I', 8)  # offset to first IFD

    num_entries = 4
    buf += struct.pack('<H', num_entries)

    # Tag entries (12 bytes each)
    entries = []
    # 256 = ImageWidth (SHORT)
    entries.append(struct.pack('<HH', 256, 3) + struct.pack('<I', 1) + struct.pack('<H', width) + b'\x00\x00')
    # 257 = ImageLength (SHORT)
    entries.append(struct.pack('<HH', 257, 3) + struct.pack('<I', 1) + struct.pack('<H', height) + b'\x00\x00')
    # 258 = BitsPerSample (SHORT)
    entries.append(struct.pack('<HH', 258, 3) + struct.pack('<I', 1) + struct.pack('<H', 8) + b'\x00\x00')
    # 262 = PhotometricInterpretation (SHORT) - 1 = BlackIsZero
    entries.append(struct.pack('<HH', 262, 3) + struct.pack('<I', 1) + struct.pack('<H', 1) + b'\x00\x00')

    for e in entries:
        buf += e

    # No more IFDs
    buf += struct.pack('<I', 0)

    # Strip offset (tag 273)
    # Strip byte counts (tag 279)
    # We'll add them in a second IFD... or just put image data directly after

    # Actually, a minimal valid TIFF needs ImageWidth, ImageLength, BitsPerSample,
    # Compression (1=no compression), StripOffsets, RowsPerStrip, StripByteCounts, PhotometricInterpretation
    # Let me rebuild properly.

    return buf

def make_valid_tiff(width, height, fill=128):
    buf = bytearray()
    buf += b'II'  # little endian
    buf += struct.pack('<H', 42)
    # placeholder for IFD offset (will be 1024 to leave room for image data)
    ifd_offset = 1024
    buf += struct.pack('<I', ifd_offset)

    # Pad to IFD offset with image data
    image_data = bytes([fill]) * (width * height)
    # Place image data at offset 8
    buf += image_data
    # Pad to IFD offset
    while len(buf) < ifd_offset:
        buf += b'\x00'

    # IFD
    num_entries = 9
    buf += struct.pack('<H', num_entries)

    tags = []
    # 256 = ImageWidth (SHORT)
    tags.append(struct.pack('<HH', 256, 3) + struct.pack('<I', 1) + struct.pack('<HH', width, 0))
    # 257 = ImageLength (SHORT)
    tags.append(struct.pack('<HH', 257, 3) + struct.pack('<I', 1) + struct.pack('<HH', height, 0))
    # 258 = BitsPerSample (SHORT, count=1)
    tags.append(struct.pack('<HH', 258, 3) + struct.pack('<I', 1) + struct.pack('<HH', 8, 0))
    # 259 = Compression (SHORT, 1 = no compression)
    tags.append(struct.pack('<HH', 259, 3) + struct.pack('<I', 1) + struct.pack('<HH', 1, 0))
    # 262 = PhotometricInterpretation (SHORT, 1 = BlackIsZero)
    tags.append(struct.pack('<HH', 262, 3) + struct.pack('<I', 1) + struct.pack('<HH', 1, 0))
    # 273 = StripOffsets (LONG, count=1) - offset to 8
    tags.append(struct.pack('<HH', 273, 4) + struct.pack('<I', 1) + struct.pack('<I', 8))
    # 277 = SamplesPerPixel (SHORT, count=1)
    tags.append(struct.pack('<HH', 277, 3) + struct.pack('<I', 1) + struct.pack('<HH', 1, 0))
    # 278 = RowsPerStrip (SHORT, count=1)
    tags.append(struct.pack('<HH', 278, 3) + struct.pack('<I', 1) + struct.pack('<HH', height, 0))
    # 279 = StripByteCounts (LONG, count=1)
    tags.append(struct.pack('<HH', 279, 4) + struct.pack('<I', 1) + struct.pack('<I', len(image_data)))

    for t in tags:
        buf += t

    # Next IFD offset = 0
    buf += struct.pack('<I', 0)

    return buf

tiff = make_valid_tiff(8, 8, 128)
out = os.path.join(os.path.dirname(__file__), 'test-cube.tif')
with open(out, 'wb') as f:
    f.write(tiff)
print(f"Created {out}: {len(tiff)} bytes")
