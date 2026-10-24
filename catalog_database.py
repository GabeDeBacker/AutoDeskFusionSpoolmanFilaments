"""
Module for importing filament catalog data from a JSON file into an SQLite database.

Functions:
- stream_json_entries(path): Streams entries from the JSON catalog file.
- import_spoolman(json_path, db_path): Imports the Spoolman catalog into the specified SQLite database.
"""

import os
import sqlite3
import json
import colorsys
import time
from math import ceil
from urllib.request import urlopen, Request
from common import path_from_add_on
from ui_state import normalize_ui_state

CATALOG_CACHE_URL = 'https://donkie.github.io/SpoolmanDB/filaments.json'
CATALOG_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
CATALOG_CACHE_FILE = 'filament_catalog_cache.json'

class CatalogDatabase:
    """Class for managing the filament catalog SQLite database."""
    def __init__(self, db_path: str):
        """Initialize the CatalogDatabase with the path to the SQLite database."""
        self.db_path = db_path
        self.connection = None

    @staticmethod
    def cache_directory():
        """Return the on-disk cache file path for normalized catalog data."""
        return path_from_add_on("cache")

    @staticmethod
    def cache_catalog_database_path():
        """Return the on-disk cache file path for normalized catalog data."""
        return path_from_add_on("cache", CATALOG_CACHE_FILE.replace('.json', '.db'))

    @staticmethod
    def cache_catalog_path():
        """Return the on-disk cache file path for normalized catalog data."""
        return path_from_add_on("cache", CATALOG_CACHE_FILE)

    @staticmethod
    def cache_spoolman_catalog_path():
        """Return the on-disk cache file path for the Spoolman catalog data."""        
        return path_from_add_on("cache", f"spoolman_{CATALOG_CACHE_FILE}")

    def close_connection(self):
        """Close the connection to the SQLite database if it is open."""
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def ensure_connection(self):
        """Ensure that a connection to the SQLite database is established and return it."""
        os.makedirs(path_from_add_on("cache"), exist_ok=True)
        if self.connection is not None:
            return self.connection
        self.connection = sqlite3.connect(self.db_path)
        return self.connection

    def hex_to_hsv(self, hex_color: str):
        """Convert a hex color string to HSV values."""
        stripped_color = hex_color.lstrip('#')
        r = g = b = 0.0
        if (len(stripped_color)== 6):
            # The value returned from rgb_to_hsv are values between 0 and 1, hence the division by 255.
            r = int(stripped_color[0:2], 16) / 255.0
            g = int(stripped_color[2:4], 16) / 255.0
            b = int(stripped_color[4:6], 16) / 255.0
        elif (len(stripped_color) == 8):
            # The value returned from rgba_to_hsv are values between 0 and 1, hence the division by 255.
            r = int(stripped_color[0:2], 16) / 255.0
            g = int(stripped_color[2:4], 16) / 255.0
            b = int(stripped_color[4:6], 16) / 255.0
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        return h, s, v

    def stream_json_array(self, path: str):
        """Stream objects from a JSON array in the file at the given path."""
        decoder = json.JSONDecoder()
        with open(path, "r", encoding="utf8") as f:
            buffer = ""
            # Skip initial '['
            char = f.read(1)
            if char != "[":
                raise ValueError("Expected JSON array")

            while True:
                chunk = f.read(64*1024)
                if not chunk:
                    break
                buffer += chunk

                while True:
                    buffer = buffer.lstrip()
                    if buffer.startswith("]"):
                        return

                    try:
                        obj, idx = decoder.raw_decode(buffer)
                    except json.JSONDecodeError:
                        break

                    yield obj
                    buffer = buffer[idx:].lstrip()
                    if buffer.startswith(","):
                        buffer = buffer[1:]

    def download_spoolman_entries(self):
        """Download raw filament rows from the upstream Spoolman catalog."""
        req = Request(
            CATALOG_CACHE_URL,
            headers={'User-Agent': 'SpoolmanDBFilamentColors/1.0'},
        )

        spoolman_json_path = self.cache_spoolman_catalog_path()
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

    def set_metadata(self, metadata):
        """Set the metadata for the filament catalog in the database."""
        con = self.ensure_connection()
        cur = con.cursor()
        # Drop and recreate table
        cur.execute("DROP TABLE IF EXISTS catalog_metadata")
        cur.execute("""
            CREATE TABLE catalog_metadata (
                schema_version INTEGER,
                catalog_version TEXT,
                generated_epoch INTEGER,
                entry_count INTEGER,
                source TEXT
            );
        """)

        # Insert metadata row
        cur.execute("""
            INSERT INTO catalog_metadata (
                schema_version,
                catalog_version,
                generated_epoch,
                entry_count,
                source
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            metadata["schema_version"],
            metadata["catalog_version"],
            metadata["generated_epoch"],
            metadata["entry_count"],
            metadata["source"]
        ))
        con.commit()

    def import_spoolman(self):
        """Import the Spoolman filament catalog from a JSON file into an SQLite database."""
        self.download_spoolman_entries()
        json_path = self.cache_spoolman_catalog_path()
        con = self.ensure_connection()
        cur = con.cursor()
        entry_count = 0

        # Speed pragmas
        cur.execute("PRAGMA journal_mode = WAL;")
        cur.execute("PRAGMA synchronous = NORMAL;")
        cur.execute("PRAGMA temp_store = MEMORY;")
        cur.execute("PRAGMA mmap_size = 268435456;")

        # Drop and recreate table
        cur.execute("DROP TABLE IF EXISTS filaments")
        cur.execute("""
            CREATE TABLE filaments (
                id TEXT PRIMARY KEY,
                manufacturer TEXT,
                name TEXT,
                material TEXT,
                density REAL,
                weight REAL,
                spool_weight REAL,
                spool_type TEXT,
                diameter REAL,
                color_hex TEXT,
                color_hexes TEXT,
                extruder_temp REAL,
                extruder_temp_range TEXT,
                bed_temp REAL,
                bed_temp_range TEXT,
                finish TEXT,
                multi_color_direction TEXT,
                pattern TEXT,
                translucent INTEGER,
                glow INTEGER,
                hue REAL,
                saturation REAL,
                value REAL
            );
        """)

        con.commit()

        # This is going to take a lot of memory temporarily, but otherwise the import will be much faster than inserting rows one by one.
        rows = []
        for entry in self.stream_json_array(json_path):
            entry_count += 1

            # Convert first hex color to HSV
            hex_color = entry["color_hex"] or (entry["color_hexes"][0] if entry["color_hexes"] else None)
            h, s, v = self.hex_to_hsv(hex_color)

            rows.append((
                entry["id"],
                entry["manufacturer"],
                entry["name"],
                entry["material"],
                entry["density"],
                entry["weight"],
                entry["spool_weight"],
                entry["spool_type"],
                entry["diameter"],
                entry["color_hex"],
                json.dumps(entry["color_hexes"]) if entry["color_hexes"] is not None else None,
                entry["extruder_temp"],
                json.dumps(entry["extruder_temp_range"]) if entry["extruder_temp_range"] is not None else None,
                entry["bed_temp"],
                json.dumps(entry["bed_temp_range"]) if entry["bed_temp_range"] is not None else None,
                entry["finish"],
                entry["multi_color_direction"],
                entry["pattern"],
                int(entry["translucent"]),
                int(entry["glow"]),
                h, s, v
            ))

        cur.execute("BEGIN TRANSACTION;")
        if rows:
            cur.executemany("""
                INSERT INTO filaments VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, rows)

        con.commit()

        con.execute("""CREATE INDEX idx_filaments_id ON filaments(id);""")
        con.execute("""CREATE INDEX idx_filaments_manufacturer ON filaments(manufacturer);""")
        con.execute("""CREATE INDEX idx_filaments_material ON filaments(material);""")
        con.execute("""CREATE INDEX idx_filaments_finish ON filaments(finish);""")
        con.execute("""CREATE INDEX idx_filaments_translucent ON filaments(translucent);""")
        con.execute("""CREATE INDEX idx_filaments_glow ON filaments(glow);""")
        con.execute("""CREATE INDEX idx_filaments_hue ON filaments(hue);""")
        con.execute("""CREATE INDEX idx_filaments_saturation ON filaments(saturation);""")
        con.execute("""CREATE INDEX idx_filaments_value ON filaments(value);""")

        #
        # Compute metadata AFTER import
        #
        metadata = {
            "schema_version": 1,                 # your choice
            "catalog_version": "spoolman-json",  # your choice
            "generated_epoch": int(time.time()), # now
            "entry_count": entry_count,
            "source": "spoolman-db"
        }

        self.set_metadata(metadata)

    def query_filaments(self, q):
        """Query filaments from the database based on the given filters.

        Args:
            q (dict): A dictionary containing query parameters such as text search, manufacturer, finish, material, color filter, HSV tolerance, sorting, and pagination.

        Returns:
            dict: A dictionary containing the total count of matching filaments and a list of filament records.
        """
        filament_columns = [
            "id",
            "manufacturer",
            "name",
            "material",
            "density",
            "weight",
            "spool_weight",
            "spool_type",
            "diameter",
            "color_hex",
            "color_hexes",
            "extruder_temp",
            "extruder_temp_range",
            "bed_temp",
            "bed_temp_range",
            "finish",
            "multi_color_direction",
            "pattern",
            "translucent",
            "glow",
            "hue",
            "saturation",
            "value"
        ]
        normalized_state = normalize_ui_state(q)
        filters = normalized_state["filters"]

        where = []
        params = []

        # Text search
        if filters["query"]:
            search_filters = str.split(filters["query"])
            for term in search_filters:
                where.append("(name LIKE ? or manufacturer LIKE ? or material LIKE ? or color_hex LIKE ? or finish LIKE ?)")
                params.extend([f"%{term}%"] * 5)

        # Manufacturer filter
        if filters["manufacturer"] and filters["manufacturer"] != "all":
            where.append("manufacturer = ?")
            params.append(filters["manufacturer"])

        # Finish filter
        if filters["finish"] and filters["finish"] != "all":
            where.append("finish = ?")
            params.append(filters["finish"])

        # Material filter
        if filters["material"] and filters["material"] != "all":
            where.append("material = ?")
            params.append(filters["material"])

        if filters["translucent"]:
            where.append("translucent = ?")
            params.append(1)

        if filters["glow"]:
            where.append("glow = ?")
            params.append(1)

        # HSV proximity
        if filters["colorFilterOn"] and filters["colorFilterHex"]:
            color_h, color_s, color_v = self.hex_to_hsv(filters["colorFilterHex"])
            hue_tolerance = filters["tolerances"]["hue"] / 100.0
            saturation_tolerance = filters["tolerances"]["saturation"] / 100.0
            value_tolerance = filters["tolerances"]["value"] / 100.0
            if hue_tolerance and saturation_tolerance and value_tolerance:
                where.append("ABS(hue - ?) <= ?")
                params.append(color_h)
                params.append(hue_tolerance)
                where.append("ABS(saturation - ?) <= ?")
                params.append(color_s)
                params.append(saturation_tolerance)
                where.append("ABS(value - ?) <= ?")
                params.append(color_v)
                params.append(value_tolerance)

        # Build WHERE clause
        if len(where) != 0:
            where_clause = "WHERE " + " AND ".join(where)
        else:
            where_clause = ""

        # Sorting
        if filters["sort"] == "name":
            order_clause = "ORDER BY name ASC"
        elif filters["sort"] == "color":
            order_clause = "ORDER BY hue ASC, saturation ASC, value ASC"
        else:
            order_clause = ""

        # Pagination
        page = getattr(q, "page", 1) if not isinstance(q, dict) else q.get("page", 1)
        if page is None:
            page = 1
        page = max(1, int(page))
        page_size = normalized_state["pageSize"]
        offset = (page - 1) * page_size

        limit_clause = "LIMIT ? OFFSET ?"
        params.extend([page_size, offset])

        # Count query
        count_sql = f"SELECT COUNT(*) FROM filaments {where_clause}"
        con = self.ensure_connection()
        cur = con.cursor()
        cur.execute(count_sql, params[:-2])  # exclude limit/offset
        total = cur.fetchone()[0]

        # Data query
        sql = f"""
            SELECT *
            FROM filaments
            {where_clause}
            {order_clause}
            {limit_clause}
        """

        cur.execute(sql, params)
        rows = cur.fetchall()
        result_rows = []

        # Convert hexes to color_hexes for consistency with the frontend
        for row in rows:
            row_dict = dict(zip(filament_columns, row))
            if row_dict["color_hexes"] is not None:
                color_hexes = json.loads(row_dict.pop("color_hexes"))
                row_dict["color_hexes"] = color_hexes
            result_rows.append(row_dict)

        return {
            "total": total,
            "page": page,
            "pageSize": page_size,
            "pages":   max(1, ceil(total / page_size)), 
            "results": result_rows
        }

    def build_filter_universe_where(self, q, exclude=None):
        """Build the WHERE clause and parameters for filtering the filament catalog.

        Args:
            q (object): An object containing query parameters such as manufacturer, finish, and material.
            exclude (str, optional): A field to exclude from the filtering. Defaults to None.

        Returns:
            tuple: A tuple containing the WHERE clause string and the list of parameters.
        """
        where = []
        params = []

        # We don't want to return null values for whatever is being excluded.
        if exclude:
            where.append(f"{exclude} is not null")

        normalized_state = normalize_ui_state(q)
        filters = normalized_state["filters"]

        # Manufacturer constraint (unless excluded)
        if filters["manufacturer"] not in (None, "", "all") and exclude != "manufacturer":
            where.append("manufacturer = ?")
            params.append(filters["manufacturer"])

        # Material constraint (unless excluded)
        if filters["material"] not in (None, "", "all") and exclude != "material":
            where.append("material = ?")
            params.append(filters["material"])

        # Finish constraint (unless excluded)
        if filters["finish"] not in (None, "", "all") and exclude != "finish":
            where.append("finish = ?")
            params.append(filters["finish"])

        clause = "WHERE " + " AND ".join(where) if where else ""
        return clause, params

    def get_filter_lists(self, q) -> dict:
        """Get the lists of available manufacturers, materials, and finishes for the filter dropdowns.

        Args:
            q (object): An object containing the current query parameters.

        Returns:
            dict: A dictionary containing lists of manufacturers, materials, and finishes.
        """
        con = self.ensure_connection()
        cur = con.cursor()

        # Manufacturer dropdown: filtered by material + finish
        wc, params = self.build_filter_universe_where(q, exclude="manufacturer")
        sql = f"SELECT DISTINCT manufacturer FROM filaments {wc} ORDER BY manufacturer"
        cur.execute(sql, params)
        results = cur.fetchall()
        if len(results) == 0:
            manufacturers = []
        else:
            manufacturers = [r[0] for r in results]

        # Material dropdown: filtered by manufacturer + finish
        wc, params = self.build_filter_universe_where(q, exclude="material")
        sql = f"SELECT DISTINCT material FROM filaments {wc} ORDER BY material"
        cur.execute(sql, params)
        results = cur.fetchall()
        if len(results) == 0:
            materials = []
        else:
            materials = [r[0] for r in results]

        # Finish dropdown: filtered by manufacturer + material
        wc, params = self.build_filter_universe_where(q, exclude="finish")
        sql = f"SELECT DISTINCT finish FROM filaments {wc} ORDER BY finish"
        cur.execute(sql, params)
        results = cur.fetchall()
        if len(results) == 0:
            finishes = []
        else:
            finishes = [r[0] for r in results]

        return {
            "manufacturers": manufacturers,
            "materials": materials,
            "finishes": finishes
        }

    def get_catalog_metadata(self) -> dict:
        """Get the catalog metadata from the database."""
        con = self.ensure_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='filaments'
        """)

        exists = cur.fetchone() is not None
        if not exists:
            return {}

        cur.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='catalog_metadata'
        """)

        exists = cur.fetchone() is not None
        if not exists:
            return {}

        cur.execute("SELECT" \
        " schema_version," \
        " catalog_version," \
        " generated_epoch," \
        " entry_count," \
        " source" \
        " FROM catalog_metadata")

        row = cur.fetchone()
        if (row is None or len(row) == 0):
            return {}

        return {
            "schema_version": row[0],
            "catalog_version": row[1],
            "generated_epoch": row[2],
            "entry_count": row[3],
            "source": row[4]
        }

    def refresh_if_needed(self, force = False):
        """Refresh the catalog if it is outdated."""
        if force:
            self.import_spoolman()
            return

        metadata = self.get_catalog_metadata()
        if (metadata is None or metadata.get('generated_epoch') is None):
            self.import_spoolman()
            return

        if metadata and metadata.get('generated_epoch') is not None:
            last_refresh = int(metadata['generated_epoch'])
            if not last_refresh or self.is_catalog_outdated(last_refresh):
                self.import_spoolman()

    def is_catalog_outdated(self, last_refresh: int) -> bool:
        """Check if the catalog is outdated based on the last refresh timestamp."""
        current_time = int(time.time())
        # Consider the catalog outdated if it was last refreshed more than 24 hours ago
        return (current_time - last_refresh) > CATALOG_CACHE_TTL_SECONDS

CATALOG_DATABASE = None
def get_catalog_database() -> CatalogDatabase:
    """Get the singleton instance of the catalog database."""
    global CATALOG_DATABASE
    if CATALOG_DATABASE is None:
        CATALOG_DATABASE = CatalogDatabase(CatalogDatabase.cache_catalog_database_path())
    return CATALOG_DATABASE
