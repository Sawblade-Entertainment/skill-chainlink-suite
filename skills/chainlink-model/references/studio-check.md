# Checking an uploaded model in Studio

Run this after `chainlink assets`, through the Roblox Studio MCP. It confirms the things Blender cannot: that scale, axes, part names, pivots, textures and bones survived the import.

Work in Edit mode, in a scratch folder that is never saved, far from the map, and delete it afterwards. Call `list_roblox_studios` first; if several are open, pick the one for this project by name.

## 1. Load

Take the ID from `assets.lock.json` (key = path under `assets/`).

```lua
local id = 1234567890            -- from assets.lock.json
local old = workspace:FindFirstChild("__ModelCheck")
if old then old:Destroy() end
local folder = Instance.new("Folder")
folder.Name = "__ModelCheck"
folder.Archivable = false          -- never saved or published with the place
folder.Parent = workspace
local ok, objs = pcall(function() return game:GetObjects("rbxassetid://" .. id) end)
if not ok then return "load failed: " .. tostring(objs) end
for _, o in objs do o.Parent = folder end
return "loaded " .. #objs
```

`Requester does not have permission for Asset` means the place's owner is not the asset's owner and the experience has not been given access. Use the MCP's `insert_asset` tool instead (`assetType = "Model"`, `parentPath = "game.Workspace.__ModelCheck"`): inserting through Studio grants the open experience access to that asset, after which `GetObjects` and runtime `InsertService:LoadAsset` work. That grant is a change to the user's experience, so mention it. A just-uploaded asset can also take a few seconds to become loadable; retry once before concluding anything.

## 2. Inspect

```lua
local out = {}
local function describe(inst, depth)
	local line = string.rep("  ", depth) .. inst.ClassName .. " " .. inst.Name
	if inst:IsA("MeshPart") then
		line ..= string.format(" size=(%.2f, %.2f, %.2f) pivotOffset=(%s)", inst.Size.X, inst.Size.Y, inst.Size.Z, tostring(inst.PivotOffset.Position))
	elseif inst:IsA("SurfaceAppearance") then
		line ..= string.format(" color=%s normal=%s rough=%s metal=%s", inst.ColorMap, inst.NormalMap, inst.RoughnessMap, inst.MetalnessMap)
	elseif inst:IsA("Bone") then
		line ..= string.format(" world=(%.2f, %.2f, %.2f)", inst.WorldPosition.X, inst.WorldPosition.Y, inst.WorldPosition.Z)
	elseif inst:IsA("Model") then
		local _, size = inst:GetBoundingBox()
		line ..= string.format(" bbox=(%.2f, %.2f, %.2f)", size.X, size.Y, size.Z)
	end
	table.insert(out, line)
	for _, child in inst:GetChildren() do
		if not child:IsA("CFrameValue") then describe(child, depth + 1) end
	end
end
for _, m in workspace.__ModelCheck:GetChildren() do describe(m, 0) end
return table.concat(out, "\n")
```

Compare with the `CLMODEL_REPORT`:

| Check | Expect |
|---|---|
| Model `bbox` | The report's `size_studs` with Y and Z swapped (Blender Z-up -> Roblox Y-up). 100x too big means the FBX was exported without `global_scale=0.01` |
| MeshPart names | Exactly the Blender object names |
| `pivotOffset` | Non-zero wherever the origin was not the bounding-box centre; all zeros on a `.glb` (pivots are lost) |
| `SurfaceAppearance` | Present with every baked map on textured models; absent on vertex-color models |
| `Bone` tree | Same names and parenting as the armature; world positions match the bone heads |

## 3. Look

Anchor the parts, move the model somewhere empty, and capture it. For a skinned mesh, pose a bone to see it deform.

```lua
local model = workspace.__ModelCheck:GetChildren()[1]
for _, d in model:GetDescendants() do
	if d:IsA("BasePart") then d.Anchored = true end
end
model:PivotTo(CFrame.new(0, 3000, 0))
```

Then `screen_capture` with `camera_position = [6, 3006, -14]` and `look_at_position = [0, 3002, 0]`, scaled to the model's size. The camera sits on the -Z side because that is the model's front. Check: facing, colors and texture orientation, no missing (inside-out) faces, metal and roughness reading as intended under Studio lighting.

## 4. Clean up

```lua
workspace.__ModelCheck:Destroy()
```

Report what was confirmed and anything that differed. If something is wrong, fix the generator and rebuild rather than patching the instance in Studio: the next upload would lose a manual fix.
