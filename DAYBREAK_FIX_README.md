# Daybreak GLTF Fix Solution

## Problem Identified

Assimp converts Daybreak X files to GLTF format, but the animation timing data is **completely corrupted**:

- **Animation keyframe timestamps**: `float_max` (1.79e308) and `-float_max` (-1.79e308)
- **Animation durations**: `-infinity` 
- **Result**: Models cannot be rendered or animated properly

### Root Cause

The Daybreak X files use custom data structures that assimp almost interprets correctly, but the timing information gets converted to invalid floating-point extremes instead of proper timestamps.

## Solution

We've created a post-processing fixer that:

1. **Detects corrupted timing data** - Identifies animation samplers with invalid float_max/-float_max values
2. **Regenerates proper timestamps** - Creates synthetic timing at 30 FPS based on keyframe count
3. **Updates binary data** - Writes corrected timestamps directly to the .bin file
4. **Fixes accessor bounds** - Updates min/max values in GLTF JSON to reflect actual data

## Tools

### 1. `fix_daybreak_gltf.py`
Fixes already-converted GLTF files.

```bash
python fix_daybreak_gltf.py input.gltf [output.gltf]
```

**What it fixes:**
- ✅ Invalid animation timing (float_max → proper timestamps)
- ✅ Corrupted accessor min/max bounds
- ✅ Extreme coordinate values
- ✅ Structure validation

### 2. `convert_daybreak_x_to_gltf.py`
All-in-one converter: X → GLTF → Auto-fix

```bash
python convert_daybreak_x_to_gltf.py input.X [output.gltf]
```

**Process:**
1. Converts X file using assimp
2. Automatically applies all fixes
3. Outputs ready-to-use GLTF

### 3. `analyze_model_detailed.py`
Analyzes models to identify issues (now with Windows encoding fixes)

```bash
python analyze_model_detailed.py model.gltf
python analyze_model_detailed.py model.X
```

## Quick Start

### Convert a Single Model

```bash
# All-in-one: Convert and fix
python convert_daybreak_x_to_gltf.py Satoko.X

# Output: Satoko_fixed.gltf + Satoko_fixed.bin
```

### Fix an Already Converted Model

```bash
# If you already have a GLTF from assimp
python fix_daybreak_gltf.py Satoko.gltf

# Output: Satoko_fixed.gltf + Satoko_fixed.bin
```

### Analyze Before and After

```bash
# Before fix
python analyze_model_detailed.py Satoko.gltf > before.txt

# After fix
python analyze_model_detailed.py Satoko_fixed.gltf > after.txt
```

## Results

### Before Fix
```
Animation 0: Anim-1
  Sampler 0: 1.80e+308s - -1.80e+308s (duration: -infs, 20 keyframes)
  Sampler 1: 1.80e+308s - -1.80e+308s (duration: -infs, 20 keyframes)
  ...
```

### After Fix
```
Animation 0: Anim-1
  Sampler 0: 0.000s - 0.633s (duration: 0.633s, 20 keyframes)
  Sampler 1: 0.000s - 0.633s (duration: 0.633s, 20 keyframes)
  ...
```

## Technical Details

### Animation Timing Fix

The fixer:
1. Reads actual keyframe data from the binary buffer
2. Checks if timestamps are corrupted (abs > 1e100, inf, or nan)
3. Generates new timestamps: `time[i] = i * (1/30)` seconds
4. Writes corrected timestamps back to binary buffer
5. Updates GLTF accessor min/max values

### Why 30 FPS?

Standard animation framerate that:
- Works well for game animations
- Matches typical DirectX 9 game expectations
- Can be adjusted in the script if needed (line ~160 in `fix_daybreak_gltf.py`)

## File Structure

```
pythonScripts/
├── convert_daybreak_x_to_gltf.py   # All-in-one converter
├── fix_daybreak_gltf.py            # GLTF fixer
├── analyze_model_detailed.py       # Model analyzer (Windows-compatible)
├── convert_x_to_gltf_minimal.py    # Simple assimp wrapper
└── requirements.txt                # Dependencies
```

## Requirements

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install assimp CLI
# Windows: Download from https://github.com/assimp/assimp/releases
# Add to PATH
```

## Known Limitations

1. **Frame rate assumption**: Currently assumes 30 FPS for regenerated timestamps
   - May not match original animation speed exactly
   - Can be adjusted in the code if you know the correct FPS

2. **Binary format only**: Processes GLTF 2.0 with separate .bin files
   - Does not support embedded GLB format
   - GLB support could be added if needed

3. **Shift-JIS names**: Japanese characters in material/texture names may display incorrectly
   - Functional data is preserved
   - Names can be viewed properly with UTF-8 editors

## Future Improvements

- [ ] Auto-detect original animation FPS from X file metadata
- [ ] Add GLB format support
- [ ] Batch processing for multiple models
- [ ] GUI interface for non-technical users
- [ ] Validate against GLTF Validator
- [ ] Add bone transform validation
- [ ] Texture path auto-fixing

## Testing

Test the fixed models:
- ✅ Blender GLTF importer
- ✅ three.js GLTF loader
- ✅ Don McCurdy's GLTF Viewer (https://gltf-viewer.donmccurdy.com/)

## Credits

This solution was developed by analyzing:
- Assimp conversion output
- GLTF 2.0 specification
- Binary buffer structure
- DirectX 9 X file format documentation

## License

Same as the parent HigurashiDaybreakModelConversion project.
