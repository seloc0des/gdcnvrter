"""Conversion diagnostics: counts fully converted, partially converted, and skipped prefabs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .unity_parser import UnityPackageData, UnityPrefab


@dataclass
class PrefabIssue:
    node_name: str
    issue_type: str  # "missing_texture", "missing_mesh", "missing_material", "unsupported_component"
    detail: str
    repair_note: str


@dataclass
class PrefabReport:
    prefab_guid: str
    prefab_name: str
    pathname: str
    status: str  # "full", "partial", "skipped"
    issues: List[PrefabIssue] = field(default_factory=list)


@dataclass
class PackageScanReport:
    total_prefabs: int
    fully_converted: int
    partially_converted: int
    skipped: int
    prefab_reports: List[PrefabReport] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            f"# Package Scan Report",
            f"- **Total Prefabs:** {self.total_prefabs}",
            f"- **Fully Converted:** {self.fully_converted}",
            f"- **Partially Converted:** {self.partially_converted}",
            f"- **Skipped:** {self.skipped}",
            "",
        ]
        for pr in self.prefab_reports:
            lines.append(f"## {pr.prefab_name} (`{pr.status.upper()}`)")
            lines.append(f"- Source: `{pr.pathname}`")
            if not pr.issues:
                lines.append("- All meshes, shared materials, and colliders resolved cleanly.")
            else:
                for iss in pr.issues:
                    lines.append(
                        f"- **{iss.node_name}** [{iss.issue_type}]: {iss.detail} — *Repair:* {iss.repair_note}"
                    )
            lines.append("")
        return "\n".join(lines)


def diagnose_prefab(pkg: UnityPackageData, prefab: UnityPrefab) -> PrefabReport:
    issues: List[PrefabIssue] = []

    if not prefab.nodes:
        return PrefabReport(
            prefab_guid=prefab.guid,
            prefab_name=prefab.name,
            pathname=prefab.pathname,
            status="skipped",
            issues=[
                PrefabIssue(
                    node_name=prefab.name,
                    issue_type="empty_prefab",
                    detail="No Transform/GameObject nodes found in prefab YAML.",
                    repair_note="Re-export the prefab from Unity as a standard static prefab.",
                )
            ],
        )

    for node in prefab.nodes.values():
        if node.mesh_guid and node.mesh_guid not in pkg.assets_by_guid:
            issues.append(
                PrefabIssue(
                    node_name=node.name,
                    issue_type="missing_mesh",
                    detail=f"Mesh GUID {node.mesh_guid} not found in package.",
                    repair_note="Include the source FBX/OBJ mesh in the .unitypackage or assign a mesh in Godot.",
                )
            )
        for mguid in node.material_guids:
            if mguid not in pkg.materials:
                issues.append(
                    PrefabIssue(
                        node_name=node.name,
                        issue_type="missing_material",
                        detail=f"Material GUID {mguid} not found in package.",
                        repair_note="Include the .mat asset in the package or assign a StandardMaterial3D in Godot.",
                    )
                )
            else:
                mat = pkg.materials[mguid]
                for tex_label, tguid in (
                    ("albedo", mat.main_tex_guid),
                    ("normal", mat.normal_tex_guid),
                    ("metallic", mat.metallic_tex_guid),
                    ("occlusion", mat.occlusion_tex_guid),
                ):
                    if tguid and tguid not in pkg.assets_by_guid:
                        issues.append(
                            PrefabIssue(
                                node_name=node.name,
                                issue_type="missing_texture",
                                detail=f"Material '{mat.name}' references missing {tex_label} texture GUID {tguid}.",
                                repair_note=f"Add the missing {tex_label} texture to the package or relink it in {mat.name}.tres.",
                            )
                        )
        for comp in node.unsupported_components:
            issues.append(
                PrefabIssue(
                    node_name=node.name,
                    issue_type="unsupported_component",
                    detail=f"Unsupported Unity component: {comp}.",
                    repair_note=f"Recreate {comp} behavior natively in Godot if needed.",
                )
            )

    status = "full" if not issues else "partial"
    return PrefabReport(
        prefab_guid=prefab.guid,
        prefab_name=prefab.name,
        pathname=prefab.pathname,
        status=status,
        issues=issues,
    )


def scan_package(pkg: UnityPackageData) -> PackageScanReport:
    reports: List[PrefabReport] = []
    full = partial = skipped = 0
    for prefab in pkg.prefabs.values():
        pr = diagnose_prefab(pkg, prefab)
        reports.append(pr)
        if pr.status == "full":
            full += 1
        elif pr.status == "partial":
            partial += 1
        else:
            skipped += 1
    return PackageScanReport(
        total_prefabs=len(reports),
        fully_converted=full,
        partially_converted=partial,
        skipped=skipped,
        prefab_reports=reports,
    )
