"""
Complete Daybreak X to GLTF Converter
Converts Daybreak X files to GLTF and automatically applies all necessary fixes

This script:
1. Converts X files to GLTF using assimp
2. Fixes invalid animation timing data
3. Validates and fixes coordinate bounds
4. Creates a ready-to-use GLTF file

Usage:
    python convert_daybreak_x_to_gltf.py input.X [output.gltf]
"""

import sys
import subprocess
from pathlib import Path
from fix_daybreak_gltf import DaybreakGLTFFixer


def convert_x_to_gltf(input_file: str, output_file: str = None) -> Path:
    """
    Convert X file to GLTF using assimp
    
    Args:
        input_file: Path to input .X file
        output_file: Path to output .gltf file (auto-generated if not provided)
    
    Returns:
        Path to generated GLTF file
    """
    input_path = Path(input_file)
    
    # Auto-generate output filename if not provided
    if output_file is None:
        output_file = input_path.parent / f"{input_path.stem}.gltf"
    else:
        output_file = Path(output_file)
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print("="*80)
    print(f"CONVERTING: {input_path.name}")
    print("="*80)
    print()
    print(f"[1/2] Converting X to GLTF with assimp...")
    print(f"  Input:  {input_path}")
    print(f"  Output: {output_file}")
    
    # Use assimp CLI to convert
    result = subprocess.run(
        ['assimp', 'export', str(input_path), str(output_file), '-f', 'gltf2'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"\n[ERROR] Assimp conversion failed:")
        print(result.stderr)
        sys.exit(1)
    
    print(f"  Conversion complete!")
    print()
    
    return output_file


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Daybreak X to GLTF Converter")
        print("="*80)
        print()
        print("Usage: python convert_daybreak_x_to_gltf.py <input.X> [output.gltf]")
        print()
        print("This script:")
        print("  1. Converts Daybreak X files to GLTF format")
        print("  2. Fixes invalid animation timing (float_max/-float_max -> proper timestamps)")
        print("  3. Validates coordinate bounds and structure")
        print("  4. Creates a ready-to-use, properly formatted GLTF file")
        print()
        print("Examples:")
        print("  python convert_daybreak_x_to_gltf.py Satoko.X")
        print("  python convert_daybreak_x_to_gltf.py Satoko.X output/Satoko_fixed.gltf")
        print()
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Check input exists
    if not Path(input_file).exists():
        print(f"[ERROR] File not found: {input_file}")
        sys.exit(1)
    
    # Convert X to GLTF
    temp_gltf = convert_x_to_gltf(input_file, output_file)
    
    # Fix the generated GLTF
    print(f"[2/2] Applying Daybreak-specific fixes...")
    print()
    
    fixer = DaybreakGLTFFixer(str(temp_gltf))
    success = fixer.fix_all()
    
    # Determine final output path
    if output_file:
        final_output = Path(output_file)
    else:
        # Replace temp file with fixed version
        final_output = temp_gltf.parent / f"{temp_gltf.stem}_fixed.gltf"
    
    fixer.save(final_output)
    
    print()
    print("="*80)
    print("[SUCCESS] Conversion complete!")
    print("="*80)
    print()
    print(f"Output files:")
    print(f"  GLTF: {final_output}")
    print(f"  BIN:  {final_output.parent / f'{final_output.stem}.bin'}")
    print()
    print("The model is now ready to use in Blender, three.js, or other GLTF viewers!")
    print()
    
    # Clean up temp file if we created a fixed version
    if final_output != temp_gltf and temp_gltf.exists():
        temp_gltf.unlink()
        temp_bin = temp_gltf.parent / f"{temp_gltf.stem}.bin"
        if temp_bin.exists():
            temp_bin.unlink()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
