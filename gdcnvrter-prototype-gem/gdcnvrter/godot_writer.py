"""Godot 4.7+ .tres / .tscn writer with deterministic UIDs, atomic writes, and safe reimport."""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Set, Tuple

from .diagnostics import PackageScanReport, PrefabReport, scan_package
from .unity_parser import PrefabNode, UnityMaterial, UnityPackageData, UnityPrefab


def deterministic_uid(key: str) -> str:
    """Generate a deterministic Godot-style uid:// string from a stable key."""
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    num = int.from_bytes(digest[:8], "big")
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    chars = []
    for _ in range(13):
        num, rem = divmod(num, 36)
        chars.append(alphabet[rem])
    return "uid://" + "".join(reversed(chars))


def _atomic_write_bytes(dest: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = f"{dest}.tmp.{os.getpid()}"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, dest)


def _atomic_write_text(dest: str, text: str) -> None:
    _atomic_write_bytes(dest, text.encode("utf-8"))


def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in ("_", "-", ".") else "_" for c in name).strip("_") or "Asset"


def _quat_to_basis(q: Tuple[float, float, float, float]) -> Tuple[float, ...]:
    """Convert Unity quaternion (x,y,z,w) to Godot 3x3 rotation basis (with Z-axis handedness flip)."""
    x, y, z, w = q
    # Flip handedness for Unity (left-handed Y-up) -> Godot (right-handed Y-up): negate Z on quaternion
    z = -z
    norm = math.sqrt(x * x + y * y + z * z + w * w) or 1.0
    x, y, z, w = x / norm, y / norm, z / norm, w / norm
    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z
    return (
        1.0 - 2.0 * (yy + zz), 2.0 * (xy - wz), 2.0 * (xz + wy),
        2.0 * (xy + wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz - wx),
        2.0 * (xz - wy), 2.0 * (yz + wx), 1.0 - 2.0 * (xx + yy),
    )


def _transform3d_str(
    pos: Tuple[float, float, float],
    rot: Tuple[float, float, float, float],
    scale: Tuple[float, float, float],
) -> str:
    b = _quat_to_basis(rot)
    sx, sy, sz = scale
    # Apply scale to basis columns and negate Z position for right-handed Godot space
    cols = (
        b[0] * sx, b[1] * sy, b[2] * sz,
        b[3] * sx, b[4] * sy, b[5] * sz,
        b[6] * sx, b[7] * sy, b[8] * sz,
        pos[0], pos[1], -pos[2],
    )
    formatted = ", ".join(f"{v:.6g}" for v in cols)
    return f"Transform3D({formatted})"


@dataclass
class ConversionResult:
    scan_report: PackageScanReport
    written_files: List[str]
    updated_materials: List[str]
    preserved_scenes: List[str]


