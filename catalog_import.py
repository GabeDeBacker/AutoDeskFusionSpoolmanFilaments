"""
Module for importing filament catalog data from a JSON file into an SQLite database.

Functions:
- stream_json_entries(path): Streams entries from the JSON catalog file.
- import_spoolman(json_path, db_path): Imports the Spoolman catalog into the specified SQLite database.
"""

import sqlite3
import json
import colorsys
import time

def hex_to_hsv(hex_color):
    """Convert a hex color string to HSV values."""
    hex_color = hex_color.lstrip('#')
    # The value returned from rgb_to_hsv are values between 0 and 1, hence the division by 255.
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h, s, v

def stream_json_array(path):
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

def set_metadata(cur, metadata):
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

def import_spoolman(json_path, db_path):
    """Import the Spoolman filament catalog from a JSON file into an SQLite database."""
    con = sqlite3.connect(db_path)
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
    for entry in stream_json_array(json_path):        
        entry_count += 1

        # Convert first hex color to HSV
        hex_color = entry["color_hex"] or (entry["color_hexes"][0] if entry["color_hexes"] else None)
        h, s, v = hex_to_hsv(hex_color)

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

    set_metadata(con.cursor(), metadata)
    con.commit()
    con.close()

FILAMENT_COLUMNS = [
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

def query_filaments(db_path, q):
    """Query filaments from the database based on the given filters."""
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

    # HSV proximity
    if q["hsvTolerance"] and q["color"]:
        color_h, color_s, color_v = hex_to_hsv(q["color"])
        if (q["hsvTolerance"]["h"] and q["hsvTolerance"]["s"] and q["hsvTolerance"]["v"]):
            where.append("WHERE ABS(hue - ?) <= ?"
                         " AND ABS(saturation - ?) <= ?"
                         " AND ABS(value - ?) <= ?")
            params.append(color_h)
            params.append(q["hsvTolerance"]["h"])
            params.append(color_s)
            params.append(q["hsvTolerance"]["s"])
            params.append(color_v)
            params.append(q["hsvTolerance"]["v"])

    # Build WHERE clause
    where_clause = "WHERE " + " AND ".join(where) if where else ""

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
    con = sqlite3.connect(db_path)
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
    con.close()

    return {
        "total": total,
        "page": page,
        "pageSize": page_size,
        "pages": (total + page_size - 1) // page_size,
        "results": [dict(zip(FILAMENT_COLUMNS, r)) for r in rows]
    }
