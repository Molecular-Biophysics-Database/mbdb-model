#!/usr/bin/env python3
import json
import os
import random
import string
import uuid
from copy import deepcopy
from glob import glob
from pathlib import Path

import click
import numpy as np
import ruamel.yaml
import yamale.schema
import yamale.validators as validators

import custom_validators
from validate_examples import merged_schema


class AnnotatedValidator:
    def __init__(self, name: str, value: validators.Validator | dict, includes):
        self.name = name
        self.validator_type = type(value)
        self.constraints = self.get_constraints(value)
        self.is_required = self.get_required_status(value)

    @staticmethod
    def get_required_status(validator: validators.Validator | dict):
        if isinstance(validator, dict):
            return True
        return validator.is_required

    @staticmethod
    def get_constraints(validator: validators.Validator | dict):
        if isinstance(validator, dict):
            return {}
        return validator.kwargs

    def __repr__(self):
        return (
            f"<name={self.name}, "
            f"validator_type={self.validator_type}, "
            f"constrains={self.constraints}, "
            f"is_required={self.is_required}>"
        )


class EnumValidator(AnnotatedValidator):
    def __init__(self, name, value: validators.Enum, includes):
        super().__init__(name=name, value=value, includes=includes)
        self.args = self.get_args(value)

    @staticmethod
    def get_args(validator: validators.Enum):
        return validator.args

    def __repr__(self):
        return (
            f"<name={self.name}, "
            f"validator_type={self.validator_type}, "
            f"constrains={self.constraints}, "
            f"is_required={self.is_required}, "
            f"args={self.args}>"
        )


class VocabularyValidator(AnnotatedValidator):
    def __init__(self, name, value: custom_validators.Vocabulary, includes):
        super().__init__(name=name, value=value, includes=includes)
        self.vocabulary = value.vocabulary


class LinkTargetValidator(AnnotatedValidator):
    def __init__(self, name, value: custom_validators.LinkTarget, includes):
        super().__init__(name=name, value=value, includes=includes)
        self.target_name = value.name


class LinkValidator(AnnotatedValidator):
    def __init__(self, name, value: custom_validators.Link, includes):
        super().__init__(name=name, value=value, includes=includes)
        self.target = value.target


class NestedValidator(AnnotatedValidator):
    def __init__(
        self, name, value: validators.Validator | dict, includes, nested_elements=None
    ):
        super().__init__(name=name, value=value, includes=includes)
        self.nested_elements = nested_elements
        if nested_elements is None:
            self.nested_elements = self.get_nested_elements(value, includes)

    def get_nested_elements(self, value, includes):
        func = self.get_nested_func()
        elements = func(value=value, includes=includes, key=self.name)
        return [to_av(element, includes) for element in elements]

    def get_nested_func(self):
        nested_func = {
            dict: self.from_dict,
            validators.List: self.from_list,
            validators.Include: self.from_include,
            custom_validators.Nested_include: self.from_include,
            custom_validators.Choose: self.from_choose,
        }

        return nested_func[self.validator_type]

    @staticmethod
    def from_dict(value: dict, **kwargs):
        return [{k: v} for k, v in value.items()]

    @staticmethod
    def from_list(key, value: validators.List, **kwargs):
        return [{key: v} for v in value.validators]

    @staticmethod
    def from_choose(value: custom_validators.Choose, includes: dict, **kwargs):
        unrolled = includes[value.base_schema.include_name].dict
        unrolled.update(value.detailed_schemas)
        return [{k: v for k, v in unrolled.items()}]

    def from_include(self, key, value: validators.Include, includes: dict, **kwargs):
        include = deepcopy(includes[value.include_name]._schema)
        if isinstance(include, (custom_validators.Choose, validators.Enum)):
            include = {key: include}

        return [{k: v} for k, v in include.items()]

    def __repr__(self):
        return (
            f"<name={self.name}, "
            f"validator_type={self.validator_type}, "
            f"constrains={self.constraints}, "
            f"is_required={self.is_required}, "
            f"nested_elements={self.nested_elements}>"
        )


class ChooseValidator(NestedValidator):
    def __init__(self, name, value: validators.Validator | dict, includes):
        super().__init__(name=name, value=value, includes=includes)
        self.type_field = self.get_type_field(value)

    @staticmethod
    def get_type_field(value):
        return value.type_field

    def __repr__(self):
        return (
            f"<name={self.name}, "
            f"validator_type={self.validator_type}, "
            f"constrains={self.constraints}, "
            f"is_required={self.is_required}, "
            f"type_field={self.type_field}, "
            f"nested_elements={self.nested_elements}>"
        )


