#!/usr/bin/python3

import gzip
import json
import logging
import requests
import sqlite3
import tarfile
import yaml
import zipfile
from abc import ABC, abstractmethod
from ete3 import NCBITaxa
from hashlib import md5
from os import makedirs
from pathlib import Path
from typing import Iterator
from urllib.request import urlretrieve

# Top level dirs
BASE_DIR = Path(__file__).parent.absolute()
SOURCES_DIR = "vocabulary_sources"
VOCAB_DIR = "generated_vocabularies"

# organism vocabulary related constants
DB_DEFAULT_PATH = BASE_DIR / SOURCES_DIR / "NCBI_taxonomy.sqlite"
TAXDUMP_DEFAULT_PATH = BASE_DIR / SOURCES_DIR / "taxdump.tar.gz"
TAXDUMP_URL = "https://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz"
TAXDUMP_MD5_URL = f"{TAXDUMP_URL}.md5"

# affiliation vocabulary related constants
# information from https://ror.readme.io/docs/data-dump#download-ror-data-dumps-programmatically-with-the-zenodo-api
ZIP_DEFAULT_PATH = BASE_DIR / SOURCES_DIR / "ROR_institutions.zip"
NEWEST_ZIP_URL = "https://zenodo.org/api/records/?communities=ror-data&sort=mostrecent"

# grant vocabulary related constants
# the Zenodo record 3516917 redirects to the newest available data dump from OpenAIRE Graph
TARBALL_DEFAULT_PATH = BASE_DIR / SOURCES_DIR / "OpenAIRE_grants.tar"
NEWEST_TARBALL_URL = "https://zenodo.org/api/records/3516917"


class CheckSumError(Exception):
    pass


class RetrivalError(Exception):
    pass


class Vocabulary(ABC):
    def __init__(
        self, output_yaml, default_path, online_data_source, local_data_source=None
    ):
        self.default_path = default_path
        self.output_yaml = output_yaml
        self.local_data_source = local_data_source
        self.online_data_source = online_data_source
        self.msg = self._generate_msg()

    @abstractmethod
    def generate_source(self):
        ...

    @abstractmethod
    def iter_of_records(self) -> Iterator[dict]:
        ...

    def _generate_msg(self):
        return f"{self.__class__.__name__} vocabulary"

    def add_records(self, limit=-1):
        if not isinstance(limit, int):
            raise TypeError(f"limit must be an int, got {type(limit)}")

        with open(self.output_yaml, "a") as f_out:
            logging.info(f"Started writing {self.msg} to file {self.output_yaml}")
            for i, record in enumerate(self.iter_of_records()):
                if i == limit:
                    break
                # final output should be a yaml sequence so record is converted to a list item
                yaml_data = yaml.dump(record, sort_keys=False, allow_unicode=True, explicit_start=True)
                f_out.write(yaml_data)

            logging.info(f"Finished writing {i} items to {self.msg}")


