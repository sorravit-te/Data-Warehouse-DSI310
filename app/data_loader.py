"""Source database download and connection helpers.

Ported from ``notebooks/dsi310_northwind_chinook_eda_v1_0.ipynb`` so the
Streamlit app and the EDA notebook download the exact same files to the
exact same (gitignored) location instead of duplicating divergent copies.
"""

from pathlib import Path

import requests
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

CHINOOK_URL = (
    "https://raw.githubusercontent.com/lerocha/chinook-database/master/"
    "ChinookDatabase/DataSources/Chinook_Sqlite.sqlite"
)
NORTHWIND_URL = (
    "https://github.com/jpwhite3/northwind-SQLite3/raw/main/dist/northwind.db"
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "notebooks" / "data"
CHINOOK_DB_PATH = DATA_DIR / "chinook.db"
NORTHWIND_DB_PATH = DATA_DIR / "northwind.db"


def download_file(url: str, destination: Path) -> Path:
    """Download a source file unless a non-empty local copy already exists."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and destination.stat().st_size > 0:
        return destination

    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with destination.open("wb") as output_file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    output_file.write(chunk)

    return destination


def build_engines() -> tuple[Engine, Engine]:
    """Download both source databases (if needed) and open engines for them."""
    download_file(CHINOOK_URL, CHINOOK_DB_PATH)
    download_file(NORTHWIND_URL, NORTHWIND_DB_PATH)

    chinook_engine = create_engine(f"sqlite:///{CHINOOK_DB_PATH.as_posix()}", echo=False)
    northwind_engine = create_engine(f"sqlite:///{NORTHWIND_DB_PATH.as_posix()}", echo=False)
    return chinook_engine, northwind_engine
