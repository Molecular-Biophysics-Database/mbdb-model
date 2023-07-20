import requests

def auth_getter_affiliations(q: str, page: int, size=20, **kwargs):
    # size for this API is fixed to 20
    url = 'https://api.ror.org/organizations'
    params = {"query": q,
              "page": page}

    response = requests.get(url, params=params)
    affiliations = []
    for hit in response.json()['items']:
        affiliations.append(
            {   "title": {"en": hit["name"]},
                "props": {
                    "authoritative_id": hit["id"].split('/')[-1], # The first part is "https://ror.org/
                    "city": hit["addresses"][0]["city"],
                    "state": hit["addresses"][0]["state"],
                    "country": hit["country"]["country_name"]
                }
            }
        )

    return affiliations

def auth_getter_organisms(q: str, page, size, **kwargs):

    # paging and size cannot be supplied and I can't find good documentation on how many results
    # maximally can be returned

    # This endpoint is slow and do not appear to return nearly as many hits as expected
    search_url = f"https://api.ncbi.nlm.nih.gov/datasets/v1/taxonomy/taxon_suggest/{q}"

    taxid_url = "https://api.ncbi.nlm.nih.gov/datasets/v1/taxonomy/taxon/"
    taxid_params = {"returned_content": "TAXIDS"}

    response = requests.get(search_url)

    organisms = []
    for hit in response.json()["sci_name_and_ids"]:
        taxid = hit["tax_id"]
        taxid_lookup = requests.get(f"{taxid_url}{taxid}", params=taxid_params)
        organisms.append(
            {   "title": {"en": hit["sci_name"]},
                "props": {
                    "authoritative_id": hit["tax_id"],
                    "rank": taxid_lookup.json()['taxonomy_nodes'][0]['taxonomy']["rank"]
                }
            }
        )

    return organisms


def auth_getter_grants(q: str, page, size, **kwargs):
    ### DON'T USE as it occasionally fails
    url = 'https://api.openaire.eu/search/projects'

    params = {"keywords": q,
              "page": page,
              "size": size,
              "format": "json"}

    response = requests.get(url=url, params=params)
    #return response

    grants = []
    for hit in response.json()["response"]["results"]["result"]:
        project = hit["metadata"]["oaf:entity"]["oaf:project"]

        grants.append(
            {
                "title":
                    {"en": project["title"]},
                "props": {
                    "authoritative_id": project["code"],
                    "funder_name": project["fundingtree"]["funder"]["name"]

                }

            }
        )
    return grants
