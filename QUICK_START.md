# Quick Start Guide - Higurashi Daybreak Model Conversion

## For End Users (Simple!)

### What You Need
1. Python 3.x installed
2. Assimp CLI installed ([Download here](https://github.com/assimp/assimp/releases))
3. The conversion scripts from this project

### Installation

```bash
# Install Python dependencies
cd pythonScripts
pip install -r requirements.txt
```

### Converting Models (3 Easy Steps!)

#### Step 1: Convert Your Model
```bash
python convert_x_to_gltf_auto.py "path/to/YourModel.X"
```

This creates:
- `YourModel_clean.gltf` - Your converted model
- `YourModel_clean.bin` - Animation/mesh data
- `YourModel_clean.mapping.txt` - Texture name reference
- `YourModel_clean_rename_textures.ps1` - Texture renaming script

#### Step 2: Rename Your Textures
1. Copy all your `.bmp` texture files to the same folder as the `_clean.gltf` file
2. Open the `.mapping.txt` file to see what the textures should be renamed to
3. Run the PowerShell script:
   ```bash
   pwsh YourModel_clean_rename_textures.ps1
   ```

#### Step 3: Open in Blender
1. Open Blender
2. File → Import → glTF 2.0
3. Select your `YourModel_clean.gltf` file
4. Done! Your model with all 124 animations is ready!

---

## Batch Conversion

### Convert All Models in a Folder
```bash
python convert_x_to_gltf_auto.py "path/to/models_folder/"
```

This will:
- Process all `.X` files in the folder
- Create a `converted_clean/` subfolder
- Generate fixed GLTF files for each model
- Create renaming scripts for each model's textures

---

## Troubleshooting

### "Assimp not found" error
**Solution:** Install Assimp CLI and add it to your PATH
- Download: https://github.com/assimp/assimp/releases
- Extract and add the `bin` folder to your system PATH

### "No textures showing in Blender"
**Solution:** Make sure you renamed the texture files
1. Check the `.mapping.txt` file
2. Verify texture files are in the same folder as the `.gltf` file
3. Run the `_rename_textures.ps1` script
4. Reload the model in Blender

### "Animations not playing"
**Solution:** The animations are there, you may need to select them
- In Blender, open the Nonlinear Animation editor
- Push down the action strips
- Or use the Action Editor to select different animations (Anim-1, Anim-2, etc.)

### "Model looks weird/broken"
**Possible causes:**
1. Missing textures (see texture troubleshooting above)
2. Wrong import settings in Blender
3. Scale issues (try scaling the imported model)

---

## File Format Reference

### What Gets Created

**Original file:**
- `Model.X` - 8-10 MB binary DirectX file

**After conversion:**
- `Model_clean.gltf` - 15-20 MB text GLTF file (ready to use)
- `Model_clean.bin` - 4-5 MB binary data (meshes, animations)
- `Model_clean.mapping.txt` - Text file showing name changes
- `Model_clean_rename_textures.ps1` - PowerShell script

### Supported Features
✅ All 124 animations per model
✅ Full bone hierarchy (81 bones for Satoko)
✅ All meshes (12 for Satoko)
✅ Material assignments
✅ Texture references (after renaming)
⚠️ Textures must be renamed manually or via script

---

## Advanced Options

### Convert to Binary GLB Format
```bash
python convert_x_to_gltf_auto.py "Model.X" --glb
```

**Note:** GLB format cannot have names auto-fixed. Use GLTF for best results.

### Manual Conversion (Not Recommended)
If you need to convert without auto-fixing:
```bash
# Step 1: Convert
python convert_x_to_gltf_cli.py "Model.X"

# Step 2: Fix names manually
python fix_gltf_texture_names.py "Model.gltf"
```

---

## Model Information

### Typical Higurashi Daybreak Model
- **Animations:** 124 animations per character
- **Bones:** ~80 bones per character
- **Meshes:** 10-15 meshes per character
- **Textures:** 3-10 texture files per character
- **Encoding:** Shift-JIS (Japanese)
- **Format:** Binary DirectX 9 .X

### Animation List (Satoko Example)
- Anim-1 to Anim-124
- Duration varies: 80 to 8800 ticks
- Each has 38 animation channels
- 228 to 12,654 keyframes per animation

---

## Getting Help

### Check the Documentation
- `README.md` - Full project documentation
- `program report/` - Detailed technical reports

### Common Issues
1. **Always use the automated converter** (`convert_x_to_gltf_auto.py`)
2. **Always rename textures** using the generated script
3. **Keep files together** - GLTF, BIN, and textures in same folder

### For Developers
See the Advanced Workflow section in `README.md` for debugging tools:
- `convert_x_binary_to_text.py` - Creates human-readable ASSXML
- `analyze_assxml.py` - Analyzes model structure
- `test_x_file.py` - Examines raw binary data

---

## Success Checklist

Before importing to Blender, verify:
- [ ] Used `convert_x_to_gltf_auto.py` for conversion
- [ ] Got `_clean.gltf` and `_clean.bin` files
- [ ] Copied texture `.bmp` files to same folder
- [ ] Ran the `_rename_textures.ps1` script
- [ ] All texture files renamed successfully
- [ ] Ready to import!

**Expected result:** Model imports with full skeleton, all meshes, and 124 animations ready to use!
