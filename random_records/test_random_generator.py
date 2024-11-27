import yamale.validators.validators as val
from random_generator import *

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
    assert is_nested(test_schema_dict["topLevel"]["listOfIncludes"])
    assert is_nested(test_schema_dict["topLevel"])
