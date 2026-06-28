"""Dataset registry for legal stems / vocals."""
from dataclasses import dataclass


@dataclass
class DatasetInfo:
    name: str
    url: str
    license_note: str


DATASETS = [
    DatasetInfo("MUSDB18-HQ", "https://sigsep.github.io/datasets/musdb.html", "Research dataset; check terms."),
    DatasetInfo("MedleyDB", "https://medleydb.weebly.com/", "Royalty-free multitrack; check terms."),
    DatasetInfo("ccMixter", "https://ccmixter.org/", "Creative Commons; check each track."),
]
