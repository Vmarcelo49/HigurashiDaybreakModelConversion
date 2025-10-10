# HigurashiDaybreakModelConversion

This project is a place to gather all the information i manage to find through testing and many hours of fruitless effort

## ⚡ NEW SOLUTION: Working GLTF Converter!

**We've identified and fixed the core issue!** Assimp converts Daybreak X files but produces corrupted animation timing (float_max/-float_max → -inf duration). 

**→ See [DAYBREAK_FIX_README.md](DAYBREAK_FIX_README.md) for the complete solution**

**Quick Start:**
```bash
python pythonScripts/convert_daybreak_x_to_gltf.py Satoko.X
```

This automatically converts and fixes all animation data, producing a working GLTF file!

---

## Main goal of the project

Convert Higurashi Daybreak .x models to .gltf or .fbx keeping proper animations
