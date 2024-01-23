import click
from pathlib import Path
import json
from typing import List
from datetime import datetime

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
    )

    return {field: func(data) for field, func, data in fields}


def to_payload(doi_dict, publish=False):
    payload = {
        "data": {
            "type": "dois",
            "attributes": doi_dict}}

    atts = payload["data"]["attributes"]

    # add the MBDB doi prefix
    atts["prefix"] = "10.82657"

    # if publish is False a draft is made
    if publish:
        atts["event"] = "publish"

    return json.dumps(payload, indent=2, ensure_ascii=False)


@click.command()
@click.argument("input_file", required=True, default=Path(__file__).parent / "test_record.json")
@click.option("--output_file", type=Path)
@click.option("--publish", default=False)
def main(input_file, output_file, publish):
    with open(input_file) as f:
        record = json.load(f)
    doi_dict = get_doi_dict(record)
    payload = to_payload(doi_dict, publish)

    if output_file:
        with open(output_file, "w") as out:
            out.write(payload)
    else:
        print(payload)

if __name__ == "__main__":
    main()
