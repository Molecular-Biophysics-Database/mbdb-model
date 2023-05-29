# Models

## main

These are the models all other models derive from including the models used to
by Invenio.

## oarepo

These models contain the same information as the main models. They're
compatible with being installed on Invenio, however they must still be moved
into the appropriate folders in the mbdb-app and installed before the changes
made to them will show up in the actual database. Instruction on how to do this
can be found in the [mbdb-app repository](https://github.com/Molecular-Biophysics-Database/mbdb-app).


## value-only

These models only contains the values of each item, all other information
have been stripped away. They're generate as they are used for:

 - Validating the meta data examples
 - Generating random data from that is purely based on the schemas
 - Easier overview of the structure of the data


## unrolled

These are a treelike representation where every nested element has been
included. They're generated to:

 - Ensure that no circular includes are present
 - Obtain the number of fields that are needed to index the models
