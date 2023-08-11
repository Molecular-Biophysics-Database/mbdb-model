# mbdb-model

## What's this repository for?

This repository is used for sharing concrete tools and for keeping
track of various specifications such as:

- Specifications of metadata
- Data format specifications
- Tools for validation and consistency checks of the generated data models

It's also where bugs and suggestions to existing specification can be made by
raising issues.

## Prerequisites

* python 3.9+
* pyyaml (avaliable through pypi)
* yamale (avaliable through pypi)
* numpy (avaliable through pypi)


## Repository organisation

### Data models (schemas)

In the model folder you'll find further information about the models,
their structure, syntax, and usage can be found.

```
mbdb-model
├── models              <--
├── metadata-examples
├── tools
└── vocabularies
```


### Example data

Examples of how validated records in YAML and JSON, the later is directly
compatible for being loaded into the Invenio instance of MBDB.

```
mbdb-model
├── models
├── metadata-examples   <--
├── tools
└── vocabularies
```


### Tools

Various tools for converting to different forms of the model (excluding the
final conversion to the Invenio compatible models).

```
mbdb-model
├── models
├── metadata-examples
├── tools               <--
└── vocabularies
```

### vocabularies

The schemas for vocabularies as well as the tools for extracting them from
their sources can be found here.

```
mbdb-model
├── models
├── metadata-examples
├── tools              
└── vocabularies         <--
```

## How to contribute?

### I would like to make a pull-request:

Great! Go ahead and make it. I'll try to make sure it doesn't cause any
harm before merging it, but please try to:

- Make small commits so it's easier to see which effect they will have
- Propagate changes upstream and downstream before submitting the
  pull-request


[MOSBRI]: https://www.mosbri.eu/
[FAIR principles]: https://doi.org/10.1038/sdata.2016.18
[mmCIF/PDBx dictionary]: https://mmcif.wwpdb.org/
[Invenio Framework]: https://invenio.readthedocs.io/en/latest/
