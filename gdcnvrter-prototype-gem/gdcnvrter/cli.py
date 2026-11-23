"""CLI entrypoint for SELODev Asset Converter (gdcnvrter)."""

from __future__ import annotations

import argparse
import json
import sys

from .diagnostics import scan_package
from .godot_writer import convert_package
from .unity_parser import load_unitypackage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gdcnvrter",
        description="SELODev Unity-to-Godot 4.7+ Asset & Prefab Converter",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="Inspect a .unitypackage and print conversion diagnostics")
    p_scan.add_argument("package", help="Path to .unitypackage file")
    p_scan.add_argument("--json", action="store_true", help="Output JSON instead of Markdown")

    p_conv = sub.add_parser("convert", help="Convert one prefab (Lite) or entire pack (Pro) to Godot 4.7+")
    p_conv.add_argument("package", help="Path to .unitypackage file")
    p_conv.add_argument("--out", required=True, help="Output directory inside Godot project")
    p_conv.add_argument("--prefab", default=None, help="Lite mode: convert only this named prefab")
    p_conv.add_argument("--overwrite", action="store_true", help="Overwrite existing .tscn scenes")

    args = parser.parse_args(argv)
    pkg = load_unitypackage(args.package)

    if args.cmd == "scan":
        report = scan_package(pkg)
        if args.json:
            payload = {
                "total_prefabs": report.total_prefabs,
                "fully_converted": report.fully_converted,
                "partially_converted": report.partially_converted,
                "skipped": report.skipped,
                "prefabs": [
                    {
                        "name": pr.prefab_name,
                        "status": pr.status,
                        "issues": [
                            {
                                "node": i.node_name,
                                "type": i.issue_type,
                                "detail": i.detail,
                                "repair": i.repair_note,
                            }
                            for i in pr.issues
                        ],
                    }
                    for pr in report.prefab_reports
                ],
            }
            print(json.dumps(payload, indent=2))
        else:
            print(report.to_markdown())
        return 0

    if args.cmd == "convert":
        res = convert_package(
            pkg,
            out_dir=args.out,
            prefab_filter=args.prefab,
            overwrite_scenes=args.overwrite,
        )
        print(
            f"Converted: {res.scan_report.fully_converted} full, "
            f"{res.scan_report.partially_converted} partial, "
            f"{res.scan_report.skipped} skipped | "
            f"Files written: {len(res.written_files)}, "
            f"Materials updated: {len(res.updated_materials)}, "
            f"Scenes preserved: {len(res.preserved_scenes)}"
        )
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
