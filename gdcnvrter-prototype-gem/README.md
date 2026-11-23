# SELODev Asset Converter (`gdcnvrter`) — Prototype

A zero-setup, pure-Python `.unitypackage` → Godot 4.7+ `.tscn` asset & prefab converter with a Godot 4.7+ EditorPlugin Lite dock.

## Features (v0.1.0 Prototype)
- **Zero Unity Install Required:** Parses `.unitypackage` (`.tar.gz`) archives, `.mat` PBR properties, and `.prefab` YAML hierarchies directly.
- **Lite Single-Prefab Preview:** `scan` inspects the package, counts full vs. partial vs. skipped prefabs, and `--prefab <Name>` converts one chosen prefab.
- **Shared Material Reuse & Colliders:** Generates deterministic `uid://` `.tres` (`StandardMaterial3D`) files shared across child `MeshInstance3D` nodes, plus `StaticBody3D` + `CollisionShape3D`.
- **Atomic Writes & Safe Reimport:** Writes via temp files + `os.replace`, updates shared `.tres` materials in-place without duplicates, and preserves user-edited `.tscn` scenes unless `--overwrite` is passed.

## Quickstart

```bash
# 1. Run the 5-case automated verification suite
python3 -m unittest discover -s tests -v

# 2. Scan a .unitypackage
python3 -m gdcnvrter.cli scan path/to/pack.unitypackage

# 3. Lite mode: convert one chosen prefab
python3 -m gdcnvrter.cli convert path/to/pack.unitypackage --out /path/to/godot_project --prefab ModularDoorway

# 4. Pro batch mode: convert all supported/partial prefabs
python3 -m gdcnvrter.cli convert path/to/pack.unitypackage --out /path/to/godot_project
```

## Godot 4.7+ Lite Addon
Copy `addons/gdcnvrter_lite/` into your Godot 4.7+ project's `res://addons/` folder and enable **SELODev Asset Converter (Lite)** in **Project → Project Settings → Plugins**.
