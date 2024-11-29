from os import write

import pytest

from model_conversion.values_only import (
    SimplifiedSchema,
    new_filename,
)

def simplified_schema(tmp_path, content: str):

    temp_schema = tmp_path  / "test_schema.yaml"
    temp_schema.write_text(content)

    ss = SimplifiedSchema()
    ss.read(temp_schema)
    return ss

def test_remove_description(tmp_path):
    content = """
    Test:
        description: str() 
        value: str()
        default_search: bool() 
    """
    schema = simplified_schema(tmp_path, content=content)
    schema.strip_description()
    assert schema.yaml_docs == [{"Test":"str()"}]

def test_remove_description_nested(tmp_path):
    content = """
    Test:
        nested:
            description: str() 
            value: str()
            default_search: bool()
            ui_file_context: blah 
    """
    schema = simplified_schema(tmp_path, content=content)
    schema.strip_description()
    assert schema.yaml_docs == [{"Test": {"nested": "str()"}}]


def test_write(tmp_path):
    schema = SimplifiedSchema()
    schema.yaml_docs = [{"Test":"str"}, {"other": "šěčř"}]
    write_path = tmp_path / "test_write.yaml"
    schema.write(write_path)
    with open(write_path, "r") as f:
        data = f.read()
    assert data == "Test: str\n---\nother: šěčř\n"

def test_new_filename(tmp_path):
    temp_dir = tmp_path / "test_dir"
    temp_dir.mkdir()
    temp_file = temp_dir / "test_file.yaml"
    parent, file = new_filename(temp_file)
    parent = parent.parts[-1]
    assert parent, file == ("test_dir", "test_file.yaml")
