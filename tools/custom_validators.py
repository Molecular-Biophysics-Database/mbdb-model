import re
from io import StringIO
from threading import local
from uuid import UUID

import ruamel.yaml
from yamale.schema.datapath import DataPath
from yamale.validators import DefaultValidators, Include, String, Validator

current_schema = local()


class LinkTarget(String):
    """
    Link target must always be a dict containing an "id" element which has LinkTarget type.
    In the data it would look like:

    {
        "id": "abcde-fghij",        # must be called "id" and gives unique identification within this document
        "title": "something"        # any elements here, for example "title"
    }

    In invenio, if an "id" would not be present, invenio will autogenerate it. It can also be generated on the client
    side in case you want to reference it in the same request

    Yamale for this looks like:

    chemical_compound:
        id: link_target(name="chemical-compound")
        title: str()
    """

    tag = "link_target"

    def __init__(self, *args, name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        

class Link(Validator):
    """
    Link looks like a dict with a $ref attribute.
    {
        "measurement": {
            "compound": {
                "$ref": "#abcde-fghij"
                "title": "something"        # note: the title value will be added automatically by Invenio,
                                            # does not need to be present in the deposited document
            }
        }
    }

    Yamale would look like:

    measurement:
        compound: link(target="chemical-compound")
    """

    tag = "link"

    def __init__(self, *args, target=None, fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.target = target
        self.fields = ruamel.yaml.safe_load(
            StringIO("blah: " + (fields or "[id,name]"))
        )["blah"]

    def _is_valid(self, value):
        if value is None:
            return True
        if not isinstance(value, dict):
            return False
        if "$ref" not in value:
            return False
        return True


class Keyword(String):
    tag = "keyword"


class Fulltext(String):
    tag = "fulltext"

class MacroMolecule_id(Keyword):
    tag = "macromolecule_id"
    # put into translation yamale2model
    # enum(pdb:, uniprot:)


class Database_id(Keyword):
    tag = "database_id"
    # put into translation yamale2model
    # enum(doi:)


class Chemical_id(Keyword):
    tag = "chemical_id"
    # put into translation yamale2model
    # enum(CAS number 'cas:', 'PubChem Compound ID pccid:', 'PubChem Substance ID pcsid:')


class Person_id(Keyword):
    tag = "person_id"
    # put into translation yamale2model
    # enum(orcid:')


class Nested_include(Include):
    tag = "nested_include"


class Publication_id(Keyword):
    tag = "publication_id"
    # put into translation yamale2model
    # enum(doi: isbn:')


class Choose(Validator):
    tag = "choose"
    # put into translation yamale2model

    def __init__(self, base_schema, *args, type_field="type", **kwargs):
        super().__init__(*args)
        self.base_schema = base_schema
        self.detailed_schemas = kwargs
        self.type_field = type_field

    def get_detailed_type(self, value):
        if self.type_field in value.keys():
            return value[self.type_field].replace(" ", "_")

    def remove_validated_items(self, value):
        base_schema = current_schema.schema.includes[self.base_schema.include_name]
        value = {**value}
        for field in base_schema.dict:
            value.pop(field, None)
        return value

    def fail(self, value):
        errs = current_schema.schema._validate_include(
            self.base_schema, value, path=DataPath(), strict=False
        )
        if errs != []:
            return "\n".join(errs)
        detailed_type = self.get_detailed_type(value)
        value = self.remove_validated_items(value)
        errs = current_schema.schema._validate_include(
            self.detailed_schemas[detailed_type], value, path=DataPath(), strict=True
        )
        return "\n".join(errs)

    def _is_valid(self, value):
        errs = current_schema.schema._validate_include(
            self.base_schema, value, path=DataPath(), strict=False
        )
        if errs != []:
            return False
        detailed_type = self.get_detailed_type(value)
        value = self.remove_validated_items(value)
        errs = current_schema.schema._validate_include(
            self.detailed_schemas[detailed_type], value, path=DataPath(), strict=True
        )
        return errs == []


class Uuid(Validator):
    """UUID/GUID validator"""

    tag = "uuid"

    def _is_valid(self, value):
        try:
            UUID(value)
            return True
        except ValueError:
            return False


class Url(Validator):
    """URL validator"""

    tag = "url"

    # modified from Django 1.7 https://github.com/django/django/blob/stable/1.7.x/django/core/validators.py
    # can likely be simplified ( user:pass, ipv4, and ipv6 likely not needed)
    url_regex = re.compile(
        r"^(?:http|ftp)s?://"  # scheme ...
        r"(?:\S+(?::\S*)?@)?"  # user:pass ...
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}(?<!-)\.?)|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|"  # ...or ipv4
        r"\[?[A-F0-9]*:[A-F0-9:]+\]?)"  # ...or ipv6
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)\Z",
        re.IGNORECASE,
    )

    def _is_valid(self, value):
        return re.match(self.url_regex, value) is not None


class Vocabulary(Validator):
    """Vocabulary validator"""

    tag = "vocabulary"

    def __init__(self, *args, fields=None, vocabulary=None, **kwargs):
        super().__init__(*args, fields=fields, **kwargs)
        self.vocabulary = vocabulary
        self.fields = fields

    def _is_valid(self, value):
        if value is None:
            return True
        if not isinstance(value, dict):
            return False
        if "id" not in value:
            return False
        return True


# include custom validators
extend_validators = DefaultValidators.copy()
for val in (
    LinkTarget,
    Link,
    Keyword,
    Fulltext,
    Uuid,
    Url,
    Database_id,
    Chemical_id,
    Person_id,
    Publication_id,
    Choose,
    Nested_include,
    Vocabulary,
):
    extend_validators[val.tag] = val
