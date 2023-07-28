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

def auth_getter_organisms(q: str, page=1, size=20, **kwargs):
    # paging and size cannot be supplied and I can't find documentation on how many results
    # can maximally be returned

    # This query endpoint returns fewer hits than expected
    search_url = f"https://api.ncbi.nlm.nih.gov/datasets/v1/taxonomy/taxon_suggest/{q}"
    suggested = requests.get(search_url)
    taxids = [hit["tax_id"] for hit in suggested.json()["sci_name_and_ids"]]

    # This endpoint is rather slow
    taxid_url = "https://api.ncbi.nlm.nih.gov/datasets/v1/taxonomy/taxon/"
    taxid_params = {"returned_content": "TAXIDS"}

    response = requests.get(f"{taxid_url}{','.join(taxids)}", params=taxid_params)

    organisms = []
    for hit in response.json()["taxonomy_nodes"]:
        hit = hit["taxonomy"]
        organisms.append(
            {
                "title": {"en": hit["organism_name"]},
                "props": {
                    "authoritative_id": hit["tax_id"],
                    "rank": hit["rank"]
                }
            }
        )

    return organisms


def auth_getter_grants(q: str, page, size, **kwargs):
    # both page and size can be specified for the endpoint
    url = 'https://api.openaire.eu/search/projects'

    params = {"keywords": q,
              "page": page,
              "size": size,
              "format": "json"}

    response = requests.get(url=url, params=params)

    grants = []
    for hit in response.json()["response"]["results"]["result"]:
        project = hit["metadata"]["oaf:entity"]["oaf:project"]

        funding_tree = project["fundingtree"]
        if not isinstance(funding_tree, list):
            funding_tree = [funding_tree]

        funders = set([tree["funder"]["name"]["$"] for tree in funding_tree])
        funder_name = ' and '.join(funders)

        grants.append(
            {
                "title":
                    {"en": project["title"]["$"]},
                "props": {
                    "authoritative_id": project["code"]["$"],
                    "funder_name": funder_name
                }
            }
        )
    return grants
