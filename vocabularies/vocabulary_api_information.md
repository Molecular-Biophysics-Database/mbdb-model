# Vocabulary resources

## Affilliations

  - **API endpoint**: https://api.ror.org/organizations  
  - **API documentation**: https://ror.readme.io/docs/rest-api
  - **max request rate**: 2000 per 5 minutes 
  - **max number of request records**: 10000
  - **update resources**: https://github.com/ror-community/ror-updates 
   (new records and records that were updated can be found in the folders where
   file names are the record (ROR) ids)  

### Fields of interest:
 
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
  - **update resources**: Have field `header.dri:dateOfTransformation` which might help (if stored, currently it isn't part of vocabulary schema) 

### Fields of interest (json format):
 
 - `metadata.oaf:entity.oaf:project.code`
 - `metadata.oaf:entity.oaf:project.title`
 - `metadata.oaf:entity.oaf:project.fundingtree.funder.name`
 - (`header.dri:dateOfCollection`)
 - (`header.dri:dateOfTransformation`)

## Organisms

  - **API endpoint**: https://api.ncbi.nlm.nih.gov/datasets/v1/taxonomy/taxon/9606 
  - **API documentation**: https://www.ncbi.nlm.nih.gov/datasets/docs/v1/reference-docs/rest-api/
  - **max request rate**: 3 per second, or 10 per second for registered client (I think it's OAuth2.0 token based) 
  - **max number of request records**: Not known
  - **update resources**: Not known (entries are rather small though)

### Fields of interest (json format):
 
 - `taxonomy.tax_id`
 - `taxonomy.organism_name`
 - `taxonomy.rank`





