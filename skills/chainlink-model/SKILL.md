---
name: chainlink-model
description: Model 3D assets in Blender (through the Blender MCP or headless) for Roblox games built with ChainLink - characters, props, weapons, stage pieces and VFX meshes - from a generator script through baked textures/PBR, rigging, FBX export into assets/, `chainlink assets` upload and a check in Roblox Studio. Use whenever the user wants to create, change, texture, rig, export or re-import a 3D model, mesh or .blend/.fbx/.glb in a project with a chain.toml, or mentions Blender for a Roblox game, even if they only say "make a sword" or "the character looks wrong in Studio".
---

# ChainLink modeling

Build 3D models for a ChainLink Roblox project with Blender. The pipeline:

```
tools/<name>_model.py  ->  art/<name>/<Name>.blend + previews + textures   (source, review)
   (generator script)  ->  assets/<category>/<Name>.fbx                    (what Roblox gets)
                           -> chainlink assets -> assets.lock.json -> asset "<category>/<Name>.fbx"
```

The generator script is the source of truth; the `.blend`, textures and FBX are regenerated outputs. A script can be diffed, reviewed and rerun, and a tweak ("make the arms longer") is a one-line change instead of a manual sculpt. Edit a `.blend` by hand only when the user's model was made by hand (then inspect before changing anything and keep their structure).

Pair this with the `chainlink` skill for the CLI, `asset` macro and project layout. Models and rigs only: animation is authored in the game's own code or tools.

## Before modeling

1. Read what the project already has: `tools/*_model.py` (copy its conventions and helpers), `art/`, `assets/`, design docs, and the game data that fixes sizes (a character's height, a stage's collision boxes). The model must match the simulation, not the other way round.
2. Settle the open choices with the user if the request leaves them open: size in studs, texture route (below), rigid or skinned, and where it loads in game code.
3. If `tools/clmodel.py` is missing, copy `scripts/clmodel.py` from this skill into `tools/` so the project builds without the skill. `scripts/example_model.py` is a complete textured prop to start from.

## Conventions

Everything here was measured on real uploads (Blender 5.3, `chainlink assets`, Nov 2026).

