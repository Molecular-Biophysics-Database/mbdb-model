import yamale
from tools.custom_validators import extend_validators
from tools.custom_validators import (
    Link,
    LinkTarget,
    Vocabulary,
    Uuid,
    Url,
    Choose
)


class TestLink:
    L = Link(target="test_target")
    valid_links_L = [
        {"$ref": "test_link", "name": "test_name"},
        None,
    ]

    invalid_links_L = [
        [],
        {},
        "$ref",
        {"ref": "test_link"},
        {"id": "test_link"},
        {"id": "test_link", "name": "test_name"},
    ]

    def test_valid_links(self):
        for valid in self.valid_links_L:
            assert self.L.is_valid(valid)

    def test_invalid_links(self):
        for invalid in self.invalid_links_L:
            assert not self.L.is_valid(invalid)

    L_fields = Link("test_target", fields="[id,name,test]")

    valid_links_fields = [
        {"$ref": "test_link", "name": "test_name", "test": 1},
        None,
    ]

    invalid_links_fields = [
        [],
        {},
        "$ref",
        {"$ref": "test_link", "name": "test_name"},
        {"ref": "test_link"},
        {"id": "test_link"},
        {"id": "test_link", "name": "test_name"},
    ]

    def test_valid_links_fields(self):
        for valid in self.valid_links_fields:
            assert self.L_fields.is_valid(valid)

    def test_invalid_links_fields(self):
        for invalid in self.invalid_links_fields:
            assert not self.L_fields.is_valid(invalid)


class TestLinkTarget:
    linktarget = LinkTarget()

    valid_linktargets = [
        "test",
    ]

    invalid_linktargets = [
        123,
        "",
        None,
        {},
        [],
    ]
    def test_valid_linktargets(self):
        for valid in self.valid_linktargets:
            assert self.linktarget.is_valid(valid)

    def test_invalid_links_fields(self):
        for invalid in self.invalid_linktargets:
            assert not self.linktarget.is_valid(invalid)


class TestVocabulary:
    vocab = Vocabulary()

    valid_vocabs = [
        {"id": 1234},
        {"id": "test"},
        None,
    ]

    invalid_vocabs = [
        [],
        {},
        "$ref",
        "id",
        {"$ref": "test_link"},
    ]

    def test_valid_links_fields(self):
        for valid in self.valid_vocabs:
            assert self.vocab.is_valid(valid)

    def test_invalid_links_fields(self):
        for invalid in self.invalid_vocabs:
            assert not self.vocab.is_valid(invalid)


class TestUuid:
    validator = Uuid()

    valid_uuid = [
        "3212c808-f29a-4750-857e-fe341e93f8c5",
    ]

    invalid_uuid = [
        "test",
        "",
        12345678 - 1234 - 1234 - 1234 - 123456789012,  # wrong type
    ]

    def test_valid_uuid(self):
        for valid in self.valid_uuid:
            assert self.validator.is_valid(valid)

    def test_invalid_uuid(self):
        for invalid in self.invalid_uuid:
            assert not self.validator.is_valid(invalid)


class TestUrl:
    valid_url = [
        "http://www.google.co.uk",
        "https://www.google.co.uk",
        "http://google.co.uk",
        "https://google.co.uk",
        "http://www.google.co.uk/~as_db3.2123/134-1a",
        "https://www.google.co.uk/~as_db3.2123/134-1a",
        "http://google.co.uk/~as_db3.2123/134-1a",
        "https://google.co.uk/~as_db3.2123/134-1a",
        "https://localhost:5000/",
        "https://google-like.com",
        "https://username:password@example.com",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    ]

    invalid_url = [
        "www.google.co.uk",
        "google.co.uk",
        "www.google.co.uk/~as_db3.2123/134-1a",
        "google.co.uk/~as_db3.2123/134-1a",
        "https://https://www.google.co.uk",
        "https://...",
        "https://..",
        "https://.",
        "https://.google.com",
        "https://..google.com",
        "https://...google.com",
        "https://.google..com",
        "https://.google...com" "https://...google..com",
        "https://...google...com",
        ".google.com",
        ".google.co.",
        "",
    ]

    validator = Url()

    def test_valid_urls(self):
        for url in self.valid_url:
            assert self.validator.is_valid(url)

    def test_invalid_urls(self):
        for url in self.invalid_url:
            assert not self.validator.is_valid(url)


class TestChoose:
    yamale_schema = """                                        
Base_test:
    name: str()
    type: enum('Case 1', 'Case 2')                        
Case_1:  
    test_1: int()
Case_2:
    test_2: num()   
"""
    test_schema = yamale.make_schema(validators=extend_validators, content=yamale_schema)

    base_schema = test_schema.dict["Base_test"]
    case_1 = test_schema.dict["Case_1"]
    case_2 = test_schema.dict["Case_2"]
    validator = Choose(base_schema=base_schema, Case_1=case_1, Case_2=case_2)

    valid_choose = [
        {"name": "test", "type": "Case 1", "test_1": 1},
        {"name": "test 2", "type": "Case 2", "test_2": 2.2},
    ]
    invalid_choose = [
        {"type": "Case 2", "test_2": 1},                     # missing name field
        {"type": "Case 2", "test_1": 1},                     # Case 2 should have the test_2 field, not test_1
        {"name": "test 2", "test_1": 1},                     # missing type field
        {"name": "test", "type": "Case 1", "test_1": 1.1},   # wrong type of test_1
        {},                                                  # empty object no allowed
    ]

    def test_valid_choose(self):
        for valid in self.valid_choose:
            assert self.validator._is_valid(valid)

    def test_invalid_choose(self):
        for invalid in self.invalid_choose:
            assert not self.validator._is_valid(invalid)
