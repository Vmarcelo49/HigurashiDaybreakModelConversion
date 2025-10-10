"""
Automated X to GLTF Converter with Auto-Fix
Converts DirectX .X models to GLTF and automatically fixes texture/mesh names

This script combines:
1. X to GLTF conversion (using Assimp CLI)
2. Automatic texture and mesh name fixing (Shift-JIS issues)
3. PowerShell script generation for texture renaming

This is the recommended all-in-one conversion tool.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple

# Import the fixers
sys.path.insert(0, str(Path(__file__).parent))
try:
    from fix_gltf_texture_names import TextureNameFixer
    from fix_gltf_animation_timing import GLTFAnimationFixer
    from fix_gltf_bone_order import GLTFBoneFixer
except ImportError as e:
    print(f"Error: Required modules must be in the same directory: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoXToGLTFConverter:
    """Automated X to GLTF converter with built-in name fixing"""
    
    def __init__(self, input_path: str, output_path: Optional[str] = None, format_type: str = 'gltf2'):
        """
        Initialize the converter
        
        Args:
            input_path: Path to input .X file or directory
            output_path: Path for output file(s). If None, uses input path with .gltf extension
            format_type: Output format ('gltf2' for .gltf, 'glb2' for .glb)
        """
        self.input_path = Path(input_path)
        self.output_path = Path(output_path) if output_path else None
        self.format_type = format_type
        self.extension = '.gltf' if format_type == 'gltf2' else '.glb'
        
        # Check if assimp is available
        if not self._check_assimp_available():
            logger.error("Assimp CLI tool is not available in PATH")
            logger.error("Please install Assimp from: https://github.com/assimp/assimp/releases")
            sys.exit(1)
    
    def _check_assimp_available(self) -> bool:
        """Check if assimp CLI tool is available"""
        try:
            result = subprocess.run(['assimp', 'version'], 
                                  capture_output=True, 
                                  text=True,
                                  timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def convert_and_fix_single_file(self, input_file: Path, output_file: Path) -> Tuple[bool, Optional[Path]]:
        """
        Convert a single .X file to GLTF and fix names
        
        Args:
            input_file: Path to input .X file
            output_file: Path to output GLTF/GLB file
            
        Returns:
            Tuple of (success, fixed_output_path)
        """
        try:
            logger.info("="*70)
            logger.info(f"Processing: {input_file.name}")
            logger.info("="*70)
            
            # Step 1: Convert to GLTF
            logger.info("Step 1/4: Converting to GLTF...")
            
            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Run assimp export
            result = subprocess.run(
                ['assimp', 'export', str(input_file), str(output_file), '-f', self.format_type],
                capture_output=True,
                text=True,
                timeout=120,
                errors='ignore'  # Ignore encoding errors in output
            )
            
            if result.returncode != 0 or not output_file.exists():
                logger.error(f"  ✗ GLTF conversion failed for {input_file.name}")
                if result.stderr:
                    logger.error(f"  Error: {result.stderr[:500]}")  # Limit error output
                return False, None
            
            # Check file size
            size_mb = output_file.stat().st_size / (1024 * 1024)
            logger.info(f"  ✓ GLTF created: {output_file.name} ({size_mb:.2f} MB)")
            
            # Check for .bin file
            if self.format_type == 'gltf2':
                bin_file = output_file.with_suffix('.bin')
                if bin_file.exists():
                    bin_size_mb = bin_file.stat().st_size / (1024 * 1024)
                    logger.info(f"    + Binary data: {bin_file.name} ({bin_size_mb:.2f} MB)")
            
            # Step 2: Fix bone ordering (only for GLTF, not GLB)
            if self.format_type == 'gltf2':
                logger.info("\nStep 2/4: Fixing bone ordering...")
                
                try:
                    bone_fixer = GLTFBoneFixer(str(output_file), str(output_file))
                    bone_fixer.load_gltf()
                    bone_fixer.fix_node_hierarchy()
                    bone_fixer.fix_bone_order()
                    if bone_fixer.reordered:
                        bone_fixer.save_gltf()
                        logger.info("  ✓ Bone ordering fixed")
                    else:
                        logger.info("  ℹ No bone ordering issues found")
                except Exception as e:
                    logger.warning(f"  ⚠ Bone ordering fix failed: {e}")
                    logger.warning("  Continuing anyway...")
            
            # Step 3: Fix animation timing (only for GLTF, not GLB)
            if self.format_type == 'gltf2':
                logger.info("\nStep 3/4: Fixing animation timing...")
                
                try:
                    anim_fixer = GLTFAnimationFixer(str(output_file), str(output_file))
                    anim_fixer.load_gltf()
                    anim_fixer.fix_animation_accessors()
                    anim_fixer.save_gltf()
                    logger.info("  ✓ Animation timing fixed")
                except Exception as e:
                    logger.warning(f"  ⚠ Animation timing fix failed: {e}")
                    logger.warning("  Continuing with original animation data...")
            
            # Step 4: Fix texture and mesh names (only for GLTF, not GLB)
            if self.format_type == 'gltf2':
                logger.info("\nStep 4/4: Fixing texture and mesh names...")
                
                # Create fixed version
                fixed_output = output_file.with_name(f"{output_file.stem}_clean{output_file.suffix}")
                
                try:
                    fixer = TextureNameFixer(str(output_file), str(fixed_output))
                    
                    # Load GLTF
                    fixer.load_gltf()
                    
                    # Extract and map texture names
                    texture_names = fixer.extract_texture_names()
                    if texture_names:
                        fixer.create_texture_mapping(texture_names)
                        logger.info(f"  → Mapped {len(texture_names)} texture names")
                    
                    # Extract and map mesh names
                    mesh_names = fixer.extract_mesh_names()
                    if mesh_names:
                        fixer.create_mesh_name_mapping(mesh_names)
                        if fixer.mesh_name_mapping:
                            logger.info(f"  → Mapped {len(fixer.mesh_name_mapping)} mesh names")
                    
                    # Update the GLTF data
                    texture_updates = fixer.update_gltf_textures()
                    mesh_updates = fixer.update_gltf_mesh_names()
                    
                    if texture_updates == 0 and mesh_updates == 0:
                        logger.info("  ℹ No name fixes needed - all names are already valid")
                        logger.info(f"  Using original: {output_file.name}")
                        return True, output_file
                    
                    # Save fixed GLTF
                    if not fixer.save_fixed_gltf():
                        logger.warning("  ⚠ Failed to save fixed GLTF, using original")
                        return True, output_file
                    
                    # Save mapping file
                    fixer.save_mapping_file()
                    
                    # Save rename script
                    if fixer.texture_mapping:
                        fixer.save_rename_script()
                    
                    logger.info(f"  ✓ Fixed GLTF saved: {fixed_output.name}")
                    
                    # Copy .bin file if it exists
                    original_bin = output_file.with_suffix('.bin')
                    if original_bin.exists():
                        fixed_bin = fixed_output.with_suffix('.bin')
                        import shutil
                        shutil.copy2(original_bin, fixed_bin)
                        logger.info(f"    + Copied binary data: {fixed_bin.name}")
                    
                    logger.info("\n" + "="*70)
                    logger.info(f"✓ SUCCESS: {input_file.name} → {fixed_output.name}")
                    logger.info("="*70)
                    
                    return True, fixed_output
                    
                except Exception as e:
                    logger.error(f"  ✗ Error during name fixing: {e}")
                    logger.warning(f"  Using unfixed version: {output_file.name}")
                    return True, output_file
            
            else:  # GLB format
                logger.info("\nStep 2/2: Skipped (GLB format doesn't support text editing)")
                logger.info("\n" + "="*70)
                logger.info(f"✓ SUCCESS: {input_file.name} → {output_file.name}")
                logger.info("="*70)
                return True, output_file
            
        except subprocess.TimeoutExpired:
            logger.error(f"✗ Conversion timed out for {input_file.name}")
            return False, None
        except Exception as e:
            logger.error(f"✗ Error processing {input_file}: {str(e)}")
            logger.exception("Detailed error information:")
            return False, None
    
    def convert(self) -> Tuple[int, int]:
        """
        Main conversion method
        
        Returns:
            Tuple of (success_count, total_files)
        """
        success_count = 0
        total_files = 0
        
        if self.input_path.is_file():
            # Single file conversion
            if self.output_path:
                output_file = self.output_path
            else:
                output_file = self.input_path.with_suffix(self.extension)
            
            total_files = 1
            success, _ = self.convert_and_fix_single_file(self.input_path, output_file)
            if success:
                success_count = 1
        
        elif self.input_path.is_dir():
            # Batch conversion of directory
            logger.info(f"Scanning directory: {self.input_path}")
            x_files = list(self.input_path.glob("*.X")) + list(self.input_path.glob("*.x"))
            
            if not x_files:
                logger.warning(f"No .X files found in {self.input_path}")
                return 0, 0
            
            total_files = len(x_files)
            logger.info(f"Found {total_files} .X files to convert")
            logger.info("")
            
            # Determine output directory
            if self.output_path:
                output_dir = self.output_path
            else:
                output_dir = self.input_path / "converted_clean"
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Convert each file
            for idx, x_file in enumerate(x_files, 1):
                logger.info(f"\n[{idx}/{total_files}]")
                output_file = output_dir / x_file.with_suffix(self.extension).name
                success, _ = self.convert_and_fix_single_file(x_file, output_file)
                if success:
                    success_count += 1
                logger.info("")  # Blank line
        
        else:
            logger.error(f"Invalid input path: {self.input_path}")
            return 0, 0
        
        return success_count, total_files


def main():
    """Main entry point for the script"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Convert Higurashi Daybreak .X models to GLTF with automatic name fixing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert a single file (recommended)
  python convert_x_to_gltf_auto.py "path/to/Satoko.X"
  
  # Convert to binary GLB format
  python convert_x_to_gltf_auto.py "path/to/Satoko.X" --glb
  
  # Convert with custom output path
  python convert_x_to_gltf_auto.py "path/to/Satoko.X" -o "output/Satoko.gltf"
  
  # Batch convert all .X files in a directory
  python convert_x_to_gltf_auto.py "path/to/models/"
  
  # Batch convert with custom output directory
  python convert_x_to_gltf_auto.py "path/to/models/" -o "converted_models/"

