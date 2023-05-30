# Metadata definitions

The metadata is defined in YAML schmeas due to ease of readability, validation
as well as commenting the schema. However, the final storage format of the data
and metadata is JSON, not YAML.

# YAML schema validation using Yamale

## Dependencies

The current schemas are based on the python package [yamale]

```bash
pip install yamale
```
Furthermore, a number of custom validators specific to the MBDB was generated
and can be found in:

```
tools/custom_validators.py
```
## Validation of (YAML) test records in

a small script to validate that the data is compatible with the current schemas
and *vice versa*. It automatically imports the custom validators, constructs
the schemas, and validates the test data against the appropriate schema.
It can be run (in *nix) using:

```bash
python tools/validate_examples.py
```

# Structure of schemas

## Item syntax

### Item example

```yaml
stoichiometry:
    description     : str(equals='Number of copies of the entity that
                                  contribute to the derived parameter, -1
                                  if unknown', required=False)
    searchable      : True
    value           : num(min=-1)
```


### Item names

  * Should be descriptive and written in long form:
     * Short hand forms are discouraged (*e.g.* use "description" rather than
       "desc")
     * Acronyms should only be used if they're part of everyday English (*e.g.*
       pH, LASER, LED)
  * Are written with underscores between words (snake case)
  * Are capitalized if they're being used as includes
  * Are written in all-caps if they're constant enumerators
  * If they don't fall into any of the two previous categories they
    should be written in lower case

### Item structure

Each item is composed of three mandatory elements:
  1. A name (see above for restrictions) that is will be used as the label in
     the front-end (after stripping away underscores).
  2. A short `description` that of what the item is meant to contain.
  3. A `value` where the data type and constrains is specified.

Each item also have an optional element:
  1. `searchable` which describes whether or not a item is searchable.
      Unless it's explicitly set to `True`, the item is currently not
      searchable.

### Item value types

Primitive (single) value types:
  * `freetext`: String of UTF-8 characters, in search it partial matches are
     possible
  * `keyword`: String of UTF-8 characters, in search it's either matched exactly
     or not at all
  * `str`: synonym for `freetext`
  * `num`: number as integer or float
  * `int`: number as integer
  * `uuid`: that matches a UUID/GUID
  * `regex`: string that matches the specified regular expression.
  * `enum`: enumerated constants which should all be of the same type. Only one
     of the listed elements are allowed per item. Maps to search type `keyword`

Array of values:
  * `list`: array of a certain type (nested array is allowed)
  * `nested_list`: array of a maps, where comparison of the individual items
     within map can be

Reuse value (usually a map or enum) in another map:
  * `include`: a map (object) or enumerator to be reused (in the sense of
    composition)

Identifiers:
  * `person_id`: validates [ORCID] when a valid ORCID is prefixed with the
     string `'orcid:'`
  * `chemical_id`: validates [CAS Registry Numbers], [Pubchem Compound ID],
     and [Pubchem Substance ID], when a valid ID is prefixed with the strings
     `'cas:'`, `'pccid:'`, and `'pcsid:'`, respectively.
  *


Polymorphic (single) value:
  * `choose`: The base map (the first include), a discriminator (`type_field`)
    and exactly one of the specified types are allowed in this field.
    Additionally, the base map needs to have a discriminator, where the default
    is `"type"`. Spaces in the value if the discriminator field will be
    replaced with underscores, which should then match the left hand side of
    the equality sign in `choose` (see example below).

`choose` values are complex to implement, makes the schema harder to understand,
and introduces data structures that are more difficult to validate and test.
**Use `choose` as little as possible!**

```yaml
# Descriptions and searchablity has been ommited for clarity

Type_1:
    item_from_1           : str()
    another_item_from_1   : int()

Type_2
    item_from_1           : int()
    another_item_from_1   : str()

Example_base:
    # items present independent of which types is chosen
    shared_item           : int()
    discriminator         : enum('Type 1', 'Type 2')


Example                   : choose(include('Example_base'),
                                   type_field='discriminator',
                                   Type_1=include('Type_1'),
                                   Type_2=include('Type_2')  )

# include Example, not Example_base in cases where an Example is needed
Use_case: include('Example')

```

Reference item
  * `link_target`: string with name of element that will be made into a link
     that can be pointed to by another element (rather than including a complete
     copy of the element). A link target is required to have an `id` field that
     can be used.
  * `link`: string with name of the `link_target` that should be linked to
     (analogous to a foreign key constrains in a relational data model).

### Special item values

#### `'other'` in `enum`:

If the string `'other'` is present in an `enum` it should trigger a request for
extending the enumerator. *i.e.* the value 'other' should **never** be stored.

#### -1:

Unless -1 is an allowed value, it indicates that the value is unknown, it should
always be written in the description if -1 should be interpreted like this.
**TODO** it might be more appropriate to changes this to `null` rather than -1.

