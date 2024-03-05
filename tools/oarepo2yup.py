import dataclasses
import json
from pathlib import Path
from pprint import pprint
from typing import List, Dict, Any

import click
import yaml


@click.command()
@click.argument("oarepo_file")
@click.argument("output_file")
def convert_oarepo_to_yup(oarepo_file, output_file):
    """
    Convert oarepo model file to yup validation schema
    Arguments:
            oarepo_file: path to the oarepo model file (must come from the compiler inside the models dir)
            output_file: path to the output file

    The converted file will have the same name as the oarepo file,
    but with the .js extension instead of .yaml
    """

    # load oarepo_file as yaml
    with open(oarepo_file, "r") as f:
        oarepo_schema = json.load(f)
    root = oarepo_schema["model"]["properties"]["metadata"]
    # convert to yup schema
    root_name = Path(output_file).stem.capitalize()
    yup_object = parse_yup(root, [root_name])

    # dump all the objects
    objects = []
    def dump_objects(fld):
        if not isinstance(fld, (ObjectYUPSchema, PolymorphicYUPSchema)):
            return
        if isinstance(fld, PolymorphicYUPSchema):
            # fix up polymorphic types
            for key, s in fld.schemas.items():
                assert isinstance(s, YUPField)
                s = s.type
                if isinstance(s, ObjectYUPSchema):
                    s.fields[fld.discriminator].remove_constraint('oneOf').add_constraint(f"oneOf({json_repr(key)})")
                elif isinstance(s, PolymorphicYUPSchema):
                    for sc in s.schemas.values():
                        sc = sc.type
                        sc.fields[fld.discriminator].remove_constraint('oneOf').add_constraint(f"oneOf({json_repr(key)})")


        objects.append(fld)

    yup_object.visit(dump_objects)

    objects.reverse()

    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w") as f:
        print(prologue, file=f)
        for r in objects:
            print(r.to_js(), file=f)

prologue = """
import {object, string, number, date, array, boolean, mixed} from "yup";

export function union(...schemas) {
	return mixed().test({
		name: "union",
		message: "value did not match any schema: ${value}",
		test(value) {
			// The real magic
			return schemas.some(s => s.isValidSync(value));
		},
	});
}
"""

@dataclasses.dataclass
class YUPField:
    type: Any
    constraints: List[str]

    @classmethod
    def parse(cls, schema, type):
        constraints = []
        for k, v in schema.items():
            # TODO: polymorphism
            if k in ('schemas', 'discriminator'):
                continue
            if k in ('keys', 'extras', 'vocabulary-type', 'model', 'pid-field'):
                continue
            if k in ('type', 'help.en', 'label.en', 'hint.en', 'mapping', 'marshmallow',
                     'ui', 'items', 'properties', 'sample', 'imports', 'facets', 'id'):
                continue
            if not hasattr(cls, f"parse_{k}"):
                raise Exception(f'Not implemented constraint {k} with value {v} at {schema}')
            constraints.extend(getattr(cls, f"parse_{k}")(v))
        return cls(type=type, constraints=constraints)

    def visit(self, visitor):
        visitor(self)
        if not isinstance(self.type, str):
            self.type.visit(visitor)

    def to_js_item(self):
        ret = [f"{self.type.to_js_item()}"]
        ret.extend(self.type.extra_constraints)
        ret.extend(self.constraints)
        return '.'.join(ret)

    def remove_constraint(self, constraint):
        self.constraints = [x for x in self.constraints if not x.startswith(constraint)]
        return self

    def add_constraint(self, constraint):
        self.remove_constraint(constraint)
        self.constraints.append(constraint)

    @classmethod
    def parse_enum(cls, value):
        return [f"oneOf({json_repr(value)})"]

    @classmethod
    def parse_required(cls, value):
        return ["required()"]

    @classmethod
    def parse_minItems(cls, value):
        return [f"min({json_repr(value)})"]

    @classmethod
    def parse_maxItems(cls, value):
        return [f"max({json_repr(value)})"]

    @classmethod
    def parse_minimum(cls, value):
        return [f"min({json_repr(value)})"]

    @classmethod
    def parse_maximum(cls, value):
        return [f"max({json_repr(value)})"]


def json_repr(value):
    return json.dumps(value)


