# SELODev Godot 4.7+ Auto-Packager — Action Plan

[Run the working static-prefab pilot, open the doorway demo, and check supported inputs.](PILOT.md)

> **Target:** `$50–$100/week` pilot hypothesis (`3–6` sales/week) · **Model:** Prototype-First → Free Lite (Single-Prefab Preview) + `$19–$25` One-Time Pro Batch License · **Publisher:** `SELODev`

## 1. Market Context & Positioning

Following the permanent closure of `godotmarketplace.com` on October 30, 2026 ([closure notice](https://godotmarketplace.com/)), the official [Godot Asset Store](https://store.godotengine.org/) is live and stable for free assets ([announcement](https://godotengine.org/article/introducing-the-godot-asset-store/)), with paid checkout still on its [roadmap](https://store.godotengine.org/roadmap/). Godot's 47% share of GMTK Game Jam 2026 entries ([Neural4D](https://blog.neural4d.com/game/godot-vs-unity/)) and paid itch.io tools like [AssetPlacer](https://cookiebadger.itch.io/assetplacer) (24 ratings) and [Ultimate Asset Placer](https://choco-ted.itch.io/ultimate-asset-placer-godot-45-gd-script) (`$30.30` / `$9.99` sale) provide ecosystem context, though neither directly measures willingness to pay for prefab conversion—which our `$19` paid pilot will test directly.

### What Godot Already Does vs. The Real Converter Gap
Godot already imports FBX/glTF ([scene importer](https://docs.godotengine.org/en/stable/classes/class_resourceimporterscene.html)) and generates mesh LODs ([mesh LOD](https://docs.godotengine.org/en/stable/tutorials/3d/mesh_lod.html)) natively. The real gap is **zero-setup `.unitypackage` prefab conversion** without installing Unity or Unreal:
* **[Unidot Importer](https://github.com/V-Sekai/unidot_importer) (Free):** Documents `.unitypackage` and prefab conversion alongside additional external FBX binary setup.
* **[Unity to Godot Exporter](https://gamefromscratch.com/new-unity-to-godot-game-engine-exporter/) (Paid):** Requires installing and running the Unity Editor.
* **[GodotFAB](https://store.godotengine.org/asset/alextrevisan/godotfab/) (Free):** Cross-platform glTF/FBX import, with its Linux restriction applying to Unreal Engine 5.8 packages.

**Our Wedge:** A local, cross-platform (`Windows`, `macOS`, `Linux`) `.unitypackage` → Godot 4.7+ `.tscn` packager under **SELODev** (using a descriptive, trademark-safe product name per the [Godot Foundation trademark policy](https://godot.foundation/policies-and-procedures/trademark-policy)), benchmarked directly against Unidot on setup time, time to first usable prefab, and manual fixes per pack (with exact versions recorded). Excluding `.uasset` decoding and C# translation keeps v1's support boundary defensible at `$0` server cost.

---

## 2. Product Architecture: Same First Success for Lite & Pro

### Free Lite Edition (MIT — `store.godotengine.org` & `itch.io`)
* **Inspect & Diagnose:** Scans a `.unitypackage`, counts **fully converted, partially converted, and skipped** prefabs separately, and names missing dependencies or unsupported components with actionable repair notes.
* **Single-Prefab Proof:** Converts **one prefab of the user's choice** (e.g., a modular doorway) into their Godot 4.7+ project with correct pivot, scale, child hierarchy, shared `StandardMaterial3D` reuse, and playable `CollisionShape3D`.

### Pro Edition (`$19` pilot / `$25` standard one-time — `itch.io` & `Paddle`)
* **Full-Pack Batch Conversion:** Runs the exact same verified pipeline across the entire `.unitypackage` (hundreds of prefabs) in one pass.
* **Non-Destructive Reimport & Atomic Writes:** Writes scenes/resources atomically, preserves existing `.uid` references, updates shared materials without duplicates, and follows a documented overwrite rule so user scene edits aren't clobbered.
* **Billing:** Sold via [itch.io](https://itch.io/game-assets/tag-godot) (`10%` default cut) and [Paddle](https://www.paddle.com/pricing) (`5% + $0.50` Merchant of Record automating global VAT and license keys).

---

## 3. Prototype Verification Matrix (Must Pass Before Launch)

| Case | Passing Result |
| :--- | :--- |
| **Modular prop with child meshes & shared materials** | Scene matches visual reference for scale, pivot, child transforms, and material assignment; shared materials stay shared. |
| **Missing texture or unsupported component** | Diagnostic report identifies the affected prefab and omission; all other supported assets still convert cleanly. |
| **Reimport after editing one source material** | Previously placed instance resolves after reopening Godot; material updates without duplicates; user edits follow documented overwrite rule. |
| **Interrupted batch** | Existing project files stay usable; retry finishes without duplicate scenes or half-written resources. |
| **Clean installation** | On each advertised OS, a tester follows published steps, imports the fixture, reopens Godot, and instantiates the scene + playable collision check. |

*Note: Use small, self-authored fixtures for public CI/bug reports, and keep commercial benchmark packs private per their EULAs.*

---

## 4. Economics & Pilot Metrics

Under [Paddle's published fee](https://www.paddle.com/pricing) (`5% + $0.50`), a **`$19` sale nets `$17.55`** and a **`$25` sale nets `$23.25`** before other costs.

| Weekly Pro Sales Target | Lite Installs at 2% Conversion | Lite Installs at 3% Conversion |
| :---: | :---: | :---: |
| **3** (`$52.65` @ `$19` / `$69.75` @ `$25`) | 150 | 100 |
| **6** (`$105.30` @ `$19` / `$139.50` @ `$25`) | 300 | 200 |

Treat `$50–$100/week` and `3–5` maintenance hours/month as **pilot hypotheses**. Track **installs**, **successful previews**, **purchases**, and **support minutes** separately:
* Low preview success → engineering work on the converter.
* High preview success + few purchases → revisit price, batch size, or target pack vertical.

---

## 5. Pilot-First Execution Sequence

1. **Build One End-to-End Conversion:** Support static props with ordinary materials and a documented component list. Get one self-authored fixture through import, placement, playable collision, and reimport.
2. **Test on Unfamiliar Packs:** Have developers test packs they already own (including one incomplete pack), record every manual fix, and publish a compatibility table (engine version, pack version, known omissions).
3. **Run a `$19` Paid Pilot:** Let participants inspect their pack and preview one prefab via Lite first; record purchases, reasons for declining, time saved vs. manual import, and support minutes.
4. **Set Release Scope & Launch Cadence:** Commit to the full public release (and monthly CI + "Bundle-Tested" demo clip routine) once developers repeat the core workflow independently and support load fits a solo product.
