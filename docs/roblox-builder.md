# Roblox Model XML skill

Generates, edits and validates Roblox model XML (`.rbxmx`) from a hierarchy or JSON spec, so Claude can produce importable prefabs, scripts and instances without opening Studio. It ships with a standard-library-only Python helper, `build_rbxmx.py`.

Invoke it directly with `/roblox-builder`.

## Contents

| File | Purpose |
|---|---|
| `SKILL.md` | Format reference, enum table, workflow and output policy |
| `build_rbxmx.py` | Builder, serializer and validator (Python 3, stdlib only) |
| `spec_example.json` | Example JSON spec |
| `README.md` | Helper usage notes |

## Workflow

1. Plan the instance hierarchy and every reference (including `PrimaryPart`).
2. Build it with `build_rbxmx.py` as a library or from a JSON spec, or hand-write the XML.
3. Validate: well-formed XML, unique referents, every non-null `Ref` target exists, sensible property types and enum values.
4. Write the file and confirm it exists.
5. Summarize the hierarchy and report the final written path.

## Output policy

- Default: `prefab/<ModelName>.rbxmx` relative to the project root, created if missing. This is the `prefab/` folder that [ChainLink](chainlink.md) syncs to `ServerStorage`.
- A user-specified path (absolute or relative) overrides the default; parent directories are created.
- Existing files are never overwritten silently. Pass `--force` (CLI) or `force=True` (API) only when authorized.

## CLI

```sh
python build_rbxmx.py --example                         # write a demo model
python build_rbxmx.py spec.json -o prefab/Custom.rbxmx  # build from a spec
```

| Flag | Meaning |
|---|---|
| `spec` | JSON file describing an instance tree |
| `-o`, `--output` | Output `.rbxmx` path |
| `--force` | Allow overwriting an existing file |
| `--example` | Write a demo model |

Validate an existing file:

```sh
python -c 'from build_rbxmx import validate_rbxmx; validate_rbxmx("prefab/DemoModel.rbxmx"); print("valid")'
```

## JSON spec

Each node has `class`, `name`, optional `props` and `children`. Typed properties use `{"$type": ..., "value": ...}`. A model's `primary_part` names a child part.

```json
{
  "class": "Model",
  "name": "SpecDemo",
  "primary_part": "Core",
  "children": [
    {
      "class": "Part",
      "name": "Core",
      "props": {
        "Anchored": {"$type": "bool", "value": true},
        "Size": {"$type": "Vector3", "value": [4, 2, 4]},
        "CFrame": {"$type": "CoordinateFrame", "value": [0, 3, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1]},
        "Material": {"$type": "token", "value": 256},
        "Color": {"$type": "Color3uint8", "value": [70, 130, 180]}
      }
    },
    {
      "class": "Folder",
      "name": "Contents",
      "children": [
        {
          "class": "ModuleScript",
          "name": "Config",
          "props": {"Source": {"$type": "ProtectedString", "value": "return { Enabled = true }"}}
        }
      ]
    }
  ]
}
```

## Python API

Import `Instance`, `part`, `model`, `script` and `folder`. Add children with `.add()`, set typed properties with helpers, then call `write_model(root, out=None, force=False)`, which creates parent directories, prints and returns the written path, and refuses to overwrite unless `force=True`.

| Helper | XML type |
|---|---|
| `string_prop`, `bool_prop`, `int_prop`, `int64_prop`, `float_prop` | scalars |
| `vector3_prop` | `Vector3` |
| `coordinateframe_prop` / `cframe_prop` | `CoordinateFrame` (position plus nine row-major rotation values) |
| `color3_prop`, `color3uint8_prop`, `brickcolor_prop` | colors |
| `udim2_prop` | `UDim2` |
| `token_prop` | enum token (integer value) |
| `ref_prop` | `Ref` to another item's referent, or `null` |

## Format essentials

- Each instance is `<Item class="..." referent="RBX...">` with a `<Properties>` child; referents must be unique.
- Children nest inside their parent's `<Item>`.
- `PrimaryPart` and other `Ref` properties must target an existing referent or be `null`.
- Script source is a `<ProtectedString name="Source">`.
- Enum properties use `<token>` with the integer value.

### Common enum values

| Material | Value | Material | Value |
|---|---:|---|---:|
| Plastic | 256 | Wood | 512 |
| SmoothPlastic | 272 | Neon | 288 |
| Marble | 784 | Slate | 800 |
| Concrete | 816 | Granite | 832 |
| Brick | 848 | Metal | 1088 |
| Grass | 1280 | Sand | 1296 |
| Fabric | 1312 | Ice | 1536 |
| Glass | 1568 | | |

`Shape` and `PartType`: Ball `0`, Block `1`, Cylinder `2`.

Verify Roblox-specific properties and enum values against the target Studio version when exact engine behavior matters.