| In Blender | In Roblox |
|---|---|
| 1 unit | 1 stud (FBX exported with `global_scale=0.01`; the default export arrives 100x too big) |
| +Z up, front faces -Y, character's left is +X | +Y up, front faces -Z (`LookVector`), left is -X |
| Object name | `MeshPart.Name`, which game code looks up: PascalCase, no `.001` |
| Object origin | `MeshPart.PivotOffset` (the part's `Position` is its bounding-box centre) |
| Root empty with child meshes | `Model` (file name) > `Model` (empty's name) > MeshParts |
| Meshes with no root | `Model` (file name) > MeshParts |
| Baked Principled textures embedded in the FBX | `SurfaceAppearance` under the MeshPart (color, normal, roughness, metalness) |
| `Color` color attribute, no texture | Vertex colors on the mesh, multiplied by `MeshPart.Color` |
| Armature + weights | One MeshPart with a `Bone` tree, `AnimationController` and `InitialPoses` |

Put the ground at Z = 0 and each origin where the part should rotate or attach: between the feet for a character, on the joint for a limb, in the grip for a weapon, at the emission point for VFX. Keep rotation 0 and scale 1 on every object (bake transforms into the mesh). Parts arrive unanchored, collidable and grey (`163, 162, 165`); game code sets `Anchored`, `CanCollide` and `Color` (white for true vertex colors).

Roblox limits: 20,000 triangles per mesh (hard), back faces are culled (flipped normals look like holes), 4 bone influences per vertex, textures up to 1024 are safe.

## The generator script

One file per model, runnable headless and inside a live Blender. Build geometry with `bmesh` in model space (studs), then hand it to `clmodel`:

```python
import sys
from pathlib import Path
import bmesh
sys.path.insert(0, str(Path(__file__).resolve().parent))
import clmodel as cl

ROOT = Path(__file__).resolve().parent.parent
NAME, ART = "Crate", ROOT / "art" / "crate"

def build():
    cl.begin(ART / f"{NAME}.blend")                      # empty scene (safe in a live session)
    col = cl.collection(NAME)
    wood = cl.material("wood", (150, 100, 58), roughness=0.85)   # sRGB 0-255
    bm = bmesh.new()
    ...                                                  # build faces, set face.material_index
    part = cl.mesh_object(NAME, bm, [wood], col, origin=(0, 0, 0))
    objects = [part]
    cl.unwrap_atlas(objects)
    textures = cl.bake_atlas(objects, NAME, ART / "textures", size=512, ao=0.5)
    problems = cl.validate(objects, textured=True, tri_budget=1500)
    files = [cl.export_model(ROOT / "assets" / "props" / f"{NAME}.fbx", None, objects, textured=True)]
    renders = cl.render_previews(ART, NAME, objects)
    return cl.finish(NAME, ART / f"{NAME}.blend", objects, files=files,
                     textures=textures, renders=renders, problems=problems)

build()
```

| `clmodel` | Does |
|---|---|
| `begin(blend)` | Empties the scene. Live, it refuses to wipe a file that is not this model's own `.blend` or the default startup scene (`SceneInUse`): ask the user, then `begin(blend, force=True)` |
| `material(name, rgb, roughness, metallic)` / `principled(mat)` | Flat Principled material; add shader nodes for procedural detail |
| `mesh_object(name, bm, mats, col, origin, parent, smooth)` | bmesh -> object with its origin at `origin` (model space); recalculates normals |
| `empty(name, col)` / `collection(name)` | Root empty for multi-part models (its name must differ from every part) |
| `vertex_colors(objects)` | Untextured route: face material colors -> `Color` attribute |
| `unwrap_atlas(objects)` / `bake_atlas(...)` | One shared UV layout and texture set; see Texturing |
| `armature(name, bones, col)` / `skin(obj, arm, weights)` | Skinned route; see Rigging |
| `validate(objects, arm, textured, tri_budget)` | List of import problems; fix them, do not ship them |
| `export_model(path, root, objects, arm, textured)` | `.fbx` (or `.glb`) with correct scale and embedded textures |
| `render_previews(dir, name, objects, views)` | Orthographic turnaround PNGs |
| `finish(name, blend, objects, arm, **extra)` | Saves the `.blend`, prints `CLMODEL_REPORT {json}` (size, tris, pivots, bones, exports) |

`export_model` skips writing when nothing it depends on changed (fingerprint stored beside the `.blend`). This matters: Blender stamps the time into every FBX, `chainlink assets` uploads any file whose hash changed, and a changed file gets a new asset ID. Commit `art/` including the `.fingerprint` files.

## Running it and looking at it

**Live (Blender MCP connected).** Call `get_blendfile_summary_path_info` first: it shows the connection is up and what file is open. Then run the generator in the session and read the report:

```python
# execute_blender_code
import runpy, sys
sys.modules.pop("clmodel", None)   # pick up edits to the helper
ns = runpy.run_path("/abs/path/tools/crate_model.py")
result = sys.modules["clmodel"].LAST_REPORT
```

Look with `get_screenshot_of_area_as_image` (`VIEW_3D`) or Read the preview PNGs; the user watches the same scene and can point at things. `finish` switches the viewport to Material Preview so screenshots show the textures; frame the model first with `jump_to_view3d_object_by_name`. Never call `bpy.ops.wm.read_factory_settings` or open another file in a live session: it disables the MCP add-on and drops the connection (`begin` avoids this).

**Headless (no connection).** Works without the add-on:

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --python tools/crate_model.py
```

Grep the output for `CLMODEL_REPORT` and Read the PNGs. The MCP's `*_for_cli` tools need `BLENDER_PATH` set; use Bash if they report a missing executable. If the live connection fails, say so once (the add-on comes from the Blender Lab extensions repository, `https://lab.blender.org/`, and its server must be started) and carry on headless.

**Iterate on what you see.** Always look at the previews before exporting further: check silhouette and proportions from front, side and three-quarter against the reference or design doc, then the texture PNG for wasted space and seams. Change the script, rerun, look again. Report tri counts and size from the report, not from memory.

## Texturing

Pick per model; ask if unsure.

| Route | When | How |
|---|---|---|
| Vertex colors | Flat-colored stylized models, VFX, anything tinted in code | `vertex_colors(objects)`, export with `textured=False`. No UVs, no texture memory |
| Color atlas | Painted or gradient detail, baked shading | `unwrap_atlas` + `bake_atlas(maps=("color",), ao=0.5)` |
| PBR | Metal, varied roughness, surface relief | `bake_atlas(maps=("color", "roughness", "metallic", "normal"))`; arrives as a `SurfaceAppearance` |

The baked maps are embedded in the FBX and uploaded with it; do not also put the PNGs in `assets/`. Never mix vertex colors with a texture (Roblox multiplies them; `bake_atlas` removes the attribute). Details, texture sizes, normal-map sources and SurfaceAppearance limits: `references/texturing.md`.

## Rigging

| Route | When | Blender side |
|---|---|---|
| Rigid parts | Default. Chunky/stylized characters, anything animated by code-driven `Motor6D`s | Separate objects per segment under a root empty, each origin on its joint. No armature |
| Skinned | Capes, tails, hair, soft bodies, smooth elbows | One mesh + `armature()` + `skin()`; root bone at the origin, unweighted |

A character can mix both: rigid body parts plus one skinned cape. Joint placement, weights, the Luau that builds Motor6Ds from pivots and drives bones: `references/rigging.md`.

## Budgets by model type

Starting points; the project's docs and target devices win.

| Type | Triangles | Texture | Notes |
|---|---|---|---|
| Character (about 6 studs) | 3k-8k total, under 2k per part | 1024 | Readable silhouette first; exaggerate hands, feet, head for small on-screen sizes |
| Prop / weapon | 200-1,500 | 256-512 | Origin in the grip or at the base; one mesh unless parts move |
| Stage piece | up to 10k per mesh | 1024, or tiling | Align to the sim's collision data; split big scenery into meshes that can stream and cull; keep gameplay collision in simple Parts |
| VFX mesh | 50-500 | none or small grayscale | White/gray vertex colors so code tints via `Color`; unit size (radius 1) so code scales it; clean UVs if a texture will scroll |

Delete faces that can never be seen (buried ends, undersides resting on the ground): they cost triangles and atlas space.

## Upload and Studio check

Uploading changes the user's live Roblox inventory, so follow the `chainlink` skill's rule: dry-run, then ask.

1. `chainlink assets --dry-run` and confirm only the files you meant to change are listed.
2. Ask the user, then `chainlink assets`. The ID lands in `assets.lock.json`; commit it.
3. Check the import in Studio through the Studio MCP: structure, size, pivots, textures, bones, and a screenshot. Recipe and Luau: `references/studio-check.md`.
4. Wire it into the game the way the project already loads models (`asset "<category>/<Name>.fbx"` gives `rbxassetid://<id>`; the server loads it with `InsertService:LoadAsset`). Reuse the project's loader rather than writing a second one.

If loading fails with `Requester does not have permission for Asset`, the asset's owner (`[Roblox] UserId`/`GroupId` in `chain.toml`) is not the experience's owner. Inserting it once in Studio (the Studio MCP's `insert_asset`) grants that experience access; for a group game, uploading under `GroupId` avoids the problem. Tell the user which happened.

## Final report

End with: what was built (size in studs, triangles per part, texture route, rig), files written, upload status and asset ID, what the Studio check showed, and anything not verified. Show the preview image paths so the user can open them.