def pick_av(validator_type):
    primitives = (
        validators.Number,
        validators.Integer,
        validators.String,
        validators.Day,
        validators.Boolean,
        custom_validators.Keyword,
        custom_validators.Fulltext,
        custom_validators.Chemical_id,
        custom_validators.Database_id,
        custom_validators.Chemical_id,
        custom_validators.Person_id,
        custom_validators.MacroMolecule_id,
        custom_validators.Publication_id,
        custom_validators.Uuid,
        custom_validators.Url,
    )

    simple_nested = (
        validators.List,
        validators.Include,
        custom_validators.Nested_include,
        dict,
    )

    if validator_type in primitives:
        return AnnotatedValidator

    elif validator_type is validators.Enum:
        return EnumValidator

    elif validator_type is custom_validators.Vocabulary:
        return VocabularyValidator

    elif validator_type is custom_validators.Link:
        return LinkValidator

    elif validator_type is custom_validators.LinkTarget:
        return LinkTargetValidator

    elif validator_type in simple_nested:
        return NestedValidator

    elif validator_type is custom_validators.Choose:
        return ChooseValidator

    else:
        raise ValueError(f"'{validator_type}' is not a known validator")


def is_nested(validator: validators.Validator | dict):
    nested_validators = (
        validators.List,
        validators.Include,
        dict,
        custom_validators.Choose,
    )
    return isinstance(validator, nested_validators)


def to_av(tree, includes):
    av_list = []
    for name, value in tree.items():
        val = pick_av(type(value))
        av_list.append(val(name=name, value=value, includes=includes))

    if len(av_list) == 1:
        return av_list[0]
    else:
        return NestedValidator(
            name="", value={}, nested_elements=av_list, includes=includes
        )


def random_int(*args, min=-9999, max=9999):
    return random.randint(min, max)


def random_float(*args, min=-9999.0, max=9999.0):
    return random.uniform(min, max)


def random_string(*args, min=10, max=100, equals=None, char_set=None):
    if equals is not None:
        return equals

    if char_set is None:
        char_set = string.ascii_letters + "ěšščřžýýáíéí"

    n_chars = random.randint(min, max)
    random_indexes = random.choices(range(0, len(char_set)), k=n_chars)

    return "".join([char_set[pos] for pos in random_indexes])


def random_dict_like(av, link_dict, vocab_dict):
    # dict like random objects (excluding includes that only have a chose element)
    ret = {
        nested.name: type_mapping(nested, link_dict, vocab_dict)
        for nested in av.nested_elements
    }

    # chose elements are implemented as includes. This leads to a nesting artifact e.g.,
    # {chose_name: {choose_name: {k1: v1, k2: v2 }}, which needs to be removed to get the correct return value of
    # {choose_name: {k1: v1, k2: v2

    choose_name = None
    for nested in av.nested_elements:
        if nested.validator_type is custom_validators.Choose:
            choose_name = nested.name

    if choose_name is not None:
        return ret.pop(choose_name)

    return ret


def random_list(av, link_dict=None, vocab_dict=None, min=1, max=5):
    number_of_items = random.randint(min, max)
    return [
        type_mapping(av.nested_elements[0], link_dict=link_dict, vocab_dict=vocab_dict)
        for i in range(number_of_items)
    ]


def random_enum(av, **kwargs):
    return random.choice(av.args)


def random_link(av: LinkValidator, link_dict, **kwargs):
    targets = link_dict[av.target]
    r_id = random.choice(tuple(targets.keys()))

    return {"id": r_id, "name": targets[r_id]}


def random_linktarget(av: LinkTargetValidator, link_dict, **kwargs):
    if av.target_name not in link_dict.keys():
        link_dict[av.target_name] = {}

    while True:
        r_id = random_string(max=10)
        exists_id = link_dict[av.target_name]
        if r_id not in exists_id.keys():
            linktarget_id = r_id
            linktarget_name = random_string(max=10)
            exists_id[r_id] = linktarget_name
            break

    return {"id": linktarget_id, "name": linktarget_name}


def random_choose(av, link_dict, vocab_dict, **kwargs):
    elements = av.nested_elements[0].nested_elements
    types = [e.args for e in elements if e.name == av.type_field][0]
    unrolled = {
        nested.name: type_mapping(nested, link_dict=link_dict, vocab_dict=vocab_dict)
        for nested in elements
    }

    picked_type = unrolled[av.type_field].replace("_", " ")
    exclude_types = [t for t in types if t != picked_type]
    for excluded in exclude_types:
        unrolled.pop(excluded.replace(" ", "_"))
    picked_content = unrolled.pop(picked_type.replace(" ", "_"))
    unrolled.update(picked_content)
    return unrolled


