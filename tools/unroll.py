#!/usr/bin/env python3

from argparse import ArgumentParser
from copy import deepcopy
from pathlib import Path
from typing import List, Tuple

import yamale
import yamale.validators.validators as validators
from yamale.readers import parse_yaml

from custom_validators import extend_validators


def _mk_arg_parser() -> ArgumentParser:
    """Command line interface"""
    parser = ArgumentParser(description="Unrolling the mbdb values-only yamale schemas")
    parser.add_argument(
        "schema_files",
        nargs="+",
        type=Path,
        help="Input Yamale schema files without descriptions",
    )
    parser.add_argument(
        "--output-folder",
        type=Path,
        help="Output folder where the unrolled structures will be stored",
    )
    parser.add_argument(
        "--includes",
        type=Path,
        nargs="+",
        help="Additional Yamale schema input files without descriptions to be used as includes",
    )
    return parser


class YamaleTree:
    """Class for building and storing unrolled yaml tree"""

    def __init__(self, schema_file: Path):
        self.schema = yamale.make_schema(schema_file, validators=extend_validators)
        self.includes = self.schema.includes
        self.tree = deepcopy(self.schema.dict)

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
            old_tree_string = str(deepcopy(self.tree))
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
            line = f"{indentation} {key}"
            line = f'{line} {(90 - len(line)) * " "} {summary} "\n"'
            tree_lines += line

        with open(path, "w") as f:
            f.write(tree_lines)

    @staticmethod
    def _value_summary(value) -> Tuple[str, str, List[str], dict]:
        """Helper function to extract summary information from yamale objects"""
        value_multiplicity = "singular"
        value_importance = ""
        value_types = [type(value).__name__]
        value_constraints = {}

        if isinstance(value, dict):
            value_importance = "required"

        if issubclass(value.__class__, yamale.validators.Validator):
            value_importance = {True: "required", False: "optional"}[value.is_required]
            value_constraints = value.kwargs
            if value_types[0] == "List":
                value_multiplicity = "list"
                value_types = [type(val).__name__ for val in value.args]
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
                yield from self._walk_tree(value, level=level + 1)

            # make sure all elements in a yamale list or any object is extracted
            elif isinstance(value, validators.List) or isinstance(
                value, validators.Any
            ):
                for arg in value.args:
                    if isinstance(arg, dict):
                        yield from self._walk_tree(arg, level=level + 1)

    def _get_include(self, value, att="dict"):
        """Helper function to extract the content of a yamale include"""
        if not att == "dict":
            return self.includes[value.include_name]._schema
        return self.includes[value.include_name].dict

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
            if isinstance(value, dict):
                self._construct_tree(value)

            elif isinstance(value, validators.Include):
                ## debugging
                # print(f'direct: {key}')
                include = self._get_include(value)
                if isinstance(include, str):
                    include = self._get_include(value, "_schema")
                tree.update({key: include})

            elif isinstance(value, validators.List) or isinstance(
                value, validators.Any
            ):
                includes = []
                value_class = value.__class__
                for arg in value.args:
                    include = arg
                    if isinstance(arg, validators.Include):
                        ## debugging
                        # print(f'list: {key}')
                        include = self._get_include(arg)
                    elif isinstance(arg, dict):
                        self._construct_tree(arg)
                    includes.append(include)
                if includes:
                    tree.update({key: value_class(*includes)})
            else:
                continue


def new_filename(file):
    parent_folder = file.parent
    file_name = file.name.replace(".yaml", ".txt")
    return parent_folder, file_name


def main():
    args = _mk_arg_parser().parse_args()
    for path in args.schema_files:
        yt = YamaleTree(path)
        if args.includes:
            yt.add_external_includes(*args.includes)
        yt.build()
        parent, name = new_filename(path)
        if args.output_folder:
            parent = args.output_folder
        yt.write(parent.joinpath(name))


if __name__ == "__main__":
    main()
