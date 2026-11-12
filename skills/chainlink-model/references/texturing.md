# Texturing for Roblox

How `clmodel.unwrap_atlas` and `clmodel.bake_atlas` work, and what Roblox does with the result.

## What arrives in Roblox

An FBX whose material is a Principled BSDF fed by image textures uploads through `chainlink assets` as a MeshPart with a `SurfaceAppearance` child holding `ColorMap`, `NormalMap`, `RoughnessMap` and `MetalnessMap`; each map becomes its own image asset automatically. `MeshPart.TextureID` stays empty. This was verified with all four maps; a color-only bake is expected to arrive the same way with just `ColorMap`, so confirm it in the Studio check the first time.

Consequences for game code:

- SurfaceAppearance maps cannot be changed by scripts at runtime. To recolor in game, either use vertex colors and `MeshPart.Color`, or set `SurfaceAppearance.Color` (a tint multiplied over the color map).
- With the default `AlphaMode = Overlay`, `MeshPart.Color` only shows where the color map is transparent. `bake_atlas` writes opaque maps.
- Swapping looks (skins) means separate model files, one per look.

## Atlas layout

`unwrap_atlas(objects, margin=0.02, angle=66)` gives every object a UV map and packs all islands of all objects into one 0-1 square, so a multi-part character still needs a single texture set. It is automatic (Smart UV Project): good for hard-surface and chunky stylized shapes, wasteful for organic ones. For a part that needs hand-placed islands, mark seams (`edge.seam = True` in bmesh) and run `bpy.ops.uv.unwrap` on it, then `bpy.ops.uv.pack_islands` over everything.

Texture size follows on-screen size, not ambition. Roblox's own guide: 256 for an object about 5 studs across, 512 for 10, 1024 for 20. A fighter that fills a third of the screen earns 1024; a pickup earns 256. Sizes must be powers of two. Look at the baked color PNG: large black areas mean wasted space (delete hidden faces, raise `angle`, or lower `size`).

## Baking

`bake_atlas(objects, name, out_dir, size, maps, ao, high, cage, samples, margin)` bakes with Cycles on the CPU and then replaces the objects' materials with one material named `name` wired to the baked images.

| Map | Source | Notes |
|---|---|---|
| `color` | Principled Base Color, including any node tree feeding it | Baked through an Emission shader, so metals keep their color (a diffuse bake turns them black) |
| `roughness`, `metallic` | The Principled inputs | Grayscale, non-color data |
| `normal` | Bump/normal nodes in the material, or `high=` meshes | Tangent space, OpenGL (+Y) convention, which is what Roblox expects |

- `ao` (0-1) multiplies baked ambient occlusion into the color map. Flat palette models read much better with 0.4-0.6; leave it at 0 for PBR-realistic assets, where Roblox lighting does the work.
- A normal map is only worth its memory when there is detail to capture. Either give the materials a Bump node (procedural noise, scratches), or build a detailed version of the model and pass it as `high=[...]`: each low-poly object then catches rays from the high-poly meshes within `cage` studs. Keep high and low overlapping in place.
- Procedural shading works: plug Noise/Voronoi/ColorRamp nodes into Base Color or Roughness and the bake captures them. Use Object texture coordinates so patterns do not depend on the UV layout.
- Bakes are deterministic on one machine, which is what lets `export_model` detect an unchanged model. Changing `samples` or `size` changes the texture and therefore the upload.

Not handled by the helper: transparency (alpha in the color map plus `AlphaMode`), emissive masks, and tiling textures for large surfaces (unwrap by hand at a fixed texel density, or leave big flat areas to Roblox Parts and materials).

## Vertex colors instead

`vertex_colors(objects)` writes each face's material color into a `Color` attribute and the FBX exporter stores it (`colors_type="SRGB"`). In Roblox the mesh shows those colors multiplied by `MeshPart.Color`, so game code should set the part color to white, or use it deliberately as a tint (team colors, hit flashes, VFX). Hard color borders need an edge between the faces; gradients need vertices where the color changes.
