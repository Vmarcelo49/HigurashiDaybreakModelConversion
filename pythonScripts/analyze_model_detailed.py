"""
Comprehensive Model Analyzer
Analyzes X and GLTF models to extract all information and detect inconsistencies

This script:
1. Extracts all model information (meshes, bones, animations, materials, etc.)
2. Detects potential issues (invalid coords, improper animation lengths, etc.)
3. Provides detailed statistics and warnings
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import math


class ModelAnalyzer:
    """Analyzes models for information and inconsistencies"""
    
    def __init__(self, model_path: str):
        """Initialize analyzer with model path"""
        self.model_path = Path(model_path)
        self.model_data = None
        self.issues = []
        self.warnings = []
        self.stats = {}
        
    def analyze(self) -> Dict:
        """Run full analysis and return results"""
        print("="*80)
        print(f"ANALYZING MODEL: {self.model_path.name}")
        print("="*80)
        print()
        
        # Load model data
        if not self._load_model():
            return None
        
        # Gather all information
        self._analyze_basic_info()
        self._analyze_meshes()
        self._analyze_materials()
        self._analyze_bones()
        self._analyze_animations()
        self._analyze_textures()
        
        # Check for inconsistencies
        self._check_inconsistencies()
        
        # Print results
        self._print_results()
        
        return {
            'stats': self.stats,
            'issues': self.issues,
            'warnings': self.warnings
        }
    
    def _load_model(self) -> bool:
        """Load model data based on file type"""
        if self.model_path.suffix.lower() == '.gltf':
            return self._load_gltf()
        elif self.model_path.suffix.lower() in ['.x', '.X']:
            return self._load_x_file()
        else:
            print(f"✗ Unsupported file format: {self.model_path.suffix}")
            return False
    
    def _load_gltf(self) -> bool:
        """Load GLTF file as JSON"""
        try:
            # Try UTF-8 first
            try:
                with open(self.model_path, 'r', encoding='utf-8') as f:
                    self.model_data = json.load(f)
            except UnicodeDecodeError:
                # Fall back to Shift-JIS or ignore errors
                try:
                    with open(self.model_path, 'r', encoding='shift-jis') as f:
                        self.model_data = json.load(f)
                except:
                    # Last resort: ignore encoding errors
                    with open(self.model_path, 'r', encoding='utf-8', errors='ignore') as f:
                        self.model_data = json.load(f)
            
            self.stats['format'] = 'GLTF'
            return True
        except Exception as e:
            print(f"✗ Error loading GLTF: {e}")
            return False
    
    def _load_x_file(self) -> bool:
        """Load X file using assimp CLI to get info"""
        try:
            result = subprocess.run(
                ['assimp', 'info', str(self.model_path), '-v'],
                capture_output=True,
                text=True,
                timeout=30,
                errors='ignore'  # Ignore encoding errors for X files with Shift-JIS
            )
            
            if result.returncode != 0:
                print(f"✗ Failed to load X file with assimp")
                return False
            
            # Parse assimp output into a structured format
            output = result.stdout if result.stdout else result.stderr
            if not output:
                print(f"⚠️  No output from assimp, but conversion may have succeeded")
                output = "No detailed information available"
            
            self.model_data = {'assimp_output': output}
            self.stats['format'] = 'DirectX X'
            return True
        except Exception as e:
            print(f"✗ Error loading X file: {e}")
            return False
    
    def _analyze_basic_info(self):
        """Extract basic model information"""
        print("[BASIC INFORMATION]")
        print("-" * 80)
        
        if self.stats['format'] == 'GLTF':
            asset = self.model_data.get('asset', {})
            print(f"Format:        {self.stats['format']}")
            print(f"Generator:     {asset.get('generator', 'Unknown')}")
            print(f"Version:       {asset.get('version', 'Unknown')}")
            
            self.stats['nodes'] = len(self.model_data.get('nodes', []))
            self.stats['scenes'] = len(self.model_data.get('scenes', []))
            print(f"Scenes:        {self.stats['scenes']}")
            print(f"Nodes:         {self.stats['nodes']}")
        else:
            print(f"Format:        {self.stats['format']}")
            output = self.model_data['assimp_output']
            # Parse basic counts from assimp output
            for line in output.split('\n'):
                if 'Nodes:' in line:
                    print(f"Nodes:         {line.split(':')[1].strip()}")
        
        print()
    
    def _analyze_meshes(self):
        """Analyze mesh information"""
        print("[MESHES]")
        print("-" * 80)
        
        if self.stats['format'] == 'GLTF':
            meshes = self.model_data.get('meshes', [])
            self.stats['mesh_count'] = len(meshes)
            total_primitives = 0
            
            for i, mesh in enumerate(meshes):
                primitives = mesh.get('primitives', [])
                total_primitives += len(primitives)
                name = mesh.get('name', f'Mesh_{i}')
                print(f"  Mesh {i}: {name}")
                print(f"    Primitives: {len(primitives)}")
                
                for j, prim in enumerate(primitives):
                    attrs = prim.get('attributes', {})
                    print(f"      Primitive {j}:")
                    print(f"        Attributes: {', '.join(attrs.keys())}")
                    if 'material' in prim:
                        print(f"        Material: {prim['material']}")
            
            self.stats['total_primitives'] = total_primitives
            print(f"\nTotal Meshes: {self.stats['mesh_count']}")
            print(f"Total Primitives: {total_primitives}")
        else:
            output = self.model_data['assimp_output']
            for line in output.split('\n'):
                if 'Meshes:' in line or 'Vertices:' in line or 'Faces:' in line:
                    print(f"  {line.strip()}")
        
        print()
    
    def _analyze_materials(self):
        """Analyze materials"""
        print("[MATERIALS]")
        print("-" * 80)
        
        if self.stats['format'] == 'GLTF':
            materials = self.model_data.get('materials', [])
            self.stats['material_count'] = len(materials)
            
            for i, mat in enumerate(materials):
                name = mat.get('name', f'Material_{i}')
                print(f"  Material {i}: {name}")
                
                # Check for PBR properties
                if 'pbrMetallicRoughness' in mat:
                    pbr = mat['pbrMetallicRoughness']
                    if 'baseColorTexture' in pbr:
                        print(f"    Base Color Texture: Index {pbr['baseColorTexture'].get('index')}")
                    if 'baseColorFactor' in pbr:
                        print(f"    Base Color: {pbr['baseColorFactor']}")
                
                # Check other textures
                if 'normalTexture' in mat:
                    print(f"    Normal Texture: Index {mat['normalTexture'].get('index')}")
                if 'emissiveTexture' in mat:
                    print(f"    Emissive Texture: Index {mat['emissiveTexture'].get('index')}")
            
            print(f"\nTotal Materials: {self.stats['material_count']}")
        else:
            output = self.model_data['assimp_output']
            for line in output.split('\n'):
                if 'Materials:' in line:
                    print(f"  {line.strip()}")
        
        print()
    
    def _analyze_bones(self):
        """Analyze bone/skeleton structure"""
        print("[BONES & SKELETON]")
        print("-" * 80)
        
        if self.stats['format'] == 'GLTF':
            skins = self.model_data.get('skins', [])
            self.stats['skin_count'] = len(skins)
            
            if not skins:
                print("  No skeleton/skin data found")
            else:
                for i, skin in enumerate(skins):
                    name = skin.get('name', f'Skin_{i}')
                    joints = skin.get('joints', [])
                    print(f"  Skin {i}: {name}")
                    print(f"    Joints/Bones: {len(joints)}")
                    print(f"    Joint Indices: {joints[:10]}{'...' if len(joints) > 10 else ''}")
                    
                    # Check bone positions
                    self._check_bone_positions(joints)
                
                self.stats['total_bones'] = sum(len(skin.get('joints', [])) for skin in skins)
                print(f"\nTotal Skins: {self.stats['skin_count']}")
                print(f"Total Bones: {self.stats['total_bones']}")
        else:
            output = self.model_data['assimp_output']
            for line in output.split('\n'):
                if 'Bones:' in line or 'bone' in line.lower():
                    print(f"  {line.strip()}")
        
        print()
    
    def _check_bone_positions(self, joint_indices: List[int]):
        """Check if bone positions are reasonable"""
        if self.stats['format'] != 'GLTF':
            return
        
        nodes = self.model_data.get('nodes', [])
        
        for joint_idx in joint_indices:
            if joint_idx >= len(nodes):
                self.issues.append(f"Invalid joint index: {joint_idx} (out of range)")
                continue
            
            node = nodes[joint_idx]
            translation = node.get('translation', [0, 0, 0])
            
            # Check for extreme coordinates
            for axis, val in zip(['X', 'Y', 'Z'], translation):
                if abs(val) > 10000:
                    self.warnings.append(
                        f"Bone '{node.get('name', joint_idx)}' has extreme {axis} position: {val}"
                    )
                if math.isnan(val) or math.isinf(val):
                    self.issues.append(
                        f"Bone '{node.get('name', joint_idx)}' has invalid {axis} position: {val}"
                    )
    
    def _analyze_animations(self):
        """Analyze animations"""
        print("[ANIMATIONS]")
        print("-" * 80)
        
        if self.stats['format'] == 'GLTF':
            animations = self.model_data.get('animations', [])
            self.stats['animation_count'] = len(animations)
            
            if not animations:
                print("  No animations found")
            else:
                for i, anim in enumerate(animations):
                    name = anim.get('name', f'Animation_{i}')
                    channels = anim.get('channels', [])
                    samplers = anim.get('samplers', [])
                    
                    print(f"  Animation {i}: {name}")
                    print(f"    Channels: {len(channels)}")
                    print(f"    Samplers: {len(samplers)}")
                    
                    # Analyze animation timing
                    self._check_animation_timing(i, anim)
                
                print(f"\nTotal Animations: {self.stats['animation_count']}")
        else:
            output = self.model_data['assimp_output']
            for line in output.split('\n'):
                if 'Animation' in line or 'animation' in line.lower():
                    print(f"  {line.strip()}")
        
        print()
    
    def _check_animation_timing(self, anim_idx: int, animation: Dict):
        """Check for animation timing issues"""
        if self.stats['format'] != 'GLTF':
            return
        
        samplers = animation.get('samplers', [])
        accessors = self.model_data.get('accessors', [])
        
        for i, sampler in enumerate(samplers):
            input_accessor_idx = sampler.get('input')
            if input_accessor_idx is None or input_accessor_idx >= len(accessors):
                continue
            
            input_accessor = accessors[input_accessor_idx]
            
            # Get timing info
            min_time = input_accessor.get('min', [0])[0]
            max_time = input_accessor.get('max', [0])[0]
            count = input_accessor.get('count', 0)
            
            duration = max_time - min_time
            
            print(f"      Sampler {i}: {min_time:.3f}s - {max_time:.3f}s (duration: {duration:.3f}s, {count} keyframes)")
            
            # Check for issues
            if duration <= 0:
                self.issues.append(
                    f"Animation '{animation.get('name', anim_idx)}' sampler {i} has zero or negative duration: {duration}"
                )
            elif duration > 3600:  # More than 1 hour
                self.warnings.append(
                    f"Animation '{animation.get('name', anim_idx)}' sampler {i} has extremely long duration: {duration:.1f}s"
                )
            
            if count < 2:
                self.warnings.append(
                    f"Animation '{animation.get('name', anim_idx)}' sampler {i} has too few keyframes: {count}"
                )
            
            # Check for improper frame spacing
            if count > 0 and duration > 0:
                avg_frame_time = duration / (count - 1) if count > 1 else 0
                if avg_frame_time > 1.0:  # More than 1 second between frames
                    self.warnings.append(
                        f"Animation '{animation.get('name', anim_idx)}' has large gaps between keyframes: {avg_frame_time:.3f}s average"
                    )
    
    def _analyze_textures(self):
        """Analyze textures"""
        print("[TEXTURES]")
        print("-" * 80)
        
        if self.stats['format'] == 'GLTF':
            textures = self.model_data.get('textures', [])
            images = self.model_data.get('images', [])
            
            self.stats['texture_count'] = len(textures)
            self.stats['image_count'] = len(images)
            
            print(f"  Textures: {len(textures)}")
            print(f"  Images: {len(images)}")
            
            for i, img in enumerate(images):
                name = img.get('name', f'Image_{i}')
                uri = img.get('uri', 'embedded')
                print(f"    Image {i}: {name}")
                print(f"      URI: {uri}")
                
                # Check if texture file exists
                if uri != 'embedded' and not uri.startswith('data:'):
                    texture_path = self.model_path.parent / uri
                    if not texture_path.exists():
                        self.issues.append(f"Missing texture file: {uri}")
        else:
            output = self.model_data['assimp_output']
            for line in output.split('\n'):
                if 'Texture' in line or 'texture' in line.lower():
                    print(f"  {line.strip()}")
        
        print()
    
    def _check_inconsistencies(self):
        """Check for general inconsistencies"""
        print("[INCONSISTENCY CHECK]")
        print("-" * 80)
        
        if self.stats['format'] == 'GLTF':
            # Check for orphaned data
            accessors = self.model_data.get('accessors', [])
            buffer_views = self.model_data.get('bufferViews', [])
            buffers = self.model_data.get('buffers', [])
            
            print(f"  Accessors: {len(accessors)}")
            print(f"  Buffer Views: {len(buffer_views)}")
            print(f"  Buffers: {len(buffers)}")
            
            # Check buffer references
            for i, accessor in enumerate(accessors):
                buffer_view_idx = accessor.get('bufferView')
                if buffer_view_idx is not None and buffer_view_idx >= len(buffer_views):
                    self.issues.append(f"Accessor {i} references invalid bufferView: {buffer_view_idx}")
            
            for i, buffer_view in enumerate(buffer_views):
                buffer_idx = buffer_view.get('buffer')
                if buffer_idx is not None and buffer_idx >= len(buffers):
                    self.issues.append(f"BufferView {i} references invalid buffer: {buffer_idx}")
            
            # Check for empty meshes
            meshes = self.model_data.get('meshes', [])
            for i, mesh in enumerate(meshes):
                if not mesh.get('primitives'):
                    self.warnings.append(f"Mesh {i} '{mesh.get('name', 'unnamed')}' has no primitives")
        
        print()
    
    def _print_results(self):
        """Print analysis summary"""
        print("="*80)
        print("[ANALYSIS SUMMARY]")
        print("="*80)
        
        print(f"\n[+] Statistics:")
        for key, value in self.stats.items():
            print(f"  {key}: {value}")
        
        if self.issues:
            print(f"\n[!] CRITICAL ISSUES FOUND: {len(self.issues)}")
            for issue in self.issues:
                print(f"  - {issue}")
        else:
            print("\n[+] No critical issues found")
        
        if self.warnings:
            print(f"\n[!] WARNINGS: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"  - {warning}")
        else:
            print("\n[+] No warnings")
        
        print("\n" + "="*80)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python analyze_model_detailed.py <model_file>")
        print("Example: python analyze_model_detailed.py Satoko.X")
        print("Example: python analyze_model_detailed.py Satoko.gltf")
        sys.exit(1)
    
    model_file = sys.argv[1]
    
    if not Path(model_file).exists():
        print(f"✗ File not found: {model_file}")
        sys.exit(1)
    
    analyzer = ModelAnalyzer(model_file)
    results = analyzer.analyze()
    
    # Exit with error code if critical issues found
    if results and results['issues']:
        sys.exit(1)


if __name__ == "__main__":
    main()
