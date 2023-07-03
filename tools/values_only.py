#!/usr/bin/env python3

from argparse import ArgumentParser
from pathlib import Path
from typing import List

import yaml


def _mk_arg_parser() -> ArgumentParser:
    """Command line interface"""
    parser = ArgumentParser(
        description="Removing description elements in mbdb main yamale schemas"
    )
    parser.add_argument(
        "schema_files",
        nargs="+",
        type=Path,
        help="Input Yamale schema files with descriptions",
    )
    parser.add_argument(
        "--output-folder",
        type=Path,
        help="Output folder where the schemas without structures will be stored",
    )
    return parser


class SimplifiedSchema:
    def __init__(self):
        self.yaml_docs: List[dict] = []

    def read(self, path: Path) -> List[dict]:
        """Reads a YAML file"""
        with open(path, "r") as f_in:
            self.yaml_docs = list(yaml.load_all(f_in, Loader=yaml.CSafeLoader))

    def write(self, path: Path) -> None:
        """Writes a YAML file"""
        with open(path, "w") as f_out:
            yaml.dump_all(
                self.yaml_docs,
                stream=f_out,
                default_flow_style=False,
                sort_keys=False,
                encoding="utf-8",
                allow_unicode=True,
            )

    def strip_description(self) -> None:
        """Go through all yaml documents and remove descriptions inplace"""
        for doc in self.yaml_docs:
            self._remove_description(doc)

    def _remove_description(self, doc: dict) -> None:
        """
        If ('description' AND 'value') are present in the same scope, all the
        keys of this scope will recursively be replaced by the value of the
        'value' key
        """
        if not isinstance(doc, dict):
            return

        for key, value in doc.items():
            if ("value" in value) and ("description" in value):
                doc.update({key: value["value"]})

            else:
                self._remove_description((doc[key]))


def new_filename(file):
    parent_folder = file.parent
    file_name = file.name
    return parent_folder, file_name


def main() -> None:
    args = _mk_arg_parser().parse_args()
    for path in args.schema_files:
        simple_schema = SimplifiedSchema()
        simple_schema.read(path)
        simple_schema.strip_description()
        parent, name = new_filename(path)
        if args.output_folder:
            parent = args.output_folder
        simple_schema.write(parent.joinpath(name))


if __name__ == "__main__":
    main()
