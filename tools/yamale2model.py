import copy
import dataclasses
import logging
import re
import click
import ruamel
import yamale
from collections import namedtuple
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Union
from ruamel.yaml import YAML as ruamel_YAML
from yamale.schema import Schema
from yamale.validators import (
    Boolean,
    Day,
    DefaultValidators,
    Enum,
    Include,
    Integer,
    List,
    Number,
    Regex,
    String,
    Validator,
)

from custom_validators import (
    Chemical_id,
    Choose,
    Database_id,
    Fulltext,
    Keyword,
    Link,
    LinkTarget,
    Nested_include,
    Person_id,
    Publication_id,
    Url,
    Uuid,
    Vocabulary,
)

log = logging.getLogger("yamale2model")


class NonAliasingRTRepresenter(ruamel.yaml.RoundTripRepresenter):
    def ignore_aliases(self, data):
        return True


class Description(Validator):
    tag = "description"

    def _is_valid(self, value):
        return True


class TrueValidator(Validator):
    tag = "true"

    def _is_valid(self, value):
        return True


class FalseValidator(Validator):
    tag = "false"

    def _is_valid(self, value):
        return True


validators = DefaultValidators.copy()
validators[Keyword.tag] = Keyword
validators[Fulltext.tag] = Fulltext
validators[Link.tag] = Link
validators[LinkTarget.tag] = LinkTarget
validators[Uuid.tag] = Uuid
validators[TrueValidator.tag] = TrueValidator
validators[FalseValidator.tag] = FalseValidator
validators[Database_id.tag] = Database_id
validators[Chemical_id.tag] = Chemical_id
validators[Person_id.tag] = Person_id
validators[Publication_id.tag] = Publication_id
validators[Nested_include.tag] = Nested_include
validators[Choose.tag] = Choose
validators[Vocabulary.tag] = Vocabulary
validators[Url.tag] = Url


class KeyModifier:
    def __init__(self, value) -> None:
        self.value = value

    def key(self, orig_key):
        return orig_key


class ArrayModifier(KeyModifier):
    def key(self, orig_key):
        return f"{orig_key}[]"


class ModelBase:
    path = None
    description = None

    def __init__(self, path, required) -> None:
        self.constraints = {}
        self.path = path
        self.required = required

    def parse(self, data):
        if isinstance(data, Validator):
            self.data = data
            for constraint in data._constraints_inst:
                constraint_name = type(constraint).__name__
                if not constraint.is_active:
                    continue
                parse_func = f"parse_{constraint_name}"
                if hasattr(self, parse_func):
                    getattr(self, parse_func)(constraint)
                else:
                    raise NotImplementedError(
                        f"Parse constraints not implemented on path {self.path}, expected method {type(self).__name__}.{parse_func}"
                    )

    def to_json(self, **extras):
        ret = {**extras, **self.constraints}
        if self.description:
            ret["help.en"] = self.description.strip()
        if self.required:
            ret["required"] = True
        return ret

    def get_links(self, links, path, defs):
        raise NotImplementedError(f"Not implemented for {type(self)}")

    def set_links(self, links, defs):
        raise NotImplementedError(f"Not implemented for {type(self)}")

    def get_referenced_includes(self, referenced_includes, defs):
        raise NotImplementedError(f"Not implemented for {type(self)}")

    def propagate_polymorphic_base_schemas(self, defs, path):
        raise NotImplementedError(f"Not implemented for {type(self)}")

    def copy(self):
        return copy.copy(self)


