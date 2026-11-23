"""Automated 5-case prototype verification suite matching PLAN.md."""

from __future__ import annotations

import os
import re
import tempfile
import unittest

from gdcnvrter.cli import main as cli_main
from gdcnvrter.diagnostics import scan_package
from gdcnvrter.godot_writer import convert_package
from gdcnvrter.unity_parser import load_unitypackage
from tests.fixture_builder import build_sample_unitypackage


class TestPrototypeMatrix(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.pkg_path = os.path.join(self.tmp.name, "sample_env.unitypackage")
        self.out_dir = os.path.join(self.tmp.name, "godot_proj")
        build_sample_unitypackage(self.pkg_path)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_case1_modular_prop_shared_materials(self) -> None:
        """Case 1: Modular prop with child meshes, transforms, collision, and shared material."""
        pkg = load_unitypackage(self.pkg_path)
        res = convert_package(pkg, self.out_dir, prefab_filter="ModularDoorway")
        scene_path = os.path.join(self.out_dir, "scenes", "ModularDoorway.tscn")
        mat_path = os.path.join(self.out_dir, "materials", "StoneBrick.tres")

        self.assertTrue(os.path.exists(scene_path))
        self.assertTrue(os.path.exists(mat_path))

        with open(scene_path, "r", encoding="utf-8") as f:
            tscn = f.read()
        # Shared material declared ONCE as ExtResource and referenced by BOTH Frame and DoorLeaf
        mat_ext = re.findall(r'\[ext_resource type="Material"[^\]]*path="res://materials/StoneBrick\.tres"', tscn)
        self.assertEqual(len(mat_ext), 1)
        self.assertEqual(tscn.count("surface_material_override/0 = ExtResource("), 2)
        # Child transform & BoxCollider present
        self.assertIn('[node name="Frame" type="MeshInstance3D" parent="."]', tscn)
        self.assertIn('[node name="DoorLeaf" type="MeshInstance3D" parent="."]', tscn)
        self.assertIn('[node name="CollisionShape3D" type="CollisionShape3D"', tscn)
        self.assertEqual(len(res.preserved_scenes), 0)

    def test_case2_missing_texture_and_unsupported_component(self) -> None:
        """Case 2: Diagnostic report flags missing texture & Cloth; other assets still convert."""
        pkg = load_unitypackage(self.pkg_path)
        report = scan_package(pkg)
        self.assertEqual(report.total_prefabs, 2)
        self.assertEqual(report.fully_converted, 1)
        self.assertEqual(report.partially_converted, 1)
        self.assertEqual(report.skipped, 0)

        partial = [p for p in report.prefab_reports if p.prefab_name == "BannerPartial"][0]
        issue_types = {i.issue_type for i in partial.issues}
        self.assertIn("missing_texture", issue_types)
        self.assertIn("unsupported_component", issue_types)

        convert_package(pkg, self.out_dir)
        self.assertTrue(os.path.exists(os.path.join(self.out_dir, "scenes", "ModularDoorway.tscn")))
        self.assertTrue(os.path.exists(os.path.join(self.out_dir, "scenes", "BannerPartial.tscn")))

    def test_case3_reimport_after_material_edit_preserves_uid_and_scene(self) -> None:
        """Case 3: Editing a source material updates .tres in-place without duplicates or clobbering scene."""
        pkg1 = load_unitypackage(self.pkg_path)
        convert_package(pkg1, self.out_dir)

        scene_path = os.path.join(self.out_dir, "scenes", "ModularDoorway.tscn")
        mat_path = os.path.join(self.out_dir, "materials", "StoneBrick.tres")
        with open(mat_path, "r", encoding="utf-8") as f:
            uid_before = re.search(r'uid="(uid://[a-z0-9]+)"', f.read()).group(1)

        # Simulate user edit in .tscn
        with open(scene_path, "a", encoding="utf-8") as f:
            f.write("\n# User scene note\n")

        # Edit source material color and reimport in safe mode (overwrite_scenes=False)
        pkg2_path = os.path.join(self.tmp.name, "sample_env_v2.unitypackage")
        build_sample_unitypackage(pkg2_path, stone_albedo=(0.2, 0.4, 0.9, 1.0))
        pkg2 = load_unitypackage(pkg2_path)
        res2 = convert_package(pkg2, self.out_dir, overwrite_scenes=False)

        self.assertIn(mat_path, res2.updated_materials)
        self.assertIn(scene_path, res2.preserved_scenes)
        with open(mat_path, "r", encoding="utf-8") as f:
            mat_after = f.read()
        self.assertIn("Color(0.2, 0.4, 0.9, 1)", mat_after)
        self.assertIn(uid_before, mat_after)
        with open(scene_path, "r", encoding="utf-8") as f:
            self.assertIn("# User scene note", f.read())
        # No duplicate .tres files
        self.assertEqual(sorted(os.listdir(os.path.join(self.out_dir, "materials"))), ["MissingBanner.tres", "StoneBrick.tres"])

    def test_case4_interrupted_batch_recovery(self) -> None:
        """Case 4: Simulated mid-batch interruption leaves prior files valid and retry finishes cleanly."""
        pkg = load_unitypackage(self.pkg_path)

        def abort_on_second(name: str) -> None:
            if os.path.exists(os.path.join(self.out_dir, "scenes")):
                raise RuntimeError("Simulated power loss")

        with self.assertRaises(RuntimeError):
            convert_package(pkg, self.out_dir, progress_hook=abort_on_second)

        # Retry without error
        res = convert_package(pkg, self.out_dir)
        scenes = sorted(os.listdir(os.path.join(self.out_dir, "scenes")))
        self.assertEqual(scenes, ["BannerPartial.tscn", "ModularDoorway.tscn"])
        self.assertEqual(len(res.preserved_scenes), 1)

    def test_case5_cli_clean_workflow(self) -> None:
        """Case 5: End-to-end CLI scan + Lite single-prefab convert + full batch."""
        self.assertEqual(cli_main(["scan", self.pkg_path, "--json"]), 0)
        self.assertEqual(cli_main(["convert", self.pkg_path, "--out", self.out_dir, "--prefab", "ModularDoorway"]), 0)
        self.assertTrue(os.path.exists(os.path.join(self.out_dir, "scenes", "ModularDoorway.tscn")))
        self.assertFalse(os.path.exists(os.path.join(self.out_dir, "scenes", "BannerPartial.tscn")))


if __name__ == "__main__":
    unittest.main()
