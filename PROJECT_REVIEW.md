# Review of the SELODev Auto-Packager plan

**November 23, 2026.** The [reviewed README](https://github.com/seloc0des/gdcnvrter/blob/c1f937d29e53215f33ad481ac641d8bc46ca804a/readme.md) was the only file on `main` at the time of review. Conversion quality, platform compatibility, and demand are open questions.

**Recommendation: fund a narrow prototype.** Start with a Godot developer who owns a static Unity environment pack and wants to use its prefabs without opening Unity. Let them inspect the pack, convert one recognizable prefab, and see exactly what needs attention. That experience gives the developer a reason to pay for the batch and gives SELODev a way to test the business before committing to the 45-day launch.

## Strengths worth keeping

- **The outcome is easy to demonstrate.** Take a modular doorway from a purchased pack, place it in a Godot level, and walk through it. The demo can show the pivot, materials, hierarchy, and collision. Time the manual workflow alongside it so the buyer can judge the savings.
- **Local processing and a one-time price fit the job.** Developers can try their own packs in their own projects. Excluding Unreal binary decoding and C# translation gives a solo maintainer a defensible support boundary.
- **Real packs and headless tests serve different purposes.** Real packs reveal naming conventions and exporter quirks. Small, self-authored fixtures give CI an exact expected result and can be shared with bug reports. Keep commercial benchmark content private where its license requires it.

## Where the plan needs work

**Give Lite and Pro the same first success.** A free single-file FBX importer demonstrates little to a customer holding a Unity package. Have Lite scan the package, list supported and unsupported content, and convert one prefab of the customer's choice. Pro can run the same operation across the pack. A customer who sees a correctly assembled doorway in their own level can make an informed purchase.

**Benchmark the closest alternatives.** Godot already imports FBX and glTF and generates mesh LODs for common imported scenes. Unidot documents package and prefab conversion alongside additional FBX setup. GodotFAB lists cross-platform glTF/FBX import, with its Linux restriction applying to Unreal packages. Compare setup time, time to first usable prefab, and fixes per pack against the relevant tool. Record the exact versions tested. [Godot scene importer](https://docs.godotengine.org/en/stable/classes/class_resourceimporterscene.html) · [Godot mesh LOD](https://docs.godotengine.org/en/stable/tutorials/3d/mesh_lod.html) · [Unidot](https://github.com/V-Sekai/unidot_importer) · [GodotFAB](https://store.godotengine.org/asset/alextrevisan/godotfab/)

**Define a successful conversion from the user's perspective.** A scene can load with the wrong material on every wall. Count fully converted, partially converted, and skipped prefabs separately. For a partial conversion, name the affected object, the missing dependency or unsupported component, and the repair the developer can make. This report matters more to a buyer deciding whether to trust 800 assets than the raw number of files written.

**Correct the market evidence.** Godot announced the official Asset Store as live and stable. The README's trademark link points to an unrelated addon. Cite the Foundation directly. Game-jam participation, competitors' ratings, and asset-placement tool prices give context, but none measures willingness to pay for prefab conversion. [Asset Store announcement](https://godotengine.org/article/introducing-the-godot-asset-store/) · [Godot Foundation trademark policy](https://godot.foundation/policies-and-procedures/trademark-policy)

## What the first prototype should prove

| Case | Passing result |
|---|---|
| Modular prop with child meshes and shared materials | The scene matches a reference for scale, pivot, child transforms, and material assignment. Shared materials stay shared. |
| Missing texture or unsupported component | The report identifies the affected prefab and omission. Other supported assets still convert. |
| Reimport after editing one source material | A previously placed instance resolves after reopening the project. The material updates without duplicates, and user edits follow a documented overwrite rule. |
| Interrupted batch | Existing project files stay usable. A retry finishes without duplicate scenes or half-written resources. |
| Clean installation | On each advertised platform, a tester follows the published steps, imports the fixture, reopens Godot, and instantiates the scene. |

A headless import and reopen can check references, node structure, and resource reuse. Pair it with a visual reference and a simple playable collision check. An empty error log alone cannot tell you whether the doorway faces the right way or whether the player can pass through it.

## Economics and launch decision

Under Paddle's published standard fee of 5% plus $0.50, a $19 sale yields $17.55 and a $25 sale yields $23.25 before other costs. The README's per-sale arithmetic holds. The uncertain inputs are qualified traffic, conversion after a successful preview, and time spent supporting each pack. [Paddle pricing](https://www.paddle.com/pricing)

| Weekly Pro sales target | Lite installs at 2% conversion | Lite installs at 3% conversion |
|---|---:|---:|
| 3 | 150 | 100 |
| 6 | 300 | 200 |

The full range is 100–300 weekly installs under those assumptions. Treat $50–$100 per week and 3–5 maintenance hours per month as pilot hypotheses. Track installs, successful previews, purchases, and support minutes separately. Low preview success calls for engineering work. Strong preview success with few purchases calls for a conversation about price, batch size, and how often buyers encounter the problem.

1. **Build one end-to-end conversion.** Support static props with ordinary materials and a documented component list. Get one self-authored fixture through import, placement, and reimport.
2. **Test on unfamiliar packs.** Ask developers to bring packs they already own. Include one incomplete pack and record every manual fix. Publish a compatibility table with engine version, pack version, and known omissions.
3. **Run a paid pilot at the proposed $19 price.** Let participants preview their own prefab first. Record purchases, reasons for declining, time saved, and support effort.
4. **Set the release scope from the pilot.** Expand format and platform claims as tests pass. Commit to a launch date when developers can repeat the core workflow independently and the support load fits a solo product.

The most persuasive evidence for this project would be a developer trusting the preview enough to pay for the rest of their pack. That single event tests conversion quality, usefulness, and price together.
