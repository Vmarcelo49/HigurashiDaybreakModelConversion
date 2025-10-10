"""
Debug Binary Data Reading
Check what's actually in the binary buffer for animation timing
"""

import json
import struct
from pathlib import Path

def debug_binary_data(gltf_path):
    """Debug binary data reading"""
    gltf_path = Path(gltf_path)
    
    print(f"Analyzing: {gltf_path}")
    print("="*70)
    
    # Load GLTF
    with open(gltf_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Load binary
    bin_path = gltf_path.parent / data['buffers'][0]['uri']
    with open(bin_path, 'rb') as f:
        bin_data = f.read()
    
    print(f"Binary file: {bin_path}")
    print(f"Binary size: {len(bin_data)} bytes")
    
    # Get first animation's first sampler input accessor
    anim = data['animations'][0]
    sampler = anim['samplers'][0]
    input_accessor_idx = sampler['input']
    
    print(f"\nFirst animation: {anim.get('name')}")
    print(f"First sampler input accessor: {input_accessor_idx}")
    
    # Get accessor details
    accessor = data['accessors'][input_accessor_idx]
    print(f"\nAccessor {input_accessor_idx}:")
    print(f"  bufferView: {accessor.get('bufferView')}")
    print(f"  byteOffset: {accessor.get('byteOffset', 0)}")
    print(f"  componentType: {accessor.get('componentType')}")
    print(f"  count: {accessor.get('count')}")
    print(f"  type: {accessor.get('type')}")
    print(f"  min: {accessor.get('min')}")
    print(f"  max: {accessor.get('max')}")
    
    # Get buffer view
    buffer_view_idx = accessor.get('bufferView')
    buffer_view = data['bufferViews'][buffer_view_idx]
    
    print(f"\nBufferView {buffer_view_idx}:")
    print(f"  buffer: {buffer_view.get('buffer', 0)}")
    print(f"  byteOffset: {buffer_view.get('byteOffset', 0)}")
    print(f"  byteLength: {buffer_view.get('byteLength')}")
    print(f"  byteStride: {buffer_view.get('byteStride', 'not set')}")
    print(f"  target: {buffer_view.get('target', 'not set')}")
    
    # Calculate total offset
    bv_offset = buffer_view.get('byteOffset', 0)
    acc_offset = accessor.get('byteOffset', 0)
    total_offset = bv_offset + acc_offset
    count = accessor.get('count', 0)
    
    print(f"\nReading data:")
    print(f"  Total offset: {total_offset}")
    print(f"  Count: {count}")
    
    # Read first 10 values as floats
    print(f"\nFirst 10 values (as floats):")
    for i in range(min(10, count)):
        pos = total_offset + (i * 4)  # 4 bytes per float
        value = struct.unpack_from('f', bin_data, pos)[0]
        print(f"    [{i}] @ offset {pos}: {value}")
    
    # Also read as raw bytes
    print(f"\nFirst 40 bytes at offset {total_offset} (hex):")
    raw_bytes = bin_data[total_offset:total_offset+40]
    hex_str = ' '.join(f'{b:02x}' for b in raw_bytes)
    print(f"  {hex_str}")
    
    # Check if all zeros
    if all(b == 0 for b in raw_bytes):
        print("\n⚠️ WARNING: Data is all zeros!")
    
    # Check for NaN pattern (0x7FC00000 for float NaN)
    nan_pattern = b'\x00\x00\xc0\x7f'
    if nan_pattern in raw_bytes:
        print("\n⚠️ WARNING: NaN pattern detected!")

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python debug_binary_data.py <gltf_file>")
        sys.exit(1)
    
    debug_binary_data(sys.argv[1])
