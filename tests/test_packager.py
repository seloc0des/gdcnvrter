import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import packager as p
from fixture import build, DOOR, MAT, MISSING


class Pilot(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root/"source.unitypackage"
        (self.root/"project.godot").write_text('config_version=5\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
        self.out = self.root/p.ROOT

    def convert(self, mode, **params):
        build(self.src, **params)
        package = p.Package(self.src)
        try:
            return p.run(package, mode, self.root, DOOR)
        finally:
            package.close()

    def test_diagnostics_and_selection(self):
        report = self.convert("inspect", incomplete=True)
        self.assertEqual(report["counts"], {"full":1,"partial":1,"skipped":1})
        self.assertFalse(self.out.exists())
        notes = str(report["prefabs"])
        self.assertIn(MISSING, notes)
        self.assertIn("MonoBehaviour", notes)
        self.convert("preview", incomplete=True)
        self.assertEqual(len(list(self.out.glob("scenes/*"))), 1)

    def test_conflict(self):
        self.convert("batch")
        mat = self.out/f"materials/{MAT}.tres"
        mat.write_bytes(b"user change")
        self.assertEqual(self.convert("batch", red=.7)["counts"]["skipped"],1)
        self.assertEqual(mat.read_bytes(),b"user change")

    def test_interruption(self):
        self.convert("batch")
        original = p.atomic
        def interrupt(path,data):
            original(path,data)
            if path.suffix == ".tres":
                raise InterruptedError()
        with patch.object(p,"atomic",interrupt), self.assertRaises(InterruptedError):
            self.convert("batch", red=.7)
        self.assertEqual(self.convert("batch", red=.7)["counts"]["full"],1)
        self.assertEqual(len(list(self.out.glob("materials/*"))),1)

    @unittest.skipUnless(shutil.which("godot"), "Godot executable required")
    def test_godot_reopen(self):
        scene = f"res://{p.ROOT}/scenes/{DOOR}.tscn"
        (self.root/"Placed.tscn").write_text('[gd_scene format=3]\n'
            +f'[ext_resource type="PackedScene" uid="{p.uid(DOOR,"scene")}" path="{scene}" id="1"]\n'
            +'[node name="Placed" type="Node3D"]\n[node name="Doorway" parent="." instance=ExtResource("1")]\n')
        for red in (.2,.7):
            self.assertEqual(self.convert("batch", red=red)["counts"]["full"],1)
            for args in [["--editor","--import"],["--script",str(Path(__file__).with_name("check_scene.gd").resolve())]]:
                cmd = ["godot","--headless","--path",str(self.root),*args]
                r = subprocess.run(cmd, env={**os.environ,"EXPECTED_RED":str(red)}, capture_output=True,text=True,timeout=45)
                log = r.stdout+r.stderr
                self.assertEqual(r.returncode,0,log)
                self.assertNotIn("ERROR:",log)
                self.assertNotIn("invalid UID",log)

    def test_texture_and_obj_import(self):
        from fixture import doc, doorway
        import base64
        import io
        import tarfile
        mesh_guid = "01234567890123456789012345678901"
        tex_guid = "ffa"+"7"*29
        material = doc(21,2100000,"Material",{"m_SavedProperties":{"m_TexEnvs":[
            {"_MainTex":{"m_Texture":{"fileID":2800000,"guid":tex_guid}}}]}})
        prefab = doorway().replace("10202","4300000").replace("0000000000000000e000000000000000",mesh_guid)
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC")
        assets = [(DOOR,"Mesh.prefab",prefab.encode()),(MAT,"Color.mat",material.encode()),
                  (mesh_guid,"Face.obj",b"v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"),
                  (tex_guid,"White.png",png)]
        with tarfile.open(self.src,"w:gz") as archive:
            for guid,name,data in assets:
                for role,value in [("asset",data),("pathname",name.encode())]:
                    info = tarfile.TarInfo(guid+"/"+role)
                    info.size = len(value)
                    archive.addfile(info,io.BytesIO(value))
        package = p.Package(self.src)
        try:
            report = p.run(package,"batch",self.root)
        finally:
            package.close()
        self.assertEqual(report["counts"]["partial"],1)
        self.assertEqual(len(list(self.out.glob("meshes/*.obj"))),1)
        self.assertEqual((self.out/f"textures/{tex_guid}.png").read_bytes(),png)
        if shutil.which("godot"):
            for args in [["--editor","--import"],[f"res://{p.ROOT}/scenes/{DOOR}.tscn","--quit-after","3"]]:
                result = subprocess.run(["godot","--headless","--path",str(self.root),*args],
                                        capture_output=True,text=True,timeout=45)
                self.assertEqual(result.returncode,0)
                self.assertNotIn("ERROR:",result.stdout+result.stderr)
