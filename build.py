"""Build a portable Python 3.10+ app with its YAML parser included."""
import argparse
from pathlib import Path
import shutil
import tempfile
import zipapp

import yaml


def build(target):
    source = Path(__file__).resolve().parent
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        stage = Path(folder)
        shutil.copyfile(source/"packager.py", stage/"packager.py")
        package = Path(yaml.__file__).parent
        shutil.copytree(package, stage/"yaml", ignore=shutil.ignore_patterns("__pycache__", "*.so", "*.pyd", "*.pyc"))
        from importlib.metadata import distribution
        dist = distribution("PyYAML")
        license_file = next(f for f in dist.files if f.name.upper() in {"LICENSE","LICENSE.TXT"})
        shutil.copyfile(dist.locate_file(license_file), stage/"PyYAML-LICENSE")
        (stage/"__main__.py").write_text('import runpy\nrunpy.run_module("packager", run_name="__main__")\n')
        zipapp.create_archive(stage, target, interpreter="/usr/bin/env python3", compressed=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, default=Path("dist/selodev-packager.pyz"), nargs="?")
    build(parser.parse_args().output)
