import copy
import dataclasses
import logging
import re
from collections import namedtuple
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Union

import click
import ruamel
import yamale
from ruamel.yaml import YAML as ruamel_YAML
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
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
from yamale2oarepo_config import PRIMITIVES_MAPPING, VOCABULARY_MAPPING

log = logging.getLogger("yamale2oarepo")


class NonAliasingRTRepresenter(ruamel.yaml.RoundTripRepresenter):
    def ignore_aliases(self, data):
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
    extension_elements = None
    default_search = None
    label = None

    def __init__(self, path, required, default_search, label) -> None:
        self.constraints = {}
        self.path = path
        self.required = required
        self.default_search = default_search
        self.label = label

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
        if self.default_search:
            if "mapping" not in ret:
                ret["mapping"] = {}
            ret["mapping"].update(PRIMITIVES_MAPPING)

        if self.extension_elements:
            for key, value in self.extension_elements.items():
                ret[key] = value.to_json()
                ret[key].pop("required", False)
                ret[key].pop("default", False)
                ret[key].pop("mapping", False)

        if not self.label:
            self.label = self.to_label()

        ret["label.en"] = self.label.strip()

        return ret

    def to_label(self):
        label = self.path.split('/')
        # if this is a described value we need to go up a level
        if label[-1] == "value" and len(label) > 2:
            label = label[-2]
        else:
            label = label[-1]
        label = label.replace("_", " ")
        label = label.capitalize()
        return label

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
    def __init__(self, data: Any, path: str, includes, default_search, label) -> None:
        super().__init__(
            path=path,
            required=data.is_required if not isinstance(data, dict) else False,
            default_search=default_search,
            label=label
        )
        self.children = {}
        self.parse(data, includes)

    def parse(self, data, includes):
        super().parse(data)
        self.children = {
            k: parse(v, f"{self.path}/{k}", includes, self.default_search, self.label)
            for k, v in data.items()
        }

    def to_json(self, **extras):
        properties = {}
        for k, v in self.children.items():
            val = v.to_json()
            if isinstance(val, KeyModifier):
                properties[val.key(k).lower()] = val.value
            else:
                properties[k.lower()] = val
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
                v = ModelPrimitive(
                    None,
                    "keyword",
                    v.path,
                    default_search=self.default_search,
                    label=self.label
                )
            if k not in self.children:
                self.children[k] = v.copy()
            else:
                print(f"Warning: Can not override child '{k}' on {self.to_json()}")


class ModelArray(ModelBase):
    def __init__(self, data: Any, path: str, includes, default_search, label) -> None:
        super().__init__(path, data.is_required, default_search, label)
        self.item = None
        self.parse(data, includes)

    def parse(self, data, includes):
        super().parse(data)
        # to disallow empty list, minItems is set to one in case it has not got a value already
        if "minItems" not in self.constraints.keys():
            self.constraints["minItems"] = 1

        if len(data.validators) > 1:
            self.item = parse(
                {x.include_name: x for x in data.validators},
                self.path,
                includes,
                default_search=self.default_search,
            )
        else:
            self.item = parse(
                data.validators[0],
                self.path,
                includes,
                default_search=self.default_search,
            )

    def parse_LengthMin(self, constraint):
        self.constraints["minItems"] = constraint.min

    def to_json(self, **extras):
        ret = super().to_json(**extras)
        # mapping for arrays needs to be an item attribute, not an array attribute
        ret = {f"^{k}": v for k, v in ret.items() if not k == "mapping"}
        if isinstance(self.item, ModelArray):
            ret.update(self.item.to_explicit_json())
        else:
            ret.update(self.item.to_json())
        # remove required from item
        ret.pop("required", False)
        ret.pop("label.en", None)
        return ArrayModifier(ret)

    def to_explicit_json(self, **extras):
        ret = super().to_json(**extras)
        item = self.item.to_json()
        item.pop("required", False)
        item.pop("label.en", None)
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
    def __init__(self, data: Any, type: str, path: str, default_search, label) -> None:
        is_required = False
        if data is not None:
            is_required = data.is_required

        super().__init__(path, is_required, default_search, label)
        self.type = type
        self.path = path

        if data:
            self.parse(data)

    def parse_Min(self, constraint):
        self.constraints["minimum"] = constraint.min

    def parse_Max(self, constraint):
        self.constraints["maximum"] = constraint.max

    def to_json(self, **extras):
        ret = super().to_json(type=self.type, **extras)
        if (
            self.type
            in (
                "fulltext",
                "keyword",
            )
        ) and self.default_search:
            ret["mapping"] = PRIMITIVES_MAPPING
        return ret

    def get_links(self, links, path, defs):
        pass

    def set_links(self, links, defs):
        pass

    def get_referenced_includes(self, referenced_includes, defs):
        pass

    def propagate_polymorphic_base_schemas(self, defs, path):
        pass


