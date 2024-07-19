from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.absolute()
MODEL_DIR = ROOT_DIR.joinpath("models").absolute()
EXAMPLES_DIR = ROOT_DIR.joinpath("metadata_examples").absolute()
