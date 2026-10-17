"""Shared file/path/JSON helpers used across add-in modules."""

import json
import os
from pathlib import Path

def addon_dir():
    """Return the absolute path to the add-in directory."""
    return os.path.dirname(os.path.realpath(__file__))

def read_json_file(path):
    """Load and return JSON from ``path`` using UTF-8."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json_file(path, payload):
    """Write ``payload`` to ``path`` as compact UTF-8 JSON."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))

def json_text(payload):
    """Serialize ``payload`` to compact UTF-8 JSON text."""
    return json.dumps(payload, ensure_ascii=False, separators=(',', ':'))

def make_file_url(path):
    """Convert a local filesystem path to a ``file://`` URL."""
    # On Windows, the path comes with backslashes, so we need to replace them
    # with forward slashes for the file URL.
    return Path(path).as_uri()

FUSION_API_ERRORS = (RuntimeError, AttributeError, TypeError, ValueError, KeyError, IndexError)
