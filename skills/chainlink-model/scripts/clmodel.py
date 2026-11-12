"""clmodel: helpers for ChainLink model generator scripts (Blender 4.2+ / 5.x).

A generator script (tools/<name>_model.py) builds a model from code and calls
these helpers to texture, validate, preview, export and save it. Copy this file
next to the generator (tools/clmodel.py) so the project builds without the skill.

    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import clmodel as cl

Conventions (see SKILL.md): 1 Blender unit = 1 stud, Z up, front faces -Y,
ground at Z = 0, object origins on joints/pivots.

The same script runs headless (`blender --background --python ...`) and inside
a live Blender session through the Blender MCP; `begin()` handles both.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

TRI_LIMIT = 20000  # Roblox rejects meshes above this
MAX_INFLUENCES = 4  # per vertex, skinned meshes
LAST_REPORT: dict = {}
EXPORTS: dict[str, str] = {}  # export path -> "written" | "unchanged"
_CACHE_DIR: Path | None = None  # where export fingerprints live (the .blend's folder)


class SceneInUse(RuntimeError):
    """The open Blender file is someone's work; ask before replacing it."""


# --- scene ---------------------------------------------------------------------


def is_live() -> bool:
    return not bpy.app.background


def begin(blend_path, force: bool = False) -> None:
    """Start from an empty scene.

    Headless: factory reset. Live: remove the data in place, because a factory
    reset disables add-ons and would drop the MCP connection. Live sessions
    refuse to wipe a file that is not this model's own .blend (or an untouched
    startup scene) unless force=True; ask the user first.
    """
    global _CACHE_DIR
    blend_path = Path(blend_path).resolve()
    _CACHE_DIR = blend_path.parent
    EXPORTS.clear()
    if not is_live():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        return
    current = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    own = current == blend_path
    # A just-opened Blender often reports its startup scene as dirty, so also
    # accept an unsaved file holding nothing but the default Camera/Cube/Light.
    cube = bpy.data.objects.get("Cube")
    startup = ({o.name for o in bpy.data.objects} <= {"Camera", "Cube", "Light"}
               and (cube is None or (cube.type == "MESH" and len(cube.data.vertices) == 8)))
    untouched = current is None and (not bpy.data.is_dirty or startup)
    if not (own or untouched or force):
        raise SceneInUse(
            f"Blender has {current or 'unsaved work'} open. Ask the user before "
            f"replacing it, then rerun with force=True (or open a new file)."
        )
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for coll in (bpy.data.objects, bpy.data.collections, bpy.data.meshes, bpy.data.armatures,
                 bpy.data.materials, bpy.data.images, bpy.data.cameras, bpy.data.lights,
                 bpy.data.worlds, bpy.data.actions):
        for block in list(coll):
            coll.remove(block)