class ModelObject(ModelBase):
    def __init__(self, data: Any, path: str, includes) -> None:
        super().__init__(
            path, data.is_required if not isinstance(data, dict) else False
        )
        self.children = {}
        self.parse(data, includes)

    def parse(self, data, includes):
        super().parse(data)
        self.children = {
            k: parse(v, f"{self.path}/{k}", includes) for k, v in data.items()
        }

    def to_json(self, **extras):
        properties = {}
        for k, v in self.children.items():
            val = v.to_json()
            if isinstance(val, KeyModifier):
                properties[val.key(k)] = val.value
            else:
                properties[k] = val
            if k == "id" and isinstance(v, ModelLinkTarget):
                extras["id"] = v.name
        return super().to_json(properties=properties, **extras)

    def get_links(self, links, path, defs):
        for k, v in self.children.items():
            child_path = f"{path}/{k}" if path else k
            v.get_links(links, child_path, defs)

    def set_links(self, links, defs):
        for v in self.children.values():
            v.set_links(links, defs)

    def get_referenced_includes(self, referenced_includes, defs):
        for v in self.children.values():
            v.get_referenced_includes(referenced_includes, defs)

    def propagate_polymorphic_base_schemas(self, defs, path):
        for v in self.children.values():
            v.propagate_polymorphic_base_schemas(defs, path + [self.path])

    def copy(self):
        ret = copy.copy(self)
        ret.children = {k: v.copy() for k, v in ret.children.items()}
        return ret

    def update_children(self, children, defs):
        for k, v in children.items():
            if k == "id" and isinstance(v, ModelLinkTarget):
                v = ModelPrimitive(None, "keyword", v.path)
            if k not in self.children:
                self.children[k] = v.copy()
            else:
                print(f"Warning: Can not override child '{k}' on {self.to_json()}")


class ModelArray(ModelBase):
    def __init__(self, data: Any, path: str, includes) -> None:
        super().__init__(path, data.is_required)
        self.item = None
        self.parse(data, includes)

    def parse(self, data, includes):
        super().parse(data)
        # to disallow empty list, minItems is set to one in case it has got a value already
        if "minItems" not in self.constraints.keys():
            self.constraints["minItems"] = 1

        if len(data.validators) > 1:
            self.item = parse(
                {x.include_name: x for x in data.validators}, self.path, includes
            )
        else:
            self.item = parse(data.validators[0], self.path, includes)

    def parse_LengthMin(self, constraint):
        self.constraints["minItems"] = constraint.min

    def to_json(self, **extras):
        ret = super().to_json(**extras)
        ret = {f"^{k}": v for k, v in ret.items()}
        if isinstance(self.item, ModelArray):
            ret.update(self.item.to_explicit_json())
        else:
            ret.update(self.item.to_json())
        # remove required from the item
        ret.pop("required", False)
        return ArrayModifier(ret)

    def to_explicit_json(self, **extras):
        ret = super().to_json(**extras)
        item = self.item.to_json()
        item.pop("required", False)
        ret["items"] = item
        ret["type"] = "array"
        return ret

    def get_links(self, links, path, defs):
        self.item.get_links(links, path, defs)

    def set_links(self, links, defs):
        self.item.set_links(links, defs)

    def get_referenced_includes(self, referenced_includes, defs):
        self.item.get_referenced_includes(referenced_includes, defs)

    def propagate_polymorphic_base_schemas(self, defs, path):
        self.item.propagate_polymorphic_base_schemas(defs, path + [self.path])


class ModelPrimitive(ModelBase):
    def __init__(self, data: Any, type: str, path: str) -> None:
        is_required = False
        if data is not None:
            is_required = data.is_required

        super().__init__(path, is_required)
        self.type = type
        self.path = path
        if data:
            self.parse(data)

    def parse_Min(self, constraint):
        self.constraints["minimum"] = constraint.min

    def parse_Max(self, constraint):
        self.constraints["maximum"] = constraint.max

    def to_json(self, **extras):
        return super().to_json(type=self.type, **extras)

    def get_links(self, links, path, defs):
        pass

    def set_links(self, links, defs):
        pass

    def get_referenced_includes(self, referenced_includes, defs):
        pass

    def propagate_polymorphic_base_schemas(self, defs, path):
        pass


class ModelEnum(ModelPrimitive):
    def __init__(self, data, path: str) -> None:
        super().__init__(data, "keyword", path)
        if hasattr(data, "enums"):
            self.constraints["enum"] = data.enums

    def parse_StringEquals(self, constraint):
        # just a single valued enum
        self.constraints["enum"] = [constraint.equals]


