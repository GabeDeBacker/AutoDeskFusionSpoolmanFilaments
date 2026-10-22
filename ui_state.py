"""UI state defaults, validation, and persistence helpers."""

import json
import os
from types import SimpleNamespace
from common import addon_dir, read_json_file, write_json_file

DEFAULT_HUE_TOLERANCE = 10
DEFAULT_SAT_TOLERANCE = 10
DEFAULT_VAL_TOLERANCE = 10
UI_STATE_FILE = 'ui_state.json'

def ui_state_path():
    """Return the persisted UI state file path."""
    return os.path.join(addon_dir(), UI_STATE_FILE)

def default_ui_state():
    """Return the canonical default UI state payload."""
    return {
        'scope': 'body',
        'pageSize': 40,
        'filters': {
            'q': '',
            'cat': '',
            'mat': '',
            'fin': '',
            'sort': 'name',
            'colorFilterOn': False,
            'colorFilterHex': '#4F8CFF',
            'tolerances': {
                'hue': DEFAULT_HUE_TOLERANCE,
                'sat': DEFAULT_SAT_TOLERANCE,
                'val': DEFAULT_VAL_TOLERANCE,
            },
            'translucent': False,
            'glow': False,
        },
    }

def load_ui_state():
    """Load and normalize persisted UI state."""
    try:
        loaded = read_json_file(ui_state_path())
    except (OSError, json.JSONDecodeError):
        return default_ui_state()
    return loaded if isinstance(loaded, dict) else default_ui_state()

def json_dumps_namespace(obj, **json_kwargs):
    """Serialize an object, converting SimpleNamespace instances to dictionaries."""
    def convert(o):
        if isinstance(o, SimpleNamespace):
            return {k: convert(v) for k, v in vars(o).items()}
        if isinstance(o, dict):
            return {k: convert(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [convert(v) for v in o]
        return o

    return json.dumps(convert(obj), **json_kwargs)

def save_ui_state(state):
    """Persist a validated UI state and return the saved payload."""
    persist = json_dumps_namespace(state, indent=2)
    write_json_file(ui_state_path(), json.loads(persist))
