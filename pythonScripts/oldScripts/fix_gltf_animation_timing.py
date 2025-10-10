"""
Fix GLTF Animation Timing Issues
Recalculates min/max values for animation timing accessors

This fixes a bug in Assimp's GLTF exporter where animation timing accessors
have invalid min/max values (DBL_MAX and -DBL_MAX instead of actual values).

The script:
1. Reads the GLTF file and its binary data
2. Identifies animation input accessors (timing data)
3. Recalculates correct min/max values from the actual binary data
4. Updates the GLTF file with corrected values
"""

import json
import struct
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GLTFAnimationFixer:
    """Fixes animation timing issues in GLTF files"""
    
    # Component type mappings
    COMPONENT_TYPES = {
        5120: ('b', 1),   # BYTE
        5121: ('B', 1),   # UNSIGNED_BYTE
        5122: ('h', 2),   # SHORT
        5123: ('H', 2),   # UNSIGNED_SHORT
        5125: ('I', 4),   # UNSIGNED_INT
        5126: ('f', 4),   # FLOAT
    }
    
    # Type size mappings
    TYPE_SIZES = {
        'SCALAR': 1,
        'VEC2': 2,
        'VEC3': 3,
        'VEC4': 4,
        'MAT2': 4,
        'MAT3': 9,
        'MAT4': 16,
    }
    
    def __init__(self, gltf_path: str, output_path: str = None):
        """
        Initialize the fixer
        
        Args:
            gltf_path: Path to the GLTF file to fix
            output_path: Path for fixed GLTF file (default: adds _fixed suffix)
        """
        self.gltf_path = Path(gltf_path)
        
        if not self.gltf_path.exists():
            raise FileNotFoundError(f"GLTF file not found: {gltf_path}")
        
        if output_path:
            self.output_path = Path(output_path)
        else:
            # Replace existing file
            self.output_path = self.gltf_path
        
        self.gltf_data = None
        self.bin_data = None
        self.bin_data_modified = False
        self.fixed_count = 0
    
    def load_gltf(self):
        """Load the GLTF file and associated binary data"""
        logger.info(f"Loading GLTF file: {self.gltf_path}")
        
        # Try different encodings to handle malformed GLTF files
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        loaded = False
        
        for encoding in encodings:
            try:
                with open(self.gltf_path, 'r', encoding=encoding, errors='ignore') as f:
                    self.gltf_data = json.load(f)
                loaded = True
                break
            except (UnicodeDecodeError, json.JSONDecodeError):
                if encoding == encodings[-1]:
                    raise
                continue
        
        if not loaded:
            raise ValueError("Failed to load GLTF file with any encoding")
        
        # Load binary data if referenced
        if 'buffers' in self.gltf_data and len(self.gltf_data['buffers']) > 0:
            buffer = self.gltf_data['buffers'][0]
            if 'uri' in buffer:
                bin_path = self.gltf_path.parent / buffer['uri']
                logger.info(f"Loading binary data: {bin_path}")
                
                with open(bin_path, 'rb') as f:
                    self.bin_data = bytearray(f.read())  # Use bytearray for modification
                
                logger.info(f"Loaded {len(self.bin_data)} bytes of binary data")
    
    def read_accessor_data(self, accessor_idx: int) -> List[float]:
        """
        Read data from an accessor
        
        Args:
            accessor_idx: Index of the accessor
            
        Returns:
            List of values read from the accessor
        """
        if accessor_idx >= len(self.gltf_data['accessors']):
            return []
        
        accessor = self.gltf_data['accessors'][accessor_idx]
        buffer_view_idx = accessor.get('bufferView')
        
        if buffer_view_idx is None:
            return []
        
        buffer_view = self.gltf_data['bufferViews'][buffer_view_idx]
        
        # Get buffer view properties
        offset = buffer_view.get('byteOffset', 0)
        length = buffer_view.get('byteLength', 0)
        
        # Get accessor properties
        accessor_offset = accessor.get('byteOffset', 0)
        component_type = accessor.get('componentType')
        count = accessor.get('count', 0)
        accessor_type = accessor.get('type', 'SCALAR')
        
        if component_type not in self.COMPONENT_TYPES:
            logger.warning(f"Unknown component type: {component_type}")
            return []
        
        # Calculate total offset
        total_offset = offset + accessor_offset
        
        # Get format and size
        fmt_char, component_size = self.COMPONENT_TYPES[component_type]
        type_size = self.TYPE_SIZES.get(accessor_type, 1)
        
        # Read data
        values = []
        stride = buffer_view.get('byteStride', component_size * type_size)
        
        for i in range(count):
            pos = total_offset + (i * stride)
            
            # Read components
            for j in range(type_size):
                component_pos = pos + (j * component_size)
                
                if component_pos + component_size > len(self.bin_data):
                    logger.warning(f"Accessor {accessor_idx}: Read beyond buffer")
                    return values
                
                value = struct.unpack_from(fmt_char, self.bin_data, component_pos)[0]
                values.append(value)
        
        return values
    
    def write_accessor_data(self, accessor_idx: int, values: List[float]) -> bool:
        """
        Write corrected data to an accessor in the binary buffer
        
        Args:
            accessor_idx: Index of the accessor
            values: List of values to write
            
        Returns:
            True if successful
        """
        if accessor_idx >= len(self.gltf_data['accessors']):
            return False
        
        accessor = self.gltf_data['accessors'][accessor_idx]
        buffer_view_idx = accessor.get('bufferView')
        
        if buffer_view_idx is None:
            return False
        
        buffer_view = self.gltf_data['bufferViews'][buffer_view_idx]
        
        # Get buffer view properties
        offset = buffer_view.get('byteOffset', 0)
        
        # Get accessor properties
        accessor_offset = accessor.get('byteOffset', 0)
        component_type = accessor.get('componentType')
        count = accessor.get('count', 0)
        accessor_type = accessor.get('type', 'SCALAR')
        
        if component_type not in self.COMPONENT_TYPES:
            return False
        
        # Calculate total offset
        total_offset = offset + accessor_offset
        
        # Get format and size
        fmt_char, component_size = self.COMPONENT_TYPES[component_type]
        type_size = self.TYPE_SIZES.get(accessor_type, 1)
        
        # Write data
        stride = buffer_view.get('byteStride', component_size * type_size)
        value_idx = 0
        
        for i in range(count):
            if value_idx >= len(values):
                break
                
            pos = total_offset + (i * stride)
            
            # Write components
            for j in range(type_size):
                if value_idx >= len(values):
                    break
                    
                component_pos = pos + (j * component_size)
                
                if component_pos + component_size > len(self.bin_data):
                    return False
                
                # Pack and write the value
                struct.pack_into(fmt_char, self.bin_data, component_pos, values[value_idx])
                value_idx += 1
        
        self.bin_data_modified = True
        return True
    
    def fix_animation_accessors(self):
        """Fix all animation timing accessors"""
        if 'animations' not in self.gltf_data or 'accessors' not in self.gltf_data:
            logger.warning("No animations or accessors found")
            return
        
        logger.info(f"Checking {len(self.gltf_data['animations'])} animations...")
        
        # Collect all input accessors from animations
        input_accessors = set()
        
        for anim in self.gltf_data['animations']:
            for sampler in anim.get('samplers', []):
                input_idx = sampler.get('input')
                if input_idx is not None:
                    input_accessors.add(input_idx)
        
        logger.info(f"Found {len(input_accessors)} unique input accessors")
        
        # Fix each input accessor
        for accessor_idx in sorted(input_accessors):
            accessor = self.gltf_data['accessors'][accessor_idx]
            
            # Check if this accessor needs fixing
            min_val = accessor.get('min', [0])[0] if accessor.get('min') else 0
            max_val = accessor.get('max', [0])[0] if accessor.get('max') else 0
            
            # Check for DBL_MAX values (indicates broken min/max)
            DBL_MAX = 1.7976931348623157e+308
            
            if abs(min_val) > 1e100 or abs(max_val) > 1e100 or min_val > max_val:
                # Need to recalculate
                values = self.read_accessor_data(accessor_idx)
                
                if values:
                    # Filter out NaN and Inf values
                    valid_values = [v for v in values if not (float('nan') == v or float('inf') == abs(v) or v != v)]
                    
                    if valid_values:
                        # Calculate correct min/max from valid values
                        actual_min = min(valid_values)
                        actual_max = max(valid_values)
                    else:
                        # All values are invalid - generate linear timing based on frame count
                        # Assume 30 FPS (Higurashi Daybreak's animation frame rate)
                        frame_count = accessor.get('count', 1)
                        actual_min = 0.0
                        actual_max = (frame_count - 1) / 30.0  # Convert frames to seconds at 30 FPS
                        
                        # Generate evenly spaced timing values
                        corrected_values = []
                        for i in range(frame_count):
                            corrected_values.append(i / 30.0)
                        
                        # Write corrected values to binary buffer
                        if self.write_accessor_data(accessor_idx, corrected_values):
                            if self.fixed_count < 3:
                                logger.info(f"Accessor {accessor_idx}: Regenerated timing data "
                                          f"({frame_count} frames @ 30fps = {actual_max:.3f}s)")
                        else:
                            if self.fixed_count < 3:
                                logger.warning(f"Accessor {accessor_idx}: Failed to write timing data to binary")
                    
                    # Update accessor
                    accessor['min'] = [actual_min]
                    accessor['max'] = [actual_max]
                    
                    self.fixed_count += 1
                    
                    if self.fixed_count <= 5:  # Show first few fixes
                        logger.info(f"Fixed accessor {accessor_idx}: "
                                  f"min={actual_min:.6f}, max={actual_max:.6f}, "
                                  f"duration={actual_max - actual_min:.6f}s")
        
        logger.info(f"✓ Fixed {self.fixed_count} animation timing accessors")
    
    def save_gltf(self):
        """Save the fixed GLTF file and binary data"""
        logger.info(f"Saving fixed GLTF to: {self.output_path}")
        
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(self.gltf_data, f, indent=2)
        
        logger.info("✓ GLTF file saved successfully")
        
        # Save modified binary data if it was changed
        if self.bin_data_modified and self.bin_data is not None:
            if 'buffers' in self.gltf_data and len(self.gltf_data['buffers']) > 0:
                buffer = self.gltf_data['buffers'][0]
                if 'uri' in buffer:
                    bin_path = self.output_path.parent / buffer['uri']
                    logger.info(f"Saving modified binary data to: {bin_path}")
                    
                    with open(bin_path, 'wb') as f:
                        f.write(self.bin_data)
                    
                    logger.info("✓ Binary data saved successfully")
    
    def fix(self):
        """Main fix method"""
        self.load_gltf()
        self.fix_animation_accessors()
        self.save_gltf()
        
        return self.fixed_count > 0


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python fix_gltf_animation_timing.py <path_to_gltf_file> [output_path]")
        print("\nFixes animation timing issues in GLTF files exported by Assimp.")
        print("If output_path is not specified, the original file will be overwritten.")
        sys.exit(1)
    
    gltf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        fixer = GLTFAnimationFixer(gltf_path, output_path)
        success = fixer.fix()
        
        if success:
            logger.info("=" * 70)
            logger.info("✓ Animation timing fixed successfully!")
            logger.info("=" * 70)
        else:
            logger.warning("No issues found or no fixes applied")
            
    except Exception as e:
        logger.error(f"Error fixing GLTF file: {e}")
        logger.exception("Detailed error:")
        sys.exit(1)


if __name__ == '__main__':
    main()
