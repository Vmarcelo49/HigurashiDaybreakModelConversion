"""
Analyze GLTF Animation Data
Check for animation timing issues
"""

import json
import sys
from pathlib import Path

def analyze_gltf_animation(gltf_path):
    """Analyze animation data in a GLTF file"""
    print(f"\nAnalyzing: {gltf_path}")
    print("="*70)
    
    with open(gltf_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check animations
    animations = data.get('animations', [])
    print(f"\nTotal Animations: {len(animations)}")
    
    if not animations:
        print("No animations found!")
        return
    
    # Check accessors (contain timing data)
    accessors = data.get('accessors', [])
    print(f"Total Accessors: {len(accessors)}")
    
    # Check buffer views
    bufferViews = data.get('bufferViews', [])
    print(f"Total Buffer Views: {len(bufferViews)}")
    
    # Analyze first few animations
    print("\n" + "="*70)
    print("Animation Details:")
    print("="*70)
    
    for i, anim in enumerate(animations[:5]):
        print(f"\nAnimation {i}: {anim.get('name', 'unnamed')}")
        
        samplers = anim.get('samplers', [])
        channels = anim.get('channels', [])
        
        print(f"  Samplers: {len(samplers)}")
        print(f"  Channels: {len(channels)}")
        
        # Check sampler data
        for j, sampler in enumerate(samplers[:3]):
            print(f"\n  Sampler {j}:")
            print(f"    Input accessor: {sampler.get('input', 'N/A')}")
            print(f"    Output accessor: {sampler.get('output', 'N/A')}")
            print(f"    Interpolation: {sampler.get('interpolation', 'LINEAR')}")
            
            # Get input accessor data (timing)
            input_idx = sampler.get('input')
            if input_idx is not None and input_idx < len(accessors):
                accessor = accessors[input_idx]
                print(f"\n    Input Accessor {input_idx}:")
                print(f"      Type: {accessor.get('type', 'N/A')}")
                print(f"      Component Type: {accessor.get('componentType', 'N/A')}")
                print(f"      Count: {accessor.get('count', 'N/A')}")
                print(f"      Min: {accessor.get('min', 'N/A')}")
                print(f"      Max: {accessor.get('max', 'N/A')}")
                
                # Check for problematic values
                min_val = accessor.get('min', [0])[0] if accessor.get('min') else None
                max_val = accessor.get('max', [0])[0] if accessor.get('max') else None
                
                if min_val is not None and max_val is not None:
                    duration = max_val - min_val
                    print(f"      Duration: {duration} seconds")
                    
                    if min_val < 0 or max_val < 0:
                        print(f"      ⚠️ WARNING: Negative timing values detected!")
                    if duration <= 0:
                        print(f"      ⚠️ WARNING: Invalid duration (zero or negative)!")
                    if abs(min_val) > 1e6 or abs(max_val) > 1e6:
                        print(f"      ⚠️ WARNING: Extremely large timing values!")
            
            # Get output accessor data (keyframes)
            output_idx = sampler.get('output')
            if output_idx is not None and output_idx < len(accessors):
                accessor = accessors[output_idx]
                print(f"\n    Output Accessor {output_idx}:")
                print(f"      Type: {accessor.get('type', 'N/A')}")
                print(f"      Component Type: {accessor.get('componentType', 'N/A')}")
                print(f"      Count: {accessor.get('count', 'N/A')}")
        
        if len(samplers) > 3:
            print(f"\n  ... and {len(samplers) - 3} more samplers")
    
    if len(animations) > 5:
        print(f"\n... and {len(animations) - 5} more animations")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python analyze_gltf_animation.py <path_to_gltf_file>")
        sys.exit(1)
    
    analyze_gltf_animation(sys.argv[1])