def collection(name: str):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def empty(name: str, col, parent=None, location=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_size = 0.5
    obj.location = location
    obj.parent = parent
    col.objects.link(obj)
    return obj


def _select(objects, active=None) -> None:
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = active or objects[0]


# --- colors and materials --------------------------------------------------------


def srgb(r: float, g: float, b: float) -> tuple[float, float, float]:
    """sRGB 0-255 -> linear 0-1 (what Blender shaders and vertex colors expect)."""
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (lin(r), lin(g), lin(b))


def principled(mat):
    for node in mat.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            return node
    raise ValueError(f"{mat.name}: no Principled BSDF")


def material(name: str, color, roughness: float = 0.8, metallic: float = 0.0):
    """Flat Principled material. `color` is sRGB 0-255. Add nodes to
    mat.node_tree afterwards for procedural detail (it is baked by bake_atlas)."""
    mat = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):
        mat.use_nodes = True
    lin = srgb(*color)
    mat.diffuse_color = (*lin, 1.0)
    bsdf = principled(mat)
    bsdf.inputs["Base Color"].default_value = (*lin, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


# --- meshes ----------------------------------------------------------------------


def mesh_object(name: str, bm, materials, col, origin=(0, 0, 0), parent=None, smooth: bool = True):
    """Turn a bmesh (built in model space) into an object whose origin sits at
    `origin` (model space): the pivot Roblox keeps as MeshPart.PivotOffset.
    Frees the bmesh."""
    origin = Vector(origin)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.translate(bm, vec=-origin, verts=bm.verts[:])
    for f in bm.faces:
        f.smooth = smooth
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in materials:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    if obj.name != name:  # Blender appended .001: something else already has the name
        bpy.data.objects.remove(obj)
        raise ValueError(f"an object named {name} already exists; part names must be unique "
                         f"(a root empty cannot share its name with a part)")
    col.objects.link(obj)
    obj.parent = parent
    bpy.context.view_layer.update()
    # origin is given in model space; the parent may itself be offset
    obj.location = (parent.matrix_world.inverted() @ origin) if parent else origin
    return obj


def vertex_colors(objects, name: str = "Color") -> None:
    """Untextured route: copy each face's material color into a color attribute
    (Roblox shows it without any texture). Do not combine with bake_atlas:
    Roblox multiplies vertex colors into the texture."""
    for obj in objects:
        me = obj.data
        if name in me.color_attributes:
            me.color_attributes.remove(me.color_attributes[name])
        attr = me.color_attributes.new(name, "BYTE_COLOR", "CORNER")
        colors = []
        for poly in me.polygons:
            mat = me.materials[poly.material_index]
            c = principled(mat).inputs["Base Color"].default_value
            colors.extend((c[0], c[1], c[2], 1.0) * poly.loop_total)
        attr.data.foreach_set("color", colors)
        me.update()


def tri_count(obj) -> int:
    return sum(p.loop_total - 2 for p in obj.data.polygons)


def bounds(objects) -> tuple[Vector, Vector]:
    bpy.context.view_layer.update()
    lo = Vector((math.inf,) * 3)
    hi = -lo
    for obj in objects:
        for v in obj.data.vertices:
            w = obj.matrix_world @ v.co
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


# --- texturing ---------------------------------------------------------------------


def unwrap_atlas(objects, margin: float = 0.02, angle: float = 66.0) -> None:
    """One shared 0-1 UV layout for every object, so the model needs a single
    texture set. Mark seams and call bpy.ops.uv.unwrap yourself instead when a
    part needs hand-placed islands; this is the automatic route."""
    _select(objects)
    for obj in objects:
        if not obj.data.uv_layers:
            obj.data.uv_layers.new(name="UVMap")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")


def _image(name: str, size: int, data: bool, fill):
    img = bpy.data.images.new(name, size, size, alpha=False)
    img.generated_color = fill
    img.colorspace_settings.name = "Non-Color" if data else "sRGB"
    return img


def _save(img, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    return str(path)


def _materials(objects):
    seen = []
    for obj in objects:
        for mat in obj.data.materials:
            if mat and mat not in seen:
                seen.append(mat)
    return seen


def _output(mat):
    for node in mat.node_tree.nodes:
        if node.type == "OUTPUT_MATERIAL" and node.is_active_output:
            return node
    raise ValueError(f"{mat.name}: no material output")


def _bake(objects, img, bake_type: str, socket: str | None = None, **kw) -> None:
    """Bake into `img`. With `socket`, that Principled input is routed through
    an Emission shader first, which bakes its exact value (the diffuse pass
    turns metals black, and metallic has no bake pass of its own)."""
    mats = _materials(objects)
    undo = []
    for mat in mats:
        tree = mat.node_tree
        target = tree.nodes.new("ShaderNodeTexImage")
        target.image = img
        for node in tree.nodes:
            node.select = False
        target.select = True
        tree.nodes.active = target
        emit = None
        surface = None
        if socket:
            out = _output(mat)
            surface = out.inputs["Surface"].links[0].from_socket
            sock = principled(mat).inputs[socket]
            emit = tree.nodes.new("ShaderNodeEmission")
            if sock.is_linked:
                tree.links.new(sock.links[0].from_socket, emit.inputs["Color"])
            else:
                v = sock.default_value
                emit.inputs["Color"].default_value = (v, v, v, 1.0) if isinstance(v, float) else tuple(v)
            tree.links.new(emit.outputs[0], out.inputs["Surface"])
        undo.append((mat, target, emit, surface))
    try:
        bpy.ops.object.bake(type=bake_type, use_clear=False, **kw)
    finally:
        for mat, target, emit, surface in undo:
            tree = mat.node_tree
            if emit:
                tree.links.new(surface, _output(mat).inputs["Surface"])
                tree.nodes.remove(emit)
            tree.nodes.remove(target)


def bake_atlas(objects, name: str, out_dir, size: int = 1024,
               maps=("color", "roughness", "metallic"), ao: float = 0.0,
               high=None, cage: float = 0.05, samples: int = 16, margin: int | None = None) -> dict:
    """Bake the objects' materials into one texture set and replace them with a
    single textured material `<name>` that the exporters embed.

    maps:  any of "color", "roughness", "metallic", "normal". Color alone is a
           plain texture (MeshPart.TextureID); adding the others makes Roblox
           build a SurfaceAppearance (PBR).
    ao:    0-1, how strongly ambient occlusion darkens the color map (gives
           flat-colored stylized models some depth).
    high:  detailed source objects; the normal map is then baked from them onto
           `objects` (selected-to-active, `cage` = ray extrusion in studs).
           Without it the normal map only holds bump/normal detail from the
           materials' own nodes, so leave "normal" out for flat materials.
    Returns {map: png path}. Needs UVs: call unwrap_atlas first.
    """
    out_dir = Path(out_dir)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    margin = margin if margin is not None else max(2, size // 128)
    for obj in objects:
        if not obj.data.uv_layers:
            raise ValueError(f"{obj.name}: no UVs; call unwrap_atlas first")
        for attr in list(obj.data.color_attributes):
            obj.data.color_attributes.remove(attr)  # would multiply the texture in Roblox
    _select(objects)

    images, paths = {}, {}
    if "color" in maps:
        img = images["color"] = _image(f"{name}_color", size, False, (0, 0, 0, 1))
        _bake(objects, img, "EMIT", "Base Color", margin=margin)
        if ao > 0:
            occ = _image(f"{name}_ao", size, True, (1, 1, 1, 1))
            scene.cycles.samples = max(samples, 32)
            _bake(objects, occ, "AO", margin=margin)
            scene.cycles.samples = samples
            px = np.empty(size * size * 4, dtype=np.float32)
            shade = np.empty_like(px)
            img.pixels.foreach_get(px)
            occ.pixels.foreach_get(shade)
            px = px.reshape(-1, 4)
            px[:, :3] *= 1.0 - ao * (1.0 - shade.reshape(-1, 4)[:, :1])
            img.pixels.foreach_set(px.ravel())
            bpy.data.images.remove(occ)
    if "roughness" in maps:
        img = images["roughness"] = _image(f"{name}_roughness", size, True, (0.8, 0.8, 0.8, 1))
        _bake(objects, img, "EMIT", "Roughness", margin=margin)
    if "metallic" in maps:
        img = images["metallic"] = _image(f"{name}_metallic", size, True, (0, 0, 0, 1))
        _bake(objects, img, "EMIT", "Metallic", margin=margin)
    if "normal" in maps:
        img = images["normal"] = _image(f"{name}_normal", size, True, (0.5, 0.5, 1, 1))
        if high:
            for obj in objects:  # each low part catches rays from the high meshes
                _select([*high, obj], active=obj)
                _bake([obj], img, "NORMAL", margin=margin, use_selected_to_active=True,
                      cage_extrusion=cage, max_ray_distance=cage * 2)
            _select(objects)
        else:
            _bake(objects, img, "NORMAL", margin=margin)  # tangent space, +X +Y +Z = OpenGL
    for key, img in images.items():
        paths[key] = _save(img, out_dir / f"{name}_{key}.png")

    baked = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):
        baked.use_nodes = True
    tree = baked.node_tree
    bsdf = principled(baked)
    bsdf.inputs["Roughness"].default_value = 0.8
    wires = {"color": "Base Color", "roughness": "Roughness", "metallic": "Metallic"}
    for i, (key, img) in enumerate(images.items()):
        tex = tree.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.location = (-600, 300 - i * 280)
        if key == "normal":
            nm = tree.nodes.new("ShaderNodeNormalMap")
            nm.location = (-300, 300 - i * 280)
            tree.links.new(tex.outputs["Color"], nm.inputs["Color"])
            tree.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
        else:
            tree.links.new(tex.outputs["Color"], bsdf.inputs[wires[key]])
    old = _materials(objects)
    for obj in objects:
        obj.data.materials.clear()
        obj.data.materials.append(baked)
        for poly in obj.data.polygons:
            poly.material_index = 0
        obj.data.update()
    for mat in old:
        if mat.users == 0:
            bpy.data.materials.remove(mat)
    return paths


# --- rigging (skinned route) ---------------------------------------------------------


def armature(name: str, bones: dict, col, parent=None):
    """bones: {bone: (head, tail, parent bone or None)} in model space, listed
    parent-first. The first bone is the root: keep it at the model origin and
    unweighted. Returns the armature object (identity transform)."""
    arm = bpy.data.objects.new(name, bpy.data.armatures.new(name))
    col.objects.link(arm)
    arm.parent = parent
    _select([arm])
    bpy.ops.object.mode_set(mode="EDIT")
    for bone, (head, tail, up) in bones.items():
        eb = arm.data.edit_bones.new(bone)
        eb.head, eb.tail = Vector(head), Vector(tail)
        if up:
            eb.parent = arm.data.edit_bones[up]
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def skin(obj, arm, weights=None) -> None:
    """Bind a mesh to an armature. `weights` is fn(vertex position in model
    space) -> {bone: weight}; without it Blender's automatic weights are used.
    Weights are limited to 4 bones per vertex and normalized (Roblox limits)."""
    if weights is None:
        _select([obj, arm], active=arm)
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    else:
        obj.parent = arm
        mod = obj.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        groups = {b.name: obj.vertex_groups.new(name=b.name) for b in arm.data.bones}
        world = obj.matrix_world
        for v in obj.data.vertices:
            w = weights(world @ v.co)
            top = sorted(w.items(), key=lambda kv: -kv[1])[:MAX_INFLUENCES]
            total = sum(x for _, x in top) or 1.0
            for bone, x in top:
                if x > 0:
                    groups[bone].add([v.index], x / total, "REPLACE")
    _select([obj])
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=MAX_INFLUENCES)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)


