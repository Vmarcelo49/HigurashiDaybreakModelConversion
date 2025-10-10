"""
Higurashi Daybreak .X Model Converter (CLI Version)
Converts DirectX .X models to GLTF format using Assimp command-line tool

This script wraps the Assimp CLI tool which handles the files better than pyassimp.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional, List, Tuple
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class XModelConverterCLI:
    """Handles conversion of DirectX .X models to GLTF using Assimp CLI"""
    
    def __init__(self, input_path: str, output_path: Optional[str] = None, format_type: str = 'gltf2'):
        """
        Initialize the converter
        
        Args:
            input_path: Path to input .X file or directory
            output_path: Path for output file(s). If None, uses input path with appropriate extension
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
    
    def get_model_info(self, input_file: Path) -> Optional[dict]:
        """
        Get information about a model file using assimp info
        
        Args:
            input_file: Path to the .X file
            
        Returns:
            Dictionary with model information or None if failed
        """
        try:
            result = subprocess.run(
                ['assimp', 'info', str(input_file)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to get info for {input_file}")
                return None
            
            # Parse the output
            output = result.stdout
            info = {
                'meshes': 0,
                'animations': 0,
                'materials': 0,
                'vertices': 0,
                'bones': 0,
                'faces': 0
            }
            
            for line in output.split('\n'):
                line = line.strip()
                if line.startswith('Meshes:'):
                    info['meshes'] = int(line.split()[1])
                elif line.startswith('Animations:'):
                    info['animations'] = int(line.split()[1])
                elif line.startswith('Materials:'):
                    info['materials'] = int(line.split()[1])
                elif line.startswith('Vertices:'):
                    info['vertices'] = int(line.split()[1])
                elif line.startswith('Bones:'):
                    info['bones'] = int(line.split()[1])
                elif line.startswith('Faces:'):
                    info['faces'] = int(line.split()[1])
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return None
    
    def convert_single_file(self, input_file: Path, output_file: Path, show_info: bool = True) -> bool:
        """
        Convert a single .X file to GLTF
        
        Args:
            input_file: Path to input .X file
            output_file: Path to output GLTF/GLB file
            show_info: Whether to show model information before conversion
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Converting: {input_file.name}")
            
            # Get model information
            if show_info:
                info = self.get_model_info(input_file)
                if info:
                    logger.info(f"  Model info:")
                    logger.info(f"    - Meshes: {info['meshes']}")
                    logger.info(f"    - Animations: {info['animations']}")
                    logger.info(f"    - Materials: {info['materials']}")
                    logger.info(f"    - Vertices: {info['vertices']}")
                    logger.info(f"    - Bones: {info['bones']}")
                    logger.info(f"    - Faces: {info['faces']}")
            
            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Run assimp export
            logger.info(f"  Exporting to: {output_file.name}")
            result = subprocess.run(
                ['assimp', 'export', str(input_file), str(output_file), '-f', self.format_type],
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"  ✗ Export failed for {input_file.name}")
                if result.stderr:
                    logger.error(f"  Error: {result.stderr}")
                return False
            
            # Check if output file was created
            if not output_file.exists():
                logger.error(f"  ✗ Output file was not created: {output_file}")
                return False
            
            # Check file size
            size_mb = output_file.stat().st_size / (1024 * 1024)
            logger.info(f"  ✓ Successfully converted: {input_file.name} -> {output_file.name} ({size_mb:.2f} MB)")
            
            # Check for associated .bin file if GLTF format
            if self.format_type == 'gltf2':
                bin_file = output_file.with_suffix('.bin')
                if bin_file.exists():
                    bin_size_mb = bin_file.stat().st_size / (1024 * 1024)
                    logger.info(f"    + Binary data: {bin_file.name} ({bin_size_mb:.2f} MB)")
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"  ✗ Conversion timed out for {input_file.name}")
            return False
        except Exception as e:
            logger.error(f"  ✗ Error converting {input_file}: {str(e)}")
            logger.exception("  Detailed error information:")
            return False
    
    def convert(self, show_info: bool = True) -> int:
        """
        Main conversion method
        
        Args:
            show_info: Whether to show model information during conversion
            
        Returns:
            Number of successfully converted files
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
            if self.convert_single_file(self.input_path, output_file, show_info):
                success_count = 1
        
        elif self.input_path.is_dir():
            # Batch conversion of directory
            logger.info(f"Scanning directory: {self.input_path}")
            x_files = list(self.input_path.glob("*.X")) + list(self.input_path.glob("*.x"))
            
            if not x_files:
                logger.warning(f"No .X files found in {self.input_path}")
                return 0
            
            total_files = len(x_files)
            logger.info(f"Found {total_files} .X files to convert")
            logger.info("="*60)
            
            # Determine output directory
            if self.output_path:
                output_dir = self.output_path
            else:
                output_dir = self.input_path / "converted"
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Convert each file
            for idx, x_file in enumerate(x_files, 1):
                logger.info(f"[{idx}/{total_files}] Processing: {x_file.name}")
                output_file = output_dir / x_file.with_suffix(self.extension).name
                if self.convert_single_file(x_file, output_file, show_info):
                    success_count += 1
                logger.info("")  # Blank line for readability
        
        else:
            logger.error(f"Invalid input path: {self.input_path}")
            return 0
        
        return success_count


def main():
    """Main entry point for the script"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Convert Higurashi Daybreak .X models to GLTF format using Assimp CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert a single file to GLTF
  python convert_x_to_gltf_cli.py "path/to/Satoko.X"
  
  # Convert to binary GLB format
  python convert_x_to_gltf_cli.py "path/to/Satoko.X" --glb
  
  # Convert with custom output path
  python convert_x_to_gltf_cli.py "path/to/Satoko.X" -o "output/Satoko.gltf"
  
  # Convert all .X files in a directory
  python convert_x_to_gltf_cli.py "path/to/models/"
  
  # Batch convert with custom output directory
  python convert_x_to_gltf_cli.py "path/to/models/" -o "converted_models/"
  
  # Quick conversion without detailed info
  python convert_x_to_gltf_cli.py "path/to/models/" --no-info
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
        '--glb',
        action='store_true',
        help='Export as binary GLB format instead of GLTF'
    )
    
    parser.add_argument(
        '--no-info',
        action='store_true',
        help='Skip displaying model information (faster conversion)'
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
    
    # Create converter and run
    converter = XModelConverterCLI(args.input, args.output, format_type)
    success_count = converter.convert(show_info=not args.no_info)
    
    # Print summary
    logger.info("="*60)
    if success_count > 0:
        logger.info(f"✓ Conversion complete: {success_count} file(s) successfully converted")
        logger.info("="*60)
        return 0
    else:
        logger.error("✗ No files were successfully converted")
        logger.info("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
