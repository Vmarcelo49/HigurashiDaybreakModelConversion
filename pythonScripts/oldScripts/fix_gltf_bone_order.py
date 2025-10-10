"""
Fix GLTF Bone Ordering Issues
Reorders bones in GLTF to ensure parents come before children

This fixes the "bone X has parent Y skipping" error that occurs when
bones are not topologically sorted in the GLTF file.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GLTFBoneFixer:
    """Fixes bone ordering in GLTF files"""
    
    def __init__(self, gltf_path: str, output_path: str = None):
        """
        Initialize the fixer
        
        Args:
            gltf_path: Path to the GLTF file to fix
            output_path: Path for fixed GLTF file (default: replace original)
        """
        self.gltf_path = Path(gltf_path)
        
        if not self.gltf_path.exists():
            raise FileNotFoundError(f"GLTF file not found: {gltf_path}")
        
        if output_path:
            self.output_path = Path(output_path)
        else:
            self.output_path = self.gltf_path
        
        self.gltf_data = None
        self.reordered = False
    
    def load_gltf(self):
        """Load the GLTF file"""
        logger.info(f"Loading GLTF file: {self.gltf_path}")
        
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(self.gltf_path, 'r', encoding=encoding, errors='ignore') as f:
                    self.gltf_data = json.load(f)
                logger.info(f"✓ GLTF loaded successfully")
                return
            except (UnicodeDecodeError, json.JSONDecodeError):
                if encoding == encodings[-1]:
                    raise
                continue
    
    def topological_sort_joints(self, joints: List[int], all_nodes: List[dict]) -> Tuple[List[int], Dict[int, int]]:
        """
        Perform topological sort on joint indices to ensure parents come before children
        
        Args:
            joints: List of joint node indices from skin
            all_nodes: All nodes from GLTF
            
        Returns:
            Tuple of (sorted joint indices, old_position -> new_position mapping)
        """
        # Build parent-child relationships within the joint set
        joints_set = set(joints)
        joint_children = {}  # joint_idx -> [child joint indices]
        joint_parent = {}    # joint_idx -> parent joint idx
        
        for joint_idx in joints:
            node = all_nodes[joint_idx]
            joint_children[joint_idx] = []
            
            if 'children' in node:
                for child_idx in node['children']:
                    # Only consider children that are also joints
                    if child_idx in joints_set:
                        joint_children[joint_idx].append(child_idx)
                        joint_parent[child_idx] = joint_idx
        
        # Find root joints (joints with no parent in the joint set)
        root_joints = []
        for joint_idx in joints:
            if joint_idx not in joint_parent:
                root_joints.append(joint_idx)
        
        # Perform depth-first traversal to get topological order
        sorted_joint_indices = []
        visited = set()
        
        def dfs(joint_idx):
            if joint_idx in visited:
                return
            visited.add(joint_idx)
            sorted_joint_indices.append(joint_idx)
            
            # Visit children in the joint hierarchy
            for child_idx in joint_children.get(joint_idx, []):
                dfs(child_idx)
        
        # Start DFS from all root joints
        for root_idx in root_joints:
            dfs(root_idx)
        
        # Add any unvisited joints (shouldn't happen in a valid hierarchy)
        for joint_idx in joints:
            if joint_idx not in visited:
                logger.warning(f"Joint {joint_idx} was not connected to any root - adding at end")
                sorted_joint_indices.append(joint_idx)
        
        return sorted_joint_indices
    
    def topological_sort_nodes(self, nodes: List[dict]) -> Tuple[List[int], Dict[int, int]]:
        """
        Perform topological sort on ALL nodes to ensure parents come before children
        
        Args:
            nodes: List of node objects from GLTF
            
        Returns:
            Tuple of (sorted node indices, old_index -> new_index mapping)
        """
        # Build parent-child relationships
        node_children = {}  # node_idx -> [child_indices]
        node_parent = {}    # node_idx -> parent_idx
        
        for i, node in enumerate(nodes):
            if 'children' in node:
                node_children[i] = node['children']
                for child_idx in node['children']:
                    node_parent[child_idx] = i
            else:
                node_children[i] = []
        
        # Find root nodes (nodes with no parent)
        root_nodes = []
        for i in range(len(nodes)):
            if i not in node_parent:
                root_nodes.append(i)
        
        # Perform depth-first traversal to get topological order
        sorted_indices = []
        visited = set()
        
        def dfs(node_idx):
            if node_idx in visited:
                return
            visited.add(node_idx)
            sorted_indices.append(node_idx)
            
            # Visit children
            for child_idx in node_children.get(node_idx, []):
                dfs(child_idx)
        
        # Start DFS from all root nodes
        for root_idx in root_nodes:
            dfs(root_idx)
        
        # Add any unvisited nodes (shouldn't happen in a valid tree)
        for i in range(len(nodes)):
            if i not in visited:
                logger.warning(f"Node {i} was not connected to any root - adding at end")
                sorted_indices.append(i)
        
        # Create mapping from old index to new index
        index_mapping = {}
        for new_idx, old_idx in enumerate(sorted_indices):
            index_mapping[old_idx] = new_idx
        
        return sorted_indices, index_mapping
    
    def fix_bone_order(self):
        """Fix bone ordering in all skins"""
        if 'skins' not in self.gltf_data:
            logger.info("No skins found in GLTF")
            return
        
        if 'nodes' not in self.gltf_data:
            logger.info("No nodes found in GLTF")
            return
        
        logger.info(f"Analyzing {len(self.gltf_data['skins'])} skin(s)...")
        
        for skin_idx, skin in enumerate(self.gltf_data['skins']):
            joints = skin.get('joints', [])
            
            if not joints:
                continue
            
            logger.info(f"\nSkin {skin_idx}: {len(joints)} joints")
            
            # Check if bones are properly ordered
            needs_reorder = False
            for i, joint_idx in enumerate(joints):
                node = self.gltf_data['nodes'][joint_idx]
                
                # Check if this node has children that appear before it
                if 'children' in node:
                    for child_idx in node['children']:
                        if child_idx in joints:
                            child_pos = joints.index(child_idx)
                            if child_pos < i:
                                needs_reorder = True
                                logger.warning(f"  Joint {joint_idx} at position {i} has child {child_idx} at earlier position {child_pos}")
            
            if not needs_reorder:
                logger.info(f"  ✓ Bones already properly ordered")
                continue
            
            logger.info(f"  Reordering joints...")
            
            # Perform topological sort on these joints
            sorted_joint_indices = self.topological_sort_joints(joints, self.gltf_data['nodes'])
            
            # Update the skin
            skin['joints'] = sorted_joint_indices
            
            logger.info(f"  ✓ Reordered {len(sorted_joint_indices)} joints")
            self.reordered = True
    
    def fix_node_hierarchy(self):
        """Ensure entire node hierarchy is topologically sorted"""
        if 'nodes' not in self.gltf_data:
            return
        
        nodes = self.gltf_data['nodes']
        logger.info(f"\nAnalyzing node hierarchy ({len(nodes)} nodes)...")
        
        # Check if reordering is needed
        needs_reorder = False
        for i, node in enumerate(nodes):
            if 'children' in node:
                for child_idx in node['children']:
                    if child_idx < i:
                        needs_reorder = True
                        logger.warning(f"  Node {i} has child {child_idx} with lower index")
                        break
            if needs_reorder:
                break
        
        if not needs_reorder:
            logger.info("  ✓ Node hierarchy already properly ordered")
            return
        
        logger.info("  Reordering node hierarchy...")
        
        # Perform topological sort
        sorted_indices, index_mapping = self.topological_sort_nodes(nodes)
        
        # Create new node list
        new_nodes = [nodes[old_idx] for old_idx in sorted_indices]
        
        # Update all node children references
        for node in new_nodes:
            if 'children' in node:
                node['children'] = [index_mapping[old_idx] for old_idx in node['children']]
        
        # Update scene references
        if 'scenes' in self.gltf_data:
            for scene in self.gltf_data['scenes']:
                if 'nodes' in scene:
                    scene['nodes'] = [index_mapping[old_idx] for old_idx in scene['nodes']]
        
        # Update skin references
        if 'skins' in self.gltf_data:
            for skin in self.gltf_data['skins']:
                if 'skeleton' in skin:
                    skin['skeleton'] = index_mapping[skin['skeleton']]
                if 'joints' in skin:
                    skin['joints'] = [index_mapping[old_idx] for old_idx in skin['joints']]
        
        # Update animation channel targets
        if 'animations' in self.gltf_data:
            for anim in self.gltf_data['animations']:
                for channel in anim.get('channels', []):
                    if 'target' in channel and 'node' in channel['target']:
                        old_node = channel['target']['node']
                        channel['target']['node'] = index_mapping[old_node]
        
        # Replace nodes
        self.gltf_data['nodes'] = new_nodes
        
        logger.info(f"  ✓ Reordered {len(new_nodes)} nodes")
        self.reordered = True
    
    def save_gltf(self):
        """Save the fixed GLTF file"""
        logger.info(f"\nSaving GLTF to: {self.output_path}")
        
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(self.gltf_data, f, indent=2)
        
        logger.info("✓ GLTF file saved successfully")
    
    def fix(self):
        """Main fix method"""
        self.load_gltf()
        self.fix_node_hierarchy()
        self.fix_bone_order()
        
        if self.reordered:
            self.save_gltf()
            logger.info("\n" + "="*70)
            logger.info("✓ Bone ordering fixed successfully!")
            logger.info("="*70)
        else:
            logger.info("\n" + "="*70)
            logger.info("ℹ No bone ordering issues found")
            logger.info("="*70)
        
        return self.reordered


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python fix_gltf_bone_order.py <path_to_gltf_file> [output_path]")
        print("\nFixes bone ordering issues in GLTF files.")
        print("If output_path is not specified, the original file will be overwritten.")
        sys.exit(1)
    
    gltf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        fixer = GLTFBoneFixer(gltf_path, output_path)
        fixer.fix()
        
    except Exception as e:
        logger.error(f"Error fixing GLTF file: {e}")
        logger.exception("Detailed error:")
        sys.exit(1)


if __name__ == '__main__':
    main()