def random_vocabulary(av: VocabularyValidator, vocab_dict, **kwargs):
    return {"id": random.choice(vocab_dict[av.vocabulary])}


def random_person_id(*args):
    orcid = "-".join(
        [random_string(min=4, max=4, char_set="0123456789") for i in range(4)]
    )
    return f"ORCID:{orcid}"


def random_id(av, *args):
    return f"{random_string(min=4, max=10)}:{random_string(min=4, max=10)}"


def random_uuid(*args):
    return str(uuid.uuid4())


def random_url(*args):
    site = random_string(min=4, max=10)
    domain = f"{random_string(min=2, max=3)}.{random_string(min=2, max=3)}"
    endpoint = random_string(min=5, max=10)
    return f"https://{site}.{domain}/{endpoint}"


def random_day(*args, min="2020-01-01", max="2030-01-01"):
    span_int = np.datetime64(max) - np.datetime64(min)
    r_int = random.randint(0, span_int.astype(int))
    return str(np.datetime64(min) + r_int)


def random_bool(*args):
    return choose_state()


def choose_state(optional_probability=0.5):
    return random.choices(
        [True, False], weights=[optional_probability, 1 - optional_probability]
    )[0]


def type_mapping(av: AnnotatedValidator, link_dict, vocab_dict):
    if not av.is_required:
        if not choose_state():
            return

    picker = {
        validators.Number: random_float,
        validators.Integer: random_int,
        validators.String: random_string,
        validators.Day: random_day,
        custom_validators.Keyword: random_string,
        custom_validators.Fulltext: random_string,
        validators.Enum: random_enum,
        validators.Boolean: random_bool,
        custom_validators.Chemical_id: random_id,
        custom_validators.Database_id: random_id,
        custom_validators.MacroMolecule_id: random_id,
        custom_validators.Publication_id: random_id,
        custom_validators.Person_id: random_person_id,
        custom_validators.Url: random_url,
        custom_validators.Uuid: random_uuid,
    }

    nested_and_links = {
        validators.Include: random_dict_like,
        custom_validators.Nested_include: random_dict_like,
        dict: random_dict_like,
        validators.List: random_list,
        custom_validators.Choose: random_choose,
        custom_validators.LinkTarget: random_linktarget,
        custom_validators.Link: random_link,
        custom_validators.Vocabulary: random_vocabulary,
    }

    if av.validator_type in picker.keys():
        random_value = picker[av.validator_type](av, **av.constraints)
        return random_value

    elif av.validator_type in nested_and_links.keys():
        random_value = nested_and_links[av.validator_type](
            av, link_dict=link_dict, vocab_dict=vocab_dict, **av.constraints
        )
        return random_value

    else:
        raise NotImplementedError(
            f"a random value for fields of type {av.validator_type} has not been implemented"
        )


def clean_linktargets(dic):
    """recursively turns all key value pairs of the form 'id': {'id': 'foo', 'name': bar}
    into 'id': 'foo', 'name': bar"""
    if "id" in dic:
        try:
            id_content = tuple(dic["id"])
        except TypeError:
            id_content = (None,)
        if "id" in id_content and "name" in id_content:
            dic.update(dic["id"])
            return

    else:
        for key, value in dic.items():
            if isinstance(value, dict):
                clean_linktargets(value)

            elif isinstance(value, list):
                if not isinstance(value[0], dict):
                    continue
                for list_element in value:
                    clean_linktargets(list_element)
            else:
                continue


def clean_none(dic):
    """recursively removes all key: value pairs of the form key: None"""
    for key, value in tuple(dic.items()):
        if value is None:
            dic.pop(key)

        elif isinstance(value, dict):
            clean_none(value)

        elif isinstance(value, list):
            if not isinstance(value[0], dict):
                continue
            for list_element in value:
                clean_none(list_element)
        else:
            continue


def clean_enum_includes(dic):
    """recursively turns all key value pairs of the form 'a': {'a': 'b'} into only the inner part 'a': 'b'"""

    if not isinstance(dic, dict):
        return
    for key, value in dic.items():
        if isinstance(value, dict):
            if key in value.keys():
                dic.update(value)
            clean_enum_includes(dic[key])

        elif isinstance(value, list):
            if not isinstance(value[0], dict):
                continue
            for list_element in value:
                clean_enum_includes(list_element)
        else:
            continue


