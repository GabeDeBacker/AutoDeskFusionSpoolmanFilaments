"""Filament catalog download, normalization, caching, and status helpers."""

import os
import time
from urllib.request import Request, urlopen
from catalog_database import CatalogDatabase, get_catalog_database

CATALOG_CACHE_URL = 'https://donkie.github.io/SpoolmanDB/filaments.json'
CATALOG_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60

def download_spoolman_entries():
    """Download raw filament rows from the upstream Spoolman catalog."""
    req = Request(
        CATALOG_CACHE_URL,
        headers={'User-Agent': 'SpoolmanDBFilamentColors/1.0'},
    )

    os.makedirs(CatalogDatabase.cache_directory(), exist_ok=True)
    spoolman_json_path =  CatalogDatabase.cache_spoolman_catalog_path()
    with open(spoolman_json_path, 'wb') as out:
        with urlopen(req, timeout=20) as resp:
            status = getattr(resp, 'status', 200)
            if status < 200 or status >= 300:
                raise ValueError(f'Unexpected HTTP status: {status}')

            # Stream in chunks (64KB is a good size)
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                out.write(chunk)

    # Now import into SQLite
    get_catalog_database().import_spoolman()


def cache_is_fresh():
    """Return whether cache age is within the configured TTL window."""
    payload = get_catalog_database().get_catalog_metadata()
    if not payload:
        return False
    try:
        generated = int(payload.get('generated_epoch') or 0)
    except (TypeError, ValueError):
        return False
    if generated <= 0:
        return False
    return (int(time.time()) - generated) < CATALOG_CACHE_TTL_SECONDS