class ModelRegex(ModelPrimitive):
    def __init__(self, data, path: str) -> None:
        super().__init__(data, "keyword", path)
        self.constraints["regex"] = data.args[0]


class ModelInclude(ModelBase):
    def __init__(self, data: Any, path: str) -> None:
        super().__init__(path, data.is_required)
        self.include = data.include_name

    def to_json(self):
        ret = {"use": f"#/$defs/{self.include}"}
        if self.required:
            ret["required"] = True
        return ret

    def get_links(self, links, path, defs):
        target = defs[self.include]
        target.get_links(links, path, defs)

    def set_links(self, links, defs):
        target = defs[self.include]
        target.set_links(links, defs)

    def get_referenced_includes(self, referenced_includes, defs):
        referenced_includes.add(self.include)
        target = defs[self.include]
        target.get_referenced_includes(referenced_includes, defs)

    def propagate_polymorphic_base_schemas(self, defs, path):
        target = defs[self.include]
        target.propagate_polymorphic_base_schemas(defs, path + [self.path])


class ModelNestedInclude(ModelInclude):
    def __init__(self, data, path):
        super().__init__(data, path)
        self.json_proto = {"type": "nested"}

    def to_json(self):
        ret = super().to_json()
        ret.update(self.json_proto)
        return ret

    def get_referenced_includes(self, referenced_includes, defs):
        if isinstance(defs[self.include], ModelChoose):
            self.json_proto = {"type": "polymorphic", "mapping": {"type": "nested"}}
        return super().get_referenced_includes(referenced_includes, defs)


class ModelChoose(ModelBase):
    def __init__(self, data: Any, path: str) -> None:
        super().__init__(path, data.is_required)
        self.base_schema = ModelInclude(data.base_schema, path)
        self.type_field = data.type_field
        self.subschemas = {
            k.replace("_", " "): ModelInclude(v, path)
            for k, v in data.detailed_schemas.items()
        }
        self.link_id = None

    def to_json(self):
        ret = super().to_json()
        ret["schemas"] = {k: v.to_json() for k, v in self.subschemas.items()}
        ret["type"] = "polymorphic"
        ret["discriminator"] = self.type_field
        if self.link_id:
            ret["id"] = self.link_id
        return ret

    def get_links(self, links, path, defs):
        self.base_schema.get_links(links, path, defs)
        for v in self.subschemas.values():
            v.get_links(links, path, defs)
        # collect id from the base schema
        base_schema: ModelObject = defs[self.base_schema.include]
        if "id" in base_schema.children and isinstance(
            base_schema.children["id"], ModelLinkTarget
        ):
            self.link_id = base_schema.children["id"].name

    def set_links(self, links, defs):
        self.base_schema.set_links(links, defs)
        for v in self.subschemas.values():
            v.set_links(links, defs)

    def get_referenced_includes(self, referenced_includes, defs):
        self.base_schema.get_referenced_includes(referenced_includes, defs)
        for v in self.subschemas.values():
            v.get_referenced_includes(referenced_includes, defs)

    def propagate_polymorphic_base_schemas(self, defs, path):
        subschema_include: ModelInclude  # must be ModelInclude
        if hasattr(self, "_polymorphic_schema_propagated"):
            return
        self._polymorphic_schema_propagated = True

        base_schema = defs[self.base_schema.include]
        new_subschemas = {}
        for subschema_name, subschema_include in self.subschemas.items():
            previous_include = subschema_include.include
            if not previous_include.endswith("Polymorphic"):
                parent = [x for x in self.path.split("/") if x and x != "value"]
                new_include = f"{parent[-1]}{previous_include}Polymorphic"
                if new_include in defs:
                    new_include = self.get_unique_include_name(new_include, path, defs)
                original_schema = defs[previous_include]
                new_schema = original_schema.copy()
                defs[new_include] = new_schema
                new_include_params: Any = namedtuple(
                    "IncludeParams", "include_name, is_required"
                )(new_include, subschema_include.required)
                new_subschema_include = ModelInclude(
                    new_include_params, subschema_include.path
                )
                new_subschemas[subschema_name] = new_subschema_include
                new_subschema_include.propagate_polymorphic_base_schemas(
                    defs, path + [self.path]
                )
                new_schema.update_children(base_schema.children, defs)
            else:
                raise Exception(
                    f"Schema {subschema_include.include} has already been generated, can not override"
                )
        self.subschemas = new_subschemas

    def get_unique_include_name(self, include_name, path, defs):
        paths = []
        for pth in path:
            new_path = []
            for pth_part in pth.split("/"):
                if not pth_part or pth_part == "value":
                    continue
                new_path.append(pth_part.lower())
            if new_path:
                paths.append(tuple(new_path))

        filtered_paths = []
        previous_path = None
        for pth in paths:
            if not previous_path:
                filtered_paths.append(pth)
                previous_path = pth
                continue
            without_prefix = []
            handling_prefix = True
            for pth_idx, pth_part in enumerate(pth):
                if (
                    handling_prefix
                    and pth_idx < len(previous_path)
                    and previous_path[pth_idx] == pth_part
                ):
                    continue
                else:
                    handling_prefix = False
                without_prefix.append(pth_part)
            if not without_prefix:
                continue
            filtered_paths.append(without_prefix)
            previous_path = pth
        filtered_paths = [x for y in filtered_paths for x in y]
        for pth in reversed(filtered_paths):
            include_name = f"{pth}_{include_name}"
            if include_name not in defs:
                return include_name
        raise Exception(f"Could not generate include name for {include_name}")

    def copy(self):
        return copy.copy(self)

    def update_children(self, children, defs):
        for v in self.subschemas.values():
            schema = defs[v.include]
            schema.update_children(children, defs)


