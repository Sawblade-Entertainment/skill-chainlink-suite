#!/usr/bin/env python3
"""Build and validate basic Roblox .rbxmx model files using only Python stdlib."""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional
from xml.dom import minidom

XMLNS_XMIME = "http://www.w3.org/2005/05/xmlmime"
XMLNS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA = "http://www.roblox.com/roblox.xsd"
ET.register_namespace("xmime", XMLNS_XMIME)
ET.register_namespace("xsi", XMLNS_XSI)


@dataclass
class Property:
    tag: str
    value: Any


def _tuple(value, size, label):
    if len(value) != size:
        raise ValueError(f"{label} must contain exactly {size} values")
    return tuple(value)


def string_prop(value): return Property("string", str(value))
def bool_prop(value): return Property("bool", bool(value))
def int_prop(value): return Property("int", int(value))
def int64_prop(value): return Property("int64", int(value))
def float_prop(value): return Property("float", float(value))
def vector3_prop(x, y=None, z=None):
    vals = _tuple(x if y is None and z is None else (x, y, z), 3, "Vector3")
    return Property("Vector3", tuple(float(v) for v in vals))
def coordinateframe_prop(position=(0, 0, 0), rotation=None):
    """Create a CFrame property; rotation is nine row-major R00..R22 values."""
    pos = _tuple(position, 3, "CFrame position")
    rot = _tuple(rotation or (1, 0, 0, 0, 1, 0, 0, 0, 1), 9, "CFrame rotation")
    return Property("CoordinateFrame", tuple(float(v) for v in pos + rot))
def cframe_prop(position=(0, 0, 0), rotation=None): return coordinateframe_prop(position, rotation)
def color3_prop(r, g=None, b=None):
    vals = _tuple(r if g is None and b is None else (r, g, b), 3, "Color3")
    return Property("Color3", tuple(float(v) for v in vals))
def color3uint8_prop(r, g=None, b=None, *, alpha=255):
    if g is None and b is None and not isinstance(r, (tuple, list)):
        val = int(r)
        if not 0 <= val <= 0xFFFFFFFF: raise ValueError("packed Color3uint8 must fit unsigned 32-bit")
        return Property("Color3uint8", val)
    vals = _tuple(r if g is None and b is None else (r, g, b), 3, "Color3uint8 RGB")
    vals = tuple(int(v) for v in vals)
    alpha = int(alpha)
    if any(v < 0 or v > 255 for v in vals) or not 0 <= alpha <= 255:
        raise ValueError("Color3uint8 channels must be in 0..255")
    return Property("Color3uint8", (alpha << 24) | (vals[0] << 16) | (vals[1] << 8) | vals[2])
def token_prop(value): return Property("token", int(value))
def ref_prop(target=None): return Property("Ref", target)
def udim2_prop(x=(0, 0), y=(0, 0)):
    return Property("UDim2", (_tuple(x, 2, "UDim2 X"), _tuple(y, 2, "UDim2 Y")))
def brickcolor_prop(value): return Property("BrickColor", int(value))


# Descriptive aliases matching property type names.
string = string_prop
boolean = bool_prop
integer = int_prop
integer64 = int64_prop
float32 = float_prop
vector3 = vector3_prop
coordinateframe = coordinateframe_prop
color3 = color3_prop
color3uint8 = color3uint8_prop
token = token_prop
ref = ref_prop
udim2 = udim2_prop
brickcolor = brickcolor_prop


class Instance:
    def __init__(self, class_name: str, name: str, **props):
        self.class_name = str(class_name)
        self.name = str(name)
        self.referent = "RBX" + uuid.uuid4().hex.upper()
        self.props: dict[str, Property] = {"Name": string_prop(self.name)}
        self.children: list[Instance] = []
        for key, value in props.items():
            self.set_property(key, value)

    def set_property(self, name: str, value):
        self.props[name] = value if isinstance(value, Property) else _infer_property(value)
        return self

    def add(self, child: "Instance"):
        if not isinstance(child, Instance): raise TypeError("child must be an Instance")
        self.children.append(child)
        return self


