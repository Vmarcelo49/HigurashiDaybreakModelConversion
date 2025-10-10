"""
Higurashi Daybreak .X Model Converter
Converts DirectX .X models to GLTF format while preserving animations

This script handles Shift-JIS encoded binary .X files from Higurashi Daybreak
and attempts to convert them to modern GLTF format using the Assimp library.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, List

try:
    import pyassimp
    from pyassimp import load, export, release
    from pyassimp.postprocess import (
        aiProcess_Triangulate,
        aiProcess_FlipUVs,
        aiProcess_CalcTangentSpace,
        aiProcess_JoinIdenticalVertices,
        aiProcess_SortByPType
    )
except ImportError:
    print("Error: pyassimp is not installed.")
    print("Install it with: pip install pyassimp")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class XModelConverter:
    """Handles conversion of DirectX .X models to GLTF format"""
    
    def __init__(self, input_path: str, output_path: Optional[str] = None):
        """
        Initialize the converter
        
        Args:
            input_path: Path to input .X file or directory
            output_path: Path for output file(s). If None, uses input path with .gltf extension
        """
        self.input_path = Path(input_path)
        self.output_path = Path(output_path) if output_path else None
        
        # Processing flags for optimal import
        self.processing_flags = (
            aiProcess_Triangulate |
            aiProcess_FlipUVs |
            aiProcess_CalcTangentSpace |
            aiProcess_JoinIdenticalVertices |
            aiProcess_SortByPType
        )
    
    def convert_single_file(self, input_file: Path, output_file: Path) -> bool:
        """
        Convert a single .X file to GLTF
        
        Args:
            input_file: Path to input .X file
            output_file: Path to output GLTF file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Loading model: {input_file}")
            
            # Load the scene with specified processing flags
            # Using context manager to properly handle pyassimp's load function
            with load(str(input_file), processing=self.processing_flags) as scene:
                if not scene:
                    logger.error(f"Failed to load scene from {input_file}")
                    return False
                
                # Log scene information
                self._log_scene_info(scene, input_file.name)
                
                # Ensure output directory exists
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Export to GLTF2 format (binary .glb also available)
                logger.info(f"Exporting to: {output_file}")
                export(scene, str(output_file), file_type='gltf2')
            
            logger.info(f"✓ Successfully converted: {input_file.name} -> {output_file.name}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Error converting {input_file}: {str(e)}")
            logger.exception("Detailed error information:")
            return False
    
    def _log_scene_info(self, scene, filename: str):
        """Log information about the loaded scene"""
        logger.info(f"Scene loaded successfully: {filename}")
        logger.info(f"  - Meshes: {len(scene.meshes)}")
        logger.info(f"  - Materials: {len(scene.materials)}")
        logger.info(f"  - Animations: {len(scene.animations)}")
        logger.info(f"  - Textures: {len(scene.textures)}")
        
        # Log animation details if present
        if scene.animations:
            for idx, anim in enumerate(scene.animations):
                logger.info(f"  - Animation {idx + 1}: '{anim.name}' "
                          f"({anim.duration} ticks, {anim.tickspersecond} tps, "
                          f"{len(anim.channels)} channels)")
        else:
            logger.warning(f"  ⚠ No animations found in {filename}")
    
    def convert(self) -> int:
        """
        Main conversion method
        
        Returns:
            Number of successfully converted files
        """
        success_count = 0
        
        if self.input_path.is_file():
            # Single file conversion
            if self.output_path:
                output_file = self.output_path
            else:
                output_file = self.input_path.with_suffix('.gltf')
            
            if self.convert_single_file(self.input_path, output_file):
                success_count = 1
        
        elif self.input_path.is_dir():
            # Batch conversion of directory
            logger.info(f"Scanning directory: {self.input_path}")
            x_files = list(self.input_path.glob("*.X")) + list(self.input_path.glob("*.x"))
            
            if not x_files:
                logger.warning(f"No .X files found in {self.input_path}")
                return 0
            
            logger.info(f"Found {len(x_files)} .X files to convert")
            
            # Determine output directory
            if self.output_path:
                output_dir = self.output_path
            else:
                output_dir = self.input_path / "converted"
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Convert each file
            for x_file in x_files:
                output_file = output_dir / x_file.with_suffix('.gltf').name
                if self.convert_single_file(x_file, output_file):
                    success_count += 1
        
        else:
            logger.error(f"Invalid input path: {self.input_path}")
            return 0
        
        return success_count


def main():
    """Main entry point for the script"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Convert Higurashi Daybreak .X models to GLTF format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert a single file
  python convert_x_to_gltf.py path/to/Satoko.X
  
  # Convert a single file with custom output
  python convert_x_to_gltf.py path/to/Satoko.X -o output/Satoko.gltf
  
  # Convert all .X files in a directory
  python convert_x_to_gltf.py path/to/models/
  
  # Convert directory with custom output location
  python convert_x_to_gltf.py path/to/models/ -o converted_models/
        """
    )
    
    parser.add_argument(
        'input',
        help='Input .X file or directory containing .X files'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file or directory (default: same location with .gltf extension)',
        default=None
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--glb',
        action='store_true',
        help='Export as binary GLB format instead of GLTF (not yet implemented)'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Create converter and run
    converter = XModelConverter(args.input, args.output)
    success_count = converter.convert()
    
    # Print summary
    logger.info("="*60)
    logger.info(f"Conversion complete: {success_count} file(s) successfully converted")
    logger.info("="*60)
    
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
