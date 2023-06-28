#!/usr/bin/env python3

import yamale
import yamale.validators as validators
import custom_validators
import typing
from dataclasses import dataclass
import random
import string
from copy import deepcopy


@dataclass
class AnnotatedValidator:
    name: str
    validator_type: validators.Validator | dict
    constraints: dict
    args: tuple
    is_required: bool
    nested_elements: typing.List['AnnotatedValidator']


def is_nested(validator: validators.Validator | dict):
    nested_validators = (validators.List, validators.Include, dict, custom_validators.Choose)
    return isinstance(validator, nested_validators)


def get_required_status(validator: validators.Validator | dict):
    if isinstance(validator, dict):
        return True
    return validator.is_required


def get_constraints(validator: validators.Validator | dict):
    if isinstance(validator, dict):
        return {}
    return validator.kwargs


def get_args(validator: validators.Validator | dict):
    if isinstance(validator, dict):
        return ()
    return validator.args


def from_dict(value: dict, **kwargs):
    return [{k: v} for k, v in value.items()]


def from_list(key, value: validators.List, **kwargs):
    return [{key: v} for v in value.validators]


def from_choose(value: custom_validators.Choose, includes: dict, **kwargs):
    unrolled = includes[value.base_schema.include_name].dict
    unrolled.update(value.detailed_schemas)
    return [{k: v for k, v in unrolled.items()}]


def from_include(key, value: validators.Include, includes: dict, **kwargs):
    include = deepcopy(includes[value.include_name]._schema)

    if isinstance(include, custom_validators.Choose):
        include = {key: include}

    return [{k: v} for k, v in include.items()]


def get_nested_func(validator_type):
    nested_func = {dict: from_dict,
                   validators.List: from_list,
                   validators.Include: from_include,
                   custom_validators.Choose: from_choose
                   }

    return nested_func[validator_type]


def to_av(tree, includes):
    av_list = []
    for name, value in tree.items():
        validator_type = type(value)

        nested_elements = []
        if is_nested(value):
            func = get_nested_func(validator_type)
            elements = func(value=value, includes=includes, key=name)
            nested_elements = [to_av(element, includes) for element in elements]

        av_list.append(AnnotatedValidator(
                                  name=name,
                                  validator_type=validator_type,
                                  is_required=get_required_status(value),
                                  constraints=get_constraints(value),
                                  args=get_args(value),
                                  nested_elements=nested_elements
                                 ))
    if len(av_list) == 1:
        return av_list[0]
    else:
        return AnnotatedValidator(
            name='',
            validator_type=dict,
            is_required=True,
            constraints={},
            args=(),
            nested_elements=av_list
        )


def random_int(*args, min=-9999, max=9999):
    return random.randint(min, max)


def random_float(*args, min=-9999.0, max=9999.0):
    return random.uniform(min, max)


def random_string(*args, min=10, max=100, equals=None, char_set=None):
    if equals is not None:
        return equals

    if char_set is None:
        char_set = string.printable + 'ěšščřžýýáíéí'

    n_chars = random.randint(min, max)
    random_indexes = random.choices(range(0, len(char_set)), k=n_chars)

    return ''.join([char_set[pos] for pos in random_indexes])


def random_dict_like(av):
    return {nested.name: type_mapping(nested) for nested in av.nested_elements}


def random_list(av, min=1, max=10):
    number_of_items = random.randint(min, max)
    return [type_mapping(av.nested_elements[0]) for i in range(number_of_items)]


def random_enum(av, **kwargs):
    return random.choice(av.args)


def random_choose(av):

    pass


def choose_state(optional_probability=0.5):
    return random.choices([True, False], weights=[optional_probability, 1 - optional_probability])[0]


def type_mapping(av: AnnotatedValidator):

    if not av.is_required:
        if not choose_state():
            return

    picker = {validators.Number: random_int,
              validators.Integer: random_float,
              validators.Include: random_dict_like,
              custom_validators.Nested_include: random_dict_like,
              dict: random_dict_like,
              validators.String: random_string,
              custom_validators.Keyword: random_string,
              custom_validators.Fulltext: random_string,
              validators.Enum: random_enum,
              validators.List: random_list,
              custom_validators.Choose: random_choose
              }

    if av.validator_type in picker.keys():
        random_value = picker[av.validator_type](av, **av.constraints)
        return random_value

    else:
        raise NotImplementedError(f'a random value for fields of type {av.validator_type} has not been implemented')


def main():
    test_num = """
        #freeNumber: num(min=0, max=10)
        #optionalNumber: num(required=False)
        #stringy: list(str(min=4, max=5), min=10)  
        #anEnum: enum('a','b','c') 
        #aKeyword: keyword()
        #aFulltext: fulltext()
        #topLevel:
        #    number: num(min=0, max=10)
        #    includedNumber: include('firstInclude')  
        aChoose: include('ChooseInclude')
        
  
---
        firstInclude:
            listOfNum: list(num(min=0))
            #second: include('secondInclude')
        
        secondInclude:
            anotherNum: num()  
        
        ChooseBaseInclude:
            type: enum('Type 1', 'Type 2')
        ChooseInclude: choose(include('ChooseBaseInclude'), 
                              Type_1=include('Type_1'), 
                              Type_2=include('Type_2'))
            
        
        Type_1:
            content1: str(equals='A')
            
        Type_2:
            content2: str(equals='B')
                     
        """

    test_num_schema = yamale.make_schema(content=test_num, validators=custom_validators.extend_validators)
    #print(test_num_schema.dict)
    b = to_av(test_num_schema.dict, test_num_schema.includes)
    print(b)
    l = type_mapping(b)
    print(l)


if __name__ == '__main__':
    main()