class ModelLinkTarget(ModelBase):
    def __init__(self, data, path: str) -> None:
        super().__init__(path, data.is_required)
        self.name = data.name

    def to_json(self):
        ret = {"type": "keyword"}
        if self.required:
            ret["required"] = True
        return ret

    def get_links(self, links, path, defs):
        if self.name in links:
            raise ValueError(f"Duplicated id on paths {path} and {links[self.name]}")
        links[self.name] = "/".join(path.split("/")[:-1])

    def set_links(self, links, defs):
        pass

    def get_referenced_includes(self, referenced_includes, defs):
        pass

    def propagate_polymorphic_base_schemas(self, defs, path):
        pass


class ModelLink(ModelBase):
    def __init__(self, data, path: str) -> None:
        super().__init__(path, data.is_required)
        self.target = data.target
        self.fields = data.fields
        if isinstance(self.fields, str):
            self.fields = ruamel.yaml.safe_load(StringIO(self.fields))

    def to_json(self):
        ret = {"type": "relation", "model": "#" + self.target, "keys": self.fields}
        if self.required:
            ret["required"] = True
        return ret

    def get_links(self, links, path, defs):
        pass

    def set_links(self, links, defs):
        self.model = "#/" + links[self.target]

    def get_referenced_includes(self, referenced_includes, defs):
        pass

    def propagate_polymorphic_base_schemas(self, defs, path):
        pass


class ModelVocabulary(ModelLink):
    def __init__(self, data, path: str) -> None:
        data.target = None
        super().__init__(data, path)
        self.vocabulary = data.vocabulary

    def to_json(self):
        ret = {
            "keys": self.fields,
            "vocabulary-type": self.vocabulary,
            "type": "vocabulary",
        }
        if self.required:
            ret["required"] = True
        return ret

    def set_links(self, links, defs):
        pass


