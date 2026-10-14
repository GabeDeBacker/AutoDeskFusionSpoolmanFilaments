"""Debug log buffering, persistence, and palette publishing utilities."""

import os
import time


class DebugController:
    """Manage debug mode and in-memory log/error snapshots."""

    def __init__(self, load_ui_state, save_ui_state, normalize_debug_flag):
        """Initialize controller with UI-state accessors and normalizer."""
        self._load_ui_state = load_ui_state
        self._save_ui_state = save_ui_state
        self._normalize_debug_flag = normalize_debug_flag
        self.logs = []
        self.errors = []

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

    def push_state(self, ui, send_to_palette, debug_palette_id, json_text):
        """Send the latest debug snapshot to the debug palette."""
        if ui is None:
            return
        payload = {'logs': self.logs[-50:], 'errors': self.errors[-50:]}
        send_to_palette(ui, debug_palette_id, 'debug_snapshot', json_text(payload))

    def send(self, ui, message, detail, send_to_palette, debug_palette_id, json_text):
        """Append a log entry and immediately publish a fresh snapshot."""
        if ui is None:
            return
        self.append_entry(message, detail, is_error=False)
        self.push_state(ui, send_to_palette, debug_palette_id, json_text)

    def send_error(self, ui, message, detail, send_to_palette, debug_palette_id, json_text):
        """Append an error entry and immediately publish a fresh snapshot."""
        if ui is None:
            return
        self.append_entry(message, detail, is_error=True)
        self.push_state(ui, send_to_palette, debug_palette_id, json_text)

    def get_mode(self):
        """Return debug mode from env override or persisted UI state."""
        env_flag = str(os.environ.get('FILAMENT_DEBUG', '')).strip().lower()
        if env_flag in ('1', 'true', 'yes', 'on'):
            return True
        return self._normalize_debug_flag(self._load_ui_state().get('debug', False))

    def save_mode(self, enabled):
        """Persist debug mode and return the normalized stored flag."""
        state = self._load_ui_state()
        state['debug'] = bool(enabled)
        self._save_ui_state(state)
        return state['debug']
