"""
ASSXML Analyzer
Analyzes ASSXML files generated from .X models to extract useful information

This script reads ASSXML files and provides:
- Model statistics
- Animation information
- Mesh and bone structure
- Texture references
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ASSXMLAnalyzer:
    """Analyzes ASSXML files"""
    
    def __init__(self, assxml_path: str):
        """
        Initialize the analyzer
        
        Args:
            assxml_path: Path to the ASSXML file
        """
        self.assxml_path = Path(assxml_path)
        self.tree = None
        self.root = None
        
    def load(self) -> bool:
        """Load and parse the ASSXML file"""
        try:
            logger.info(f"Loading: {self.assxml_path.name}")
            
            # Get file size
            size_mb = self.assxml_path.stat().st_size / (1024 * 1024)
            logger.info(f"File size: {size_mb:.2f} MB")
            
            # Parse XML with error recovery
            logger.info("Parsing XML...")
            try:
                self.tree = ET.parse(self.assxml_path)
                self.root = self.tree.getroot()
            except ET.ParseError as e:
                logger.warning(f"XML parsing error: {e}")
                logger.info("Attempting to parse with error recovery...")
                
                # Try to read and clean the file
                with open(self.assxml_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Parse from string
                self.root = ET.fromstring(content)
                self.tree = ET.ElementTree(self.root)
            
            logger.info("✓ File loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load file: {e}")
            logger.info("Falling back to simple text analysis...")
            return False
    
    def get_model_info(self) -> Dict:
        """Extract basic model information"""
        info = {
            'format_id': self.root.get('format_id', 'Unknown'),
            'nodes': 0,
            'meshes': 0,
            'materials': 0,
            'textures': 0,
            'animations': 0,
            'bones': 0
        }
        
        # Find scene element
        scene = self.root.find('.//Scene')
        if scene:
            # Count nodes (recursive)
            info['nodes'] = len(scene.findall('.//Node'))
            
            # Count meshes
            mesh_list = scene.find('.//MeshList')
            if mesh_list:
                info['meshes'] = int(mesh_list.get('num', 0))
            
            # Count materials
            mat_list = scene.find('.//MaterialList')
            if mat_list:
                info['materials'] = int(mat_list.get('num', 0))
            
            # Count textures
            tex_list = scene.find('.//TextureList')
            if tex_list:
                info['textures'] = int(tex_list.get('num', 0))
            
            # Count animations
            anim_list = scene.find('.//AnimationList')
            if anim_list:
                info['animations'] = int(anim_list.get('num', 0))
        
        return info
    
    def get_animation_details(self) -> List[Dict]:
        """Extract detailed animation information"""
        animations = []
        
        scene = self.root.find('.//Scene')
        if not scene:
            return animations
        
        anim_list = scene.find('.//AnimationList')
        if not anim_list:
            return animations
        
        for anim in anim_list.findall('Animation'):
            anim_info = {
                'name': anim.get('name', 'Unnamed'),
                'duration': float(anim.get('duration', 0)),
                'tick_count': float(anim.get('tick_cnt', 0)),
                'channels': 0,
                'keyframes': 0
            }
            
            # Count channels
            node_anim_list = anim.find('.//NodeAnimList')
            if node_anim_list:
                anim_info['channels'] = int(node_anim_list.get('num', 0))
                
                # Count total keyframes
                for node_anim in node_anim_list.findall('NodeAnim'):
                    # Position keyframes
                    pos_keys = node_anim.find('.//PositionKeyList')
                    if pos_keys:
                        anim_info['keyframes'] += int(pos_keys.get('num', 0))
                    
                    # Rotation keyframes
                    rot_keys = node_anim.find('.//RotationKeyList')
                    if rot_keys:
                        anim_info['keyframes'] += int(rot_keys.get('num', 0))
                    
                    # Scale keyframes
                    scale_keys = node_anim.find('.//ScalingKeyList')
                    if scale_keys:
                        anim_info['keyframes'] += int(scale_keys.get('num', 0))
            
            animations.append(anim_info)
        
        return animations
    
    def get_node_hierarchy(self, max_depth: int = 3) -> List[str]:
        """Get node hierarchy (bone structure)"""
        hierarchy = []
        
        scene = self.root.find('.//Scene')
        if not scene:
            return hierarchy
        
        def traverse_nodes(node, depth=0, prefix=""):
            if depth > max_depth:
                return
            
            node_name = node.get('name', '[unnamed]')
            hierarchy.append(f"{prefix}{node_name}")
            
            # Get child nodes
            node_list = node.find('NodeList')
            if node_list:
                num_children = int(node_list.get('num', 0))
                if num_children > 0:
                    for child in node_list.findall('Node'):
                        traverse_nodes(child, depth + 1, prefix + "  ")
        
        # Start from root node
        root_node = scene.find('.//Node')
        if root_node:
            traverse_nodes(root_node)
        
        return hierarchy
    
    def get_texture_references(self) -> List[str]:
        """Extract all texture file references"""
        textures = []
        
        scene = self.root.find('.//Scene')
        if not scene:
            return textures
        
        # Find all texture elements
        for texture in scene.findall('.//Texture'):
            filename = texture.find('File')
            if filename is not None and filename.text:
                textures.append(filename.text.strip())
        
        return list(set(textures))  # Remove duplicates
    
    def get_mesh_names(self) -> List[str]:
        """Extract all mesh names"""
        mesh_names = []
        
        scene = self.root.find('.//Scene')
        if not scene:
            return mesh_names
        
        mesh_list = scene.find('.//MeshList')
        if mesh_list:
            for mesh in mesh_list.findall('Mesh'):
                name = mesh.get('name', '[unnamed]')
                mesh_names.append(name)
        
        return mesh_names
    
    def analyze(self):
        """Perform full analysis and display results"""
        print("\n" + "="*70)
        print("ASSXML MODEL ANALYSIS")
        print("="*70)
        
        if self.root is None:
            print("\n⚠️  XML parsing failed, using text-based analysis...")
            self._text_based_analysis()
            return
        
        # Basic info
        info = self.get_model_info()
        print("\n📊 MODEL INFORMATION")
        print(f"  Format ID:   {info['format_id']}")
        print(f"  Nodes:       {info['nodes']}")
        print(f"  Meshes:      {info['meshes']}")
        print(f"  Materials:   {info['materials']}")
        print(f"  Textures:    {info['textures']}")
        print(f"  Animations:  {info['animations']}")
        
        # Animations
        if info['animations'] > 0:
            print(f"\n🎬 ANIMATIONS ({info['animations']} total)")
            animations = self.get_animation_details()
            for idx, anim in enumerate(animations[:10], 1):  # Show first 10
                print(f"\n  {idx}. {anim['name']}")
                print(f"     Duration:  {anim['duration']:.2f} ticks")
                print(f"     Channels:  {anim['channels']}")
                print(f"     Keyframes: {anim['keyframes']}")
            
            if len(animations) > 10:
                print(f"\n  ... and {len(animations) - 10} more animations")
        
        # Node hierarchy
        print(f"\n🌳 NODE HIERARCHY (top 3 levels)")
        hierarchy = self.get_node_hierarchy(max_depth=3)
        for line in hierarchy[:20]:  # Show first 20 lines
            print(f"  {line}")
        if len(hierarchy) > 20:
            print(f"  ... and {len(hierarchy) - 20} more nodes")
        
        # Meshes
        mesh_names = self.get_mesh_names()
        if mesh_names:
            print(f"\n🔷 MESHES ({len(mesh_names)} total)")
            for idx, name in enumerate(mesh_names[:10], 1):
                print(f"  {idx}. {name}")
            if len(mesh_names) > 10:
                print(f"  ... and {len(mesh_names) - 10} more meshes")
        
        # Textures
        textures = self.get_texture_references()
        if textures:
            print(f"\n🖼️  TEXTURES ({len(textures)} total)")
            for idx, tex in enumerate(textures[:15], 1):
                print(f"  {idx}. {tex}")
            if len(textures) > 15:
                print(f"  ... and {len(textures) - 15} more textures")
        
        print("\n" + "="*70)
        print("✓ Analysis complete")
        print("="*70 + "\n")
    
    def _text_based_analysis(self):
        """Fallback text-based analysis when XML parsing fails"""
        import re
        
        with open(self.assxml_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Extract counts using regex
        animations_match = re.search(r'<AnimationList num="(\d+)">', content)
        meshes_match = re.search(r'<MeshList num="(\d+)">', content)
        materials_match = re.search(r'<MaterialList num="(\d+)">', content)
        
        print("\n📊 MODEL INFORMATION (from text parsing)")
        if animations_match:
            print(f"  Animations:  {animations_match.group(1)}")
        if meshes_match:
            print(f"  Meshes:      {meshes_match.group(1)}")
        if materials_match:
            print(f"  Materials:   {materials_match.group(1)}")
        
        # Extract animation names
        anim_pattern = re.compile(r'<Animation name="([^"]+)" duration="([^"]+)"')
        animations = anim_pattern.findall(content)
        
        if animations:
            print(f"\n🎬 ANIMATIONS ({len(animations)} total)")
            for idx, (name, duration) in enumerate(animations[:10], 1):
                try:
                    dur_float = float(duration)
                    print(f"  {idx}. {name} - Duration: {dur_float:.2f} ticks")
                except:
                    print(f"  {idx}. {name}")
            
            if len(animations) > 10:
                print(f"  ... and {len(animations) - 10} more animations")
        
        # Extract mesh names
        mesh_pattern = re.compile(r'<Mesh name="([^"]+)"')
        meshes = mesh_pattern.findall(content)
        
        if meshes:
            unique_meshes = list(set(meshes))
            print(f"\n🔷 MESHES ({len(unique_meshes)} unique)")
            for idx, name in enumerate(unique_meshes[:10], 1):
                print(f"  {idx}. {name}")
            if len(unique_meshes) > 10:
                print(f"  ... and {len(unique_meshes) - 10} more meshes")
        
        # Extract node names
        node_pattern = re.compile(r'<Node name="([^"]+)"')
        nodes = node_pattern.findall(content)
        
        if nodes:
            print(f"\n🌳 NODES ({len(nodes)} total)")
            for idx, name in enumerate(nodes[:15], 1):
                print(f"  {idx}. {name}")
            if len(nodes) > 15:
                print(f"  ... and {len(nodes) - 15} more nodes")
        
        print("\n" + "="*70)
        print("✓ Analysis complete (text-based)")
        print("="*70 + "\n")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze ASSXML files from converted .X models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a single ASSXML file
  python analyze_assxml.py "Satoko_text.assxml"
  
  # Verbose output
  python analyze_assxml.py "Satoko_text.assxml" -v

This tool helps you understand:
  - Model structure and complexity
  - Animation data (count, duration, channels)
  - Bone hierarchy
  - Mesh organization
  - Texture references
        """
    )
    
    parser.add_argument(
        'input',
        help='Input ASSXML file to analyze'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Analyze the file
    analyzer = ASSXMLAnalyzer(args.input)
    
    # Try to load (but continue even if it fails)
    analyzer.load()
    
    analyzer.analyze()
    return 0


if __name__ == "__main__":
    sys.exit(main())