def convert_package(
    pkg: UnityPackageData,
    out_dir: str,
    prefab_filter: Optional[str] = None,
    overwrite_scenes: bool = False,
    progress_hook: Optional[Callable[[str], None]] = None,
) -> ConversionResult:
    """Convert one prefab (Lite mode) or all prefabs (Pro batch mode) into Godot 4.7+ files."""
    scan = scan_package(pkg)
    written: List[str] = []
    updated_mats: List[str] = []
    preserved_scenes: List[str] = []

    state_path = os.path.join(out_dir, ".gdcnvrter_state.json")
    state: Dict[str, dict] = {}
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}

    target_reports: List[PrefabReport] = []
    for pr in scan.prefab_reports:
        if prefab_filter and pr.prefab_name.lower() != prefab_filter.lower():
            continue
        if pr.status == "skipped":
            continue
        target_reports.append(pr)

    # Collect referenced textures, meshes, and materials across target prefabs
    needed_mats: Set[str] = set()
    needed_assets: Set[str] = set()
    for pr in target_reports:
        prefab = pkg.prefabs[pr.prefab_guid]
        for node in prefab.nodes.values():
            if node.mesh_guid and node.mesh_guid in pkg.assets_by_guid:
                needed_assets.add(node.mesh_guid)
            for mg in node.material_guids:
                if mg in pkg.materials:
                    needed_mats.add(mg)
                    mat = pkg.materials[mg]
                    for tg in (mat.main_tex_guid, mat.normal_tex_guid, mat.metallic_tex_guid, mat.occlusion_tex_guid):
                        if tg and tg in pkg.assets_by_guid:
                            needed_assets.add(tg)

    # 1. Extract binary assets (meshes & textures) atomically
    res_paths: Dict[str, str] = {}
    for guid in sorted(needed_assets):
        entry = pkg.assets_by_guid[guid]
        rel = os.path.join("assets", _safe_name(os.path.basename(entry.pathname)))
        # Disambiguate collisions cleanly by short guid if needed
        dest = os.path.join(out_dir, rel)
        res_path = f"res://{rel.replace(os.sep, '/')}"
        res_paths[guid] = res_path
        if entry.asset_bytes is not None:
            if not os.path.exists(dest) or overwrite_scenes:
                _atomic_write_bytes(dest, entry.asset_bytes)
                written.append(dest)

    # 2. Write/update shared .tres StandardMaterial3D files (always safe to update in-place, preserving UID)
    mat_res_paths: Dict[str, str] = {}
    for mguid in sorted(needed_mats):
        mat = pkg.materials[mguid]
        rel = os.path.join("materials", f"{_safe_name(mat.name)}.tres")
        dest = os.path.join(out_dir, rel)
        res_path = f"res://{rel.replace(os.sep, '/')}"
        mat_res_paths[mguid] = res_path
        mat_uid = deterministic_uid(f"mat:{mguid}")
        tres_text = _render_material_tres(mat, mat_uid, res_paths)

        existed = os.path.exists(dest)
        old_text = open(dest, "r", encoding="utf-8").read() if existed else None
        if old_text != tres_text:
            _atomic_write_text(dest, tres_text)
            written.append(dest)
            if existed:
                updated_mats.append(dest)

    # 3. Write .tscn scenes (preserving user-edited scenes unless overwrite_scenes=True)
    for pr in target_reports:
        prefab = pkg.prefabs[pr.prefab_guid]
        rel = os.path.join("scenes", f"{_safe_name(prefab.name)}.tscn")
        dest = os.path.join(out_dir, rel)
        if progress_hook:
            progress_hook(prefab.name)

        if os.path.exists(dest) and not overwrite_scenes:
            preserved_scenes.append(dest)
            continue

        scene_uid = deterministic_uid(f"scene:{prefab.guid}")
        tscn_text = _render_prefab_tscn(prefab, scene_uid, res_paths, mat_res_paths)
        _atomic_write_text(dest, tscn_text)
        written.append(dest)
        state[prefab.guid] = {"scene": rel, "uid": scene_uid, "status": pr.status}

    _atomic_write_text(state_path, json.dumps(state, indent=2))
    return ConversionResult(
        scan_report=scan,
        written_files=written,
        updated_materials=updated_mats,
        preserved_scenes=preserved_scenes,
    )


def _render_material_tres(mat: UnityMaterial, mat_uid: str, res_paths: Dict[str, str]) -> str:
    ext_lines: List[str] = []
    tex_ext_ids: Dict[str, str] = {}
    idx = 1
    for label, tguid in (
        ("albedo", mat.main_tex_guid),
        ("normal", mat.normal_tex_guid),
        ("metallic", mat.metallic_tex_guid),
        ("ao", mat.occlusion_tex_guid),
    ):
        if tguid and tguid in res_paths:
            eid = f"{idx}_tex"
            t_uid = deterministic_uid(f"tex:{tguid}")
            ext_lines.append(f'[ext_resource type="Texture2D" uid="{t_uid}" path="{res_paths[tguid]}" id="{eid}"]')
            tex_ext_ids[label] = eid
            idx += 1

    load_steps = len(ext_lines) + 1
    r, g, b, a = mat.albedo_color
    roughness = max(0.0, min(1.0, 1.0 - mat.smoothness))

    lines = [f'[gd_resource type="StandardMaterial3D" load_steps={load_steps} format=3 uid="{mat_uid}"]', ""]
    lines.extend(ext_lines)
    if ext_lines:
        lines.append("")
    lines.append("[resource]")
    lines.append(f'resource_name = "{mat.name}"')
    lines.append(f"albedo_color = Color({r:.4g}, {g:.4g}, {b:.4g}, {a:.4g})")
    if "albedo" in tex_ext_ids:
        lines.append(f'albedo_texture = ExtResource("{tex_ext_ids["albedo"]}")')
    lines.append(f"metallic = {mat.metallic:.4g}")
    if "metallic" in tex_ext_ids:
        lines.append(f'metallic_texture = ExtResource("{tex_ext_ids["metallic"]}")')
    lines.append(f"roughness = {roughness:.4g}")
    if "normal" in tex_ext_ids:
        lines.append("normal_enabled = true")
        lines.append(f'normal_texture = ExtResource("{tex_ext_ids["normal"]}")')
    if "ao" in tex_ext_ids:
        lines.append("ao_enabled = true")
        lines.append(f'ao_texture = ExtResource("{tex_ext_ids["ao"]}")')
    lines.append("")
    return "\n".join(lines)