This script automatically:
  1. Converts .X files to GLTF using Assimp
  2. Fixes Shift-JIS texture and mesh names
  3. Generates texture renaming scripts
  4. Creates mapping files for reference
  
Output files:
  - <name>_clean.gltf - Fixed GLTF file (ready to use)
  - <name>_clean.bin - Binary data
  - <name>_clean.mapping.txt - Name mapping reference
  - <name>_clean_rename_textures.ps1 - PowerShell script to rename textures
        """
    )
    
    parser.add_argument(
        'input',
        help='Input .X file or directory containing .X files'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file or directory (default: same location with _clean suffix)',
        default=None
    )
    
    parser.add_argument(
        '--glb',
        action='store_true',
        help='Export as binary GLB format instead of GLTF (cannot auto-fix names in GLB)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Determine format type
    format_type = 'glb2' if args.glb else 'gltf2'
    
    if args.glb:
        logger.warning("⚠ GLB format selected: Texture/mesh names cannot be automatically fixed")
        logger.warning("   Consider using GLTF format for full auto-fixing support")
        logger.info("")
    
    # Create converter and run
    converter = AutoXToGLTFConverter(args.input, args.output, format_type)
    success_count, total_files = converter.convert()
    
    # Print summary
    logger.info("\n" + "="*70)
    logger.info("CONVERSION SUMMARY")
    logger.info("="*70)
    if success_count > 0:
        logger.info(f"✓ Successfully converted: {success_count}/{total_files} file(s)")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Review the _clean.gltf file(s)")
        logger.info("  2. Check the .mapping.txt file(s) for texture names")
        logger.info("  3. Copy texture files to the same directory")
        logger.info("  4. Run the generated PowerShell script to rename textures")
        logger.info("  5. Open in Blender or your 3D viewer")
        logger.info("="*70)
        return 0
    else:
        logger.error("✗ No files were successfully converted")
        logger.info("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
