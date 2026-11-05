---
name: roblox-builder
description: Build, edit, validate, or generate Roblox model XML (.rbxmx) assets from a hierarchy or JSON specification. Use when a user asks for importable Roblox models, instances, parts, scripts, or other .rbxmx content.
---

# Roblox Model XML (.rbxmx)

## When to use
Use this skill when creating or updating a Roblox model file (`.rbxmx`) containing instances and their properties. It is suitable for programmatic prefabs, simple scene hierarchies, and model assets. Verify Roblox-specific properties and enum values against the target Studio/runtime when exact engine behavior matters.

## Format essentials
An `.rbxmx` is XML. A typical file begins with this root element and metadata:

```xml
<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="http://www.roblox.com/roblox.xsd" version="4">
  <Meta name="ExplicitAutoJoints">true</Meta>
  <Item class="Model" referent="RBX..."><Properties>...</Properties></Item>
</roblox>
```

- Each instance is an `<Item class="..." referent="RBX...">` with a `<Properties>` child. The `referent` must be unique in the file.
- Properties use typed tags named for their Roblox XML serialization type, e.g. `<string name="Name">Tree</string>`, `<bool>`, `<int>`, `<int64>`, `<float>`, `<token>`, and `<Ref>`.
- `<Vector3>` contains `<X>`, `<Y>`, `<Z>`. `<CoordinateFrame>` serializes a CFrame as `<X>`, `<Y>`, `<Z>`, then `<R00>` through `<R22>` in row-major order.
- Color may be encoded as `<Color3uint8>` with a packed ARGB integer, or `<Color3>` with `<R>`, `<G>`, `<B>` floats. `BrickColor` is an integer; `UDim2` has `X` and `Y` UDim components.
- Enum-valued properties such as Material, Shape, and PartType use `<token>` with the corresponding integer enum value.
- Nest child `<Item>` elements inside their parent's `<Item>` to express hierarchy. `PrimaryPart` is a `<Ref name="PrimaryPart">` pointing to the referenced Part's referent. Other Ref properties must likewise target an existing referent or be `null`.
- Common classes include `Model`, `Part`, `MeshPart`, `Script`, `LocalScript`, `ModuleScript`, `Folder`, `Attachment`, `Weld`, and `SurfaceGui`. Script source is stored as `<ProtectedString name="Source">...</ProtectedString>`.

### Common enum values

| Enum | Value | Enum | Value |
|---|---:|---|---:|
| Material Plastic | 256 | Material Wood | 512 |
| Material Slate | 800 | Material Concrete | 816 |
| Material Metal | 1088 | Material Grass | 1280 |
| Material Neon | 288 | Material Glass | 1568 |
| Material SmoothPlastic | 272 | Material Brick | 848 |
| Material Granite | 832 | Material Marble | 784 |
| Material Sand | 1296 | Material Fabric | 1312 |
| Material Ice | 1536 | PartType Ball | 0 |
| PartType Block | 1 | PartType Cylinder | 2 |

`Shape` uses the same primitive tokens: Ball `0`, Block `1`, Cylinder `2`.

## Build, validate, and write workflow
1. Plan the instance hierarchy and identify all references (including `PrimaryPart`).
2. Build it with `build_rbxmx.py` (next to this file) as a Python library, from its JSON spec CLI, or hand-write XML.
3. Validate that the XML is well-formed, each item referent is unique, and every non-null Ref target exists. Also review property types/enum values.
4. Write the file and confirm the destination and existence.
5. Summarize the created hierarchy and **always report the final written path**.

### Output policy
By default, write to `prefab/` relative to the project root, creating it if missing, with filename `<ModelName>.rbxmx`. If the user specifies another path, absolute or relative and in any directory, write there instead and create parent directories as needed. Never overwrite an existing file without noting it; ask before overwrite or use an explicit force option only when authorized. Always report the final written path.

## Hand-written example
This compact example shows a Model with a Part and Script; production XML should include all required properties for its intended behavior and unique referents.

```xml
<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://www.roblox.com/roblox.xsd" version="4">
  <Meta name="ExplicitAutoJoints">true</Meta>
  <Item class="Model" referent="RBXMODEL1">
    <Properties><string name="Name">Sample</string><Ref name="PrimaryPart">RBXPART1</Ref></Properties>
    <Item class="Part" referent="RBXPART1">
      <Properties>
        <string name="Name">Block</string><bool name="Anchored">true</bool>
        <token name="Material">256</token><Vector3 name="Size"><X>4</X><Y>1</Y><Z>4</Z></Vector3>
      </Properties>
    </Item>
    <Item class="Script" referent="RBXSCRIPT1">
      <Properties><string name="Name">Hello</string><ProtectedString name="Source">print("Hello")</ProtectedString></Properties>
    </Item>
  </Item>
</roblox>
```