def get_vocabulary_ids(vocabulary_fixture_path):
    with open(vocabulary_fixture_path) as f:
        entries = ruamel.yaml.safe_load_all(f)
        return [vocab["id"] for vocab in entries]


def changes_to_general_schema(schema: yamale.schema.Schema, input_file: Path):
    """changes requirement of fields such that consistent test data can be generated"""
    # derived parameters optional, however as a derived parameter is also optional in later if it's not set to be
    # required it can lead to links pointing to nowhere which is an error, so derived parameters is changed to required
    schema.includes["General_parameters"]._schema[
        "derived_parameters"
    ].is_required = True

    # make sure that supported technique is fixed to the technique of the input file
    technique = {
        "BLI": "Bio-layer interferometry (BLI)",
        "MST": "Microscale thermophoresis/Temperature related intensity change (MST/TRIC)",
        "SPR": "Surface plasmon resonance (SPR)",
    }

    schema.includes["SUPPORTED_TECHNIQUES"]._schema.args = (technique[input_file.stem],)

    # marshmallow and random_generator has opposite ways of determining the required status of child items in the corner
    # case it is an include of a single item. This, so far, only occurs for a few enums, so their status is changed to
    # True to allow the parent item to determine if the include it's required or not.

    const_enums = [
        "OBTAINED_TYPES",
        "CONCENTRATION_UNITS",
        "FLOWRATE_UNITS",
        "HUMIDITY_UNITS",
        "PRESSURE_UNITS",
        "TEMPERATURE_UNITS",
        "TIME_UNITS",
        "ENERGY_UNITS",
        "POWER_UNITS",
        "LENGTH_UNITS",
        "MOLECULAR_WEIGHT_UNITS",
        "SUPPORTED_TECHNIQUES",
        "COMPANIES",
    ]
    for con in const_enums:
        schema.includes[con]._schema.is_required = True
    return schema


def make_file_name(n, i, data_dir):
    data_dir = Path(data_dir)
    if not data_dir.exists():
        os.mkdir(data_dir)

    width = int(np.floor(np.log10(n)) + 1)
    return data_dir / f"{str(i + 1).zfill(width)}_testfile.json"


def with_header(mapped_dict):
    return {"metadata": mapped_dict}


def write_file(document_list, output_folder, as_fixture):
    if as_fixture:
        document_list = [document_list]

    for i, document in enumerate(document_list):
        fn = make_file_name(n=len(document_list), i=i, data_dir=output_folder)
        with open(fn, "w") as f_out:
            json.dump(document, f_out, ensure_ascii=False, indent=2)


@click.command()
@click.argument(
    "input_file",
    default=Path(__file__).parent.parent / "models" / "values-only" / "MST.yaml",
    required=True,
    type=Path,
)
@click.option(
    "--n_outputs",
    default=25,
    required=False,
    show_default=True,
)
@click.option(
    "--as_fixture",
    default=False,
    required=False,
    show_default=True,
)
@click.option(
    "--output_folder",
    default=Path(__file__).parent / "random_generated_data",
    required=False,
)
@click.option(
    "--include_schema",
    default=Path(__file__).parent.parent
    / "models"
    / "values-only"
    / "general_parameters.yaml",
    required=False,
)
def main(input_file, n_outputs, output_folder, include_schema, as_fixture):
    vocab_dir = Path(__file__).parent.parent / "vocabularies"
    vocabs = glob(f"{vocab_dir}/generated_vocabularies/*.yaml")

    if not vocabs:
        print("No vocabularies detected, generating them")
        os.system(vocab_dir / "generate_vocabularies.py")
        vocabs = glob(f"{vocab_dir}/generated_vocabularies/*.yaml")

    vocab_dict = {Path(vocab).stem: get_vocabulary_ids(vocab) for vocab in vocabs}

    inputs = (input_file, include_schema)
    full_schema = merged_schema(*inputs, validators=custom_validators.extend_validators)
    full_schema = changes_to_general_schema(full_schema, input_file)

    annotated_validators = to_av(full_schema.dict, full_schema.includes)

    document_list = []
    for i in range(n_outputs):
        link_dict = {}
        document = type_mapping(
            annotated_validators, link_dict=link_dict, vocab_dict=vocab_dict
        )
        clean_linktargets(document)
        clean_enum_includes(document)
        clean_none(document)

        document_list.append(with_header(document))

    write_file(document_list, output_folder, as_fixture)

    print(f"Generated {n_outputs} test documents in {output_folder}")


if __name__ == "__main__":
    main()
