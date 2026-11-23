# SELODev Godot 4.7+ Auto-Packager — Action Plan

> **Target:** `$50–$100/week` (`$200–$430/month` net) · **Model:** Free Lite Funnel + `$19–$25` One-Time Pro License · **Publisher:** `SELODev`

## 1. Market Context & Why This Product Wins

Following the permanent closure of `godotmarketplace.com` on October 30, 2026 ([closure notice](https://godotmarketplace.com/)) and with the official [Godot Asset Store](https://store.godotengine.org/) still free-only in beta ([roadmap](https://store.godotengine.org/roadmap/)), Godot's 47% share of GMTK Game Jam 2026 entries ([Neural4D](https://blog.neural4d.com/game/godot-vs-unity/)) creates real demand for asset tooling.

Real-world 2026 paid Godot 4 benchmarks on itch.io—such as [AssetPlacer](https://cookiebadger.itch.io/assetplacer) (24 total ratings over 3+ years) and [Ultimate Asset Placer](https://choco-ted.itch.io/ultimate-asset-placer-godot-45-gd-script) (listed at `$30.30`, discounted to `$9.99`)—show that `$50–$100/week` (`3–6` sales/week) is a realistic, dependable side-income target.

### The Exact Converter Gap
Every major existing converter forces a painful compromise:
- **[Unidot Importer](https://godotengine.org/asset-library/asset/2427) (Free):** Requires manual external-binary setup (`FBX2glTF` / `unitypackage_util`) and has beta friction on Godot 4.3+.
- **[Unity to Godot Exporter](https://gamefromscratch.com/new-unity-to-godot-game-engine-exporter/) (Paid):** Requires installing and running the Unity Editor.
- **[GodotFAB](https://store.godotengine.org/asset/alextrevisan/godotfab/) (Free):** Marked unstable, and Unreal package conversion is Linux-only requiring Unreal Engine 5.8.

**The Solution:** A zero-setup, cross-platform (`Windows`, `macOS`, `Linux`) utility under **SELODev** (with a descriptive, trademark-safe product name that avoids leading with "Godot" per [Foundation trademark guidelines](https://store.godotengine.org/asset/npgamedev/godot-mcp-toolkit/)) that converts `.unitypackage` archives and raw Fab/Synty FBX/glTF/OBJ + PBR packs into drop-in Godot 4.7+ `.tscn` scenes **without installing Unity or Unreal**.

---

## 2. Product Architecture & Scope Discipline

To keep ongoing maintenance to ~3–5 hours/month with **$0 server costs**, v1 strictly excludes proprietary Unreal `.uasset` decoding and C# script translation:

### Free Lite Edition (MIT — `store.godotengine.org` & `itch.io`)
- In-editor Godot 4.7+ addon for single-asset glTF/FBX imports.
- Auto-wires PBR textures (albedo, normal, roughness, metallic, AO) into `StandardMaterial3D` and generates clean `CollisionShape3D` nodes.
- Ranks inside the Godot Editor to drive steady organic installs.

### Pro Edition (`$19` launch / `$25` standard one-time — `itch.io` & `Paddle`)
- Cross-platform batch packager for full `.unitypackage` tarballs and Fab/Synty folders without Unity installed.
- Reconstructs `.tscn` prefab hierarchies, generates LODs, and preserves valid `uid://` resource IDs.
- Sold via [itch.io](https://itch.io/game-assets/tag-godot) (`10%` default cut) and [Paddle](https://www.paddle.com/pricing) (`5% + $0.50` Merchant of Record automating global VAT and license keys).

---

## 3. Unit Economics (`$50–$100/Week` Target)

On [Paddle](https://www.paddle.com/pricing) (`5% + $0.50` fee):
- **$19 Pro License** nets **$17.55/sale** → **3 sales/week** = `$52.65/week` | **6 sales/week** = `$105.30/week`.
- **$25 Pro License** nets **$23.25/sale** → **3 sales/week** = `$69.75/week` | **5 sales/week** = `$116.25/week`.

At a 2%–3% Free-to-Pro conversion rate, **3–6 sales/week** requires roughly **125–250 Free Lite installs/week** across [store.godotengine.org](https://store.godotengine.org/) and [itch.io](https://itch.io/game-assets/tag-godot).

---

## 4. 45-Day Build & Launch Roadmap

### Days 01–15 · Core Build
- Build the local `.unitypackage` tarball/YAML parser and glTF/FBX → Godot 4.7+ `.tscn` packager.
- Verify clean imports across 5 benchmark packs (Synty Polygon, Fab glTF, Humble 3D bundles).
- Set up headless Godot 4.7+ automated CI tests so future engine updates can be verified automatically.

### Days 16–30 · SELODev Funnel & Billing
- Assign a descriptive, trademark-safe product name under the **SELODev** publisher profile.
- Publish the Free **Lite** addon (MIT) on [store.godotengine.org](https://store.godotengine.org/) and [itch.io](https://itch.io/game-assets/tag-godot).
- Configure [Paddle](https://www.paddle.com/pricing) (`5% + $0.50`) and itch.io Pro listings (`$19` launch → `$25` standard).

### Days 31–45 · Initial Launch
- Post 2–3 short side-by-side videos on YouTube and `r/godot` showing 30-second Synty/Fab conversion without Unity installed.
- Add a clean "Upgrade to Pro" link inside the Lite addon's editor panel and `README.md`.
- Collect early buyer feedback and patch first-week FBX/material edge cases.

### Ongoing · Monthly 9.5/10 Routine (~3–5 hrs/month)
- **1 hr/mo:** Run headless CI against the latest Godot 4.7.x / 4.8 beta build to stay "Day-One Compatible."
- **1–2 hrs/mo:** Record one 45-second "Bundle-Tested" clip whenever a major Humble Bundle, Synty sale, or Fab freebie drops.
- **1–2 hrs/mo:** Patch the top 1–2 user-reported edge cases and push a point release to bump "Last Updated" visibility.

---

## 5. Key Risks & Mitigations

| Risk Factor | Why It Matters | Built-In Mitigation |
| :--- | :--- | :--- |
| **Godot 4.x Format Drift** | Updates (`4.7` → `4.8`) can alter `uid://` or shader properties. | Run monthly headless CI smoke tests on beta builds (~1 hr/mo). |
| **Free MIT Alternatives** | [Unidot](https://godotengine.org/asset-library/asset/2427) is free, though setup is manual. | Win on zero-setup UX, prefab/LOD polish, and monthly bundle-tested updates. |
| **Asset License Confusion** | Some Unity Store packs are Unity-only by EULA. | Include an in-app notice to convert only non-restricted packs (Fab glTF, Synty direct, Humble). |
| **Scope Creep into `.uasset`** | Unreal binary packs force UE 5.8 installs or cloud servers. | Exclude `.uasset` in v1; keep everything 100% local with `$0` server costs. |