# --- checks --------------------------------------------------------------------------


def validate(objects, arm=None, textured: bool = False, tri_budget: int | None = None) -> list[str]:
    """Problems that break or degrade a Roblox import. Empty list = clean."""
    problems = []
    for obj in objects:
        me = obj.data
        tris = tri_count(obj)
        if tris > TRI_LIMIT:
            problems.append(f"{obj.name}: {tris} tris exceeds Roblox's {TRI_LIMIT} per mesh; split or simplify")
        elif tri_budget and tris > tri_budget:
            problems.append(f"{obj.name}: {tris} tris is over the {tri_budget} budget")
        if "." in obj.name:
            problems.append(f"{obj.name}: rename; the name becomes the MeshPart name used by game code")
        if any(abs(s - 1) > 1e-5 for s in obj.scale) or any(abs(r) > 1e-5 for r in obj.rotation_euler):
            problems.append(f"{obj.name}: unapplied rotation/scale; bake it into the mesh")
        if any(p.area < 1e-10 for p in me.polygons):
            problems.append(f"{obj.name}: zero-area faces")
        if textured:
            if not me.uv_layers:
                problems.append(f"{obj.name}: no UVs")
            else:
                uv = [0.0] * (len(me.loops) * 2)
                me.uv_layers.active.data.foreach_get("uv", uv)
                if uv and (min(uv) < -1e-4 or max(uv) > 1 + 1e-4):
                    problems.append(f"{obj.name}: UVs outside 0-1")
            if len(me.materials) != 1:
                problems.append(f"{obj.name}: {len(me.materials)} materials; a textured MeshPart takes one")
        if arm and obj.vertex_groups:
            names = {b.name for b in arm.data.bones}
            for v in me.vertices:
                gs = [g for g in v.groups if obj.vertex_groups[g.group].name in names and g.weight > 0]
                if not gs:
                    problems.append(f"{obj.name}: vertex {v.index} has no bone weight")
                    break
                if len(gs) > MAX_INFLUENCES:
                    problems.append(f"{obj.name}: vertex {v.index} has {len(gs)} influences (max {MAX_INFLUENCES})")
                    break
    if arm:
        if any(abs(s - 1) > 1e-5 for s in arm.scale) or any(abs(r) > 1e-5 for r in arm.rotation_euler):
            problems.append(f"{arm.name}: armature object must have rotation 0 and scale 1")
        root = arm.data.bones[0]
        if (arm.matrix_world @ root.head_local).length > 1e-4:
            problems.append(f"{arm.name}: root bone {root.name} should sit at the model origin")
    return problems