def _render_prefab_tscn(
    prefab: UnityPrefab,
    scene_uid: str,
    res_paths: Dict[str, str],
    mat_res_paths: Dict[str, str],
) -> str:
    ext_lines: List[str] = []
    ext_id_by_guid: Dict[str, str] = {}
    sub_lines: List[str] = []
    sub_id_by_node: Dict[str, str] = {}
    ext_counter = 1
    sub_counter = 1

    # Register unique external resources (shared materials stay shared!)
    for node in prefab.nodes.values():
        if node.mesh_guid and node.mesh_guid in res_paths and node.mesh_guid not in ext_id_by_guid:
            eid = f"{ext_counter}_mesh"
            m_uid = deterministic_uid(f"mesh:{node.mesh_guid}")
            ext_lines.append(f'[ext_resource type="PackedScene" uid="{m_uid}" path="{res_paths[node.mesh_guid]}" id="{eid}"]')
            ext_id_by_guid[node.mesh_guid] = eid
            ext_counter += 1
        for mg in node.material_guids:
            if mg in mat_res_paths and mg not in ext_id_by_guid:
                eid = f"{ext_counter}_mat"
                mat_uid = deterministic_uid(f"mat:{mg}")
                ext_lines.append(f'[ext_resource type="Material" uid="{mat_uid}" path="{mat_res_paths[mg]}" id="{eid}"]')
                ext_id_by_guid[mg] = eid
                ext_counter += 1
        if node.box_collider_size is not None:
            sid = f"BoxShape3D_{sub_counter}"
            sx, sy, sz = node.box_collider_size
            sub_lines.append(f'[sub_resource type="BoxShape3D" id="{sid}"]')
            sub_lines.append(f"size = Vector3({sx:.6g}, {sy:.6g}, {sz:.6g})")
            sub_lines.append("")
            sub_id_by_node[node.transform_id] = sid
            sub_counter += 1

    load_steps = len(ext_lines) + len(sub_id_by_node) + 1
    lines = [f'[gd_scene load_steps={load_steps} format=3 uid="{scene_uid}"]', ""]
    lines.extend(ext_lines)
    if ext_lines:
        lines.append("")
    lines.extend(sub_lines)

    # Traverse hierarchy from roots
    def emit_node(tid: str, parent_path: Optional[str], is_root: bool) -> None:
        node = prefab.nodes[tid]
        node_name = _safe_name(node.name)
        t_str = _transform3d_str(node.local_position, node.local_rotation, node.local_scale)

        if is_root:
            lines.append(f'[node name="{node_name}" type="Node3D"]')
            lines.append(f"transform = {t_str}")
            cur_path = "."
        else:
            node_type = "MeshInstance3D" if node.mesh_guid else "Node3D"
            lines.append(f'[node name="{node_name}" type="{node_type}" parent="{parent_path}"]')
            lines.append(f"transform = {t_str}")
            for slot_idx, mg in enumerate(node.material_guids):
                if mg in ext_id_by_guid:
                    lines.append(f'surface_material_override/{slot_idx} = ExtResource("{ext_id_by_guid[mg]}")')
            cur_path = node_name if parent_path == "." else f"{parent_path}/{node_name}"

        lines.append("")

        # Attach StaticBody3D + CollisionShape3D if BoxCollider present
        if tid in sub_id_by_node:
            cx, cy, cz = node.box_collider_center or (0.0, 0.0, 0.0)
            lines.append(f'[node name="StaticBody3D" type="StaticBody3D" parent="{cur_path}"]')
            lines.append("")
            sb_path = "StaticBody3D" if cur_path == "." else f"{cur_path}/StaticBody3D"
            lines.append(f'[node name="CollisionShape3D" type="CollisionShape3D" parent="{sb_path}"]')
            lines.append(f"transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, {cx:.6g}, {cy:.6g}, {-cz:.6g})")
            lines.append(f'shape = SubResource("{sub_id_by_node[tid]}")')
            lines.append("")

        for child_tid in node.children_transform_ids:
            if child_tid in prefab.nodes:
                emit_node(child_tid, cur_path, is_root=False)

    if len(prefab.root_transform_ids) == 1:
        emit_node(prefab.root_transform_ids[0], None, is_root=True)
    else:
        lines.append(f'[node name="{_safe_name(prefab.name)}" type="Node3D"]')
        lines.append("")
        for rtid in prefab.root_transform_ids:
            emit_node(rtid, ".", is_root=False)

    return "\n".join(lines)
