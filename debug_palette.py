"""Debug log buffering, persistence, and palette publishing utilities."""

import json
import os
import time
from app_helpers import get_user_interface
from palette_helpers import ensure_palette, send_to_palette
from text_i18n import get_i18n_text

from ui_state import (
    load_ui_state,
    normalize_debug_flag,
    save_ui_state,
)

DEBUG_PALETTE_ID = 'SpoolmanDBFilamentDebugPalette'

class DebugController:
    """Manage debug mode and in-memory log/error snapshots."""

    def __init__(self):
        """Initialize controller with UI-state accessors and normalizer."""
        self._load_ui_state = load_ui_state
        self._save_ui_state = save_ui_state
        self._normalize_debug_flag = normalize_debug_flag
        self.logs = []
        self.errors = []

    def set_mode(self, enabled):
        """Persist debug mode and return the normalized stored flag."""
        state = self._load_ui_state()
        state['debug'] = bool(enabled)
        self._save_ui_state(state)
        if enabled:
            self.open_palette(visible=True)
        else:
            self.close_palette()
        return state['debug']

    def append_entry(self, message, detail=None, is_error=False):
        """Append one log/error entry and enforce rolling retention limits."""
        entry = {
            'message': str(message),
            'detail': '' if detail is None else str(detail),
            'timestamp': time.time(),
        }
        if is_error:
            self.errors.append(entry)
            self.errors[:] = self.errors[-200:]
        else:
            self.logs.append(entry)
            self.logs[:] = self.logs[-200:]
        return entry

    def clear(self):
        """Clear both normal logs and error logs."""
        self.logs.clear()
        self.errors.clear()
        self.send_to_palette()
        send_to_palette(DEBUG_PALETTE_ID, 'debug_cleared', '')

    def send(self, message, detail):
        """Append a log entry and immediately publish a fresh snapshot."""
        self.append_entry(message, detail, is_error=False)
        self.send_to_palette()

    def send_error(self, message, detail,):
        """Append an error entry and immediately publish a fresh snapshot."""
        self.append_entry(message, detail, is_error=True)
        self.send_to_palette()

    def get_mode(self):
        """Return debug mode from env override or persisted UI state."""
        env_flag = str(os.environ.get('FILAMENT_DEBUG', '')).strip().lower()
        if env_flag in ('1', 'true', 'yes', 'on'):
            return True
        return self._normalize_debug_flag(self._load_ui_state().get('debug', False))

    def send_to_palette(self):
        """Persist debug mode and return the normalized stored flag."""
        if not self.get_mode():
            return

        palette = get_user_interface().palettes.itemById(DEBUG_PALETTE_ID)

        if palette:
            payload = {'logs': self.logs[-50:], 'errors': self.errors[-50:]}
            palette.sendInfoToHTML(
                'debug_snapshot',
                json.dumps(payload, ensure_ascii=False, separators=(',', ':')))

    def set_palette_visibility(self, visible):
        """Set the visibility of the debug palette."""
        palette = get_user_interface().palettes.itemById(DEBUG_PALETTE_ID)
        if palette:
            palette.isVisible = bool(visible)

        if visible:
            self.send_to_palette()

    def open_palette(self, visible = False):
        """Open the debug palette and make it visible."""

        action_handlers = {
            'clear_debug_log': handle_clear_debug_log,
            'request_debug_snapshot': handle_request_debug_snapshot,
            'set_debug_mode': handle_set_debug_mode
        }

        palette = ensure_palette(
            DEBUG_PALETTE_ID,
            get_i18n_text('palette_debug_title'),
            'debug_palette.html',
            360,
            420,
            action_handlers
        )
        palette.isVisible = visible
        if visible:
            self.send_to_palette()

    def close_palette(self):
        """Close the debug palette by deleting it."""
        palette = get_user_interface().palettes.itemById(DEBUG_PALETTE_ID)
        if palette:
            palette.deleteMe()


# This is the shared singleton
debug = DebugController()

def handle_clear_debug_log(data):
    """Handle the request to clear the debug log."""
    del data
    debug.clear()

def handle_request_debug_snapshot(data):
    """Handle the request to fetch a debug snapshot."""
    del data
    debug.send_to_palette()

def handle_set_debug_mode(data):
    """Handle the request to set the debug mode."""
    enabled = normalize_debug_flag(data)
    debug.set_mode(enabled)
    if enabled:
        debug.send('debug mode enabled', 'debug palette active')
