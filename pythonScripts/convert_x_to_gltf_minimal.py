"""
Minimal X to GLTF Converter
Uses assimp CLI with absolute minimum custom code to convert .X files to GLTF format
"""

import sys
import subprocess
from pathlib import Path


def convert_x_to_gltf(input_file: str, output_file: str = None):
    """
    Convert .X file to GLTF with minimal custom code
    
    Args:
        input_file: Path to input .X file
        output_file: Path to output .gltf file (optional, auto-generated if not provided)
    """
    input_path = Path(input_file)
    
    # Auto-generate output filename if not provided
    if output_file is None:
        output_file = input_path.with_suffix('.gltf')
    else:
        output_file = Path(output_file)
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Converting: {input_path} -> {output_file}")
    
    # Use assimp CLI to convert - let assimp handle everything
    result = subprocess.run(
        ['assimp', 'export', str(input_path), str(output_file), '-f', 'gltf2'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"✗ Conversion failed: {result.stderr}")
        sys.exit(1)
    
    print(f"✓ Conversion complete: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_x_to_gltf_minimal.py <input.x> [output.gltf]")
        print("Example: python convert_x_to_gltf_minimal.py Satoko.X")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    convert_x_to_gltf(input_file, output_file)