@dataclasses.dataclass
class ObjectYUPSchema:
    type: str
    fields: Dict[str, YUPField]
    extra_constraints: List[str] = dataclasses.field(default_factory=list)

    @classmethod
    def parse(cls, schema, path):
        assert "properties" in schema
        fields = {}
        for k, v in schema["properties"].items():
            fields[k] = parse_yup(v, path + [k])
        return cls(type=class_name(path), fields=fields)

    def visit(self, visitor):
        visitor(self)
        for fld in self.fields.values():
            fld.visit(visitor)

    def to_js(self):
        fields = ",\n    ".join(f"{k}: {v.to_js_item()}" for k, v in self.fields.items())
        return f"""
export const {self.type} = object({{
    {fields}
}});
        """

    def to_js_item(self):
        return f"{self.type}"


@dataclasses.dataclass
class PrimitiveYUPSchema:
    type: str
    extra_constraints: List[str] = dataclasses.field(default_factory=list)

    @classmethod
    def parse(cls, schema, path):
        match schema["type"]:
            case "keyword":
                return cls(type="string")
            case "fulltext":
                return cls(type="string")
            case "fulltext+keyword":
                return cls(type="string")
            case "double":
                return cls(type="number")
            case "integer":
                return cls(type="number", extra_constraints=["integer()"])
            case "date":
                return cls(type="date")
            case "url":
                return cls(type="string", extra_constraints=["url()"])
            case "vocabulary":
                # TODO: proper parsing
                return cls(type="vocabulary")
            case "boolean":
                return cls(type="boolean")
            case "relation":
                # TODO: proper parsing
                return cls(type="relation")

        raise Exception(f'Not implemented primitive type {schema["type"]}')

    def visit(self, visitor):
        visitor(self)

    def to_js_item(self):
        match self.type:
            case 'string':
                return "string()"
            case 'number':
                return "number()"
            case 'date':
                return "date()"
            case 'boolean':
                return "boolean()"
            case 'vocabulary':
                # TODO: fix to contain only the allowed fields
                return "object()"
            case 'relation':
                # TODO: fix to contain only the allowed fields
                return "object()"
            case _:
                raise Exception(f'Not implemented type {self.type}')

@dataclasses.dataclass
class ArrayYUPSchema:
    type: Any
    extra_constraints: List[str] = dataclasses.field(default_factory=list)

    @classmethod
    def parse(cls, schema, path):
        item = parse_yup(schema["items"], path + ["item"])
        return cls(type=item)

    def visit(self, visitor):
        visitor(self)
        self.type.visit(visitor)

    def to_js_item(self):
        return f"array({self.type.to_js_item()})"


@dataclasses.dataclass
class PolymorphicYUPSchema:
    type: Any
    schemas: Dict[str, Any]
    discriminator: str
    extra_constraints: List[str] = dataclasses.field(default_factory=list)

    @classmethod
    def parse(cls, schema, path):
        schemas = {k: parse_yup(v, path+[k]) for k, v in schema['schemas'].items()}
        discriminator = schema['discriminator']
        return cls(type=class_name(path), schemas=schemas, discriminator=discriminator)

    def visit(self, visitor):
        visitor(self)
        for fld in self.schemas.values():
            fld.visit(visitor)

    def to_js_item(self):
        return f"{self.type}"

    def to_js(self):
        subschemas = ",\n    ".join(f"{v.type.type}" for k, v in self.schemas.items())
        return f"""
export const {self.type} = union(\n    {subschemas});
        """

def parse_yup(schema, path):
    if not isinstance(schema, dict):
        raise Exception(f'Not implemented type {type(schema)}')
    match schema['type']:
        case 'object':
            parsed = ObjectYUPSchema.parse(schema, path)
        case 'nested':
            parsed = ObjectYUPSchema.parse(schema, path)
        case 'polymorphic':
            parsed = PolymorphicYUPSchema.parse(schema, path)
        case 'array':
            parsed = ArrayYUPSchema.parse(schema, path)
        case _:
            parsed = PrimitiveYUPSchema.parse(schema, path)
    return YUPField.parse(schema, type=parsed)


def class_name(path):
    parts = [y for x in path for y in x.split(' ')]
    parts = [y for x in parts for y in x.split('_')]
    parts = [y for x in parts for y in x.split('-')]
    return ''.join(x.capitalize() for x in parts)


if __name__ == "__main__":
    convert_oarepo_to_yup()
