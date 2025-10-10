"""
X File Binary to Text Converter
Converts binary DirectX .X files to text (ASCII) .X files using Assimp

This is useful for:
- Debugging file contents
- Manual inspection of model structure
- Identifying encoding issues
- Creating human-readable versions of binary models
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class XBinaryToTextConverter:
    """Converts binary .X files to text .X files using Assimp CLI"""
    
    def __init__(self, input_path: str, output_path: Optional[str] = None):
        """
        Initialize the converter
        
        Args:
            input_path: Path to input binary .X file or directory
            output_path: Path for output file(s). If None, adds _text suffix
        """
        self.input_path = Path(input_path)
        self.output_path = Path(output_path) if output_path else None
        
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
            if result.returncode == 0:
                # Log version info
                version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown"
                logger.info(f"Found Assimp: {version_line}")
                return True
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def get_file_info(self, file_path: Path) -> Tuple[bool, int]:
        """
        Determine if file is binary or text and get size
        
        Args:
            file_path: Path to the .X file
            
        Returns:
            Tuple of (is_binary, file_size)
        """
        try:
            size = file_path.stat().st_size
            
            # Read first 512 bytes to check if binary
            with open(file_path, 'rb') as f:
                header = f.read(512)
            
            # Check for binary indicators
            # Binary X files start with: xof 0303bin or xof 0302bin
            # Text X files start with: xof 0303txt or xof 0302txt
            is_binary = b'bin' in header[:20] or sum(b > 127 for b in header) > len(header) * 0.1
            
            return is_binary, size
            
        except Exception as e:
            logger.error(f"Error reading file info: {e}")
            return False, 0
    
    def convert_single_file(self, input_file: Path, output_file: Path) -> bool:
        """
        Convert a single binary .X file to text .X file
        
        Args:
            input_file: Path to input binary .X file
            output_file: Path to output text .X file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Converting: {input_file.name}")
            
            # Check if already text format
            is_binary, file_size = self.get_file_info(input_file)
            size_mb = file_size / (1024 * 1024)
            
            if not is_binary:
                logger.warning(f"  ⚠ File appears to already be in text format")
                logger.info(f"  File size: {size_mb:.2f} MB")
                
                # Just copy the file
                import shutil
                output_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(input_file, output_file)
                logger.info(f"  → Copied to: {output_file.name}")
                return True
            
            logger.info(f"  Binary file detected ({size_mb:.2f} MB)")
            
            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Method 1: Try direct export to .X format (text)
            logger.info(f"  Method 1: Attempting direct export to X format...")
            result = subprocess.run(
                ['assimp', 'export', str(input_file), str(output_file), '-f', 'x'],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0 and output_file.exists():
                output_size_mb = output_file.stat().st_size / (1024 * 1024)
                logger.info(f"  ✓ Successfully converted: {input_file.name} -> {output_file.name}")
                logger.info(f"    Binary: {size_mb:.2f} MB → Text: {output_size_mb:.2f} MB")
                
                # Verify it's actually text format now
                is_text_binary, _ = self.get_file_info(output_file)
                if not is_text_binary:
                    logger.info(f"    ✓ Confirmed: Output is in text format")
                else:
                    logger.warning(f"    ⚠ Warning: Output may still be binary")
                
                return True
            
            # Method 2: Try using assxml dump format (human-readable XML)
            logger.info(f"  Method 1 failed, trying Method 2: ASSXML dump...")
            xml_output = output_file.with_suffix('.assxml')
            result = subprocess.run(
                ['assimp', 'export', str(input_file), str(xml_output), '-f', 'assxml'],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0 and xml_output.exists():
                output_size_mb = xml_output.stat().st_size / (1024 * 1024)
                logger.info(f"  ✓ Created ASSXML dump: {xml_output.name}")
                logger.info(f"    Size: {output_size_mb:.2f} MB")
                logger.info(f"    ℹ ASSXML is Assimp's XML format - readable but not standard .X")
                return True
            
            # Method 3: Try dump command
            logger.info(f"  Method 2 failed, trying Method 3: dump command...")
            result = subprocess.run(
                ['assimp', 'dump', str(input_file), str(xml_output), '-l', '-s'],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0 and xml_output.exists():
                output_size_mb = xml_output.stat().st_size / (1024 * 1024)
                logger.info(f"  ✓ Created dump: {xml_output.name}")
                logger.info(f"    Size: {output_size_mb:.2f} MB")
                return True
            
            # All methods failed
            logger.error(f"  ✗ All export methods failed for {input_file.name}")
            if result.stderr:
                logger.error(f"  Last error: {result.stderr}")
            return False
            
        except subprocess.TimeoutExpired:
            logger.error(f"  ✗ Conversion timed out for {input_file.name}")
            return False
        except Exception as e:
            logger.error(f"  ✗ Error converting {input_file}: {str(e)}")
            logger.exception("  Detailed error information:")
            return False
    
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
                # Add _text suffix before extension
                stem = self.input_path.stem
                output_file = self.input_path.with_name(f"{stem}_text.X")
            
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
            logger.info("="*60)
            
            # Determine output directory
            if self.output_path:
                output_dir = self.output_path
            else:
                output_dir = self.input_path / "text_format"
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Convert each file
            for idx, x_file in enumerate(x_files, 1):
                logger.info(f"[{idx}/{len(x_files)}]")
                output_file = output_dir / f"{x_file.stem}_text.X"
                if self.convert_single_file(x_file, output_file):
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
        description="Convert binary DirectX .X files to text (ASCII) .X format using Assimp",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert a single binary .X file to text
  python convert_x_binary_to_text.py "path/to/Satoko.X"
  
  # Convert with custom output path
  python convert_x_binary_to_text.py "path/to/Satoko.X" -o "output/Satoko_text.X"
  
  # Convert all .X files in a directory
  python convert_x_binary_to_text.py "path/to/models/"
  
  # Batch convert with custom output directory
  python convert_x_binary_to_text.py "path/to/models/" -o "text_models/"

Text format .X files are:
  - Human readable
  - Easier to debug
  - Can be edited in a text editor
  - Useful for identifying encoding issues
  - Generally larger in file size than binary
        """
    )
    
    parser.add_argument(
        'input',
        help='Input binary .X file or directory containing .X files'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file or directory (default: adds _text suffix)',
        default=None
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
    
    # Create converter and run
    converter = XBinaryToTextConverter(args.input, args.output)
    success_count = converter.convert()
    
    # Print summary
    logger.info("="*60)
    if success_count > 0:
        logger.info(f"✓ Conversion complete: {success_count} file(s) successfully converted")
        logger.info("="*60)
        logger.info("Text .X files can be opened in any text editor")
        logger.info("They are useful for debugging and manual inspection")
        return 0
    else:
        logger.error("✗ No files were successfully converted")
        logger.info("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
