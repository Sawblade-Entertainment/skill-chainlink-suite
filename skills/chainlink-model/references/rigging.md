# Rigging for Roblox

Two routes. Both were verified through `chainlink assets` (FBX).

## Rigid parts (default)

Each body segment is its own object, parented to a root empty named after the character, with its origin on the joint it rotates around. No armature, no weights.

```python
root = cl.empty("Kairo", col)
torso = cl.mesh_object("Torso", bm_torso, mats, col, origin=(0, 0, 3.05), parent=root)
arm_l = cl.mesh_object("LeftArm", bm_arm_l, mats, col, origin=(0.64, 0, 4.70), parent=root)   # shoulder
```

- Build every part in model space in the rest pose; `mesh_object` moves the geometry so the origin lands on `origin`.
- Name parts for what game code expects (`Head`, `Torso`, `LeftArm`, `RightArm`, `LeftLeg`, `RightLeg`, ...). Left is +X in Blender when the character faces -Y.
- Overlap neighbouring parts a little at the joint (a ball or sleeve inside the parent) so rotation never opens a gap.
- Rest pose: arms slightly away from the body, legs straight, so each part's silhouette and pivot are unambiguous.

In Roblox each MeshPart keeps its joint as `PivotOffset`. Game code connects them; if the project already has a rig module, use it. Otherwise:

```lua
-- parent and child are MeshParts from the loaded model, still in their imported rest pose
local function joint(parent: MeshPart, child: MeshPart): Motor6D
	local motor = new "Motor6D"
	motor.Name = child.Name
	motor.Part0 = parent
	motor.Part1 = child
	motor.C1 = child.PivotOffset
	motor.C0 = parent.CFrame:ToObjectSpace(child.CFrame * child.PivotOffset)
	motor.Parent = parent
	return motor
end
```

Posing is then `motor.Transform = CFrame.Angles(...)` (or `motor.C0` for code-driven rigs that do not use an Animator). Anchor only the root part.

## Skinned (deforming) meshes

One mesh bound to an armature. Roblox imports it as a single MeshPart containing a `Bone` hierarchy, plus an `AnimationController` and an `InitialPoses` folder in the model; `Model.PrimaryPart` is set to the mesh. The armature object itself does not appear.

```python
bones = {
    "Root":  ((0, 0, 0),   (0, 0.3, 0), None),      # at the model origin, never weighted
    "Tail1": ((0, 0, 0),   (0, 0, 1.4), "Root"),
    "Tail2": ((0, 0, 1.4), (0, 0, 2.7), "Tail1"),
    "Tail3": ((0, 0, 2.7), (0, 0, 4.0), "Tail2"),
}
arm = cl.armature("Tail", bones, col)

def weights(p):                                      # p: vertex position in model space
    return {"Tail1": ..., "Tail2": ..., "Tail3": ...}

cl.skin(mesh, arm, weights)                          # or cl.skin(mesh, arm) for automatic weights
problems = cl.validate([mesh], arm=arm)
cl.export_model(path, None, [mesh], arm=arm)
```

Rules Roblox enforces or punishes:

- At most 4 bones per vertex, weights normalized (`skin` does both).
- Armature object at rotation 0, scale 1; root bone at the origin with no weights.
- Every vertex weighted to something, or it stays behind when the mesh moves.
- Unique bone names; they become `Bone.Name` and are how code finds them.
- Add edge loops where the mesh bends (two or three around each joint); a tube with no loops at the elbow cannot bend there.

Scripted weights (a function of position) are predictable and reproducible, which suits tails, capes, tentacles and limbs. Automatic weights (`skin(mesh, arm)`) are quicker for organic bodies; check the deformation by posing a bone in Blender (`arm.pose.bones["Tail2"].rotation_euler`) and rendering before exporting.

In game, pose with `bone.Transform = CFrame.Angles(...)` every frame, or play animations through the `AnimationController`. Skinned meshes only deform on the client's render; do not rely on bone positions for gameplay collision.

## Choosing

Rigid parts are cheaper, never deform badly, and suit code-driven pose data and chunky styles. Use skinning for the pieces that must bend smoothly, and keep them as separate skinned meshes attached to a rigid body where possible (a cape MeshPart joined to `Torso`) rather than skinning the whole character.
