# ChainLink Model skill

Models 3D assets for a ChainLink game with Blender: characters, props, weapons, stage pieces and VFX meshes. Claude writes a generator script, runs it in Blender (live through the Blender MCP, or headless), looks at the renders, exports an FBX into `assets/`, uploads it with `chainlink assets` after asking, and checks the import in Roblox Studio.

Invoke it directly with `/chainlink-model`.

## Contents

| File | Purpose |
|---|---|
| `SKILL.md` | Pipeline, Blender-to-Roblox conventions, the generator pattern, budgets, upload and check workflow |
| `scripts/clmodel.py` | Helper library for generator scripts: scene setup, materials, UV atlas, texture/PBR baking, armatures and skinning, validation, export, previews, build report |
| `scripts/example_model.py` | A complete PBR-textured prop (wooden crate with a metal frame) to copy and adapt |
| `references/texturing.md` | Vertex colors vs color atlas vs PBR, baking details, what Roblox does with the maps |
| `references/rigging.md` | Rigid parts with `Motor6D`s and skinned meshes with bones, with the Luau to drive them |
| `references/studio-check.md` | Loading, inspecting and screenshotting an uploaded model through the Studio MCP |

## Requirements

| Needs | For | Without it |
|---|---|---|
| Blender (verified on 5.3) | Building models | Nothing works |
| [Blender MCP](https://www.blender.org/lab/mcp-server/) add-on, enabled with its server started | Running generators in the open Blender and looking at the viewport | Falls back to `blender --background`; previews are read from PNG files |
| `chainlink login-cloud` (Open Cloud key) | `chainlink assets` uploads | Stops after export |
| Roblox Studio MCP with the project's place open | The import check | Upload is not verified |

## Pipeline

```
tools/<name>_model.py  ->  art/<name>/<Name>.blend, previews, textures   (source and review)
                       ->  assets/<category>/<Name>.fbx                  (uploaded by chainlink assets)
                       ->  assets.lock.json  ->  asset "<category>/<Name>.fbx"
```

The generator script is the source of truth; everything else is regenerated. The skill copies `clmodel.py` into the project's `tools/` so the build does not depend on the skill being installed.

1. Read the project's existing generators, design docs and the game data that fixes sizes.
2. Write or edit `tools/<name>_model.py`.
3. Run it, look at the preview renders and texture, iterate.
4. `chainlink assets --dry-run`, ask, then `chainlink assets`.
5. Load the asset in Studio, compare structure and size with the build report, screenshot, clean up.
6. Wire it into game code with the project's existing model loader.

## Conventions

Measured on real uploads (Blender 5.3 and `chainlink assets`).

| In Blender | In Roblox |
|---|---|
| 1 unit | 1 stud (FBX exported with `global_scale=0.01`; Blender's default arrives 100x too big) |
| +Z up, front faces -Y | +Y up, front faces -Z |
| Object name | `MeshPart.Name` |
| Object origin | `MeshPart.PivotOffset` |
| Root empty with child meshes | `Model` > `Model` > MeshParts |
| Baked Principled textures embedded in the FBX | `SurfaceAppearance` with color, normal, roughness and metalness maps |
| `Color` attribute, no texture | Vertex colors, multiplied by `MeshPart.Color` |
| Armature and weights | One MeshPart with a `Bone` tree and an `AnimationController` |

`.glb` also imports at 1:1 with its textures, but loses object origins and wraps each mesh in an extra `<Name>_Node` model, so FBX is the default.

## Texturing and rigging choices

| Texture route | Use for |
|---|---|
| Vertex colors | Flat stylized models, VFX, anything tinted from code |
| Baked color atlas | Painted detail, gradients, baked ambient occlusion |
| PBR (`SurfaceAppearance`) | Metal, varied roughness, surface relief |

| Rig route | Use for |
|---|---|
| Rigid parts | Default: one object per body segment, origin on its joint, joined by `Motor6D`s in game code |
| Skinned | Capes, tails, hair and other parts that must bend smoothly |

Animation is out of scope: the skill ends at a correctly rigged model.

## Things it guards against

- **Re-uploads from rebuilds.** Blender stamps the time into every FBX, and `chainlink assets` gives any changed file a new asset ID. `clmodel.export_model` fingerprints what the export depends on and leaves the file alone when nothing changed. Commit `art/`, including the `.fingerprint` files.
- **Wiping someone's scene.** In a live Blender session the helper only empties the scene when the open file is the model's own `.blend` or an untouched startup scene; otherwise Claude asks first.
- **Dropping the MCP connection.** A factory reset disables add-ons, so live sessions clear data in place instead.
- **Uploads without consent.** Uploading always goes dry-run, then ask.
- **Asset permission errors.** When the experience's owner is not the asset's owner, `LoadAsset` fails until the asset is inserted once in Studio or uploaded under the owning group (`[Roblox] GroupId`).

## Example prompts

| Say something like | What happens |
|---|---|
| "Model a treasure chest prop, about 3 studs, with metal bands" | New generator, PBR bake, FBX in `assets/props/` |
| "Kairo's arms are too short, lengthen them 15%" | Edits the existing generator, rebuilds, shows before/after renders |
| "Give the fighter a cape that can flap" | Adds a skinned cape mesh with a bone chain |
| "The sword imports sideways in Studio" | Runs the Studio check, fixes orientation in the generator, re-exports |
