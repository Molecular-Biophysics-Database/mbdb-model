from argparse import ArgumentParser
from pathlib import Path
import json

def _mk_arg_parser() -> ArgumentParser:
    """Command line interface"""
    parser = ArgumentParser(
        description="Convert a JSON file into a form more readable for humans"
    )
    parser.add_argument(
        "json_files",
        nargs="+",
        type=Path,
        help="Files to prettify",
    )
    parser.add_argument(
        "--out",
        nargs="+",
        type=Path,
        help="Where converted files will be stored either (individual paths or a single directory), default is to overwrite input JSON files",
    )
    return parser

def load_json(json_file):
    with open(json_file) as f:
        return json.load(f)

def prettify(json_dict, indent=2, ensure_ascii=False):
    return json.dumps(json_dict, indent=indent, ensure_ascii=ensure_ascii)


def main():
    args = _mk_arg_parser().parse_args()
    if args.out:
        if args.out.is_dir():
            pass


    for path in args.json_files:

        simple_schema = SimplifiedSchema()
        simple_schema.read(path)
        simple_schema.strip_description()
        parent, name = new_filename(path)
        if args.output_folder:
            parent = args.output_folder
        simple_schema.write(parent.joinpath(name))


if __name__ == '__main__':
    main()