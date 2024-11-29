from yamale import make_schema

from tools.schema_merge import (
    merged_schema,
    add_includes,
)


def test_merge_schema(tmp_path):

    # schema (method specific)
    temp_schema = tmp_path / "test_schema.yaml"
    temp_schema.write_text(
    """
    UseTest: include('Test')
    """
    )

    # includes (general parameters)
    temp_includes = tmp_path / "test_includes.yaml"
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

    for k, v in merged.includes.items():
        assert v.dict == result.includes[k].dict


def test_add_include(tmp_path):

    content = """Test1: str()"""
    schema = make_schema(content=content)

    temp_includes = tmp_path / "test_includes.yaml"
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
    add_includes(temp_includes,schema)
    assert schema.dict == result.dict

    for k, v in schema.includes.items():
        assert v.dict == result.includes[k].dict