class Organism(Vocabulary):
    def __init__(
        self, output_yaml, taxdump_path=None, taxdump_md5_url=None, organism_db=None
    ):
        super().__init__(
            output_yaml=output_yaml,
            local_data_source=organism_db,
            default_path=DB_DEFAULT_PATH,
            online_data_source=TAXDUMP_URL,
        )

        self.taxdump_path = taxdump_path
        self.taxdump_md5_url = taxdump_md5_url

        choose_data_source(self)
        self.organism_db = self.local_data_source
        self.converted_name = {
            "taxid": "id",
            "spname": "title",
            "rank": "rank",
        }

    def _retrieve_taxdump(self):
        """Downloads the NCBI taxdump"""

        if self.taxdump_md5_url is None:
            self.taxdump_md5_url = TAXDUMP_MD5_URL

        if self.taxdump_path is None:
            self.taxdump_path = TAXDUMP_DEFAULT_PATH

        urlretrieve(self.online_data_source, self.taxdump_path)
        (md5_filename, _) = urlretrieve(self.taxdump_md5_url)
        with open(md5_filename, "r") as md5_file:
            checksum = md5_file.readline().split()[0]

        compare_md5_checksums(self.taxdump_path, checksum)

    def generate_source(self):
        """generates the database using online source"""
        DB_DEFAULT_PATH.touch()
        self._retrieve_taxdump()
        NCBITaxa(dbfile=str(DB_DEFAULT_PATH), taxdump_file=str(TAXDUMP_DEFAULT_PATH))

    def update_db(self):
        """updates the database using online source"""
        self._retrieve_taxdump()
        NCBITaxa(dbfile=str(DB_DEFAULT_PATH)).update_taxonomy_database(
            taxdump_file=str(TAXDUMP_DEFAULT_PATH)
        )

    def make_query(self, fields=None, table=None):
        """Constructs the SQL query to extract the relevant items from the NCBI taxonomy sqlite
        database"""

        if fields is None:
            fields = ",".join([key for key in self.converted_name.keys()])
        if table is None:
            table = "species"
        return f"""SELECT {fields} FROM {table}"""

    def dict_item_factory(self, cursor, row):
        """returns with converted """
        row_dict = {key: value for key, value in zip(self.converted_name.values(), row)}
        return {"id": str(row_dict["id"]),
                "title": {"en": row_dict["title"]},
                "props": {"rank": row_dict["rank"]},
                }

    def iter_of_records(self) -> Iterator[dict]:
        """Converts an ete3 NCBI taxonomy sqlite DB to a list of vocabulary dicts"""
        with sqlite3.connect(self.organism_db) as connection:
            connection.row_factory = self.dict_item_factory
            cursor = connection.cursor()
            return cursor.execute(self.make_query())


class Affiliation(Vocabulary):
    def __init__(self, output_yaml, affiliation_zip=None):
        super().__init__(
            output_yaml=output_yaml,
            local_data_source=affiliation_zip,
            default_path=ZIP_DEFAULT_PATH,
            online_data_source=NEWEST_ZIP_URL,
        )

        choose_data_source(self)
        self.affiliation_zip = self.local_data_source

    def generate_source(self):
        """Downloads the affiliations from online source"""
        print("Locating newest version of the affiliation source (ROR data)")
        response = requests.get(self.online_data_source)
        if not response.ok:
            raise RetrivalError(
                f"Online affiliation source could not be reached status code of "
                f"{response.status_code} was return"
            )
        file_info = response.json()["hits"]["hits"][0]["files"][0]
        fetch_from_zenodo(file_info, self.default_path)

    @staticmethod
    def extract_affiliation(ror_dict):
        """Converts a ror json record dict to a vocabulary dict"""
        affiliation = {
            "id": ror_dict["id"].split("/")[-1],
            "title": {"en": ror_dict["name"]},
            "props":{
                "city": ror_dict["addresses"][0]["city"],
                "country": ror_dict["country"]["country_name"],
                "state": ror_dict["addresses"][0]["state"]
            }
        }
        # null values are not allowed in Invenio vocabularies so remove state if it is not there
        props = affiliation["props"]
        if props['state'] is None:
            del props['state']

        return affiliation

    @staticmethod
    def get_json(file_names):
        """Returns the json file from a list of filenames"""
        for name in file_names:
            if name.endswith(".json"):
                return name
        raise ValueError(f"No json file in {file_names}")

    def iter_of_records(self) -> Iterator[dict]:
        """Converts a zip archive containing a json file of ror records
        into an iterator of vocabulary dicts"""

        with zipfile.ZipFile(self.affiliation_zip, "r") as affiliation_zip:
            source = self.get_json(affiliation_zip.namelist())
            with affiliation_zip.open(source, "r") as json_file:
                for ror_dict in json.load(json_file):
                    yield self.extract_affiliation(ror_dict)