@dataclasses.dataclass
class Model:
    includes: Dict[str, ModelBase]
    model: ModelBase
    files_meta: Dict = None
    package: str = None

    def to_json(self):
        includes = {k: v.to_json() for k, v in self.includes.items()}
        return {
            "profiles": ["record", "draft", "files", "draft_files"],
            "record": {
                "use": ["invenio"],
                "module": {"qualified": f"mbdb_{self.package}"},
                "properties": {"metadata": self.model.to_json()},
                "files": {**self.files_meta, "use": ["invenio_files"]},
                "draft": {},
                "draft-files": {},
                "mapping": {
                    "template": {
                        "settings": {
                            "index.mapping.total_fields.limit": 3000,
                            "index.mapping.nested_fields.limit": 200,
                        }
                    }
                },
            },
            "plugins": {
                "builder": {"disable": ["script_sample_data"]},
                "packages": [
                    "oarepo-model-builder-files==4.*",
                    "oarepo-model-builder-cf==4.*",
                    "oarepo-model-builder-vocabularies==4.*",
                    "oarepo-model-builder-relations==4.*",
                    "oarepo-model-builder-polymorphic==1.*",
                    "oarepo-model-builder-drafts",
                    "oarepo-model-builder-drafts-files",
                ],
            },
            "$defs": includes,
            "settings": {"i18n-languages": ["en"]},
        }

    def set_links(self):
        links = {}
        self.model.get_links(links, "", self.includes)
        self.model.set_links(links, self.includes)

    def remove_unused_includes(self):
        referenced_includes = set()
        self.model.get_referenced_includes(referenced_includes, self.includes)
        self.includes = {
            k: v for k, v in self.includes.items() if k in referenced_includes
        }

    def add_includes_from(self, filename):
        included_model = parse_file(filename)
        for k, v in included_model.model.children.items():
            self.includes[k] = v
        self.includes.update(included_model.includes)

    def propagate_polymorphic_base_schemas(self):
        self.model.propagate_polymorphic_base_schemas(self.includes, [])

    def add_files_meta(self, files_meta: Dict):
        self.files_meta = files_meta


def parse_described_value(d, path, includes):
    value = d.get("value")
    description = d.get("description")
    if description:
        description = description.kwargs.get("equals", None)
    searchable = d.get("searchable", False)
    if searchable:
        searchable = isinstance(searchable, TrueValidator)
    value = parse(value, f"{path}/value", includes)
    value.description = description
    value.searchable = searchable
    return value


def parse(d, path, includes):
    clz = type(d)
    if clz is dict:
        log.debug("%s: %s", path, {k: type(v).__name__ for k, v in d.items()})
        known_count = 1 if "value" in d else 0
        known_count += (
            1 if "description" in d and isinstance(d["description"], String) else 0
        )
        known_count += (
            1
            if "searchable" in d
            and isinstance(d["searchable"], (TrueValidator, FalseValidator))
            else 0
        )
        if known_count == len(d):
            log.debug("... described value")
            return parse_described_value(d, path, includes)
        log.debug("... plain dict")
        return ModelObject(d, path, includes)
    elif clz is String:
        return parse_keyword(d, path)
    elif clz is Enum:
        return ModelEnum(d, path)
    elif clz is Uuid:
        return ModelPrimitive(d, "uuid", path)
    elif clz is Url:
        return ModelPrimitive(d, "url", path)
    elif clz is Day:
        return ModelPrimitive(d, "date", path)
    elif clz is Boolean:
        return ModelPrimitive(d, "boolean", path)
    elif clz is Number:
        return ModelPrimitive(d, "double", path)
    elif clz is Integer:
        return ModelPrimitive(d, "integer", path)
    elif clz is Keyword:
        return parse_keyword(d, path)
    elif clz is Fulltext:
        return ModelPrimitive(d, "fulltext", path)
    elif clz is Regex:
        return ModelRegex(d, path)
    elif clz is Include:
        return ModelInclude(d, path)
    elif clz is Nested_include:
        return ModelNestedInclude(d, path)
    elif clz is List:
        return ModelArray(d, path, includes)
    elif clz is Schema:
        return parse_schema(d, path, includes)
    elif clz is LinkTarget:
        return ModelLinkTarget(d, path)
    elif clz is Vocabulary:
        return ModelVocabulary(d, path)
    elif clz is Link:
        return ModelLink(d, path)
    elif clz is Choose:
        return ModelChoose(d, path)
    elif clz is Publication_id:
        return parse_publication_id(d, path)
    elif clz is Chemical_id:
        return parse_chemical_id(d, path)
    elif clz is Person_id:
        return parse_person_id(d, path)
    elif clz is Database_id:
        return parse_database_id(d, path)
    elif clz is str:
        return parse(
            yamale.make_schema(content="root:\n" + "    " + d).dict["root"],
            path,
            includes,
        )
    else:
        raise NotImplementedError(
            f"Element of type {type(d)} not implemented on path {path}"
        )