class ModelEnum(ModelPrimitive):
    def __init__(self, data, path: str, default_search, label) -> None:
        super().__init__(data, "keyword", path, default_search, label)
        if hasattr(data, "enums"):
            self.constraints["enum"] = data.enums

    def parse_StringEquals(self, constraint):
        # just a single valued enum
        self.constraints["enum"] = [constraint.equals]


class ModelRegex(ModelPrimitive):
    def __init__(self, data, path: str, default_search, label) -> None:
        super().__init__(data, "keyword", path, default_search, label)
        self.constraints["regex"] = data.args[0]


class ModelInclude(ModelBase):
    def __init__(self, data, path: str, default_search, label) -> None:
        super().__init__(path, data.is_required, default_search, label)
        self.include = data.include_name

    def to_json(self):
        ret = {"use": f"#/$defs/{self.include}"}
        if self.required:
            ret["required"] = True
        if self.description:
            ret["help.en"] = self.description.strip()
        if not self.label:
            self.label = self.to_label()
        ret["label.en"] = self.label.strip()

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
    def __init__(self, data, path: str, default_search, label) -> None:
        super().__init__(data, path, default_search, label)
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
    def __init__(self, data, path: str, default_search, label) -> None:
        super().__init__(path, data.is_required, default_search, label)
        self.base_schema = ModelInclude(data.base_schema, path, default_search, label)
        self.type_field = data.type_field
        self.subschemas = {
            k.replace("_", " "): ModelInclude(v, path, default_search, label)
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
        ret.pop("required", False)
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
                    new_include_params,
                    subschema_include.path,
                    self.default_search,
                    self.label
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
    def __init__(self, data, path: str, default_search, label) -> None:
        super().__init__(path, data.is_required, default_search, label)
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
    def __init__(self, data, path: str, default_search, label) -> None:
        super().__init__(path, data.is_required, default_search, label)
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
    def __init__(self, data, path: str, default_search, label) -> None:
        data.target = None
        super().__init__(data, path, default_search, label)
        self.vocabulary = data.vocabulary

    def to_json(self):
        # Calling grandparents method instead of parent method is a sign that
        # the inheritance structure is not optimal
        ret = super(ModelLink, self).to_json()
        vocab_fields = {
            "keys": self.fields,
            "vocabulary-type": self.vocabulary,
            "type": "vocabulary",
        }
        ret.update(vocab_fields)
        if self.default_search:
            # searching for vocabulary needs to be placed in extra
            # instead of directly in mapping
            ret.pop("mapping")
            # note that only vocabularies titles are made searchable
            # TODO: allow placement of custom fields to be searchable
            ret["extras"] = VOCABULARY_MAPPING
        return ret

    def set_links(self, links, defs):
        pass


@dataclasses.dataclass
class Model:
    includes: Dict[str, ModelBase]
    model: ModelBase
    package: str = None

    def to_json(self):
        return self.model.to_json()["properties"]

    def to_defs(self):
        return {k: v.to_json() for k, v in self.includes.items()}

    @staticmethod
    def to_files_meta(filename):
        return parse_file(filename, modelbase_only=True).to_json()

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


def parse_described_value(d, path, includes):
    value = d.get("value")

    description = d.get("description")
    if description:
        description = description.kwargs.get("equals", None)

    label = d.get("label")
    if label:
        label = label.kwargs.get("equals", None)

    default_search = d.get("default_search", False)
    if default_search:
        default_search = isinstance(default_search, TrueValidator)

    value = parse(
        value,
        f"{path}/value",
        includes,
        default_search=default_search,
    )
    value.description = description
    value.label = label
    value.default_search = default_search

    value.extension_elements = {
        k: parse(v, f"{path}/{k}", includes)
        for k, v in d.items()
        if k not in ("description", "value", "default_search", "label")
    }

    return value


def parse(d, path, includes, default_search=False, label=None):
    clz = type(d)
    if clz is dict:
        log.debug("%s: %s", path, {k: type(v).__name__ for k, v in d.items()})
        if ("description" in d) and ("value" in d):
            log.debug("... described value")
            return parse_described_value(d, path, includes)
        log.debug("... plain dict")
        return ModelObject(d, path, includes, default_search, label)
    elif clz is String:
        return parse_keyword(d, path, default_search, label)
    elif clz is Enum:
        return ModelEnum(d, path, default_search, label)
    elif clz is Uuid:
        return ModelPrimitive(d, "uuid", path, default_search, label)
    elif clz is Url:
        return ModelPrimitive(d, "url", path, default_search, label)
    elif clz is Day:
        return ModelPrimitive(d, "date", path, default_search, label)
    elif clz is Boolean:
        return ModelPrimitive(d, "boolean", path, default_search, label)
    elif clz is Number:
        return ModelPrimitive(d, "double", path, default_search, label)
    elif clz is Integer:
        return ModelPrimitive(d, "integer", path, default_search, label)
    elif clz is Keyword:
        return parse_keyword(d, path, default_search, label)
    elif clz is Fulltext:
        return ModelPrimitive(d, "fulltext", path, default_search, label)
    elif clz is Regex:
        return ModelRegex(d, path, default_search, label)
    elif clz is Include:
        return ModelInclude(d, path, default_search, label)
    elif clz is Nested_include:
        return ModelNestedInclude(d, path, default_search, label)
    elif clz is List:
        return ModelArray(d, path, includes, default_search, label)
    elif clz is Schema:
        return parse_schema(d, path, includes)
    elif clz is LinkTarget:
        return ModelLinkTarget(d, path, default_search, label)
    elif clz is Vocabulary:
        return ModelVocabulary(d, path, default_search, label)
    elif clz is Link:
        return ModelLink(d, path, default_search, label)
    elif clz is Choose:
        return ModelChoose(d, path, default_search, label)
    elif clz is Publication_id:
        return parse_publication_id(d, path, default_search, label)
    elif clz is Chemical_id:
        return parse_chemical_id(d, path, default_search, label)
    elif clz is Person_id:
        return parse_person_id(d, path, default_search, label)
    elif clz is Database_id:
        return parse_database_id(d, path, default_search, label)
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


def parse_keyword(d, path, default_search, label):
    for constraint in d._constraints_inst:
        constraint_name = type(constraint).__name__
        if not constraint.is_active:
            continue
        if constraint_name == "StringEquals":
            return ModelEnum(d, path, default_search, label)
    return ModelPrimitive(d, "keyword", path, default_search, label)


def parse_database_id(d, path, default_search, label):
    return parse_keyword(d, path, default_search, label)


def parse_person_id(d, path, default_search, label):
    return parse_keyword(d, path, default_search, label)


def parse_publication_id(d, path, default_search, label):
    return parse_keyword(d, path, default_search, label)


def parse_chemical_id(d, path, default_search, label):
    return parse_keyword(d, path, default_search, label)


def parse_schema(schema, path, includes):
    for k, v in schema.includes.items():
        includes[k] = v
    return parse(schema.dict, path, includes)


def parse_file(ym_file, modelbase_only=False) -> Union[Model, ModelBase]:
    schema_data = Path(ym_file).read_text()
    schema_data = re.sub(
        r"default_search(\s*:\s*)True", r"default_search\1true()", schema_data
    )
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


def json_to_yaml(json_dict):
    yaml = ruamel_YAML()
    yaml.default_flow_style = False
    yaml.preserve_quotes = True
    yaml.allow_unicode = True
    yaml.sort_base_mapping_type_on_output = True
    yaml.Representer = NonAliasingRTRepresenter
    io = StringIO()
    yaml.dump(ruamel_quote_booleans(json_dict), io)
    io.seek(0)
    loaded = yaml.load(io)
    set_flow_style(loaded)
    io = StringIO()
    yaml.dump(loaded, io)
    return io.getvalue()


def get_filename(name: str, out_dir: Path, model_package: str) -> Path:
    if model_package:
        model_package = f"{model_package}-"

    return out_dir / f"{model_package}{name}.yaml"


def ruamel_quote_booleans(d):
    if isinstance(d, (list, tuple)):
        return [ruamel_quote_booleans(x) for x in d]
    elif isinstance(d, dict):
        return {
            ruamel_quote_booleans(k): ruamel_quote_booleans(v) for k, v in d.items()
        }
    elif d in ("Yes", "No", "On", "Off"):
        return DoubleQuotedScalarString(d)
    else:
        return d


@click.command()
@click.argument(
    "input_file",
    default=Path(__file__).parent.parent / "models" / "main" / "MST.yaml",
    required=True,
)
@click.option("--debug", type=bool)
@click.option("--only_defs", type=bool)
@click.option("--out_dir", type=Path)
@click.option(
    "--include",
    default=Path(__file__).parent.parent
    / "models"
    / "main"
    / "general_parameters.yaml",
    required=False,
)
def run(input_file, debug, out_dir, only_defs, include):
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

    out = [(model.to_defs(), "definitions", model.package)]

    if not only_defs:
        out += [
            (model.to_json(), "metadata", model.package),
            (model.to_files_meta(filename=attachment), "files", ""),
        ]

    for json_dict, name, model_package in out:
        yaml_text = json_to_yaml(json_dict)

        if out_dir:
            output_file = get_filename(name, out_dir, model_package)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(yaml_text)

        else:
            print(yaml_text)


if __name__ == "__main__":
    run()
