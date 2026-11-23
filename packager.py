"""Local SELODev static prefab converter. Run without arguments for the desktop UI."""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tarfile
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import yaml

GUID = re.compile(r"[0-9a-fA-F]{32}")
HEADER = re.compile(r"^--- !u!(\d+) &(-?\d+)([^\n]*)$", re.M)
ROOT = "SELOPackager"
BUILTIN = "0000000000000000e000000000000000"
SHAPES = {10202: "BoxMesh", 10207: "SphereMesh", 10208: "CapsuleMesh"}
IMAGE = {".png", ".jpg", ".jpeg", ".webp"}
MAX_ASSET = 128 * 1024**2


def digest(data):
    return hashlib.sha256(data).hexdigest()


def uid(guid, kind):
    # Use a conservative subset of Godot's textual ResourceUID alphabet.
    return "uid://" + "".join(chr(97 + b % 25) for b in hashlib.sha256((guid + kind).encode()).digest()[:12])


class UnityLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        result = super().construct_mapping(node, deep)
        for key, value in node.value:
            if isinstance(key, yaml.ScalarNode) and key.value in {"guid", "m_Name"} and isinstance(value, yaml.ScalarNode):
                result[key.value] = value.value
        return result


def documents(raw):
    source = raw.decode("utf-8-sig")
    markers = list(HEADER.finditer(source))
    if not markers:
        raise ValueError("Requires Unity text serialization. Re-export the asset as text.")
    result = {}
    for i, marker in enumerate(markers):
        if marker[3].strip():
            raise ValueError("Flatten nested prefab instances or variants before export.")
        body = yaml.load(source[marker.end():markers[i+1].start() if i+1 < len(markers) else None], Loader=UnityLoader)
        if not isinstance(body, dict) or len(body) != 1:
            raise ValueError("Invalid Unity object document.")
        key = int(marker[2])
        if key in result:
            raise ValueError("Duplicate Unity object identifier.")
        result[key] = next(iter(body.items()))
    return result


class Package:
    def __init__(self, filename):
        self.files = defaultdict(dict)
        self.temp = tempfile.TemporaryDirectory()
        try:
            with tarfile.open(filename, "r|gz") as archive:
                for i, entry in enumerate(archive):
                    if i >= 100000 or entry.offset_data + entry.size > 1024**3:
                        raise ValueError("Package exceeds the 1 GiB / 100,000 entry pilot limit.")
                    match = re.fullmatch(r"(?:\./)?([a-fA-F0-9]{32})/(pathname|asset)", entry.name)
                    if not match or not entry.isfile():
                        continue
                    guid, field = match[1].lower(), match[2]
                    if field in self.files[guid] or entry.size > (4096 if field == "pathname" else MAX_ASSET):
                        raise ValueError("Duplicate or oversized package member.")
                    stream = archive.extractfile(entry)
                    if field == "pathname":
                        value = stream.read().decode("utf-8-sig").rstrip("\r\n")
                    else:
                        value = Path(self.temp.name, guid)
                        with value.open("wb") as target:
                            shutil.copyfileobj(stream, target)
                    self.files[guid][field] = value
        except BaseException:
            self.temp.cleanup()
            raise

    def close(self):
        self.temp.cleanup()

    def prefabs(self):
        return sorted((v["pathname"], g) for g, v in self.files.items()
                      if v.get("pathname", "").lower().endswith(".prefab"))

    def asset(self, guid):
        entry = self.files.get(guid, {})
        if "asset" not in entry or "pathname" not in entry:
            raise ValueError(f"Missing dependency {guid}. Include dependencies when exporting.")
        return entry["pathname"], entry["asset"].read_bytes()


def numbers(data, keys):
    values = [float(data[k]) for k in keys]
    if not all(map(math.isfinite, values)):
        raise ValueError("Non-finite Unity property.")
    return values


def vector(values):
    return ", ".join(format(x, ".10g") for x in values)


def quoted(value):
    return json.dumps(value, ensure_ascii=False)


