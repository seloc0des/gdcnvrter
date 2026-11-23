"""Self-authored .unitypackage fixture builder for automated CI and prototype verification."""

from __future__ import annotations

import io
import tarfile
from typing import Dict


GUID_DOOR_MESH = "11111111111111111111111111111111"
GUID_FRAME_MESH = "22222222222222222222222222222222"
GUID_TEX_ALBEDO = "33333333333333333333333333333333"
GUID_MAT_STONE = "44444444444444444444444444444444"
GUID_PREFAB_DOORWAY = "55555555555555555555555555555555"

GUID_MAT_MISSING_TEX = "66666666666666666666666666666666"
GUID_TEX_MISSING = "77777777777777777777777777777777"
GUID_PREFAB_PARTIAL = "88888888888888888888888888888888"


DOOR_OBJ = b"""# Self-authored unit doorway leaf
v -0.5 0.0 -0.05
v  0.5 0.0 -0.05
v  0.5 2.0 -0.05
v -0.5 2.0 -0.05
f 1 2 3 4
"""

FRAME_OBJ = b"""# Self-authored doorway frame
v -0.7 0.0 -0.1
v  0.7 0.0 -0.1
v  0.7 2.2 -0.1
v -0.7 2.2 -0.1
f 1 2 3 4
"""

