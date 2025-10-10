"""
Daybreak GLTF Fixer
Fixes the corrupted data that assimp produces when converting Daybreak X files to GLTF

KNOWN ISSUES FIXED:
1. Animation timing accessors have float_max/-float_max values causing -inf durations
2. Invalid keyframe timestamps
3. Potential coordinate/transform issues

Usage:
    python fix_daybreak_gltf.py input.gltf [output.gltf]
"""

import json
import struct
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import math


class DaybreakGLTFFixer:
    """Fixes known issues in Daybreak X->GLTF conversions"""
    
    def __init__(self, gltf_path: str):
        self.gltf_path = Path(gltf_path)
        self.gltf_data = None
        self.bin_data = None
        self.bin_path = None
        self.fixes_applied = []
        self.issues_found = []
        
    def load(self) -> bool:
        """Load GLTF and associated binary data"""
        try:
            # Load GLTF JSON
            with open(self.gltf_path, 'r', encoding='utf-8', errors='ignore') as f:
                self.gltf_data = json.load(f)
            
            # Find and load BIN file
            buffers = self.gltf_data.get('buffers', [])
            if buffers and 'uri' in buffers[0]:
                self.bin_path = self.gltf_path.parent / buffers[0]['uri']
                if self.bin_path.exists():
                    with open(self.bin_path, 'rb') as f:
                        self.bin_data = bytearray(f.read())
                else:
                    print(f"Warning: Binary file not found: {self.bin_path}")
                    self.bin_data = bytearray()
            
            return True
        except Exception as e:
            print(f"Error loading GLTF: {e}")
            return False
    
    def fix_all(self) -> bool:
        """Apply all known fixes"""
        print("="*80)
        print(f"FIXING DAYBREAK GLTF: {self.gltf_path.name}")
        print("="*80)
        print()
        
        if not self.load():
            return False
        
        # Apply fixes
        self.fix_animation_timing()
        self.fix_extreme_coordinates()
        self.validate_structure()
        
        # Report
        self.print_report()
        
        return len(self.issues_found) == 0
    
    def fix_animation_timing(self):
        """Fix animation timing with invalid float_max/-float_max values"""
        print("[1/3] Fixing animation timing...")
        
        animations = self.gltf_data.get('animations', [])
        accessors = self.gltf_data.get('accessors', [])
        buffer_views = self.gltf_data.get('bufferViews', [])
        
        fixed_count = 0
        
        for anim_idx, animation in enumerate(animations):
            samplers = animation.get('samplers', [])
            
            for sampler_idx, sampler in enumerate(samplers):
                input_accessor_idx = sampler.get('input')
                if input_accessor_idx is None:
                    continue
                
                accessor = accessors[input_accessor_idx]
                
                # Check if min/max are corrupted (float_max or -inf)
                min_val = accessor.get('min', [0])[0]
                max_val = accessor.get('max', [0])[0]
                
                is_corrupted = (
                    abs(min_val) > 1e100 or 
                    abs(max_val) > 1e100 or
                    math.isinf(min_val) or 
                    math.isinf(max_val) or
                    math.isnan(min_val) or
                    math.isnan(max_val) or
                    min_val > max_val
                )
                
                if is_corrupted:
                    # Read actual timing data from buffer
                    buffer_view_idx = accessor.get('bufferView')
                    if buffer_view_idx is not None and buffer_view_idx < len(buffer_views):
                        buffer_view = buffer_views[buffer_view_idx]
                        byte_offset = buffer_view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
                        count = accessor.get('count', 0)
                        
                        # Read float array
                        times = []
                        for i in range(count):
                            offset = byte_offset + (i * 4)  # 4 bytes per float
                            if offset + 4 <= len(self.bin_data):
                                time_val = struct.unpack_from('<f', self.bin_data, offset)[0]
                                times.append(time_val)
                        
                        if times:
                            # Check if the actual data is also corrupted
                            actual_corrupted = any(
                                abs(t) > 1e100 or math.isinf(t) or math.isnan(t) 
                                for t in times
                            )
                            
                            if actual_corrupted:
                                # Generate synthetic timing at 30 FPS
                                frame_time = 1.0 / 30.0
                                new_times = [i * frame_time for i in range(count)]
                                
                                # Write back to buffer
                                for i, time_val in enumerate(new_times):
                                    offset = byte_offset + (i * 4)
                                    struct.pack_into('<f', self.bin_data, offset, time_val)
                                
                                times = new_times
                                self.fixes_applied.append(
                                    f"Animation {anim_idx} sampler {sampler_idx}: "
                                    f"Regenerated {count} keyframe timestamps at 30 FPS"
                                )
                            
                            # Update min/max in accessor
                            actual_min = min(times)
                            actual_max = max(times)
                            accessor['min'] = [actual_min]
                            accessor['max'] = [actual_max]
                            fixed_count += 1
                            
                            self.fixes_applied.append(
                                f"Animation {anim_idx} sampler {sampler_idx}: "
                                f"Fixed timing {min_val:.2e} to {actual_min:.3f}s, "
                                f"{max_val:.2e} to {actual_max:.3f}s"
                            )
        
        print(f"  Fixed {fixed_count} animation samplers with invalid timing")
        print()
    
    def fix_extreme_coordinates(self):
        """Check for and fix extreme coordinate values"""
        print("[2/3] Checking for extreme coordinates...")
        
        accessors = self.gltf_data.get('accessors', [])
        buffer_views = self.gltf_data.get('bufferViews', [])
        
        extreme_count = 0
        
        for acc_idx, accessor in enumerate(accessors):
            # Check position, normal, and transform accessors
            acc_type = accessor.get('type')
            component_type = accessor.get('componentType')
            
            # Skip if not float data (5126 = FLOAT)
            if component_type != 5126:
                continue
            
            # Get min/max
            min_vals = accessor.get('min', [])
            max_vals = accessor.get('max', [])
            
            if not min_vals or not max_vals:
                continue
            
            # Check for extreme values
            is_extreme = any(
                abs(v) > 10000 or math.isinf(v) or math.isnan(v)
                for v in (min_vals + max_vals)
            )
            
            if is_extreme:
                # Read and recalculate actual bounds
                buffer_view_idx = accessor.get('bufferView')
                if buffer_view_idx is not None and buffer_view_idx < len(buffer_views):
                    buffer_view = buffer_views[buffer_view_idx]
                    byte_offset = buffer_view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
                    count = accessor.get('count', 0)
                    
                    # Determine component count
                    type_sizes = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
                    num_components = type_sizes.get(acc_type, 1)
                    
                    # Read all values
                    all_values = []
                    for comp in range(num_components):
                        comp_values = []
                        for i in range(count):
                            offset = byte_offset + (i * num_components + comp) * 4
                            if offset + 4 <= len(self.bin_data):
                                val = struct.unpack_from('<f', self.bin_data, offset)[0]
                                comp_values.append(val)
                        all_values.append(comp_values)
                    
                    # Recalculate min/max
                    new_min = [min(vals) if vals else 0.0 for vals in all_values]
                    new_max = [max(vals) if vals else 0.0 for vals in all_values]
                    
                    # Check if actual data is also extreme
                    actual_extreme = any(
                        abs(v) > 10000 or math.isinf(v) or math.isnan(v)
                        for v in (new_min + new_max)
                    )
                    
                    if actual_extreme:
                        self.issues_found.append(
                            f"Accessor {acc_idx} ({acc_type}): Contains extreme values "
                            f"min={new_min}, max={new_max}"
                        )
                    else:
                        accessor['min'] = new_min
                        accessor['max'] = new_max
                        extreme_count += 1
                        self.fixes_applied.append(
                            f"Accessor {acc_idx}: Fixed bounds from "
                            f"{min_vals} to {new_min}"
                        )
        
        if extreme_count > 0:
            print(f"  Fixed {extreme_count} accessors with extreme coordinate bounds")
        else:
            print(f"  No coordinate issues found")
        print()
    
    def validate_structure(self):
        """Validate overall GLTF structure"""
        print("[3/3] Validating structure...")
        
        # Check for required fields
        required_fields = ['scenes', 'nodes']
        for field in required_fields:
            if field not in self.gltf_data:
                self.issues_found.append(f"Missing required field: {field}")
        
        # Check accessor/bufferView references
        accessors = self.gltf_data.get('accessors', [])
        buffer_views = self.gltf_data.get('bufferViews', [])
        buffers = self.gltf_data.get('buffers', [])
        
        for i, accessor in enumerate(accessors):
            bv_idx = accessor.get('bufferView')
            if bv_idx is not None and bv_idx >= len(buffer_views):
                self.issues_found.append(f"Accessor {i} references invalid bufferView {bv_idx}")
        
        for i, buffer_view in enumerate(buffer_views):
            buf_idx = buffer_view.get('buffer')
            if buf_idx is not None and buf_idx >= len(buffers):
                self.issues_found.append(f"BufferView {i} references invalid buffer {buf_idx}")
        
        print(f"  Structure validation complete")
        print()
    
    def save(self, output_path: Path = None):
        """Save fixed GLTF and binary data"""
        if output_path is None:
            output_path = self.gltf_path.parent / f"{self.gltf_path.stem}_fixed.gltf"
        else:
            output_path = Path(output_path)
        
        # Update buffer URI if needed
        if self.bin_data and self.gltf_data.get('buffers'):
            new_bin_name = f"{output_path.stem}.bin"
            self.gltf_data['buffers'][0]['uri'] = new_bin_name
            new_bin_path = output_path.parent / new_bin_name
        
        # Save GLTF JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.gltf_data, f, indent=2)
        
        # Save binary data
        if self.bin_data:
            with open(new_bin_path, 'wb') as f:
                f.write(self.bin_data)
        
        print(f"Saved fixed GLTF to: {output_path}")
        if self.bin_data:
            print(f"Saved fixed binary to: {new_bin_path}")
    
    def print_report(self):
        """Print fix report"""
        print("="*80)
        print("FIX REPORT")
        print("="*80)
        print()
        
        if self.fixes_applied:
            print(f"[+] FIXES APPLIED ({len(self.fixes_applied)}):")
            for fix in self.fixes_applied[:20]:  # Show first 20
                print(f"  - {fix}")
            if len(self.fixes_applied) > 20:
                print(f"  ... and {len(self.fixes_applied) - 20} more")
            print()
        
        if self.issues_found:
            print(f"[!] REMAINING ISSUES ({len(self.issues_found)}):")
            for issue in self.issues_found[:10]:  # Show first 10
                print(f"  - {issue}")
            if len(self.issues_found) > 10:
                print(f"  ... and {len(self.issues_found) - 10} more")
            print()
        else:
            print("[+] NO REMAINING ISSUES!")
            print()
        
        print("="*80)


def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_daybreak_gltf.py <input.gltf> [output.gltf]")
        print()
        print("Fixes known issues in Daybreak X->GLTF conversions:")
        print("  - Invalid animation timing (float_max/-float_max)")
        print("  - Extreme coordinate values")
        print("  - Corrupted accessor bounds")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not Path(input_file).exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    fixer = DaybreakGLTFFixer(input_file)
    success = fixer.fix_all()
    fixer.save(output_file)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
