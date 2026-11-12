"""Example generator: a wooden crate with a metal frame, PBR-textured.

Copy to tools/<name>_model.py (with clmodel.py beside it) and adapt.

    blender --background --python tools/crate_model.py

Writes art/crate/Crate.blend, previews and textures, and assets/props/Crate.fbx.
Verified end to end: imports at 3.02 studs with a SurfaceAppearance.
"""
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clmodel as cl

ROOT = Path(__file__).resolve().parent.parent
NAME = "Crate"
ART = ROOT / "art" / "crate"
OUT = ROOT / "assets" / "props"
SIZE = 3.0  # studs


def box(bm, center, size, mat_index, bevel=0.0):
    before = set(bm.faces)
    r = bmesh.ops.create_cube(bm, size=1.0)
    verts = r["verts"]
    bmesh.ops.scale(bm, vec=Vector(size), verts=verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=verts)
    if bevel:
        edges = list({e for v in verts for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=1, affect="EDGES")
    for f in bm.faces:  # bevel rebuilds faces, so tag everything new
        if f not in before:
            f.material_index = mat_index


def build():
    cl.begin(ART / f"{NAME}.blend")
    col = cl.collection(NAME)

    wood = cl.material("wood", (150, 100, 58), roughness=0.85)
    tree = wood.node_tree
    bsdf = cl.principled(wood)
    noise = tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 6.0
    mapping = tree.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1.0, 1.0, 9.0)
    coord = tree.nodes.new("ShaderNodeTexCoord")
    tree.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    tree.links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*cl.srgb(104, 66, 36), 1)
    ramp.color_ramp.elements[1].color = (*cl.srgb(186, 134, 82), 1)
    tree.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    tree.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bump = tree.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    tree.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    metal = cl.material("metal", (150, 156, 168), roughness=0.35, metallic=1.0)
    dark = cl.material("gap", (40, 28, 20), roughness=0.9)

    bm = bmesh.new()
    h = SIZE / 2
    box(bm, (0, 0, h), (SIZE * 0.86, SIZE * 0.86, SIZE * 0.86), 2)  # dark core seen through the gaps
    plank = SIZE * 0.92 / 4
    for i in range(4):  # planks on the four sides and top/bottom
        o = -SIZE * 0.46 + plank * (i + 0.5)
        for sx in (-1, 1):
            box(bm, (sx * SIZE * 0.47, o, h), (0.12, plank * 0.92, SIZE * 0.9), 0, 0.02)
            box(bm, (o, sx * SIZE * 0.47, h), (plank * 0.92, 0.12, SIZE * 0.9), 0, 0.02)
            box(bm, (o, 0, h + sx * SIZE * 0.47), (plank * 0.92, SIZE * 0.9, 0.12), 0, 0.02)
    e = SIZE * 0.5 - 0.09
    for sx in (-1, 1):  # metal frame along the 12 edges
        for sy in (-1, 1):
            box(bm, (sx * e, sy * e, h), (0.2, 0.2, SIZE), 1, 0.03)
            box(bm, (sx * e, 0, h + sy * e), (0.2, SIZE, 0.2), 1, 0.03)
            box(bm, (0, sx * e, h + sy * e), (SIZE, 0.2, 0.2), 1, 0.03)
    crate = cl.mesh_object(NAME, bm, [wood, metal, dark], col, origin=(0, 0, 0), smooth=False)
    objects = [crate]

    cl.unwrap_atlas(objects)
    textures = cl.bake_atlas(objects, NAME, ART / "textures", size=1024,
                             maps=("color", "roughness", "metallic", "normal"), ao=0.6)
    problems = cl.validate(objects, textured=True, tri_budget=3000)
    files = [cl.export_model(OUT / f"{NAME}.fbx", None, objects, textured=True)]
    renders = cl.render_previews(ART, NAME, objects)
    return cl.finish(NAME, ART / f"{NAME}.blend", objects, files=files, textures=textures,
                     renders=renders, problems=problems)


build()