# Minimal valid 1x1 PNG
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc`\x00\x00\x00\x02\x00\x01"
    b"\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
)


def make_material_yaml(name: str, tex_guid: str, albedo_rgb=(0.8, 0.75, 0.7, 1.0)) -> bytes:
    r, g, b, a = albedo_rgb
    return f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  m_Name: {name}
  m_SavedProperties:
    m_TexEnvs:
    - _MainTex:
        m_Texture: {{fileID: 2800000, guid: {tex_guid}, type: 3}}
    m_Floats:
    - _Glossiness: 0.35
    - _Metallic: 0.1
    m_Colors:
    - _Color: {{r: {r}, g: {g}, b: {b}, a: {a}}}
""".encode("utf-8")


PREFAB_DOORWAY_YAML = f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!1 &100000
GameObject:
  m_Name: ModularDoorway
  m_Component:
  - component: {{fileID: 400000}}
--- !u!4 &400000
Transform:
  m_GameObject: {{fileID: 100000}}
  m_LocalRotation: {{x: 0, y: 0, z: 0, w: 1}}
  m_LocalPosition: {{x: 0, y: 0, z: 0}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
  m_Children:
  - {{fileID: 400001}}
  - {{fileID: 400002}}
  m_Father: {{fileID: 0}}
--- !u!1 &100001
GameObject:
  m_Name: Frame
  m_Component:
  - component: {{fileID: 400001}}
  - component: {{fileID: 330001}}
  - component: {{fileID: 230001}}
  - component: {{fileID: 650001}}
--- !u!4 &400001
Transform:
  m_GameObject: {{fileID: 100001}}
  m_LocalRotation: {{x: 0, y: 0, z: 0, w: 1}}
  m_LocalPosition: {{x: 0, y: 0, z: 0}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
  m_Children: []
  m_Father: {{fileID: 400000}}
--- !u!33 &330001
MeshFilter:
  m_GameObject: {{fileID: 100001}}
  m_Mesh: {{fileID: 4300000, guid: {GUID_FRAME_MESH}, type: 3}}
--- !u!23 &230001
MeshRenderer:
  m_GameObject: {{fileID: 100001}}
  m_Materials:
  - {{fileID: 2100000, guid: {GUID_MAT_STONE}, type: 2}}
--- !u!65 &650001
BoxCollider:
  m_GameObject: {{fileID: 100001}}
  m_Size: {{x: 1.4, y: 2.2, z: 0.2}}
  m_Center: {{x: 0, y: 1.1, z: 0}}
--- !u!1 &100002
GameObject:
  m_Name: DoorLeaf
  m_Component:
  - component: {{fileID: 400002}}
  - component: {{fileID: 330002}}
  - component: {{fileID: 230002}}
--- !u!4 &400002
Transform:
  m_GameObject: {{fileID: 100002}}
  m_LocalRotation: {{x: 0, y: 0, z: 0, w: 1}}
  m_LocalPosition: {{x: 0.5, y: 0, z: 0}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
  m_Children: []
  m_Father: {{fileID: 400000}}
--- !u!33 &330002
MeshFilter:
  m_GameObject: {{fileID: 100002}}
  m_Mesh: {{fileID: 4300000, guid: {GUID_DOOR_MESH}, type: 3}}
--- !u!23 &230002
MeshRenderer:
  m_GameObject: {{fileID: 100002}}
  m_Materials:
  - {{fileID: 2100000, guid: {GUID_MAT_STONE}, type: 2}}
""".encode("utf-8")


PREFAB_PARTIAL_YAML = f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!1 &200000
GameObject:
  m_Name: BannerPartial
  m_Component:
  - component: {{fileID: 410000}}
  - component: {{fileID: 330010}}
  - component: {{fileID: 230010}}
  - component: {{fileID: 1830010}}
--- !u!4 &410000
Transform:
  m_GameObject: {{fileID: 200000}}
  m_LocalRotation: {{x: 0, y: 0, z: 0, w: 1}}
  m_LocalPosition: {{x: 0, y: 1.5, z: 0}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
  m_Children: []
  m_Father: {{fileID: 0}}
--- !u!33 &330010
MeshFilter:
  m_GameObject: {{fileID: 200000}}
  m_Mesh: {{fileID: 4300000, guid: {GUID_DOOR_MESH}, type: 3}}
--- !u!23 &230010
MeshRenderer:
  m_GameObject: {{fileID: 200000}}
  m_Materials:
  - {{fileID: 2100000, guid: {GUID_MAT_MISSING_TEX}, type: 2}}
--- !u!183 &1830010
Cloth:
  m_GameObject: {{fileID: 200000}}
""".encode("utf-8")


def build_sample_unitypackage(out_path: str, stone_albedo=(0.8, 0.75, 0.7, 1.0)) -> None:
    """Write a self-authored .unitypackage containing a clean doorway + a partial banner."""
    entries: Dict[str, Dict[str, bytes]] = {
        GUID_DOOR_MESH: {"pathname": b"Assets/Env/Meshes/DoorLeaf.obj", "asset": DOOR_OBJ},
        GUID_FRAME_MESH: {"pathname": b"Assets/Env/Meshes/Frame.obj", "asset": FRAME_OBJ},
        GUID_TEX_ALBEDO: {"pathname": b"Assets/Env/Textures/Stone_Albedo.png", "asset": TINY_PNG},
        GUID_MAT_STONE: {"pathname": b"Assets/Env/Materials/StoneBrick.mat", "asset": make_material_yaml("StoneBrick", GUID_TEX_ALBEDO, stone_albedo)},
        GUID_PREFAB_DOORWAY: {"pathname": b"Assets/Env/Prefabs/ModularDoorway.prefab", "asset": PREFAB_DOORWAY_YAML},
        GUID_MAT_MISSING_TEX: {"pathname": b"Assets/Env/Materials/MissingBanner.mat", "asset": make_material_yaml("MissingBanner", GUID_TEX_MISSING)},
        GUID_PREFAB_PARTIAL: {"pathname": b"Assets/Env/Prefabs/BannerPartial.prefab", "asset": PREFAB_PARTIAL_YAML},
    }

    with tarfile.open(out_path, "w:gz") as tf:
        for guid, files in entries.items():
            for fname, data in files.items():
                ti = tarfile.TarInfo(name=f"{guid}/{fname}")
                ti.size = len(data)
                tf.addfile(ti, io.BytesIO(data))
