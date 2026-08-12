#!/usr/bin/env python3

#MODEL_DIR='../models'
#./full_unroll.py --schema-files $MODEL_DIR/values-only/MST.yaml --includes $MODEL_DIR/values-only/general_parameters.yaml

#./full_unroll.py --schema-files $MODEL_DIR/values-only/*.yaml --includes $MODEL_DIR/values-only/general_parameters.yaml

import sys
from argparse import ArgumentParser
from copy import deepcopy
from pathlib import Path
from typing import List, Tuple

import yamale
import yamale.validators.validators as validators
from yamale.readers import parse_yaml

current_dir = Path(__file__).parent.absolute()
root_dir = current_dir.parent.absolute()
sys.path.append(str(root_dir))
from tools import custom_validators
from tools.paths import MODEL_DIR


class ExpandedInclude:
    """Container that keeps the original include reference and its expanded content."""

    def __init__(self, validator, included):
        self.validator = validator
        self.included = included

    def __repr__(self):
        return f"ExpandedInclude(validator={self.validator!r}, included={self.included!r})"


class ExpandedChoose:
    """Container that keeps the original Choose validator and expanded options."""

    def __init__(self, validator, options):
        self.validator = validator
        self.options = options

    def __repr__(self):
        return f"ExpandedChoose(validator={self.validator!r}, options={self.options!r})"