def _infer_property(value):
    if isinstance(value, bool): return bool_prop(value)
    if isinstance(value, int): return int_prop(value)
    if isinstance(value, float): return float_prop(value)
    if isinstance(value, str): return string_prop(value)
    if isinstance(value, (tuple, list)) and len(value) == 3: return vector3_prop(value)
    raise TypeError(f"Unsupported property value {value!r}; use a typed property helper")


def part(name, size=(4, 1, 2), position=(0, 0, 0), color=(163, 162, 165),
         material=256, anchored=True, shape=None, transparency=0.0):
    obj = Instance("Part", name,
                   Size=vector3_prop(size), CFrame=coordinateframe_prop(position),
                   Color3uint8=color3uint8_prop(color), Material=token_prop(material),
                   Anchored=bool_prop(anchored), Transparency=float_prop(transparency))
    if shape is not None: obj.set_property("Shape", token_prop(shape))
    return obj


def model(name, children=(), primary_part=None):
    obj = Instance("Model", name)
    for child in children: obj.add(child)
    if primary_part is not None: obj.set_property("PrimaryPart", ref_prop(primary_part))
    return obj


def script(name, source, kind="Script"):
    if kind not in ("Script", "LocalScript", "ModuleScript"):
        raise ValueError('kind must be "Script", "LocalScript", or "ModuleScript"')
    return Instance(kind, name, Source=Property("ProtectedString", str(source)))


def folder(name): return Instance("Folder", name)


def _scalar(prop: Property):
    value = prop.value
    if prop.tag == "Ref":
        if value is None: return "null"
        if isinstance(value, Instance): return value.referent
        return str(value)
    if prop.tag == "bool": return "true" if value else "false"
    if prop.tag in ("string", "ProtectedString"): return str(value)
    return str(value)


def _write_property(parent, name, prop: Property):
    tag = ET.SubElement(parent, prop.tag, {"name": name})
    val = prop.value
    if prop.tag in ("Vector3", "Color3"):
        children = ("X", "Y", "Z") if prop.tag == "Vector3" else ("R", "G", "B")
        for child, value in zip(children, val): ET.SubElement(tag, child).text = _num(value)
    elif prop.tag == "CoordinateFrame":
        labels = ("X", "Y", "Z", "R00", "R01", "R02", "R10", "R11", "R12", "R20", "R21", "R22")
        if len(val) != 12: raise ValueError("CoordinateFrame property must have 12 values")
        for child, value in zip(labels, val): ET.SubElement(tag, child).text = _num(value)
    elif prop.tag == "UDim2":
        for axis, pair in zip(("X", "Y"), val):
            node = ET.SubElement(tag, axis)
            ET.SubElement(node, "UDim", {"S": _num(pair[0]), "O": str(int(pair[1]))})
    else:
        tag.text = _scalar(prop)
    return tag


def _num(value):
    return format(float(value), ".9g")


def _append_item(parent, obj: Instance):
    item = ET.SubElement(parent, "Item", {"class": obj.class_name, "referent": obj.referent})
    props = ET.SubElement(item, "Properties")
    # Ensure canonical Name is serialized and avoid accidental duplicate Name entries.
    values = dict(obj.props)
    values["Name"] = string_prop(obj.name)
    for name, prop in values.items(): _write_property(props, name, prop)
    for child in obj.children: _append_item(item, child)
    return item


def to_xml(root: Instance) -> bytes:
    if not isinstance(root, Instance): raise TypeError("root must be an Instance")
    roblox = ET.Element("roblox", {
        "xmlns:xmime": XMLNS_XMIME,
        "xmlns:xsi": XMLNS_XSI,
        "xsi:noNamespaceSchemaLocation": SCHEMA,
        "version": "4",
    })
    ET.SubElement(roblox, "Meta", {"name": "ExplicitAutoJoints"}).text = "true"
    _append_item(roblox, root)
    raw = ET.tostring(roblox, encoding="utf-8")
    return minidom.parseString(raw).toprettyxml(indent="  ", encoding="utf-8")


