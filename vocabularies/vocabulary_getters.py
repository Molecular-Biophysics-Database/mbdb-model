import requests
from oarepo_vocabularies.authorities.service import AuthorityService


class RORService(AuthorityService):
    def search(self, *, query=None, page=1, size=20, **kwargs):
        # size for this API is fixed to 20
        url = 'https://api.ror.org/organizations'
        params = {
                  "query": query,
                  "page": page
        }

        response = requests.get(url, params=params)
        response_json = response.json()
        affiliations = [self.convert_ror_record(hit) for hit in response_json['items']]

        return {
            'hits': {'total': response_json['number_of_results'], 'hits': affiliations}
        }

    def get(self, item_id, **kwargs):
        if not item_id.startswith("ror:"):
            raise KeyError(f'item_id, "{item_id}", is not a ROR id')

        url = f"https://api.ror.org/organizations/{item_id[4:]}"
        r = requests.get(url).json()
        return self.convert_ror_record(r)

    @staticmethod
    def convert_ror_record(hit):
        return {
                "id": f"ror:{hit['id'].split('/')[-1]}",
                "title": {"en": hit["name"]},
                "props": {
                    "city": hit["addresses"][0]["city"],
                    "state": hit["addresses"][0]["state"],
                    "country": hit["country"]["country_name"]
                }
        }


class NCBIService(AuthorityService):
    def search(self, *, query=None, page=1, size=20, **kwargs):
        # paging and size cannot be supplied and I can't find documentation on how many results
        # can maximally be returned, however, 20 appears to be maximum

        # This endpoint is unstable in terms of which hits are returned
        search_url = f"https://api.ncbi.nlm.nih.gov/datasets/v1/taxonomy/taxon_suggest/{query}"
        suggested = requests.get(search_url)
        suggested_json = suggested.json()
        taxids = [hit["tax_id"] for hit in suggested_json["sci_name_and_ids"]]  # noqa

        return {
            'hits': {'total': len(suggested_json["sci_name_and_ids"]), 'hits': self.from_taxid(taxids)}
        }

    def get(self, item_id, **kwargs):
        if not item_id.startswith("taxid:"):
            raise KeyError(f'item_id, "{item_id}", is not a NCBI tax id')

        return self.from_taxid([item_id[6:]])[0]

    @staticmethod
    def convert_ncbi_record(hit):
        try:
            rank = hit["rank"]
        except KeyError:
            rank ="NO RANK"
        return {
                "id": f'taxid:{hit["tax_id"]}',
                "title": {"en": hit["organism_name"]},
                "props": {
                    "rank": rank
                }
        }

    def from_taxid(self, taxids):
        taxid_url = "https://api.ncbi.nlm.nih.gov/datasets/v1/taxonomy/taxon/"
        taxid_params = {"returned_content": "TAXIDS"}  # noqa

        response = requests.get(f"{taxid_url}{','.join(taxids)}", params=taxid_params)

        organisms = []
        for hit in response.json()["taxonomy_nodes"]:
            hit = hit["taxonomy"]
            organisms.append(self.convert_ncbi_record(hit))
        return organisms


class OpenAireService(AuthorityService):   # noqa
    def search(self, *, query=None, page=1, size=10, **kwargs):
        # both page and size can be specified for the endpoint
        url = 'https://api.openaire.eu/search/projects'
        params = {
                  "keywords": query,
                  "page": page,
                  "size": size,
                  "format": "json"
        }

        response = requests.get(url=url, params=params)
        response_json = response.json()
        grants = [self.convert_oa_record(hit) for hit in response_json["response"]["results"]["result"]]

        return {
            'hits': {'total': response_json["response"]["header"]["total"]["$"], 'hits': grants}
        }

    def get(self, item_id, **kwargs):
        if not item_id.startswith("oa:"):
            raise KeyError(f'item_id, "{item_id}", is not a OpenAire id')    # noqa

        params = {"openaireProjectID": item_id[3:],
                  "format": "json"}
        url = "https://api.openaire.eu/search/projects"
        response = requests.get(url, params=params).json()
        return self.convert_oa_record(response["response"]["results"]["result"][0])

    @staticmethod
    def convert_oa_record(hit):
        funding_tree = hit["metadata"]["oaf:entity"]["oaf:project"]["fundingtree"]  # noqa
        if not isinstance(funding_tree, list):
            funding_tree = [funding_tree]

        funders = set([tree["funder"]["name"]["$"] for tree in funding_tree])
        funder_name = ' and '.join(funders)

        try:
            title = hit["metadata"]["oaf:entity"]["oaf:project"]["title"]["$"]
        except KeyError:
            title = "NO TITLE AVAILABLE"

        return {
                "id": f'oa:{hit["header"]["dri:objIdentifier"]["$"]}',
                "title": {
                    "en": title
                },
                "props": {
                    "grant_id": str(hit["metadata"]["oaf:entity"]["oaf:project"]["code"]["$"]),
                    "funder_name": funder_name
                }
        }
