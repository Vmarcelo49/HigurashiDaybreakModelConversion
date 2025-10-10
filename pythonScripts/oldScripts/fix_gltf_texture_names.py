"""
GLTF Texture Name Fixer
Fixes invalid texture filenames in GLTF files caused by Shift-JIS encoding

This script:
1. Scans GLTF files for texture references
2. Identifies unique texture names with invalid characters
3. Creates sanitized replacement names
4. Updates GLTF file with corrected references
5. Generates a mapping file for texture file renaming
"""

import json
import re
import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import OrderedDict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TextureNameFixer:
    """Fixes texture filenames in GLTF files"""
    
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
            self.output_path = self.gltf_path.with_stem(f"{self.gltf_path.stem}_fixed")
        
        self.gltf_data = None
        self.texture_mapping = OrderedDict()
        self.mesh_name_mapping = OrderedDict()
    
    def load_gltf(self) -> dict:
        """Load the GLTF file"""
        logger.info(f"Loading GLTF file: {self.gltf_path}")
        
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'shift-jis']
        
        for encoding in encodings:
            try:
                with open(self.gltf_path, 'r', encoding=encoding, errors='ignore') as f:
                    self.gltf_data = json.load(f)
                logger.info(f"✓ GLTF file loaded successfully (encoding: {encoding})")
                return self.gltf_data
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                if encoding == encodings[-1]:
                    logger.error(f"Failed to load GLTF file with any encoding: {e}")
                    raise
                continue
        
        return self.gltf_data
    
    def extract_texture_names(self) -> Set[str]:
        """Extract all unique texture names from the GLTF file"""
        texture_names = set()
        
        if 'images' in self.gltf_data:
            for image in self.gltf_data['images']:
                if 'uri' in image:
                    texture_names.add(image['uri'])
        
        logger.info(f"Found {len(texture_names)} unique texture references")
        return texture_names
    
    def extract_mesh_names(self) -> Set[str]:
        """Extract all mesh names from the GLTF file"""
        mesh_names = set()
        
        if 'meshes' in self.gltf_data:
            for mesh in self.gltf_data['meshes']:
                if 'name' in mesh:
                    mesh_names.add(mesh['name'])
        
        logger.info(f"Found {len(mesh_names)} unique mesh names")
        return mesh_names
    
    def sanitize_filename(self, filename: str, counter: int) -> str:
        """
        Create a sanitized filename
        
        Args:
            filename: Original filename
            counter: Counter for unique naming
            
        Returns:
            Sanitized filename
        """
        # Handle empty or just extension filenames
        if not filename or filename.startswith('.'):
            return f"texture_{counter:02d}.bmp"
        
        # Get file extension
        parts = filename.rsplit('.', 1)
        ext = parts[1] if len(parts) > 1 else 'bmp'
        name_part = parts[0] if len(parts) > 1 else filename
        
        # Check if it's already valid ASCII and filename-safe
        try:
            filename.encode('ascii')
            # If valid ASCII but might have issues, still sanitize
            if re.match(r'^[a-zA-Z0-9_\-]+\.[a-zA-Z0-9]+$', filename):
                return filename
        except UnicodeEncodeError:
            pass
        
        # Try to create a meaningful name from the original
        # Remove any non-ASCII characters and see what's left
        ascii_part = ''.join(c for c in name_part if ord(c) < 128 and c.isalnum())
        
        # Common Japanese texture patterns (romanized)
        texture_mapping = {
            'kao': 'face',
            'me': 'eye',
            'kami': 'hair',
            'band': 'band',
            'head': 'head',
            'atama': 'head',
            'tama': 'head',
            'karada': 'body',
            'hada': 'skin',
            'fuku': 'cloth',
            'skirt': 'skirt',
            'sk': 'skirt',
            'suka': 'skirt',
        }
        
        # Try to identify texture type
        texture_type = None
        original_lower = filename.lower()
        
        for pattern, name in texture_mapping.items():
            if pattern in original_lower or pattern in ascii_part.lower():
                texture_type = name
                break
        
        # Generate new name
        if texture_type:
            new_name = f"texture_{texture_type}_{counter:02d}.{ext}"
        elif ascii_part and len(ascii_part) > 2:
            # Use sanitized ASCII part if available
            sanitized_ascii = re.sub(r'[^a-zA-Z0-9_]', '_', ascii_part)
            new_name = f"texture_{sanitized_ascii}_{counter:02d}.{ext}"
        else:
            new_name = f"texture_{counter:02d}.{ext}"
        
        return new_name
    
    def create_texture_mapping(self, texture_names: Set[str]) -> Dict[str, str]:
        """
        Create a mapping of original to sanitized texture names
        
        Args:
            texture_names: Set of original texture names
            
        Returns:
            Dictionary mapping original to new names
        """
        logger.info("Creating texture name mapping...")
        
        sorted_names = sorted(texture_names)
        counter = 1
        
        for original_name in sorted_names:
            sanitized_name = self.sanitize_filename(original_name, counter)
            self.texture_mapping[original_name] = sanitized_name
            
            # Display mapping
            logger.info(f"  {original_name:30s} -> {sanitized_name}")
            counter += 1
        
        return self.texture_mapping
    
    def create_mesh_name_mapping(self, mesh_names: Set[str]) -> Dict[str, str]:
        """
        Create a mapping of mesh names if they contain invalid characters
        
        Args:
            mesh_names: Set of original mesh names
            
        Returns:
            Dictionary mapping original to new names
        """
        logger.info("Checking mesh names...")
        
        for original_name in sorted(mesh_names):
            try:
                original_name.encode('ascii')
                # Check if it's already valid
                if re.match(r'^[a-zA-Z0-9_\-]+$', original_name):
                    continue
            except UnicodeEncodeError:
                pass
            
            # Need to sanitize this mesh name
            sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '_', original_name)
            sanitized = re.sub(r'_+', '_', sanitized)  # Remove duplicate underscores
            sanitized = sanitized.strip('_')
            
            if sanitized != original_name:
                self.mesh_name_mapping[original_name] = sanitized
                logger.info(f"  Mesh: {original_name:30s} -> {sanitized}")
        
        return self.mesh_name_mapping
    
    def update_gltf_textures(self) -> int:
        """
        Update texture references in the GLTF data
        
        Returns:
            Number of references updated
        """
        logger.info("Updating texture references in GLTF...")
        update_count = 0
        
        if 'images' in self.gltf_data:
            for image in self.gltf_data['images']:
                if 'uri' in image:
                    original_uri = image['uri']
                    if original_uri in self.texture_mapping:
                        image['uri'] = self.texture_mapping[original_uri]
                        update_count += 1
        
        logger.info(f"✓ Updated {update_count} texture references")
        return update_count
    
    def update_gltf_mesh_names(self) -> int:
        """
        Update mesh names in the GLTF data
        
        Returns:
            Number of mesh names updated
        """
        if not self.mesh_name_mapping:
            return 0
        
        logger.info("Updating mesh names in GLTF...")
        update_count = 0
        
        if 'meshes' in self.gltf_data:
            for mesh in self.gltf_data['meshes']:
                if 'name' in mesh:
                    original_name = mesh['name']
                    if original_name in self.mesh_name_mapping:
                        mesh['name'] = self.mesh_name_mapping[original_name]
                        update_count += 1
        
        logger.info(f"✓ Updated {update_count} mesh names")
        return update_count
    
    def save_fixed_gltf(self) -> bool:
        """Save the fixed GLTF file"""
        logger.info(f"Saving fixed GLTF to: {self.output_path}")
        try:
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(self.gltf_data, f, indent=2, ensure_ascii=False)
            
            file_size = self.output_path.stat().st_size / (1024 * 1024)
            logger.info(f"✓ Fixed GLTF saved successfully ({file_size:.2f} MB)")
            return True
        except Exception as e:
            logger.error(f"Failed to save fixed GLTF: {e}")
            return False
    
    def save_mapping_file(self) -> bool:
        """Save the texture mapping to a file for reference"""
        mapping_path = self.output_path.with_suffix('.mapping.txt')
        logger.info(f"Saving texture mapping to: {mapping_path}")
        
        try:
            with open(mapping_path, 'w', encoding='utf-8') as f:
                f.write("# Texture Filename Mapping\n")
                f.write("# Original Name -> Sanitized Name\n")
                f.write("# Use this to rename your actual texture files\n\n")
                
                if self.texture_mapping:
                    f.write("## TEXTURES\n")
                    for original, sanitized in self.texture_mapping.items():
                        f.write(f"{original} -> {sanitized}\n")
                
                if self.mesh_name_mapping:
                    f.write("\n## MESH NAMES\n")
                    for original, sanitized in self.mesh_name_mapping.items():
                        f.write(f"{original} -> {sanitized}\n")
            
            logger.info("✓ Mapping file saved")
            return True
        except Exception as e:
            logger.error(f"Failed to save mapping file: {e}")
            return False
    
    def save_rename_script(self) -> bool:
        """Generate a PowerShell script to rename actual texture files"""
        script_path = self.output_path.with_name(f"{self.output_path.stem}_rename_textures.ps1")
        logger.info(f"Generating texture rename script: {script_path}")
        
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write("# PowerShell script to rename texture files\n")
                f.write("# Run this in the directory containing your texture files\n\n")
                f.write("$ErrorActionPreference = 'Stop'\n\n")
                f.write("Write-Host 'Renaming texture files...' -ForegroundColor Cyan\n\n")
                
                for idx, (original, sanitized) in enumerate(self.texture_mapping.items(), 1):
                    f.write(f"# {idx}. {original} -> {sanitized}\n")
                    f.write(f"if (Test-Path '{original}') {{\n")
                    f.write(f"    Rename-Item '{original}' '{sanitized}'\n")
                    f.write(f"    Write-Host '  ✓ Renamed: {original} -> {sanitized}' -ForegroundColor Green\n")
                    f.write(f"}} else {{\n")
                    f.write(f"    Write-Host '  ⚠ Not found: {original}' -ForegroundColor Yellow\n")
                    f.write(f"}}\n\n")
                
                f.write("Write-Host 'Done!' -ForegroundColor Green\n")
            
            logger.info("✓ Rename script saved")
            logger.info(f"  Run: pwsh {script_path.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save rename script: {e}")
            return False
    
    def fix(self) -> bool:
        """Main method to fix the GLTF file"""
        try:
            # Load GLTF
            self.load_gltf()
            
            # Extract and map texture names
            texture_names = self.extract_texture_names()
            if texture_names:
                self.create_texture_mapping(texture_names)
            
            # Extract and map mesh names
            mesh_names = self.extract_mesh_names()
            if mesh_names:
                self.create_mesh_name_mapping(mesh_names)
            
            # Update the GLTF data
            texture_updates = self.update_gltf_textures()
            mesh_updates = self.update_gltf_mesh_names()
            
            if texture_updates == 0 and mesh_updates == 0:
                logger.warning("No changes needed - all names are already valid")
                return False
            
            # Save fixed GLTF
            if not self.save_fixed_gltf():
                return False
            
            # Save mapping file
            self.save_mapping_file()
            
            # Save rename script
            if self.texture_mapping:
                self.save_rename_script()
            
            return True
            
        except Exception as e:
            logger.error(f"Error during fixing: {e}")
            logger.exception("Detailed error:")
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fix invalid texture filenames in GLTF files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fix a single GLTF file
  python fix_gltf_texture_names.py "Satoko.gltf"
  
  # Fix with custom output name
  python fix_gltf_texture_names.py "Satoko.gltf" -o "Satoko_clean.gltf"
  
  # Batch process multiple files
  python fix_gltf_texture_names.py "models/*.gltf"

This will generate:
  - Fixed GLTF file with sanitized texture references
  - .mapping.txt file with original->new name mappings
  - PowerShell script to rename actual texture files
        """
    )
    
    parser.add_argument(
        'input',
        help='Input GLTF file to fix'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output path for fixed GLTF (default: adds _fixed suffix)',
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
    
    # Process the file
    fixer = TextureNameFixer(args.input, args.output)
    success = fixer.fix()
    
    if success:
        logger.info("="*60)
        logger.info("✓ GLTF file fixed successfully!")
        logger.info("="*60)
        logger.info("Next steps:")
        logger.info("1. Review the .mapping.txt file")
        logger.info("2. Copy your texture files to the same directory")
        logger.info("3. Run the generated PowerShell script to rename them")
        logger.info("4. Open the fixed GLTF in Blender")
        return 0
    else:
        logger.error("Failed to fix GLTF file")
        return 1


if __name__ == "__main__":
    sys.exit(main())
