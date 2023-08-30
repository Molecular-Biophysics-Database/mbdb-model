import requests
import json
import jsonschema
import yaml
from copy import deepcopy

with open('config.yaml') as f:
    default = yaml.safe_load(f)

with open('auth.yaml') as f:
    auth = tuple(yaml.safe_load(f).values())

class DOI:
    draft_response: requests.Response
    publish_response: requests.Response

    def __init__(self,
                 prefix=default["prefix"],
                 url=default["url"],
                 auth=auth,
                 headers=default["headers"],
                 data_template=default["data_template"]):

        self.prefix = prefix
        self.url = url
        self.dois_url =  f'{self.url}/dois'
        self.auth = auth
        self.headers = headers
        self.data_template = data_template
        if not self._host_is_up:
            raise requests.ConnectionError(f"Host {self.url} is not operating normally, connection not made")

    def _host_is_up(self):
        response = requests.get(url=f'{self.url}/heartbeat')
        return response.ok

    def make_draft(self, data_dict=None):
        if data_dict is None:
            data_dict = {}
        data_dict.update({"prefix": self.prefix})
        data = self._make_data(data_dict)
        self.draft_response = self._make_request("POST", data, url=self.dois_url)

    def get_draft(self, doi=None):
        if doi is None:
            doi = self._get_doi(self.draft_response)
        return self._make_request(method="GET",
                                  data='',
                                  url=self.doi_endpoint(doi)).json()

    def doi_endpoint(self, doi):
        return f"{self.dois_url}/{doi}"

    def update_draft(self, data_dict, doi=None):
        if doi is None:
            doi = self._get_doi(self.draft_response)
        url = self.doi_endpoint(doi)
        data = self._make_data(data_dict)
        self.draft_response = self._make_request("PUT", data, url=url)

    def delete_draft(self, doi=None):
        if doi is None:
            doi = self._get_doi(self.draft_response)
        url = self.doi_endpoint(doi)
        data = ''
        self.publish_response = self._make_request("DELETE", data, url=url)

    def publish_draft(self, doi=None, data_dict=None):
        if data_dict is None:
            data_dict = {}
        if doi is None:
            doi = self._get_doi(self.draft_response)
        url = self.doi_endpoint(doi)
        data_dict.update({"event": "publish"})
        data = self._make_data(data_dict)
        self.publish_response = self._make_request("PUT", data, url=url)

    def _make_request(self, method, data: str, url=None):
        if url is None:
            url = self.url
        response = requests.request(method=method, url=url, data=data, headers=self.headers, auth=self.auth)
        if not response.ok:
            print(f"Warning! Unsuccessful request with data {data}, status code {response.status_code} was returned")
        return response

    @staticmethod
    def _get_doi(response):
        return response.json()["data"]["attributes"]["doi"]

    def _make_data(self, data_dict):
        data = deepcopy(self.data_template)
        data["data"].update({"attributes": data_dict})
        return json.dumps(data)


def extract_title(full_record):
    return [{"title": full_record['metadata']['general_parameters']['record']['title']}]

def extract_publication_year(full_record):
    return full_record['metadata']['general_parameters']['record']['date_available']

def extract_publisher(full_record):
    return full_record['metadata']['general_parameters']['record']['publisher']

def extract_types(full_record):
    record = full_record['metadata']['general_parameters']['record']
    return {"resourceTypeGeneral": record['resource_type_general'],
            "resourceType": record['resource_type']
            }

def extract_url(full_record):
    url = 'https://mbdb.org'
    mbdb_type = f"mbdb-{full_record['metadata']['general_parameters']['record']['resource_type'].lower()}"
    mbdb_id = full_record['metadata']['general_parameters']['record']['id']
    return '/'.join([url, mbdb_type, mbdb_id])

def extract_creator(full_record):
    depositors = full_record['metadata']['general_parameters']['depositors']

    try:
        contributors = depositors['contributors']
    except KeyError:
        contributors = []

    person_ordered = [depositors['depositor'], depositors['principal_contact']]
    person_ordered.extend(contributors)
    return [single_creator(person) for person in person_ordered]

def person_id(identifier):
    pid = identifier.split(':')[-1]
    return {
            "schemeUri": "https://orcid.org",
            "nameIdentifier": f"https://orcid.org/{pid}",
            "nameIdentifierScheme": "ORCID"
           }

def single_creator(dict_entry: dict):
    creator = {
        "givenName": dict_entry["given_name"],
        "familyName": dict_entry["family_name"]
    }
    item_fields = dict_entry.keys()
    if "affiliations" in item_fields:
        creator.update({"affiliation": [{"name": aff} for aff in dict_entry['affiliations']]})

    if "identifiers" in item_fields:
        creator.update({"nameIdentifiers": [person_id(ID) for ID in dict_entry['identifiers']]})

    return creator

def to_datacite(json_file):
    doi_attributes = {
        "creators": extract_creator,
        "titles": extract_title,
        "publicationYear": extract_publication_year,
        "publisher": extract_publisher,
        "types": extract_types,
        "url": extract_url,
    }

    with open(json_file) as f_in:
        full_record = json.load(f_in)

    for field, extractor in doi_attributes.items():
        doi_attributes.update({field: extractor(full_record)})

    return doi_attributes

def validate_json(record, schema_file):
    with open(schema_file) as f_in:
        schema = json.load(f_in)

    return jsonschema.validate(instance=record, schema=schema)


test_doi = DOI()

test_json = to_datacite('/home/emil/bin/mbdb-orga/mbdb-model/metadata-examples/MST.json')
validate_json(test_json, "pre_draft_schema.json")
test_doi.make_draft(data_dict=test_json)
test_draft = test_doi.get_draft()
test_doi.delete_draft()
#test_doi.publish_draft(doi='10.82657/876h-3d76')
