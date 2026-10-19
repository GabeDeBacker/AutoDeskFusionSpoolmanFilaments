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

from common import addon_dir, path_from_add_on

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
        if self.connection is not None:
            return self.connection
        self.connection = sqlite3.connect(self.db_path)
        return self.connection

    def hex_to_hsv(self, hex_color: str):
        """Convert a hex color string to HSV values."""
        hex_color = hex_color.lstrip('#')
        # The value returned from rgb_to_hsv are values between 0 and 1, hence the division by 255.
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
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

    def import_spoolman(self, json_path):
        """Import the Spoolman filament catalog from a JSON file into an SQLite database."""
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
                json.dumps(entry["color_hexes"]),
                entry["extruder_temp"],
                json.dumps(entry["extruder_temp_range"]),
                entry["bed_temp"],
                json.dumps(entry["bed_temp_range"]),
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
        where = []
        params = []

        # Text search
        if q["text"]:
            where.append("search_text LIKE ?")
            params.append(f"%{q['text']}%")

        # Manufacturer filter
        if q["manufacturer"]:
            where.append("manufacturer = ?")
            params.append(q["manufacturer"])

        # Finish filter
        if q["finish"]:
            where.append("finish = ?")
            params.append(q["finish"])

        # Material filter
        if q["material"]:
            where.append("material = ?")
            params.append(q["material"])

        # HSV proximity
        if q["colorFilterOn"] and q["hsvTolerance"] and q["color"]:
            color_h, color_s, color_v = self.hex_to_hsv(q["color"])
            if (q["hsvTolerance"]["h"] and q["hsvTolerance"]["s"] and q["hsvTolerance"]["v"]):
                where.append("ABS(hue - ?) <= ?")
                params.append(color_h)
                params.append(q["hsvTolerance"]["h"])
                where.append("ABS(saturation - ?) <= ?")
                params.append(color_s)
                params.append(q["hsvTolerance"]["s"])
                where.append("ABS(value - ?) <= ?")
                params.append(color_v)
                params.append(q["hsvTolerance"]["v"])

        # Build WHERE clause
        if len(where) != 0:
            where_clause = "WHERE " + " AND ".join(where)
        else:
            where_clause = ""

        # Sorting
        if q["sort"] == "name":
            order_clause = "ORDER BY name ASC"
        elif q["sort"] == "color":
            order_clause = "ORDER BY hue ASC, saturation ASC, value ASC"
        else:
            order_clause = ""

        # Pagination
        page = q["page"]
        page_size = q["pageSize"]
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

        return {
            "total": total,
            "page": page,
            "pageSize": page_size,
            "pages": (total + page_size - 1) // page_size,
            "results": [dict(zip(filament_columns, r)) for r in rows]
        }

    def build_filter_universe_where(self, q, exclude=None):
        """Build the WHERE clause and parameters for filtering the filament catalog.

        Args:
            q (dict): A dictionary containing query parameters such as manufacturer, finish, and material.
            exclude (str, optional): A field to exclude from the filtering. Defaults to None.

        Returns:
            tuple: A tuple containing the WHERE clause string and the list of parameters.
        """
        where = []
        params = []

        # Manufacturer constraint (unless excluded)
        if q.get("manufacturer") not in (None, "", "all") and exclude != "manufacturer":
            where.append("manufacturer = ?")
            params.append(q["manufacturer"])

        # Material constraint (unless excluded)
        if q.get("material") not in (None, "", "all") and exclude != "material":
            where.append("material = ?")
            params.append(q["material"])

        # Finish constraint (unless excluded)
        if q.get("finish") not in (None, "", "all") and exclude != "finish":
            where.append("finish = ?")
            params.append(q["finish"])

        clause = "WHERE " + " AND ".join(where) if where else ""
        return clause, params

    def get_filter_lists(self, q):
        """Get the lists of available manufacturers, materials, and finishes for the filter dropdowns.

        Args:
            q (dict): A dictionary containing the current query parameters.

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
        if (len(results) == 0):
            manufacturers = []
        else:
            manufacturers = [r[0] for r in results]

        # Material dropdown: filtered by manufacturer + finish
        wc, params = self.build_filter_universe_where(q, exclude="material")
        sql = f"SELECT DISTINCT material FROM filaments {wc} ORDER BY material"
        cur.execute(sql, params)
        results = cur.fetchall()
        if (len(results) == 0):
            materials = []
        else:
            materials = [r[0] for r in results]

        # Finish dropdown: filtered by manufacturer + material
        wc, params = self.build_filter_universe_where(q, exclude="finish")
        sql = f"SELECT DISTINCT finish FROM filaments {wc} ORDER BY finish"
        cur.execute(sql, params)
        results = cur.fetchall()
        if (len(results) == 0):
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
        cur.execute("SELECT key, value FROM catalog_metadata")
        return {row[0]: row[1] for row in cur.fetchall()}

CATALOG_DATABASE = None
def get_catalog_database() -> CatalogDatabase:
    """Get the singleton instance of the catalog database."""
    global CATALOG_DATABASE
    if CATALOG_DATABASE is None:
        CATALOG_DATABASE = CatalogDatabase(CatalogDatabase.cache_catalog_database_path())
    return CATALOG_DATABASE
