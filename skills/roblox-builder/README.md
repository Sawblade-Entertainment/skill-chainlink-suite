# Roblox Model XML builder

A Python 3 standard-library-only helper for constructing, serializing, and validating Roblox `.rbxmx` models.

## CLI
From a project root, use the bundled script:

```sh
python /path/to/roblox-builder/build_rbxmx.py --example
python /path/to/roblox-builder/build_rbxmx.py /path/to/spec.json -o prefab/Custom.rbxmx
```

Without `-o`, output is `prefab/<ModelName>.rbxmx` under the current working directory. Existing files are protected; pass `--force` to authorize overwriting. `--example` emits a demo. Validate an existing file with:

```sh
python -c 'from build_rbxmx import validate_rbxmx; validate_rbxmx("prefab/DemoModel.rbxmx"); print("valid")'
```

## Python API
Import `Instance`, `part`, `model`, `script`, and `folder` from `build_rbxmx.py`. Add children with `.add()`, use typed helpers such as `vector3_prop`, `coordinateframe_prop`, `color3uint8_prop`, `token_prop`, and `ref_prop`, then call `write_model(root, out=None)`. `write_model` creates parent directories, prints and returns the written path, and refuses an existing file unless called with `force=True`. See `spec_example.json` and `SKILL.md` for details.