# --- export ----------------------------------------------------------------------------


def _fingerprint(root, objects, arm, textured: bool, suffix: str) -> str:
    """Hash of everything the export depends on. The FBX exporter stamps the
    current time into the file, so file hashes change on every rebuild; this
    lets export_model leave an unchanged model's file alone."""
    h = hashlib.sha256(f"{suffix}|{textured}|{root.name if root else None}".encode())

    def feed(data, attr, kind, width=1):
        buf = np.empty(len(data) * width, dtype=kind)
        data.foreach_get(attr, buf)
        h.update(np.round(buf, 5).tobytes() if kind == np.float32 else buf.tobytes())

    bpy.context.view_layer.update()
    for obj in sorted(objects, key=lambda o: o.name):
        me = obj.data
        h.update(f"{obj.name}|{obj.parent.name if obj.parent else None}|".encode())
        h.update(np.round(np.array(obj.matrix_world, dtype=np.float32), 5).tobytes())
        feed(me.vertices, "co", np.float32, 3)
        feed(me.loops, "vertex_index", np.int32)
        feed(me.polygons, "loop_total", np.int32)
        feed(me.polygons, "material_index", np.int32)
        feed(me.polygons, "use_smooth", bool)
        for uv in me.uv_layers:
            feed(uv.data, "uv", np.float32, 2)
        for attr in me.color_attributes:
            feed(attr.data, "color", np.float32, 4)
        for v in me.vertices:
            for g in v.groups:
                h.update(f"{v.index}:{obj.vertex_groups[g.group].name}:{g.weight:.5f}".encode())
        for mat in me.materials:
            h.update(mat.name.encode())
            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image:
                    px = np.empty(len(node.image.pixels), dtype=np.float32)
                    node.image.pixels.foreach_get(px)
                    h.update(node.image.name.encode() + np.round(px, 4).tobytes())
                elif node.type == "BSDF_PRINCIPLED":
                    for key in ("Base Color", "Roughness", "Metallic"):
                        v = node.inputs[key].default_value
                        h.update(repr([round(c, 5) for c in v] if hasattr(v, "__len__") else round(v, 5)).encode())
    if arm:
        for bone in arm.data.bones:
            h.update(f"{bone.name}|{bone.parent.name if bone.parent else None}|".encode())
            h.update(np.round(np.array(arm.matrix_world @ bone.matrix_local, dtype=np.float32), 5).tobytes())
            h.update(np.round(np.array(bone.tail_local, dtype=np.float32), 5).tobytes())
    return h.hexdigest()


