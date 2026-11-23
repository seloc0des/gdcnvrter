"""Generate redistributable test assets using only authored geometry and Unity text."""
import argparse
import io
import tarfile

import yaml

DOOR = "aed" + "1"*29
MAT = "abc" + "2"*29
BROKEN = "bad" + "3"*29
SKIP = "def" + "4"*29
MISSING = "fed" + "5"*29


def ref(value):
    return {"fileID":value}


def doc(tag, ident, name, data):
    return f"--- !u!{tag} &{ident}\n" + yaml.safe_dump({name:data}, sort_keys=False)


def doorway(broken=False):
    output = "%YAML 1.1\n%TAG !u! tag:unity3d.com,2011:\n"
    for i,(name,pos,scale) in enumerate([
        ("Doorway",(0,0,0),(1,1,1)), ("Left",(-1,1,0),(.4,2,.5)),
        ("Right",(1,1,0),(.4,2,.5)), ("Lintel",(0,2.2,0),(2.4,.4,.5))]):
        k = 10*i+1
        components = [k+1] + ([k+2,k+3,k+4] if i else [])
        if broken and i == 0:
            components.append(90)
            output += doc(114,90,"MonoBehaviour",{"m_GameObject":ref(1)})
        output += doc(1,k,"GameObject",{"m_Name":name,"m_Component":[{"component":ref(c)} for c in components]})
        output += doc(4,k+1,"Transform",{"m_GameObject":ref(k),"m_Father":ref(2 if i else 0),
            "m_LocalPosition":dict(zip("xyz",pos)), "m_LocalRotation":dict(zip("xyzw",(0,0,0,1))),
            "m_LocalScale":dict(zip("xyz",scale)), "m_Children":[] if i else [ref(12),ref(22),ref(32)]})
        if i:
            output += doc(33,k+2,"MeshFilter",{"m_Mesh":{"fileID":10202,"guid":"0000000000000000e000000000000000"}})
            output += doc(23,k+3,"MeshRenderer",{"m_Materials":[{"fileID":2100000,"guid":MAT}]})
            output += doc(65,k+4,"BoxCollider",{"m_Size":dict.fromkeys("xyz",1),"m_Center":dict.fromkeys("xyz",0)})
    return output


def build(path, red=.2, incomplete=False):
    props = {"m_Colors":[{"_Color":{"r":red,"g":.3,"b":.4,"a":1}}]}
    assets = [(DOOR,"Doorway.prefab",doorway()), (MAT,"Stone.mat",doc(21,2100000,"Material",{"m_SavedProperties":props}))]
    if incomplete:
        props = {"m_TexEnvs":[{"_MainTex":{"m_Texture":{"fileID":2800000,"guid":MISSING}}}]}
        damaged_mat = "aca" + "6"*29
        assets.extend([(BROKEN,"Damaged.prefab",doorway(True).replace(MAT,damaged_mat)),
                       (damaged_mat,"Damaged.mat",doc(21,2100000,"Material",{"m_SavedProperties":props})),
                       (SKIP,"Binary.prefab","Binary fixture")])
    with tarfile.open(path,"w:gz") as tar:
        for guid, name, source in assets:
            for member, value in [("pathname","Assets/Fixture/"+name),("asset",source)]:
                data = value.encode()
                entry = tarfile.TarInfo(guid+"/"+member)
                entry.size = len(data)
                tar.addfile(entry,io.BytesIO(data))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--incomplete",action="store_true")
    args = parser.parse_args()
    build(args.output,incomplete=args.incomplete)
