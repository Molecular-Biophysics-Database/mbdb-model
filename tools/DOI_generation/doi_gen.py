import click
from pathlib import Path
import json
from typing import List
from datetime import datetime
from datacite import DataCiteRESTClient
import jsonschema

####### <creators_functions>
def add_optional_fields_creator(field: str, person: dict, creator: dict) -> None:
    options = {
        "affiliations": ("affiliation", to_affiliation),
        "identifiers":  ("nameIdentifiers", to_name_identifiers),
    }

    if field not in options.keys():
        raise ValueError(f"'{field}' is not allowed, allowed values are {options.keys}")

    if field not in person.keys():
        return None

    field_name, func = options[field]
    creator.update({field_name: [func(element) for element in person[field]]})


def to_affiliation(affiliation) -> dict:
    aff_id = affiliation["id"][4:]  # remove ror: from id
    aff_name = affiliation["title"]["en"]
    return {
            "schemeUri": "https://ror.org/",
            "affiliationIdentifier": f"https://ror.org/{aff_id}",
            "affiliationIdentifierScheme": "ROR",
            "name": f"{aff_name}",
        }


def to_name_identifiers(orcid: str) -> dict:
    orcid = orcid[6:]
    return {
            "schemeUri": "https://orcid.org",
            "nameIdentifier": f"https://orcid.org/{orcid}",
            "nameIdentifierScheme": "ORCID"
        }


def to_creator(person: dict) -> dict:
    given_name = person["given_name"]
    family_name = person["family_name"]

    creator = {
          "name": f'{family_name}, {given_name}',
          "givenName": given_name,
          "familyName": family_name
        }

    for field in ("affiliations", "identifiers"):
        add_optional_fields_creator(field, person, creator)

    return creator


def to_creators(depositors: dict) -> List[dict]:
    creators = [depositors["principal_contact"]]

    # only add depositor if depositor is not identical to the principal_contact
    if depositors["depositor"] != depositors["principal_contact"]:
        creators += [depositors["depositor"]]

    # only add contributors if there are any
    if "contributors" in depositors.keys():
        creators += depositors["contributors"]

    return [to_creator(creator) for creator in creators]
######## </creators_functions>


def to_titles(title: str) -> List[dict]:
    return [{"title": title}]


def to_types(record_info: dict) -> dict:
    return {
        "resourceTypeGeneral": record_info["resource_type_general"],
        "resourceType": record_info["resource_type"]
    }


def to_publisher(record_info: dict) -> str:
    return record_info["publisher"]


def to_publication_year(record_info: dict) -> int:
    # expected format is YYYY-MM-DD
    date = datetime.strptime(record_info["date_available"], "%Y-%m-%d")
    return date.year


def to_subjects(record_info: dict) -> List[dict]:
    return [{"subject": record_info["subject_category"]}]


def add_schema_version(datacite_version):
    return datacite_version


def get_doi_dict(record):
    gp = record["metadata"]["general_parameters"]
    record_info = gp["record_information"]

    fields = (
        ("creators", to_creators, gp["depositors"]),
        ("titles", to_titles, record_info["title"]),
        ("types", to_types, record_info),
        ("publisher", to_publisher, record_info),
        ("publicationYear", to_publication_year, record_info),
        ("subjects", to_subjects, record_info),
        ("schemaVersion", add_schema_version, "http://datacite.org/schema/kernel-4")
    )

    return {field: func(data) for field, func, data in fields}


class DOIClient(DataCiteRESTClient):
    """DOIClient takes care of communication with the Datacite REST API.
    extends the datacite.DataCiteRESTClient with increased validation.

    usage:

    """
    def __init__(self, username, password, prefix, record=None, test_mode=True):
        super().__init__(username, password, prefix, test_mode)
        self.record = record
        with open("schema43.json") as f:
            self.schema = json.load(f)

    def fetch_record(self, doi):
        """Fetches the record at doi and loads it into self.record"""
        if self.record:
            Warning("self.record was not empty but was overwritten!")
        self.record = self.get_metadata(doi)

    def create_draft(self):
        """create a Datacite entry in draft state and return the created DOI"""
        self._validate_record(msg_obj="Draft", msg_opr="created")
        return self.draft_doi(self.record)

    def update_record(self, doi):
        """updates the datacite record at the url doi with the content of self.doi_dict, note"""
        self._validate_record(msg_obj="Record", msg_opr="updated")
        self.put_doi(doi, self.record)

    def publish_draft(self, doi):
        # no local data
        if self.record is None:
            self.record = self.get_metadata(doi)  # does it exist online ?
        self.record["event"] = "publish"
        self._validate_record(msg_obj="Draft", msg_opr="published")
        self.put_doi(doi, self.record())

    def _validate_record(self, msg_obj: str, msg_opr: str):
        """Returns None if self.data_doi is a valid datacite record else it raises ValidationError"""
        try:
            jsonschema.validate(instance=self.record, schema=self.schema)
        except jsonschema.ValidationError as e:
            errmsg = f"{msg_obj} did not pass validation so it was not {msg_opr}. " \
                     f"The validation error was due to {e} "
            raise jsonschema.ValidationError(errmsg)


@click.command()
@click.argument("input_file", type=Path)
@click.option("--doi", type=str, default=None)
@click.option("--make_draft", default=True)
@click.option("--publish", default=False)
def main(input_file, doi, make_draft, publish):
    if not input_file or doi:
        raise TypeError('either input_file (as argument) or --doi must be specified')

    doi_dict = None
    if input_file:
        with open(input_file) as f:
            record = json.load(f)
        doi_dict = get_doi_dict(record)

    dc = DOIClient(
        record=doi_dict,
        username="",
        password="",
        prefix="10.82657",
    )

    if make_draft:
        # update existing draft
        if doi:
            dc.update_record(doi)
        # create a new one and use it's doi if we want to publish
        else:
            doi = dc.create_draft()

    if publish:
        dc.publish_draft(doi)

    print(json.dumps(dc.record, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
