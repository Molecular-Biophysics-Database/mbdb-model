from random_generator import *
import yamale
import yamale.validators.validators as val

test_schema = """
topLevel:
    number: num(min=0, max=10)
    optionalNumber: num(required=False)
    singleInclude: include('firstInclude')
    optionalInclude: include('firstInclude', required=False)
    listOfIncludes: list(include('firstInclude'))

---
firstInclude:
    listOfNum: list(num(min=0))
    optionalString: str(required=False)
"""

test_schema_dict = yamale.make_schema(content=test_schema).dict
test_schema_includes = yamale.make_schema(content=test_schema).includes


def test_is_nested():
    assert is_nested(test_schema_dict['topLevel']['listOfIncludes'])
    assert is_nested(test_schema_dict['topLevel'])


def test_get_required_status():
    assert get_required_status(test_schema_dict['topLevel'])
    assert not get_required_status(test_schema_dict['topLevel']['optionalNumber'])
    assert not get_required_status(test_schema_dict['topLevel']['optionalInclude'])


def test_get_constraints():
    assert get_constraints(test_schema_dict['topLevel']) == {}
    assert get_constraints(test_schema_dict['topLevel']['number']) == {'min': 0, 'max': 10}
    assert get_constraints(test_schema_dict['topLevel']['optionalNumber']) == {}


def test_from_dict():
    result = [{'listOfNum': val.List(val.Number(min=0))}, {'optionalString': val.String()}]
    assert from_dict(test_schema_includes['firstInclude'].dict) == result


def test_from_list():
    result = [{'listOfIncludes': val.Include('firstInclude')}]
    assert from_list('listOfIncludes', test_schema_dict['topLevel']['listOfIncludes']) == result


def test_from_include():
    result = [{'listOfNum': val.List(val.Number(min=0))}, {'optionalString': val.String(required=False)}]
    assert from_include(test_schema_dict['topLevel']['singleInclude'], includes=test_schema_includes) == result


def test_get_nested_func():
    assert get_nested_func(type({'a': 'b'})) == from_dict
    assert get_nested_func(type(val.List())) == from_list
    assert get_nested_func(type(val.Include(''))) == from_include