def parse_keyword(d, path):
    for constraint in d._constraints_inst:
        constraint_name = type(constraint).__name__
        if not constraint.is_active:
            continue
        if constraint_name == "StringEquals":
            return ModelEnum(d, path)
    return ModelPrimitive(d, "keyword", path)


def parse_database_id(d, path):
    return parse_keyword(d, path)


def parse_person_id(d, path):
    return parse_keyword(d, path)


def parse_publication_id(d, path):
    return parse_keyword(d, path)


def parse_chemical_id(d, path):
    return parse_keyword(d, path)


def parse_schema(schema, path, includes, skip_top=False):
    for k, v in schema.includes.items():
        includes[k] = v
    if skip_top:
        assert len(schema.dict) == 1
        top_name, top_value = list(schema.dict.items())[0]
        return parse(top_value, f"{path}/{top_name}", includes)
    else:
        return parse(schema.dict, path, includes)


def parse_file(ym_file, modelbase_only=False) -> Union[Model, ModelBase]:
    schema_data = Path(ym_file).read_text()
    schema_data = re.sub(r"searchable(\s*:\s*)True", r"searchable\1true()", schema_data)
    schema = yamale.make_schema(content=schema_data, validators=validators)
    includes = {}
    model = parse_schema(schema, "", includes)
    parsed_includes = {}
    while includes:
        new_includes = {}
        for k, v in includes.items():
            parsed_includes[k] = parse(v, f"/{k}", new_includes)
        includes = {}
        for k, v in new_includes.items():
            if k not in parsed_includes:
                includes[k] = v

    if modelbase_only:
        return model

    return Model(
        model=model,
        includes=parsed_includes,
        package=Path(ym_file).stem.lower().replace("_with_description", ""),
    )


def set_flow_style(d):
    if isinstance(d, (list, tuple)):
        d.fa.set_flow_style()
    elif isinstance(d, dict):
        for v in d.values():
            set_flow_style(v)


@click.command()
@click.argument(
    "input_file",
    default=Path(__file__).parent.parent / "models" / "main" / "MST.yaml",
    required=True,
)
@click.argument("output_file", required=False)
@click.option("--debug", type=bool)
@click.option(
    "--include",
    default=Path(__file__).parent.parent
    / "models"
    / "main"
    / "general_parameters.yaml",
    required=False,
)
def run(input_file, output_file, debug, include):
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    ym_file = input_file
    attachment = (
        Path(__file__).parent.parent / "models" / "main" / "file_attachment.yaml"
    )
    model = parse_file(ym_file)
    if include:
        model.add_includes_from(include)
    model.remove_unused_includes()
    model.set_links()
    model.propagate_polymorphic_base_schemas()
    model.add_files_meta(parse_file(attachment, modelbase_only=True).to_json())
    yaml = ruamel_YAML()
    yaml.default_flow_style = False
    yaml.allow_unicode = True
    yaml.sort_base_mapping_type_on_output = True
    yaml.Representer = NonAliasingRTRepresenter
    io = StringIO()
    yaml.dump(model.to_json(), io)
    io.seek(0)
    loaded = yaml.load(io)
    set_flow_style(loaded)
    io = StringIO()
    yaml.dump(loaded, io)
    model_yaml = io.getvalue()
    if output_file:
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        Path(output_file).write_text(model_yaml)
    else:
        print(model_yaml)


if __name__ == "__main__":
    run()