class YamaleTree:
    """Class for building and storing unrolled yaml tree"""

    def __init__(self, schema_file: Path):
        self.schema = yamale.make_schema(
            schema_file, validators=custom_validators.extend_validators # custom_validators.extend_validators are our custom validators defined in tools/custom_validators.py
        )
        self.includes = self.schema.includes # This is a dictionary that gets populated with the includes from schema when the Schema object is created. It maps include names to their content.
        self.tree = deepcopy(self.schema._schema) # This is the actual unrolled tree that will be built by replacing include references with their content. The unrolling process will modify this tree in place.
                                                  # self.schema._schema is the processed version of the original raw schema dict, where all validation strings have been replaced with their corresponding validator objects.
                                                  # A deep copy constructs a new compound object and then, recursively, inserts copies into it of the objects found in the original

    def add_external_includes(self, *args: Path) -> None:
        """adds includes from external schemas"""
        for external_include in args:
            self._add_includes(external_include)

        # update includes and tree with the new information
        self.includes = self.schema.includes
        self.tree = deepcopy(self.schema.dict)

    def _add_includes(self, external_include: Path) -> None:
        """
        Helper function to extract includes from all documents
        within a multi document yamale schema
        """
        includes = parse_yaml(external_include)
        for include in includes:
            self.schema.add_include(include)

    def build(self):
        """
        Expands the tree from the initially supplied schema by passing it
        iteratively to _construct_tree until it no longer changes
        """
        while True:
            old_tree_string = str(self.tree)
            self._construct_tree(self.tree)
            new_tree_string = str(self.tree)
            if old_tree_string == new_tree_string:
                break

    def write(self, path):
        """
        Collects annotations, sets indentation levels and writes the unrolled
        yaml tree to the supplied file path
        """
        tree_lines = ""
        for key, value, level in self._walk_tree(self.tree):
            indentation = "  |  " * level
            summary = self._value_summary(value)
            #debugging
            #print(f"key: {key}, value: {value}, summary: {summary}, is_required: {value.is_required if issubclass(value.__class__, yamale.validators.Validator) else 'N/A'}, choose: {isinstance(value, ExpandedChoose)}, simple_dict: {isinstance(value, dict)}")
            line = f"{indentation} {key}"
            line = f'{line} {(90 - len(line)) * " "} {summary} "\n"'
            tree_lines += line

        with open(path, "w") as f:
            f.write(tree_lines)

    @staticmethod
    def _value_summary(value) -> Tuple[str, str, List[str], dict]:
        # #debugging
        # val = "value: " + str(value) + "\n"
        # p = Path('/home/plucarovaj/Documents/for-sync/mbdb-testing/systematic-testing/unroll')
        # with open(p.joinpath("value.txt"), "w") as f:
        #     f.write(val)
        """Helper function to extract summary information from yamale objects"""
        if isinstance(value, ExpandedInclude):
            include_required = {True: "required", False: "optional"}[value.validator.is_required]
            if isinstance(value.included, ExpandedChoose):
                return "singular", include_required, ["Choose"], value.validator.kwargs
            value = value.validator

        if isinstance(value, ExpandedChoose):
            value = value.validator

        value_multiplicity = "singular"
        value_importance = ""
        value_types = [type(value).__name__]
        value_constraints = {}

        # #debugging
        # if not isinstance(value, dict):
        #     val = "value: " + str(value) + "\n"
        #     with open(p.joinpath("non-dict.txt"), "a") as f:
        #         f.write(val)

        if isinstance(value, dict):
            # #debugging
            # val = "value: " + str(value) + "\n"
            # with open(p.joinpath("dict.txt"), "a") as f:
            #     f.write(val)
            value_importance = "-"

        if issubclass(value.__class__, yamale.validators.Validator):
            # #debugging
            # val = "value: " + str(value) + "\n"
            # with open(p.joinpath("validator.txt"), "a") as f:
            #     f.write(val)
            value_importance = {True: "required", False: "optional"}[value.is_required]
            value_constraints = value.kwargs
            if value_types[0] == "List":
                value_multiplicity = "list"
                #print(f"key: {key}, List value: {value}, is_required: {value.is_required}") # debugging, summary_list.txt
                value_types = [
                    type(val.validator).__name__
                    if isinstance(val, ExpandedChoose) or isinstance(val, ExpandedInclude)
                    else type(val).__name__
                    for val in value.args
                ]
        return value_multiplicity, value_importance, value_types, value_constraints

    def _walk_tree(self, tree, level=0):
        """
        Helper function that recursively walks the tree after it has been
        build
        """
        for key, value in tree.items():
            yield key, value, level

            # make sure all elements of a subcategory is extracted
            if isinstance(value, dict):
                #print(f"{key}: {value}")  # debugging
                yield from self._walk_tree(value, level=level + 1)

            # make sure all elements in a yamale list or any object is extracted
            elif isinstance(value, validators.List):
                for arg in value.args:
                    if isinstance(arg, dict):
                        yield from self._walk_tree(arg, level=level + 1)
                    elif isinstance(arg, ExpandedChoose):
                        for option_name, option_fields in arg.options.items():
                            yield option_name, option_fields, level + 1
                            if isinstance(option_fields, dict):
                                yield from self._walk_tree(option_fields, level=level + 2)
                    elif isinstance(arg, ExpandedInclude):
                        if isinstance(arg.included, dict):
                            yield from self._walk_tree(arg.included, level=level + 1)
                        elif isinstance(arg.included, ExpandedChoose):
                            for option_name, option_fields in arg.included.options.items():
                                yield option_name, option_fields, level + 1
                                if isinstance(option_fields, dict):
                                    yield from self._walk_tree(option_fields, level=level + 2)

            elif isinstance(value, ExpandedInclude):
                if isinstance(value.included, dict):
                    yield from self._walk_tree(value.included, level=level + 1)
                elif isinstance(value.included, ExpandedChoose):
                    for option_name, option_fields in value.included.options.items():
                        yield option_name, option_fields, level + 1
                        if isinstance(option_fields, dict):
                            yield from self._walk_tree(option_fields, level=level + 2)

            elif isinstance(value, ExpandedChoose):
                for option_name, option_fields in value.options.items():
                    yield option_name, option_fields, level + 1
                    if isinstance(option_fields, dict):
                        yield from self._walk_tree(option_fields, level=level + 2)

    def _get_include(self, value, att="dict"):
        """Helper function to extract the content of a yamale include"""
        if att == "dict":                                               # example value: Include(('General_parameters',), {})
            return deepcopy(self.includes[value.include_name].dict)     #for example above: value.include_name = 'General_parameters', 
                                                                        #self.includes[value.include_name] is the Schema object created for the 'General_parameters' include,
                                                                        #and self.includes[value.include_name].dict is the original raw schema dict for that include, which is what we want to insert into the tree to replace the include reference.
        elif att == "_schema":
            # #debugging
            #print(value.include_name, value)
            return deepcopy(self.includes[value.include_name]._schema)
        else:
            return

    @staticmethod
    def _is_choose_validator(value) -> bool:
        return hasattr(value, "base_schema") and hasattr(value, "detailed_schemas")

    def _parse_choose_string(self, value: str):
        parsed = yamale.make_schema(
            content=f"tmp: {value}", validators=custom_validators.extend_validators
        )
        # debugging
        #print(parsed.dict["tmp"])
        return parsed.dict["tmp"]

    def _resolve_choose(self, value):
        """Expand choose(...) into per-option merged field dictionaries."""
        choose_value = value
        if isinstance(choose_value, str):
            choose_value = self._parse_choose_string(choose_value) # in some cases the choose validator may not be recognized as a custom validator , but string.
            # parse_choose_string turns it to the actual Choose object.
            #The parsing is done by creating a temporary schema with the choose string as the content, and then extracting the parsed value from the resulting schema dict.

        base_fields = {}
        if hasattr(choose_value, "base_schema") and isinstance(
            choose_value.base_schema, validators.Include
        ):
            base_data = self.includes.get(choose_value.base_schema.include_name)
            if base_data is not None:
                base_dict = base_data.dict if hasattr(base_data, "dict") else base_data
                if isinstance(base_dict, dict):
                    base_fields = deepcopy(base_dict)

        options = {}
        for option_name, option_include in choose_value.detailed_schemas.items(): # example: detailed_schemas: {'Yes': Include(('Yes_purity',), {}), 'No': Include(('Empty_object',), {})}
            option_fields = {}
            if isinstance(option_include, validators.Include):
                option_data = self.includes.get(option_include.include_name) # option_data is the schema object corresponding to the include's reference
                if option_data is not None:
                    option_dict = (
                        option_data.dict if hasattr(option_data, "dict") else option_data # option_dict is the original raw schema dict for that include if it exists
                    )
                    if isinstance(option_dict, dict):
                        option_fields = deepcopy(option_dict)

            merged = deepcopy(base_fields)
            merged.update(option_fields)
            options[option_name] = merged

        return ExpandedChoose(choose_value, options)

    def _construct_tree(self, tree):
        """
        Helper function that finds include objects and replaces them with the
        object it references. This is where the actual unrolling of the yamale
        schema happens
        """
        for (
            key,
            value,
        ) in tree.items():
            if isinstance(value, ExpandedChoose):
                for option_fields in value.options.values():
                    if isinstance(option_fields, dict):
                        self._construct_tree(option_fields)

            elif isinstance(value, ExpandedInclude):
                if isinstance(value.included, dict):
                    self._construct_tree(value.included)
                if isinstance(value.included, ExpandedChoose):
                    for option_fields in value.included.options.values():
                        if isinstance(option_fields, dict):
                            self._construct_tree(option_fields)

            elif isinstance(value, dict):
                self._construct_tree(value)

            elif isinstance(value, validators.Include):
                ## debugging
                # print(f'direct: {key}')
                #is_required = value.is_required if hasattr(value, "is_required") else "N/A"
                included = self._get_include(value) # this is the content of the include, which can be a dict (the original schema) or a yamale validator object depending on the structure of the included schema
                if isinstance(included, str):
                    included = self._get_include(value, "_schema")
                    #debugging
                    #print(included, type(included)) # e.g. 'Choose((), {})' or 'Enum(('K', '°C', '°F'), {})'
                if self._is_choose_validator(included):
                    #debugging
                    #print(f'base_schema: {include.base_schema}, detailed_schemas: {include.detailed_schemas}') # base_detailed_schemas.txt
                    #print(include, type(include)) # the include: 'Choose((), {})'  <class 'tools.custom_validators.Choose'>
                    included = self._resolve_choose(included)
                    #debugging
                    #print(f'include after resolve_choose: {include}, type: {type(include)}') # include_after_resolve_choose.txt
                include = ExpandedInclude(value, included)
                tree.update({key: include})

            elif self._is_choose_validator(value):
                ## debugging
                #print(f'key: {key}, value: {value}, value_type: {type(value)}, value_is_str: {isinstance(value, str)}') # choose_validator.txt
                tree.update({key: self._resolve_choose(value)})

            elif isinstance(value, validators.List):
                includes = []
                value_class = value.__class__ # this is the List class from yamale
                for arg in value.args:
                    include = arg
                    if isinstance(arg, validators.Include): #e.g. nested_include('Entity') in list(nested_include('Entity'), min=1)
                        ## debugging
                        #print(f'list: {key}') # e.g. list: entities_of_interest
                        #print(f'arg: {arg}, type(arg): {type(arg)}') # e.g. arg: Nested_include(('Entity',), {}), type(arg): <class 'tools.custom_validators.Nested_include'>
                        include = self._get_include(arg) # returns the raw dict for the include's Schema
                        if isinstance(include, str): # if the returned include is a string, we need to get the _schema instead to resolve choose validator correctly
                            #debugging
                            #print(include, type(include)) # list_include_string.txt, e.g. choose(include('Entity_base'),...) <class 'str'>
                            #print(arg, type(arg)) # Nested_include(('Entity',), {}) <class 'tools.custom_validators.Nested_include'>
                            include = self._get_include(arg, "_schema")
                            #debugging
                            #print(include, type(include)) # list_include_string_schema.txt, e.g. Choose((), {}) <class 'tools.custom_validators.Choose'>
                        if self._is_choose_validator(include):
                            #print(include.base_schema, type(include)) #e.g. Include(('Entity_base',), {}) <class 'tools.custom_validators.Choose'>
                            include = self._resolve_choose(include)
                    elif isinstance(arg, dict):
                        ##debugging
                        #print(f"dict arg: {arg}") # list_dict_arg.txt
                        self._construct_tree(arg)
                    # elif isinstance(arg, ExpandedInclude):
                    #     if isinstance(arg.included, dict):
                    #         self._construct_tree(arg.included)
                    elif isinstance(arg, ExpandedChoose):
                        for option_fields in arg.options.values():
                            if isinstance(option_fields, dict):
                                self._construct_tree(option_fields)
                    elif isinstance(arg, str) and "choose(" in arg:
                        include = self._resolve_choose(arg)
                    elif self._is_choose_validator(arg):
                        include = self._resolve_choose(arg)
                    includes.append(include)
                if includes:
                    list_kwargs = deepcopy(value.kwargs)
                    list_kwargs.update(
                        {
                            "required": value.is_required,
                            "none": value.can_be_none,
                        }
                    )
                    tree.update({key: value_class(*includes, **list_kwargs)})
            else:
                continue


