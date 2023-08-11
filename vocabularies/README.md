# vocabularies

**WARNING**
The tools are in an early state of development, so please be careful when using
them

Vocabularies can, from a schema perspective, be considered to a user-extendable
multi-field enumerator.

From an Invenio perspective, the individual vocabulary items are a special kind
of records that lives in a different endpoint than the main records, and
they're more restrictive in which schemas are allowed (see below) .

## schemas

### Defining vocabulary schema

Where the schemas for the individual vocabularies are defined.
Invenio vocabulary schemas constrained to be of the form:

```yaml
id: !!str
title: !!str
props: !!map
  prop1: !!str
  prop2: !!str
```

The requirements are:
 - The fields `id` and `title` are mandatory
 - The `props` map and all its subfields are optional   
 - No values are allowed to be `null`, however optional fields can be removed altogether from individual vocabulary to
   accommodate missing values
 - All input must be string type

### Register vocabulary  

It is important to note that schemas are strictly speaking not necessary register a vocabulary, however they're 
important for generating vocabularies. Installation itself is done by registering it in the [app](https://github.com/Molecular-Biophysics-Database/mbdb-app) in the file:

```mbdb-app/local/mbdb-common/mbdb_common/fixtures/catalogue.yaml``` 

as well as providing a sample vocabulary (see below) to be

## generate_vocabularies.py
 
Generates vocabulary samples in a form where they can be directly loaded using the nrp toolkit used by the app.
One generator should be made for each vocabulary.

Note that it downloads resources and uses them to generate sample vocabularies. As 100ks-1Ms of items are present in 
these resource, online tools for searching them will be used for adding new vocabularies (see below). 

## auth_getters.py

These tools are for searching the respective resources whenever a vocabulary. An auth getter should be defined for each 
vocabulary.

### API for affiliations

  - **API endpoint**: https://api.ror.org/organizations  
  - **API documentation**: https://ror.readme.io/docs/rest-api
  - **max request rate**: 2000 per 5 minutes 
  - **max number of request records**: 10000
  - **update resources**: https://github.com/ror-community/ror-updates 
   (new records and records that were updated can be found in the folders where
   file names are the record (ROR) ids)  

#### Fields of interest:
 
 - `id` (it's in the form url/ror_id)
 - `name` 
 - `addresses[0].city` 
 - `addresses[0].state`
 - `country.country_name`

## Grants

  - **API endpoint**: https://api.openaire.eu/search/projects  
  - **API documentation**: https://graph.openaire.eu/develop/api.html#projects
  - **max request rate**: 60 per hour, or 7200 per hour for registered client (request with OAuth2.0 token)  
  - **max number of request records**: 10000
  - **update resources**: `header.dri:dateOfTransformation` if stored, currently it isn't 
    part of grant vocabulary schema 

#### Fields of interest (json format):
 
 - `metadata.oaf:entity.oaf:project.code`
 - `metadata.oaf:entity.oaf:project.title`
 - `metadata.oaf:entity.oaf:project.fundingtree.funder.name`
 - (`header.dri:dateOfCollection`)
 - (`header.dri:dateOfTransformation`)

### APIs for organisms
For searching the following endpoint is used:

  - **API endpoint**: https://api.ncbi.nlm.nih.gov/datasets/v1/taxonomy/taxon_suggest/BL21
  - **API documentation**: https://www.ncbi.nlm.nih.gov/datasets/docs/v1/reference-docs/rest-api/
  - **max request rate**: 3 per second, or 10 per second for registered client (I think it's OAuth2.0 token based) 
  - **max number of request records**: Not known
  - **update resources**: Not known (entries are rather small though)

#### Field of interest (json format):
- `sci_name_and_ids.hit.tax_id`

Information is extracted using this endpoint:

  - **API endpoint**: https://api.ncbi.nlm.nih.gov/datasets/v1/taxonomy/taxon/9606 
  - **API documentation**: https://www.ncbi.nlm.nih.gov/datasets/docs/v1/reference-docs/rest-api/
  - **max request rate**: 3 per second, or 10 per second for registered client (I think it's OAuth2.0 token based) 
  - **max number of request records**: Not known
  - **update resources**: Not known (entries are rather small though)

#### Fields of interest (json format):
 
 - `taxonomy.tax_id`
 - `taxonomy.organism_name`
 - `taxonomy.rank`