class Grant(Vocabulary):
    def __init__(self, output_yaml, grants_tarball=None):
        super().__init__(
            output_yaml=output_yaml,
            local_data_source=grants_tarball,
            default_path=TARBALL_DEFAULT_PATH,
            online_data_source=NEWEST_TARBALL_URL,
        )

        choose_data_source(self)
        self.grants_tarball = self.local_data_source

    def generate_source(self):
        print("Fetching newest version of the grants source (OpenAIRE Graph data) ")
        response = requests.get(self.online_data_source)
        if not response.ok:
            raise RetrivalError(
                f"Online grant source could not be reached status code of "
                f"{response.status_code} was return"
            )

        file_info = [
            file_info
            for file_info in response.json()["files"]
            if file_info["key"] == "project.tar"
        ][0]
        fetch_from_zenodo(file_info, self.default_path)

    @staticmethod
    def extract_grant(openaire_dict):
        logging.debug(f'Extracting grantID: {openaire_dict["code"]}')

        try:
           funder_name = openaire_dict["funding"][0]["name"]
        except IndexError:
           funder_name = None

        return {
            "id": openaire_dict["code"],
            "title": {"en": openaire_dict["title"]},
            "props": {"funder_name": funder_name}
        }

    def iter_of_records(self) -> Iterator[dict]:
        """Converts a tarball of gzipped newline seperated json documents of OpenAIRE project records
        to an iterator of vocabulary dicts"""

        with tarfile.open(self.grants_tarball, mode="r") as tar:
            for gz_file in tar.getmembers():
                for record in gzip.GzipFile(
                    fileobj=tar.extractfile(gz_file)
                ).readlines():
                    yield self.extract_grant(json.loads(record.decode()))


def choose_data_source(vocabulary: type[Vocabulary]):
    if vocabulary.local_data_source is None:
        print(f"Default source for {vocabulary.msg} will be used")
        vocabulary.local_data_source = vocabulary.default_path
        if not vocabulary.local_data_source.exists():
            print(
                f"Warning {vocabulary.default_path} doesn't exist, will fetch it online"
            )
            vocabulary.generate_source()

    if not vocabulary.local_data_source.exists():
        raise FileNotFoundError(f"{vocabulary.local_data_source} doesn't exist")


def fetch_from_zenodo(file_info: dict, filename):
    """Downloads the file specified in the info map from Zenodo"""
    md5_checksum = file_info["checksum"].split(":")[-1]
    file_url = file_info["links"]["self"]
    file_mib_size = file_info["size"] / (1024 * 1024)
    print(f'Fetching file {file_url.split("/")[-1]} ({file_mib_size:.1f} MiB)')
    urlretrieve(file_url, filename)
    compare_md5_checksums(filename, md5_checksum)


def compare_md5_checksums(filename, checksum):
    """Calculates the md5 checksum of filename
    and compares it to the checksum and raises CheckSumError if they don't match"""
    print("Comparing MD5 checksums")
    file_checksum = md5(open(filename, "rb").read()).hexdigest()
    if file_checksum == checksum:
        print("Checksums match")
    else:
        raise CheckSumError("Checksums doesn't match")

def main():
    for folder in (SOURCES_DIR, VOCAB_DIR):
        makedirs(BASE_DIR / folder, exist_ok=True)

    logging.basicConfig(
        filename=BASE_DIR / "generated_vocabularies.log",
        encoding="utf-8",
        filemode="w",
        format="%(levelname)s:%(name)s:%(asctime)s:%(message)s",
        level=logging.INFO,
    )

    logging.info("Started")

    vocab_params = [("organisms.yaml", Organism, 1000),
                    ("affiliations.yaml", Affiliation, 1000),
                    ("grants.yaml", Grant, 1000),
                    ]

    for fn, generator, limit in vocab_params:
        vocab = generator(output_yaml=BASE_DIR / VOCAB_DIR / fn)
        vocab.add_records(limit=limit)

    logging.info("Finished")


if __name__ == "__main__":
    main()