def new_filename(file):
    parent_folder = file.parent
    file_name = file.name.replace(".yaml", "-full.txt")
    return parent_folder, file_name


def _mk_arg_parser() -> ArgumentParser:
    """Command line interface"""
    parser = ArgumentParser(description="Unrolling the mbdb values-only yamale schemas")
    parser.add_argument(
        "--schema-files",
        nargs="+",
        type=Path,
        help="Input Yamale schema files without descriptions",
        default=[MODEL_DIR / "values-only" / "MST.yaml"], # list expected because of nargs="+"
                                                                     # MODEL_DIR is a Path object, therefore MODEL_DIR / "string" automatically creates a new Path object for the combined path
    )
    parser.add_argument(
        "--output-folder",
        type=Path,
        help="Output folder where the unrolled structures will be stored",
        default=MODEL_DIR / "unrolled" / "fully-unrolled",
    )
    parser.add_argument(
        "--includes",
        nargs="+",
        type=Path,
        help="Additional Yamale schema input files without descriptions to be used as includes",
        default=[
            MODEL_DIR
            / "values-only"
            / "general_parameters.yaml"
        ],
    )
    return parser


def main():
    args = _mk_arg_parser().parse_args()
    for path in args.schema_files:
        yt = YamaleTree(path)
        #debugging
        # print(yt.schema.includes) #i1_initial_includes.txt
        if args.includes:
            yt.add_external_includes(*args.includes)
        #debugging
        #print(yt.schema.includes) #i2_with_external_includes.txt
        #for key, value in yt.tree.items():
        #     print(f"key: {key}, value: {value}, value_name: {value.include_name}, referred_include: {yt.includes[value.include_name].dict}, value_required: {value.is_required if issubclass(value.__class__, yamale.validators.Validator) else 'N/A'}") #yt_before_build.txt
        #     #self.includes[value.include_name].dict
        yt.build()
        # #debugging
        # for key, value in yt.tree.items():
        #     print(f"key: {key}, value: {value}, value_type: {type(value)}, value_required: {value.is_required if issubclass(value.__class__, yamale.validators.Validator) else 'N/A'}") #yt_after_build.txt, yt_after_build2.txt, yt_after_build3.txt
        parent, name = new_filename(path)
        if args.output_folder:
            parent = args.output_folder
        yt.write(parent.joinpath(name))


if __name__ == "__main__":
    main()
