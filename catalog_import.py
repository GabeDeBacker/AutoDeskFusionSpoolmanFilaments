"""
Module for importing filament catalog data from a JSON file into an SQLite database.

Functions:
- stream_json_entries(path): Streams entries from the JSON catalog file.
- import_catalog(json_path, db_path): Imports the catalog into the specified SQLite database.
"""

import sqlite3
import json
import colorsys

def hex_to_hsv(hex_color):
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360.0, s, v

def stream_json_entries(path):
    decoder = json.JSONDecoder()
    with open(path, "r", encoding="utf8") as f:
        text = f.read()

    # Parse the top-level object
    top = json.loads(text[: text.index('"entries"') + 10])

    # Extract metadata
    metadata = {
        "schema_version": top["schema_version"],
        "catalog_version": top["catalog_version"],
        "generated_epoch": top["generated_epoch"],
        "entry_count": top["entry_count"],
        "source": top["source"]
    }

    # Now stream the entries array
    # Find the start of the array
    start = text.index('"entries"')
    start = text.index('[', start) + 1

    # Stream objects one by one
    buffer = text[start:]
    while True:
        buffer = buffer.lstrip()
        if buffer.startswith(']'):
            break

        try:
            obj, consumed = decoder.raw_decode(buffer)
        except json.JSONDecodeError:
            break

        yield metadata, obj
        buffer = buffer[consumed:].lstrip()
        if buffer.startswith(','):
            buffer = buffer[1:]

def import_catalog(json_path, db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Clear old data
    cur.execute("DELETE FROM catalog_metadata")
    cur.execute("DELETE FROM filaments")

    # Create tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS catalog_metadata (
            schema_version INTEGER,
            catalog_version TEXT,
            generated_epoch INTEGER,
            entry_count INTEGER,
            source TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS filaments (
            id INTEGER PRIMARY KEY,
            manufacturer TEXT,
            material TEXT,
            color_name TEXT,
            hex TEXT,
            hexes TEXT,
            finish TEXT,
            translucent INTEGER,
            opacity REAL,
            roughness REAL,
            hex_quality TEXT,
            search_text TEXT,
            hue REAL,
            saturation REAL,
            value REAL
        );
    """)

    first = True
    for metadata, entry in stream_json_entries(json_path):
        if first:
            cur.execute("DELETE FROM catalog_metadata")
            cur.execute("""
                INSERT INTO catalog_metadata VALUES (?, ?, ?, ?, ?)
            """, (
                metadata["schema_version"],
                metadata["catalog_version"],
                metadata["generated_epoch"],
                metadata["entry_count"],
                metadata["source"]
            ))
            first = False

        h, s, v = hex_to_hsv(entry["hex"])

        cur.execute("""
            INSERT INTO filaments (
                manufacturer, material, color_name, hex, hexes,
                finish, translucent, opacity, roughness,
                search_text, hue, saturation, value
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry["manufacturer"],
            entry["material"],
            entry["color_name"],
            entry.get("hex"),
            json.dumps(entry.get("hexes", [])),
            entry.get("finish"),
            int(entry.get("translucent", False)),
            entry.get("opacity"),
            entry.get("roughness"),
            entry.get("hex_quality"),
            entry.get("search_text"),
            h,
            s,
            v
        ))

        cur.execute("CREATE INDEX idx_filaments_hue ON filaments(hue);")
        cur.execute("CREATE INDEX idx_filaments_saturation ON filaments(saturation);")
        cur.execute("CREATE INDEX idx_filaments_value ON filaments(value);")

    con.commit()
    con.close()
