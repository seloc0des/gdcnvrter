# SELODev Prefab Packager pilot

Use the file chooser or the command line to inspect a Unity text prefab package, preview one prefab, or convert the entire package into an existing Godot project. The prototype exposes both conversion modes. Commercial edition packaging and checkout are future pilot decisions.

## Try the doorway

The downloadable pilot bundle includes a built Python app, a self-authored Unity package and a Godot project. Extract the ZIP, open `demo/project.godot` in Godot 4.7.2, and press F6 on Walkthrough.tscn or F5 to run the project. Walk between the posts with the arrow keys, then try walking through a post.

Run `python selodev-packager.pyz` for the desktop picker (Python 3.10+ with Tk), or use the terminal commands below. On Linux use `python3` if needed. The built app includes PyYAML. The CLI works without Tk.

    python selodev-packager.pyz inspect Doorway.unitypackage
    python selodev-packager.pyz preview Doorway.unitypackage demo Assets/Fixture/Doorway.prefab
    python selodev-packager.pyz batch Doorway.unitypackage demo

In your own Godot project, let the editor finish importing, then drag the generated scene from SELOPackager/scenes into your level. Filenames use Unity GUIDs so renames preserve references. The inspection report maps source names to GUIDs. Inspect runs the conversion in memory and predicts the result before Godot imports the resources. The JSON report includes counts and per-prefab repair notes. A skipped prefab makes the CLI exit with status 1. Partial results remain available. Dependencies are matched within the selected package.

## Supported scope

| Content | Pilot behavior |
|---|---|
| GameObject and Transform | One root, child order, local position, rotation, scale, and pivot. Reflects the Z axis into Godot space. Sanitizes incompatible node names. |
| MeshFilter and MeshRenderer | Unity built-in cube, sphere and capsule. Standalone OBJ main mesh with fileID 4300000. OBJ conversion flags axis, scale and surface order for inspection. |
| Materials | Shared StandardMaterial3D by Unity material GUID. Base color, base texture, UV scale/offset, standard glossiness to roughness. PNG, JPEG and WebP pass through for Godot import. Other shader properties may need manual matching. |
| Collision | Static BoxCollider, local center and size, and enabled state. Triggers need an Area3D. Review collision manually for inactive objects or nonuniform parent scale. |
| Unsupported | FBX submeshes, embedded model materials, nested prefabs and variants, binary prefab serialization, scripts, animation, skinned meshes, custom shaders, lights and other colliders. Repair notes flag omitted components or references. |

A full result means the prefab passed the converter's supported mapping checks. It does not certify visual parity. Partial means a generated scene has a known omission or needs review. Skipped means conversion or write protection prevented that prefab from being generated. A later Godot import can still reject damaged source mesh or texture data. Inspect/convert handles archives up to 1 GiB uncompressed and individual assets up to 128 MiB.

## Reimport and recovery

Use the same Godot project on the next conversion. Scene and material resource UIDs are derived from Unity GUIDs. Generated textures and meshes retain their paths and Godot import sidecars. Extend a generated prefab by placing it in a wrapper scene, or assign a separate material override there.

The inventory in SELOPackager/.inventory.json records content hashes. Each prefab is checked before its changed files are written. A manually edited or unrelated existing destination skips that prefab and explains the conflict. Back up and move the conflicting file aside to regenerate it. Keep the inventory with generated output. Removed source assets are retained so existing placed scenes keep their dependencies. A shared source material update also updates other scenes that use it.

One writer at a time uses a project-local OS lock. Dependencies are replaced before their scene. Each replacement is atomic. The inventory records the old and new hash before replacement so retrying after an interrupted process can finish. Earlier prefabs in an interrupted batch may already have updated. Close the Godot editor during large reimports if you want to avoid intermediate refreshes.

## Build and test from source

    python -m pip install -r requirements.txt
    python build.py
    python tests/fixture.py Doorway.unitypackage
    python dist/selodev-packager.pyz batch Doorway.unitypackage demo
    python -m unittest discover -s tests -v

Put Godot 4.7.2 on PATH as `godot` for the engine checks. The suite runs headless imports and reopens a placed instance, checks the shared material before and after an update, queries the physics world across the doorway, loads an OBJ and PNG, and exercises missing content, interruption, and local edit protection. Generate a mixed diagnostic pack with `python tests/fixture.py Mixed.unitypackage --incomplete`.

The desktop build workflow packages per-OS executables with PyInstaller. Clean-machine UI testing on Windows and macOS, visual comparisons on unfamiliar licensed packs, and timing against Unidot are open verification items. The public fixture measures correctness on authored inputs only.