def export_model(path, root, objects, arm=None, textured: bool = False) -> str:
    """Write .fbx (preferred) or .glb under assets/. Textures from bake_atlas
    are embedded in the file, so they upload with the model. Both land 1:1 in
    Roblox; .glb drops object origins (pivots) and adds a `<Name>_Node` model
    around each mesh, so use it only for single static meshes."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = (_CACHE_DIR or path.parent) / f"{path.name}.fingerprint"
    fingerprint = _fingerprint(root, objects, arm, textured, path.suffix.lower())
    if path.exists() and stamp.exists() and stamp.read_text().strip() == fingerprint:
        EXPORTS[str(path)] = "unchanged"  # same file hash, so `chainlink assets` will not re-upload it
        return str(path)
    everything = [o for o in (root, arm, *objects) if o is not None]
    _select(everything, active=root or objects[0])
    if path.suffix.lower() == ".fbx":
        kwargs = dict(
            filepath=str(path),
            use_selection=True,
            object_types={"EMPTY", "MESH", "ARMATURE"},
            global_scale=0.01,  # Blender writes cm; Roblox reads 1 FBX unit as 1 stud (default = 100x too big)
            mesh_smooth_type="FACE",
            use_triangles=True,
            use_tspace=textured,
            colors_type="SRGB",
            add_leaf_bones=False,
            bake_anim=False,
            path_mode="COPY",
            embed_textures=textured,
        )
        bpy.ops.export_scene.fbx(**kwargs)
    elif path.suffix.lower() == ".glb":
        bpy.ops.export_scene.gltf(
            filepath=str(path),
            export_format="GLB",
            use_selection=True,
            export_yup=True,
            export_apply=True,
            export_animations=False,
            export_tangents=textured,
            export_image_format="AUTO",
            export_vertex_color="NONE" if textured else "ACTIVE",
            export_all_vertex_colors=not textured,
        )
    else:
        raise ValueError(f"{path.name}: export .fbx or .glb")
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(fingerprint + "\n")
    EXPORTS[str(path)] = "written"
    return str(path)


# --- previews ---------------------------------------------------------------------------


def render_previews(out_dir, name: str, objects, views=None, size=(800, 800)) -> list[str]:
    """EEVEE orthographic turnaround, framed on the model. Read the PNGs to
    judge silhouette, proportions and texture before exporting."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.image_settings.file_format = "PNG"
    try:
        scene.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    col = bpy.data.collections.get("Preview") or collection("Preview")
    world = bpy.data.worlds.get("PreviewWorld") or bpy.data.worlds.new("PreviewWorld")
    scene.world = world
    if bpy.app.version < (5, 0, 0):
        world.use_nodes = True
    for node in world.node_tree.nodes:
        if node.type == "BACKGROUND":
            node.inputs["Color"].default_value = (0.78, 0.82, 0.88, 1)
            node.inputs["Strength"].default_value = 0.7

    lo, hi = bounds(objects)
    target = (lo + hi) / 2
    extent = max((hi - lo).length, 0.1)

    def aim(obj, at):
        obj.rotation_euler = (Vector(at) - obj.location).to_track_quat("-Z", "Y").to_euler()

    if not any(o.type == "LIGHT" for o in col.objects):
        for lname, d, energy in (("Key", (-6, -9, 12), 3.2), ("Fill", (8, -5, 4), 1.0), ("Rim", (3, 9, 8), 1.6)):
            light = bpy.data.objects.new(lname, bpy.data.lights.new(lname, "SUN"))
            light.data.energy = energy
            light.location = target + Vector(d).normalized() * extent * 3
            aim(light, target)
            col.objects.link(light)
    cam = bpy.data.objects.get("PreviewCam")
    if cam is None:
        cam = bpy.data.objects.new("PreviewCam", bpy.data.cameras.new("PreviewCam"))
        col.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = extent * 1.15
    cam.data.clip_end = extent * 10
    scene.camera = cam

    views = views or {"front": 0, "three_quarter": 35, "side": 90, "back": 180}
    rendered = []
    for view, az in views.items():
        a = math.radians(az)
        cam.location = target + Vector((math.sin(a), -math.cos(a), 0.25)).normalized() * extent * 3
        aim(cam, target)
        scene.render.filepath = str(out_dir / f"{name.lower()}_{view}.png")
        bpy.ops.render.render(write_still=True)
        rendered.append(scene.render.filepath)
    a = math.radians(35)
    cam.location = target + Vector((math.sin(a), -math.cos(a), 0.25)).normalized() * extent * 3
    aim(cam, target)
    return rendered


