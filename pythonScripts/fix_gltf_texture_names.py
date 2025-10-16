"""GLTF Texture Name Fixer - Fixes invalid texture filenames in GLTF files"""

import json
import re
import sys
import logging
from pathlib import Path
from typing import Dict, Set
from collections import OrderedDict

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TextureNameFixer:
    def __init__(self, gltf_path: str, output_path: str = None):
        self.gltf_path = Path(gltf_path)
        if not self.gltf_path.exists():
            raise FileNotFoundError(f"GLTF file not found: {gltf_path}")
        
        self.output_path = Path(output_path) if output_path else self.gltf_path.with_stem(f"{self.gltf_path.stem}_fixed")
        self.gltf_data = None
        self.texture_mapping = OrderedDict()
        self.mesh_name_mapping = OrderedDict()
    
    def load_gltf(self) -> dict:
        logger.info(f"Loading GLTF: {self.gltf_path}")
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'shift-jis']
        
        for encoding in encodings:
            try:
                with open(self.gltf_path, 'r', encoding=encoding, errors='ignore') as f:
                    self.gltf_data = json.load(f)
                logger.info(f"✓ Loaded (encoding: {encoding})")
                return self.gltf_data
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                if encoding == encodings[-1]:
                    logger.error(f"Failed to load GLTF: {e}")
                    raise
        return self.gltf_data
    
    def extract_texture_names(self) -> Set[str]:
        texture_names = set()
        if 'images' in self.gltf_data:
            for image in self.gltf_data['images']:
                if 'uri' in image:
                    texture_names.add(image['uri'])
        logger.info(f"Found {len(texture_names)} textures")
        return texture_names
    
    def extract_mesh_names(self) -> Set[str]:
        mesh_names = set()
        if 'meshes' in self.gltf_data:
            for mesh in self.gltf_data['meshes']:
                if 'name' in mesh:
                    mesh_names.add(mesh['name'])
        logger.info(f"Found {len(mesh_names)} meshes")
        return mesh_names
    
    def sanitize_filename(self, filename: str, counter: int) -> str:
        if not filename or filename.startswith('.'):
            return f"texture_{counter:02d}.bmp"
        
        parts = filename.rsplit('.', 1)
        ext = parts[1] if len(parts) > 1 else 'bmp'
        name_part = parts[0] if len(parts) > 1 else filename
        
        try:
            filename.encode('ascii')
            if re.match(r'^[a-zA-Z0-9_\-]+\.[a-zA-Z0-9]+$', filename):
                return filename
        except UnicodeEncodeError:
            pass
        
        ascii_part = ''.join(c for c in name_part if ord(c) < 128 and c.isalnum())
        
        texture_types = {
            'kao': 'face', 'me': 'eye', 'kami': 'hair', 'band': 'band',
            'head': 'head', 'atama': 'head', 'tama': 'head', 'karada': 'body',
            'hada': 'skin', 'fuku': 'cloth', 'skirt': 'skirt', 'sk': 'skirt', 'suka': 'skirt',
        }
        
        texture_type = None
        original_lower = filename.lower()
        for pattern, name in texture_types.items():
            if pattern in original_lower or pattern in ascii_part.lower():
                texture_type = name
                break
        
        if texture_type:
            return f"texture_{texture_type}_{counter:02d}.{ext}"
        elif ascii_part and len(ascii_part) > 2:
            sanitized_ascii = re.sub(r'[^a-zA-Z0-9_]', '_', ascii_part)
            return f"texture_{sanitized_ascii}_{counter:02d}.{ext}"
        else:
            return f"texture_{counter:02d}.{ext}"
    
    def create_texture_mapping(self, texture_names: Set[str]) -> Dict[str, str]:
        logger.info("Creating texture mapping...")
        for counter, original_name in enumerate(sorted(texture_names), 1):
            sanitized_name = self.sanitize_filename(original_name, counter)
            self.texture_mapping[original_name] = sanitized_name
            logger.info(f"  {original_name:30s} -> {sanitized_name}")
        return self.texture_mapping
    
    def create_mesh_name_mapping(self, mesh_names: Set[str]) -> Dict[str, str]:
        logger.info("Checking mesh names...")
        for original_name in sorted(mesh_names):
            try:
                original_name.encode('ascii')
                if re.match(r'^[a-zA-Z0-9_\-]+$', original_name):
                    continue
            except UnicodeEncodeError:
                pass
            
            sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '_', original_name)
            sanitized = re.sub(r'_+', '_', sanitized).strip('_')
            
            if sanitized != original_name:
                self.mesh_name_mapping[original_name] = sanitized
                logger.info(f"  Mesh: {original_name:30s} -> {sanitized}")
        return self.mesh_name_mapping
    
    def update_gltf_textures(self) -> int:
        logger.info("Updating texture references...")
        update_count = 0
        if 'images' in self.gltf_data:
            for image in self.gltf_data['images']:
                if 'uri' in image and image['uri'] in self.texture_mapping:
                    image['uri'] = self.texture_mapping[image['uri']]
                    update_count += 1
        logger.info(f"✓ Updated {update_count} texture references")
        return update_count
    
    def update_gltf_mesh_names(self) -> int:
        if not self.mesh_name_mapping:
            return 0
        logger.info("Updating mesh names...")
        update_count = 0
        if 'meshes' in self.gltf_data:
            for mesh in self.gltf_data['meshes']:
                if 'name' in mesh and mesh['name'] in self.mesh_name_mapping:
                    mesh['name'] = self.mesh_name_mapping[mesh['name']]
                    update_count += 1
        logger.info(f"✓ Updated {update_count} mesh names")
        return update_count
    
    def save_fixed_gltf(self) -> bool:
        logger.info(f"Saving to: {self.output_path}")
        try:
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(self.gltf_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ Saved ({self.output_path.stat().st_size / (1024 * 1024):.2f} MB)")
            return True
        except Exception as e:
            logger.error(f"Failed to save: {e}")
            return False
    
    def save_mapping_file(self) -> bool:
        mapping_path = self.output_path.with_suffix('.mapping.txt')
        logger.info(f"Saving mapping: {mapping_path}")
        try:
            with open(mapping_path, 'w', encoding='utf-8') as f:
                f.write("# Texture Filename Mapping\n# Original -> Sanitized\n\n")
                if self.texture_mapping:
                    f.write("## TEXTURES\n")
                    for orig, san in self.texture_mapping.items():
                        f.write(f"{orig} -> {san}\n")
                if self.mesh_name_mapping:
                    f.write("\n## MESHES\n")
                    for orig, san in self.mesh_name_mapping.items():
                        f.write(f"{orig} -> {san}\n")
            logger.info("✓ Mapping saved")
            return True
        except Exception as e:
            logger.error(f"Failed to save mapping: {e}")
            return False
    
    def save_rename_script(self) -> bool:
        script_path = self.output_path.with_name(f"{self.output_path.stem}_rename_textures.ps1")
        logger.info(f"Generating rename script: {script_path}")
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write("# PowerShell script to rename texture files\n")
                f.write("$ErrorActionPreference = 'Stop'\n")
                f.write("Write-Host 'Renaming textures...' -ForegroundColor Cyan\n\n")
                for idx, (orig, san) in enumerate(self.texture_mapping.items(), 1):
                    f.write(f"# {idx}. {orig} -> {san}\n")
                    f.write(f"if (Test-Path '{orig}') {{\n")
                    f.write(f"    Rename-Item '{orig}' '{san}'\n")
                    f.write(f"    Write-Host '  ✓ {orig} -> {san}' -ForegroundColor Green\n")
                    f.write(f"}} else {{\n")
                    f.write(f"    Write-Host '  ⚠ Not found: {orig}' -ForegroundColor Yellow\n")
                    f.write(f"}}\n\n")
                f.write("Write-Host 'Done!' -ForegroundColor Green\n")
            logger.info(f"✓ Script saved: pwsh {script_path.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save script: {e}")
            return False
    
    def fix(self) -> bool:
        try:
            self.load_gltf()
            
            texture_names = self.extract_texture_names()
            if texture_names:
                self.create_texture_mapping(texture_names)
            
            mesh_names = self.extract_mesh_names()
            if mesh_names:
                self.create_mesh_name_mapping(mesh_names)
            
            texture_updates = self.update_gltf_textures()
            mesh_updates = self.update_gltf_mesh_names()
            
            if texture_updates == 0 and mesh_updates == 0:
                logger.warning("No changes needed - all names already valid")
                return False
            
            if not self.save_fixed_gltf():
                return False
            
            self.save_mapping_file()
            if self.texture_mapping:
                self.save_rename_script()
            
            return True
        except Exception as e:
            logger.error(f"Error: {e}")
            logger.exception("Details:")
            return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fix invalid texture filenames in GLTF files")
    parser.add_argument('input', help='Input GLTF file')
    parser.add_argument('-o', '--output', help='Output path (default: adds _fixed suffix)', default=None)
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose logging')
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    fixer = TextureNameFixer(args.input, args.output)
    success = fixer.fix()
    
    if success:
        logger.info("="*60)
        logger.info("✓ GLTF fixed successfully!")
        logger.info("="*60)
        logger.info("Next: Review .mapping.txt, copy textures, run rename script, open in Blender")
        return 0
    else:
        logger.error("Failed to fix GLTF")
        return 1


if __name__ == "__main__":
    sys.exit(main())