class Conversion:
    def __init__(self, package, guid):
        self.package = package
        self.guid = guid
        self.outputs = {}
        self.notes = []
        self.external = {}
        self.subs = []
        self.nodes = []

    def ext(self, path, kind):
        key = (path, kind)
        return f'ExtResource("{self.external.setdefault(key, len(self.external)+1)}")'

    def sub(self, kind, props=""):
        key = str(len(self.subs)+1)
        self.subs.append(f'[sub_resource type="{kind}" id="{key}"]\n{props}')
        return f'SubResource("{key}")'

    def material(self, ref, owner):
        guid = str(ref.get("guid", ""))
        path, raw = self.package.asset(guid)
        mats = documents(raw)
        kind, mat = mats.get(ref.get("fileID"), ("", {}))
        if kind != "Material":
            raise ValueError(f"Cannot resolve material in {path}. Assign a Godot material.")
        saved = mat.get("m_SavedProperties") or {}
        colors = {k: v for row in saved.get("m_Colors", []) for k, v in row.items()}
        color = colors.get("_BaseColor", colors.get("_Color"))
        textures = {k: v for row in saved.get("m_TexEnvs", []) for k, v in row.items()}
        texture = textures.get("_BaseMap") or textures.get("_MainTex") or {}
        header = f'[gd_resource type="StandardMaterial3D" format=3 uid="{uid(guid,"material")}"]'
        props = ["[resource]"]
        if color:
            props.append("albedo_color = Color(" + vector(numbers(color, "rgba")) + ")")
        tex = texture.get("m_Texture") or {}
        if tex.get("fileID"):
            try:
                tg = str(tex.get("guid", ""))
                filename, data = self.package.asset(tg)
                suffix = Path(filename).suffix.lower()
                if suffix not in IMAGE:
                    raise ValueError(f"Unsupported texture {filename}. Replace with PNG or JPEG.")
                dest = f"textures/{tg}{suffix}"
                self.outputs[dest] = data
                header += f'\n\n[ext_resource type="Texture2D" path="res://{ROOT}/{dest}" id="tex"]'
                props.append('albedo_texture = ExtResource("tex")')
                for src, prop in [("m_Scale", "uv1_scale"), ("m_Offset", "uv1_offset")]:
                    if src in texture:
                        props.append(f'{prop} = Vector3({vector(numbers(texture[src], "xy"))}, {1 if src=="m_Scale" else 0})')
            except ValueError as error:
                self.notes.append(f"{owner}: {error}")
        for key, value in textures.items():
            if key not in {"_BaseMap", "_MainTex"} and (value.get("m_Texture") or {}).get("fileID"):
                self.notes.append(f"{owner}: assign {key} manually in a material override.")
        shader = mat.get("m_Shader") or {}
        floats = {k:v for row in saved.get("m_Floats", []) for k,v in row.items()}
        if any(floats.get(key, 0) for key in ("_Metallic", "_Mode", "_Surface", "_EmissionEnabled", "_AlphaClip")):
            self.notes.append(f"{owner}: check metallic, transparency or emission settings in {path}.")
        if "_Glossiness" in floats:
            props.append(f'roughness = {1.0 - min(1.0, max(0.0, float(floats["_Glossiness"]))):.8g}')
        if shader.get("guid") not in (None, "0000000000000000f000000000000000"):
            self.notes.append(f"{owner}: check custom shader in {path}. Only base color and albedo texture transfer.")
        dest = f"materials/{guid}.tres"
        self.outputs[dest] = (header+"\n\n"+"\n".join(props)+"\n").encode()
        return self.ext(dest, "Material")

    def mesh(self, mesh, renderer, owner, parent):
        ref = mesh.get("m_Mesh") or {}
        guid, key = str(ref.get("guid", "")), ref.get("fileID")
        if guid == BUILTIN and key in SHAPES:
            kind = SHAPES[key]
            props = {"SphereMesh":"radius = 0.5\nheight = 1.0", "CapsuleMesh":"radius = 0.5\nheight = 2.0"}.get(kind,"")
            resource = self.sub(kind, props)
        else:
            path, raw = self.package.asset(guid)
            if Path(path).suffix.lower() != ".obj" or key != 4300000:
                raise ValueError(f"Unsupported mesh {path} (fileID {key}). Assign the imported model manually.")
            dest = f"meshes/{guid}.obj"
            self.outputs[dest] = raw
            resource = self.ext(dest, "ArrayMesh")
            self.notes.append(f"{owner}: verify OBJ axes, scale and surface order against Unity importer settings.")
        lines = [f'[node name="_Mesh" type="MeshInstance3D" parent={quoted(parent)}]', f"mesh = {resource}"]
        if not renderer.get("m_Enabled", 1):
            lines.append("visible = false")
        for i, ref in enumerate(renderer.get("m_Materials") or []):
            try:
                lines.append(f"surface_material_override/{i} = {self.material(ref, owner)}")
            except ValueError as error:
                self.notes.append(f"{owner}: {error}")
        self.nodes.append("\n".join(lines))

    def scene(self):
        _, raw = self.package.asset(self.guid)
        docs = documents(raw)
        transforms = {k:v for k,(kind,v) in docs.items() if kind == "Transform"}
        parents = defaultdict(list)
        for key, obj in transforms.items():
            parents[obj["m_Father"]["fileID"]].append(key)
        if len(parents[0]) != 1:
            raise ValueError("Expected one static prefab root. Flatten variants and nested instances.")
        seen = set()

        def visit(key, parent=None, siblings=None):
            if key in seen:
                raise ValueError("Cycle in transform hierarchy.")
            seen.add(key)
            tr = transforms[key]
            kind, go = docs[tr["m_GameObject"]["fileID"]]
            if kind != "GameObject":
                raise ValueError("Transform refers to an invalid GameObject.")
            owner = str(go.get("m_Name") or "Object")
            name = re.sub(r'[^\w -]', "_", owner).strip() or "Object"
            if siblings is not None:
                while name in siblings:
                    name += f"_{abs(key)}"
                siblings.add(name)
            here = "." if parent is None else (name if parent == "." else parent+"/"+name)
            x,y,z = numbers(tr["m_LocalPosition"], "xyz")
            qx,qy,qz,qw = numbers(tr["m_LocalRotation"], "xyzw")
            self.nodes.append(f'[node name={quoted(name)} type="Node3D"'+ ("" if parent is None else " parent="+quoted(parent))+"]\n"
                              +f"position = Vector3({vector([x,y,-z])})\nquaternion = Quaternion({vector([-qx,-qy,qz,qw])})\n"
                              +f'scale = Vector3({vector(numbers(tr["m_LocalScale"], "xyz"))})')
            if not go.get("m_IsActive", 1):
                self.nodes[-1] += "\nvisible = false"
                self.notes.append(f"{owner}: inactive object. Review collision enabled state.")
            parts = [docs[row["component"]["fileID"]] for row in go["m_Component"]]
            renderer = next((v for typ,v in parts if typ == "MeshRenderer"), None)
            for index, (typ, obj) in enumerate(parts):
                if typ == "MeshFilter" and renderer is not None:
                    try:
                        self.mesh(obj, renderer, owner, here)
                    except ValueError as error:
                        self.notes.append(f"{owner}: {error}")
                elif typ == "BoxCollider":
                    if obj.get("m_IsTrigger"):
                        self.notes.append(f"{owner}: replace trigger with Area3D.")
                        continue
                    shape = self.sub("BoxShape3D", "size = Vector3("+vector(numbers(obj["m_Size"], "xyz"))+")")
                    x,y,z = numbers(obj["m_Center"], "xyz")
                    body = f"_Body{index}"
                    path = body if here == "." else here+"/"+body
                    self.nodes.extend([f'[node name="{body}" type="StaticBody3D" parent={quoted(here)}]',
                        f'[node name="Shape" type="CollisionShape3D" parent={quoted(path)}]\nshape = {shape}\nposition = Vector3({vector([x,y,-z])})\ndisabled = {str(not obj.get("m_Enabled",1)).lower()}'])
                elif typ not in {"Transform", "MeshRenderer"}:
                    self.notes.append(f"{owner}: {typ} omitted. Recreate it on a wrapper scene.")
            reserved = {"_Mesh"} | {f"_Body{i}" for i in range(len(parts))}
            children = [row["fileID"] for row in tr.get("m_Children") or []]
            if set(children) != set(parents[key]):
                raise ValueError("Inconsistent transform parent and child references.")
            for child in children:
                visit(child, here, reserved)
        visit(parents[0][0])
        if len(seen) != len(transforms):
            raise ValueError("Prefab has disconnected transforms.")
        if any(kind == "PrefabInstance" for kind,_ in docs.values()):
            self.notes.append("Nested instance omitted. Flatten the prefab and export again.")
        sections = [f'[gd_scene format=3 uid="{uid(self.guid,"scene")}"]']
        for (path, kind), index in self.external.items():
            sections.append(f'[ext_resource type="{kind}" path="res://{ROOT}/{path}" id="{index}"]')
        sections += self.subs + self.nodes
        self.outputs[f"scenes/{self.guid}.tscn"] = ("\n\n".join(sections)+"\n").encode()


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".pack-", delete=False) as out:
        temp = Path(out.name)
    try:
        with temp.open("wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


class Writer:
    def __init__(self, project):
        if not (project/"project.godot").is_file():
            raise ValueError("Choose the directory containing project.godot.")
        self.root = project.resolve()/ROOT
        if self.root.is_symlink():
            raise ValueError("Output directory must be inside the project.")
        self.root.mkdir(exist_ok=True)
        self.lock = None

    def __enter__(self):
        path = self.checked(".writer.lock")
        self.lock = path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self.lock.seek(0)
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.manifest = self.checked(".inventory.json")
            self.state = json.loads(self.manifest.read_bytes()) if self.manifest.exists() else {}
            return self
        except BaseException:
            self.lock.close()
            raise

    def __exit__(self, *_):
        self.lock.close()

    def checked(self, name):
        path = self.root/name
        if path.resolve() != path:
            raise ValueError(f"Refusing redirected output {name}.")
        return path

    def write(self, outputs):
        updates = {}
        for name, data in outputs.items():
            path = self.checked(name)
            current = digest(path.read_bytes()) if path.exists() else None
            expected = self.state.get(name, [])
            new = digest(data)
            if current == new and current in expected:
                continue
            if current is not None and current not in expected:
                raise ValueError(f"Protected existing file {name}. Back up your edit and move it aside to regenerate.")
            updates[name] = (current, new)
        if not updates:
            return
        # Record both legal states first. After interruption, either complete file is safe to resume.
        for name, (old, new) in updates.items():
            self.state[name] = [old, new]
        atomic(self.manifest, json.dumps(self.state, sort_keys=True).encode())
        for name, (_, new) in updates.items():
            atomic(self.checked(name), outputs[name])
            self.state[name] = [new]
        atomic(self.manifest, json.dumps(self.state, sort_keys=True).encode())


def run(package, mode, project=None, selected=None):
    from contextlib import nullcontext
    items = package.prefabs()
    if mode == "preview":
        items = [(path,g) for path,g in items if g == selected or path == selected]
        if len(items) != 1:
            raise ValueError("Select one prefab by its package path or GUID.")
    result = []
    with (Writer(Path(project)) if mode != "inspect" else nullcontext()) as writer:
        for path, guid in items:
            conversion = Conversion(package, guid)
            try:
                conversion.scene()
                if writer:
                    writer.write(conversion.outputs)
                status = "partial" if conversion.notes else "full"
            except (ValueError, yaml.YAMLError, KeyError, TypeError, IndexError, AttributeError, RecursionError) as error:
                status = "skipped"
                conversion.notes.append(str(error) or type(error).__name__)
            result.append(dict(path=path, guid=guid, status=status, notes=conversion.notes))
    counts = Counter(r["status"] for r in result)
    return {"mode":mode, "counts":{k:counts[k] for k in ("full","partial","skipped")}, "prefabs":result}


def gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    window = tk.Tk()
    window.title("SELODev Prefab Packager")
    frame = ttk.Frame(window, padding=12)
    frame.pack(fill="both", expand=True)
    selected = tk.StringVar()
    package = None
    paths = ttk.Combobox(frame, state="readonly", textvariable=selected, width=75)
    logs = tk.Text(frame, width=92, height=24, wrap="word")

    def show(report):
        logs.delete("1.0", "end")
        logs.insert("end", "   ".join(f"{v} {k}" for k,v in report["counts"].items())+"\n")
        for row in report["prefabs"]:
            logs.insert("end", f'\n{row["status"].upper()}   {row["path"]}\n')
            for note in row["notes"]:
                logs.insert("end", "    "+note+"\n")

    def inspect():
        nonlocal package
        name = filedialog.askopenfilename(filetypes=[("Unity package","*.unitypackage"),("All files","*")])
        if not name:
            return
        try:
            new = Package(name)
            if package:
                package.close()
            package = new
            report = run(package, "inspect")
            names = [p for p,_ in package.prefabs()]
            paths.configure(values=names)
            selected.set(names[0] if names else "")
            show(report)
        except Exception as error:
            messagebox.showerror("Package inspection", str(error))

    def convert(mode):
        if not package or not selected.get():
            return
        project = filedialog.askdirectory(title="Choose your Godot project folder")
        if project:
            try:
                show(run(package, mode, project, selected.get()))
            except Exception as error:
                messagebox.showerror("Conversion", str(error))

    ttk.Button(frame,text="Open Unity package…",command=inspect).pack(anchor="w")
    paths.pack(fill="x", pady=8)
    buttons = ttk.Frame(frame)
    buttons.pack(anchor="w")
    for title, mode in [("Convert selected prefab…","preview"),("Convert entire package…","batch")]:
        ttk.Button(buttons,text=title,command=lambda m=mode: convert(m)).pack(side="left")
    logs.pack(fill="both", expand=True, pady=8)
    try:
        window.mainloop()
    finally:
        if package:
            package.close()


def main():
    if len(sys.argv) == 1:
        gui()
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    for mode in ("inspect", "preview", "batch"):
        cmd = commands.add_parser(mode)
        cmd.add_argument("package", type=Path)
        if mode != "inspect":
            cmd.add_argument("project", type=Path)
        if mode == "preview":
            cmd.add_argument("prefab")
    args = parser.parse_args()
    pkg = Package(args.package)
    try:
        report = run(pkg, args.mode, getattr(args,"project",None), getattr(args,"prefab",None))
        print(json.dumps(report, indent=2))
        return int(bool(report["counts"]["skipped"]))
    finally:
        pkg.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, tarfile.TarError) as exc:
        sys.exit(str(exc))