# --- finish ------------------------------------------------------------------------------


def show_materials() -> None:
    """Live sessions: switch every 3D viewport to Material Preview, so viewport
    screenshots show the baked textures instead of grey Solid shading."""
    if not is_live():
        return
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        space.shading.type = "MATERIAL"


def finish(name: str, blend_path, objects, arm=None, **extra) -> dict:
    """Save the .blend and return/print the build report. `extra` carries
    whatever the generator wants recorded (model path, textures, renders,
    problems)."""
    global LAST_REPORT
    lo, hi = bounds(objects)
    report = {
        "name": name,
        "blender": bpy.app.version_string,
        "size_studs": [round(c, 3) for c in (hi - lo)],
        "bounds_min": [round(c, 3) for c in lo],
        "bounds_max": [round(c, 3) for c in hi],
        "parts": {
            o.name: {
                "tris": tri_count(o),
                "verts": len(o.data.vertices),
                "pivot": [round(c, 3) for c in o.matrix_world.translation],
            }
            for o in objects
        },
        "total_tris": sum(tri_count(o) for o in objects),
        "bones": [b.name for b in arm.data.bones] if arm else [],
        "exports": dict(EXPORTS),
        **extra,
    }
    blend_path = Path(blend_path)
    blend_path.parent.mkdir(parents=True, exist_ok=True)
    show_materials()
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    report["blend"] = str(blend_path)
    LAST_REPORT = report
    print("CLMODEL_REPORT " + json.dumps(report))
    return report
