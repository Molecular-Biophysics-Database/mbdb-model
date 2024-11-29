from yamale import make_schema

from tools.schema_merge import (
    merged_schema,
    add_includes,
)


def test_merge_schema(tmp_path):
    # Use tmp_path to create a temporary directory
    temp_dir = tmp_path / "my_temp_dir"
    temp_dir.mkdir()

    # schema (method specific)
    temp_schema = temp_dir / "test_schema.yaml"
    temp_schema.write_text(
    """
    UseTest: include('Test')
    """
    )

    # includes (general parameters)
    temp_includes = temp_dir / "test_includes.yaml"
    temp_includes.write_text(
    """
    Test: 
        testString: str()
        testNumber: num()
    """
    )

    # the merge of schema and includes should behave as if it was created in the same file
    content = """
UseTest: include('Test')
---
Test: 
    testString: str()
    testNumber: num()
"""
    result = make_schema(content=content)
    merged = merged_schema(temp_schema,temp_includes)
    assert merged.dict == result.dict

def test_add_include(tmp_path):

    content = """Test1: str()"""
    schema = make_schema(content=content)

    temp_dir = tmp_path / "my_temp_dir"
    temp_dir.mkdir()

    temp_includes = temp_dir / "test_includes.yaml"
    temp_includes.write_text(
    """
Test2: 
    testString: str()
---
Test3: 
    testNumber: num()
    """
    )

    result_content = """
Test1: str()
---
Test2: 
    testString: str()
Test3: 
    testNumber: num()
    """
    result = make_schema(content=result_content)
    assert schema.dict == result.dict