def write_model(root: Instance, out=None, *, force=False):
    """Write model XML (default prefab/<model-name>.rbxmx); refuse overwrite unless force=True."""
    path = Path(out) if out is not None else Path("prefab") / f"{root.name}.rbxmx"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        raise FileExistsError(f"refusing to overwrite {path}; pass force=True only when authorized")
    if path.exists() and force:
        print(f"Overwriting existing file: {path}")
    path.write_bytes(to_xml(root))
    print(path)
    return path


def validate_rbxmx(path):
    """Raise ValueError on malformed XML, duplicate Item referents, or dangling Refs."""
    try: tree = ET.parse(path)
    except (ET.ParseError, OSError) as exc: raise ValueError(f"Cannot parse {path}: {exc}") from exc
    root = tree.getroot()
    if root.tag != "roblox": raise ValueError("Root element must be <roblox>")
    items = list(root.iter("Item"))
    refs = [item.get("referent") for item in items]
    if any(ref is None or not ref for ref in refs): raise ValueError("Every Item must have a non-empty referent")
    if len(refs) != len(set(refs)): raise ValueError("Duplicate Item referents found")
    targets = set(refs)
    for prop in root.iter("Ref"):
        target = (prop.text or "").strip()
        if target and target.lower() != "null" and target not in targets:
            raise ValueError(f"Ref target does not exist: {target}")
    return True


def _spec_value(value):
    if not isinstance(value, dict) or "$type" not in value: return value
    typ, v = value["$type"], value.get("value")
    constructors = {
        "string": lambda: string_prop(v), "bool": lambda: bool_prop(v), "int": lambda: int_prop(v),
        "int64": lambda: int64_prop(v), "float": lambda: float_prop(v),
        "Vector3": lambda: vector3_prop(v), "CoordinateFrame": lambda: coordinateframe_prop(v[:3], v[3:]),
        "Color3": lambda: color3_prop(v), "Color3uint8": lambda: color3uint8_prop(v),
        "token": lambda: token_prop(v), "BrickColor": lambda: brickcolor_prop(v),
        "UDim2": lambda: udim2_prop(v[0], v[1]), "ProtectedString": lambda: Property("ProtectedString", str(v)),
        "Ref": lambda: ref_prop(v),
    }
    if typ not in constructors: raise ValueError(f"Unknown typed spec property: {typ}")
    return constructors[typ]()


def from_spec(spec):
    if not isinstance(spec, dict): raise ValueError("Each instance spec must be an object")
    obj = Instance(spec["class"], spec["name"])
    for key, value in spec.get("props", {}).items(): obj.set_property(key, _spec_value(value))
    for child in spec.get("children", []): obj.add(from_spec(child))
    # Resolve a PrimaryPart name convenience after children have been created.
    primary = spec.get("primary_part")
    if primary:
        found = next((child for child in obj.children if child.name == primary), None)
        if found is None: raise ValueError(f"primary_part {primary!r} is not a direct child of {obj.name!r}")
        obj.set_property("PrimaryPart", ref_prop(found))
    return obj


def _example_model():
    base = part("Base", size=(8, 1, 8), position=(0, 0.5, 0), color=(70, 130, 180), material=256)
    logic = script("Greeting", 'print("Hello from an imported model!")\n')
    return model("DemoModel", [base, logic], primary_part=base)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", nargs="?", help="JSON file describing an instance tree")
    parser.add_argument("-o", "--output", help="output .rbxmx path")
    parser.add_argument("--force", action="store_true", help="allow overwriting an existing file")
    parser.add_argument("--example", action="store_true", help="write a demo model")
    args = parser.parse_args(argv)
    if bool(args.spec) == bool(args.example): parser.error("provide one spec.json or --example")
    root = _example_model() if args.example else from_spec(json.loads(Path(args.spec).read_text(encoding="utf-8")))
    out = Path(args.output) if args.output else Path("prefab") / f"{root.name}.rbxmx"
    if out.exists() and not args.force: parser.error(f"refusing to overwrite {out}; pass --force")
    write_model(root, out, force=args.force)
    validate_rbxmx(out)
    print(f"Validated: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
