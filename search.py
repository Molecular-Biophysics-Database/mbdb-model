from invenio_search import RecordsSearch

class BasicSearch(RecordsSearch):

    class Meta:
        index = ''
        fields = ('metadata.general_parameters.record.title',
                  'metadata.general_parameters.record.keywords',
                  'metadata.general_parameters.record.id',
                  'metadata.general_parameters.associated_publications.main.title',
                  'metadata.general_parameters.associated_publications.main.pid',
                  'metadata.general_parameters.associated_publications.main.authors.full_name'
                  'metadata.general_parameters.depositors.principal_contact.full_name',
                  'metadata.general_parameters.instrument.performance_test.sample_composition.name',
                  'metadata.general_parameters.chemical_information.chemical_environments.constituents.name',
                  'metadata.general_parameters.chemical_information.chemical_environments.constituents.inchikey',
                  'metadata.general_parameters.chemical_information.entities_of_interest.name',
                  'metadata.general_parameters.chemical_information.entities_of_interest.inchikey',
                  'metadata.general_parameters.chemical_information.entities_of_interest.components.name',
                  'metadata.general_parameters.chemical_information.entities_of_interest.external_databases',  )
        facets = {}


search = BasicSearch()
