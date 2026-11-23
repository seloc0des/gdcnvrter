"""Pure-Python parser for Unity .unitypackage archives, .mat materials, and .prefab YAML."""

from __future__ import annotations

import os
import re
import tarfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


UNSUPPORTED_CLASS_IDS = {
    "95": "Animator",
    "114": "MonoBehaviour (C# script)",
    "183": "Cloth",
    "198": "ParticleSystem",
    "137": "SkinnedMeshRenderer",
}

SUPPORTED_CLASS_IDS = {"1", "4", "23", "33", "64", "65", "135", "136"}


@dataclass
class AssetEntry:
    guid: str
    pathname: str
    asset_bytes: Optional[bytes] = None
    meta_text: str = ""


@dataclass
class UnityMaterial:
    guid: str
    name: str
    pathname: str
    albedo_color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    metallic: float = 0.0
    smoothness: float = 0.5
    main_tex_guid: Optional[str] = None
    normal_tex_guid: Optional[str] = None
    metallic_tex_guid: Optional[str] = None
    occlusion_tex_guid: Optional[str] = None


@dataclass
class PrefabNode:
    go_id: str
    name: str
    transform_id: str
    parent_transform_id: Optional[str] = None
    children_transform_ids: List[str] = field(default_factory=list)
    local_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    local_rotation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    local_scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    mesh_guid: Optional[str] = None
    material_guids: List[str] = field(default_factory=list)
    box_collider_size: Optional[Tuple[float, float, float]] = None
    box_collider_center: Optional[Tuple[float, float, float]] = None
    has_mesh_collider: bool = False
    unsupported_components: List[str] = field(default_factory=list)


@dataclass
class UnityPrefab:
    guid: str
    name: str
    pathname: str
    nodes: Dict[str, PrefabNode] = field(default_factory=dict)  # keyed by transform_id
    root_transform_ids: List[str] = field(default_factory=list)


@dataclass
class UnityPackageData:
    assets_by_guid: Dict[str, AssetEntry]
    materials: Dict[str, UnityMaterial]
    prefabs: Dict[str, UnityPrefab]


def load_unitypackage(path: str) -> UnityPackageData:
    """Load a .unitypackage (.tar.gz) archive into memory."""
    raw: Dict[str, Dict[str, bytes]] = {}
    with tarfile.open(path, "r:gz") as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            parts = member.name.strip("./").split("/")
            if len(parts) < 2:
                continue
            guid, filename = parts[0], parts[1]
            f = tf.extractfile(member)
            if f is None:
                continue
            raw.setdefault(guid, {})[filename] = f.read()

    assets_by_guid: Dict[str, AssetEntry] = {}
    for guid, files in raw.items():
        if "pathname" not in files:
            continue
        pathname = files["pathname"].decode("utf-8", errors="replace").strip().splitlines()[0]
        meta_text = files.get("asset.meta", b"").decode("utf-8", errors="replace")
        assets_by_guid[guid] = AssetEntry(
            guid=guid,
            pathname=pathname,
            asset_bytes=files.get("asset"),
            meta_text=meta_text,
        )

    materials: Dict[str, UnityMaterial] = {}
    prefabs: Dict[str, UnityPrefab] = {}

    for guid, entry in assets_by_guid.items():
        lower = entry.pathname.lower()
        if lower.endswith(".mat") and entry.asset_bytes:
            mat = _parse_material(guid, entry.pathname, entry.asset_bytes.decode("utf-8", errors="replace"))
            materials[guid] = mat
        elif lower.endswith(".prefab") and entry.asset_bytes:
            prefab = _parse_prefab(guid, entry.pathname, entry.asset_bytes.decode("utf-8", errors="replace"))
            prefabs[guid] = prefab

    return UnityPackageData(assets_by_guid=assets_by_guid, materials=materials, prefabs=prefabs)


