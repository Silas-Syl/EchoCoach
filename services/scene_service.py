from pathlib import Path
import yaml


BASE_DIR = Path(__file__).resolve().parent.parent
SCENE_FILE = BASE_DIR / "data" / "scenes.yaml"


def load_scenes():
    """
    Load all speaking practice scenarios from data/scenes.yaml.
    """
    with open(SCENE_FILE, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)
