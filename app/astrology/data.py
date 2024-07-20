import json
from pathlib import Path

from app.astrology.schemas import AstrologyData


def load_astrology_data() -> AstrologyData:
    """Load the astrology data from the JSON file."""
    with Path("new_zodiac_data.json").open() as f:
        contents = f.read()
    return AstrologyData(**json.loads(contents))


astrology_data = load_astrology_data()