def _parse_vec4(text: str, key: str, default: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    m = re.search(rf"{key}:\s*\{{([^}}]+)\}}", text)
    if not m:
        return default
    body = m.group(1)
    vals = []
    for axis in ("r", "g", "b", "a"):
        am = re.search(rf"\b{axis}:\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)", body)
        if am:
            vals.append(float(am.group(1)))
    if len(vals) == 4:
        return (vals[0], vals[1], vals[2], vals[3])
    vals = []
    for axis in ("x", "y", "z", "w"):
        am = re.search(rf"\b{axis}:\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)", body)
        if am:
            vals.append(float(am.group(1)))
    return tuple(vals) if len(vals) == 4 else default  # type: ignore[return-value]


def _parse_vec3(text: str, key: str, default: Tuple[float, float, float]) -> Tuple[float, float, float]:
    m = re.search(rf"{key}:\s*\{{([^}}]+)\}}", text)
    if not m:
        return default
    body = m.group(1)
    vals = []
    for axis in ("x", "y", "z"):
        am = re.search(rf"\b{axis}:\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)", body)
        if am:
            vals.append(float(am.group(1)))
    return (vals[0], vals[1], vals[2]) if len(vals) == 3 else default


def _parse_material(guid: str, pathname: str, text: str) -> UnityMaterial:
    name_m = re.search(r"m_Name:\s*(.+)", text)
    name = name_m.group(1).strip() if name_m else os.path.splitext(os.path.basename(pathname))[0]

    def find_tex(prop: str) -> Optional[str]:
        m = re.search(rf"-\s*{prop}:\s*\n\s*m_Texture:\s*\{{[^}}]*guid:\s*([a-f0-9]{{32}})", text)
        return m.group(1) if m else None

    color = _parse_vec4(text, r"(?:_Color|_BaseColor)", (1.0, 1.0, 1.0, 1.0))
    # Look for _Color or _BaseColor inside m_Colors
    cm = re.search(r"-\s*(?:_Color|_BaseColor):\s*\{([^}]+)\}", text)
    if cm:
        color = _parse_vec4(f"_Color: {{{cm.group(1)}}}", "_Color", color)

    metallic = 0.0
    mm = re.search(r"-\s*_Metallic:\s*([-+]?\d*\.?\d+)", text)
    if mm:
        metallic = float(mm.group(1))

    smoothness = 0.5
    sm = re.search(r"-\s*(?:_Glossiness|_Smoothness):\s*([-+]?\d*\.?\d+)", text)
    if sm:
        smoothness = float(sm.group(1))

    return UnityMaterial(
        guid=guid,
        name=name,
        pathname=pathname,
        albedo_color=color,
        metallic=metallic,
        smoothness=smoothness,
        main_tex_guid=find_tex("_MainTex") or find_tex("_BaseMap"),
        normal_tex_guid=find_tex("_BumpMap"),
        metallic_tex_guid=find_tex("_MetallicGlossMap"),
        occlusion_tex_guid=find_tex("_OcclusionMap"),
    )


def _split_yaml_docs(text: str) -> List[Tuple[str, str, str]]:
    """Split Unity YAML into (class_id, file_id, body) tuples."""
    blocks = re.split(r"(?=^--- !u!\d+ &\d+)", text, flags=re.MULTILINE)
    docs = []
    for b in blocks:
        hm = re.match(r"^--- !u!(\d+) &(\d+)\s*\n(.*)", b, flags=re.DOTALL)
        if hm:
            docs.append((hm.group(1), hm.group(2), hm.group(3)))
    return docs


def _parse_prefab(guid: str, pathname: str, text: str) -> UnityPrefab:
    docs = _split_yaml_docs(text)
    game_objects: Dict[str, Tuple[str, List[str]]] = {}
    transforms: Dict[str, dict] = {}
    mesh_filters: Dict[str, Optional[str]] = {}
    mesh_renderers: Dict[str, List[str]] = {}
    box_colliders: Dict[str, Tuple[Tuple[float, float, float], Tuple[float, float, float]]] = {}
    mesh_colliders: Dict[str, bool] = {}
    unsupported_by_go: Dict[str, List[str]] = {}

    for cid, fid, body in docs:
        if cid == "1":  # GameObject
            nm = re.search(r"m_Name:\s*(.+)", body)
            name = nm.group(1).strip() if nm else f"Node_{fid}"
            comps = re.findall(r"component:\s*\{fileID:\s*(\d+)\}", body)
            game_objects[fid] = (name, comps)
        elif cid == "4":  # Transform
            gom = re.search(r"m_GameObject:\s*\{fileID:\s*(\d+)\}", body)
            go_id = gom.group(1) if gom else ""
            fm = re.search(r"m_Father:\s*\{fileID:\s*(\d+)\}", body)
            father_id = fm.group(1) if fm and fm.group(1) != "0" else None
            children = re.findall(r"-\s*\{fileID:\s*(\d+)\}", body.split("m_Children:")[-1].split("m_Father:")[0]) if "m_Children:" in body else []
            transforms[fid] = {
                "go_id": go_id,
                "father": father_id,
                "children": children,
                "pos": _parse_vec3(body, "m_LocalPosition", (0.0, 0.0, 0.0)),
                "rot": _parse_vec4(body, "m_LocalRotation", (0.0, 0.0, 0.0, 1.0)),
                "scale": _parse_vec3(body, "m_LocalScale", (1.0, 1.0, 1.0)),
            }
        elif cid == "33":  # MeshFilter
            mm = re.search(r"m_Mesh:\s*\{[^}]*guid:\s*([a-f0-9]{32})", body)
            mesh_filters[fid] = mm.group(1) if mm else None
        elif cid == "23":  # MeshRenderer
            mats = re.findall(r"-\s*\{[^}]*guid:\s*([a-f0-9]{32})", body)
            mesh_renderers[fid] = mats
        elif cid == "65":  # BoxCollider
            size = _parse_vec3(body, "m_Size", (1.0, 1.0, 1.0))
            center = _parse_vec3(body, "m_Center", (0.0, 0.0, 0.0))
            box_colliders[fid] = (size, center)
        elif cid == "64":  # MeshCollider
            mesh_colliders[fid] = True
        else:
            gom = re.search(r"m_GameObject:\s*\{fileID:\s*(\d+)\}", body)
            if gom:
                label = UNSUPPORTED_CLASS_IDS.get(cid, f"UnityClass_{cid}")
                unsupported_by_go.setdefault(gom.group(1), []).append(label)

    nodes: Dict[str, PrefabNode] = {}
    roots: List[str] = []

    for tid, tdata in transforms.items():
        go_id = tdata["go_id"]
        go_name, comp_ids = game_objects.get(go_id, (f"Node_{tid}", []))
        mesh_guid = None
        mat_guids: List[str] = []
        box_size = None
        box_center = None
        has_mc = False

        for comp_id in comp_ids:
            if comp_id in mesh_filters and mesh_filters[comp_id]:
                mesh_guid = mesh_filters[comp_id]
            if comp_id in mesh_renderers:
                mat_guids.extend(mesh_renderers[comp_id])
            if comp_id in box_colliders:
                box_size, box_center = box_colliders[comp_id]
            if comp_id in mesh_colliders:
                has_mc = True

        node = PrefabNode(
            go_id=go_id,
            name=go_name,
            transform_id=tid,
            parent_transform_id=tdata["father"],
            children_transform_ids=tdata["children"],
            local_position=tdata["pos"],
            local_rotation=tdata["rot"],
            local_scale=tdata["scale"],
            mesh_guid=mesh_guid,
            material_guids=mat_guids,
            box_collider_size=box_size,
            box_collider_center=box_center,
            has_mesh_collider=has_mc,
            unsupported_components=unsupported_by_go.get(go_id, []),
        )
        nodes[tid] = node
        if tdata["father"] is None:
            roots.append(tid)

    prefab_name = os.path.splitext(os.path.basename(pathname))[0]
    return UnityPrefab(guid=guid, name=prefab_name, pathname=pathname, nodes=nodes, root_transform_ids=roots)