### Marking an item as required or optional

An element is marked as required by default. If it should be optional its value
should contain the `required=False` flag.

If a map (object) only contains optional items it should be made into a separate
map (object) and included (see below) with and marked by the `required=False`
flag.


### Namespace items

Namespace items are maps (objects) which only purpose is serve to collect
items under a common namespace. This means that they don't have the
`description`, `value` and `searchable` elements. They're always required, and
only found in the at the top level in the `General_parameters` map (object).

# Structure of a record

Each record contains the items needed to annotate the data derived for a
**single** measurement series and is composed of two items:

  1. `general_parameters`
  2. `method_specific_parameters`

The `general_parameters` contains the items that needs to be specified for all
types of depositions, regardless of which experimental technique they were
derived from, *i.e.* the required items are available in all records.

The `method_specific_parameters` contains the items needed to annotate a the
data derived for a **single** experiment  specific class of biophysical methods.
These items varies greatly between different techniques

## `general_parameters`

The item `general_parameters` is composed of the map `General_parameters` which
is found in `general_parameters_with_descriptions.yaml`. In addition to maps
(objects) used in the general parameters, this file also contains maps that are
already used insight an `include` in multiple maps, or maps that likely will be
included in multiple places. As it's used for specifying information across
methods it's important that:

 * It only contains generic information (identification of method, chemical
   species etc.).
 * It is flexible enough to capture all types of methods.
 * Changes to this object should only be made reluctantly as it affects every
   record in the database and hence has possibility to break the entire
   database, and could require considerable effort to incorporate.


The overall structure of `General_parameters` is:

```yaml
General_parameters:
  record
  associated_publications
  depositors
  funding
  technique
  instrument
  raw_data_information
  physical_environment_at_sample_handling
  chemical_information
  derived_parameters
```
### `record`

Namespace item containing the metadata of the record itself *i.e.* the unique
identifier of the records and which version of the schema the record was
was recorded in.

### `associated_publications`

If the data was produced and disseminated as part of a scientific publication,
the details of the associated publication(s) can be specified here.

### `depositors`

Information about the people involved in making the deposition.

### `funding`

Information about the funding that was used to generate the data for the
deposition.

### `technique`

The name of the biophysical technique used to generate data, currently
deposition are only allowed when they were obtained by measurement
using:

  * MST and related measurement modes (TRIC, initial fluorescence, spectral
shift)
  * BLI
  * SPR

### `instrument`

Information about the instrument used to perform the measurement, including
test of instrument performance.

### `raw_data_information`

Information about the files containing the raw data, as well about the files
containing processed data.

### `physical_environment_at_sample_handling`

Information about the physical state of the sample immediately prior
to being measured.

### `chemical_information`

This namespace item contains the detailed information about the molecular
entities of interest that as well as the chemical environment
(buffer components). Searches to establish the absence, presence,
or concentration of specific molecules is believed be a central
component that of MBDB, as well as for interoperability with other
online resources.

Due to their importance more information about chemical object is
supplied below:

#### `chemical_environments`

Chemical environments are the parts of the solutions are not explicitly being
investigated during the course of the experiment. This is not to imply
that these components aren't important, merely that these were not the focus
of the measurement, and hence that these components behaviour during the
measurement was not accounted for. Common examples of such components
include water, pH buffering components, BSA, salts who's concentration was not
were not varied as part of the measurement (including control measurements). A
chemical environments is the sum of such components within a given measurement.

As these components were not the main focus of the conducted of the measurement
they have fewer search options than the entities of interest.

#### `entities_of_interest`

In this item, all the entities that are being measured as well as all the
entities that were present to alter the behaviour of the measured entities
during the measurement.

Marking some component as being the focus of the measurement is done in order
to make it explicit which molecules the conductor of the measurement focusing
on.

## `method_specific_parameters`

In this item, all the items that are specific to the technique specified in the
`general_parameters`.

This is the most variable part of the schema as here's large differences in
which measurement parameters needed, how the measured data is structured, and
how data analysis is performed. This does not only hold true for different
techniques, but even within single technique there are sometimes large variation
in how measurements and data analysis is performed.

# Relations among records

## Measurement groups

If several measurements series closely related (*e.g.* identical samples
measured with different techniques, all measurement from a single publication
*etc*) this can be annotated by placing the records in the same group.

## Projects

If measurements that are part of more loosely connected (*e.g.* part of the
long running research from a research group or long running collaborations) this
can be annotated by placing the records in within the same project.


[yamale]: https://github.com/23andMe/Yamale
[ORCID]: https://info.orcid.org/what-is-orcid/
[CAS Registry Numbers]: https://www.cas.org/cas-data/cas-registry
[Pubchem Compound ID]: https://www.ncbi.nlm.nih.gov/pccompound
[Pubchem Substance ID]: https://www.ncbi.nlm.nih.gov/pcsubstance
