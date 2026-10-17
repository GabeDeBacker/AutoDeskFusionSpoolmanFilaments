"""HTML event handler for the add-in palettes."""

import json
from catalog import handle_request_catalog_for_palette
from lang import ensure_lang
from app_helpers import get_user_interface
import adsk.core
from spoolman_database_filament_colors import PALETTE_ID

class HTMLEventHandler(adsk.core.HTMLEventHandler):
    """Handle incoming HTML events for all add-in palettes."""
    def __init__(self, palette_id, handlers):
        """Initialize controller with UI-state accessors and normalizer."""
        super().__init__()
        self.handlers = handlers
        self.palette_id = palette_id

    def notify(self, eventArgs):
        """Route a palette action and execute its corresponding operation."""  

        if eventArgs.action == 'request_lang':
            palette = get_user_interface().palettes.itemById(self.palette_id)
            palette.sendInfoToHTML('setLang', ensure_lang())
            return

        if eventArgs.action == 'request_catalog':
            force_data = json.loads(eventArgs.data)
            if ('force' in force_data and force_data['force']):
                handle_request_catalog_for_palette(self.palette_id, True)
            else:
                handle_request_catalog_for_palette(self.palette_id, False)
            return

        if eventArgs.action == 'response':
            response_data = json.loads(eventArgs.data)
            if 'data' not in response_data:
                raise ValueError(f"Missing 'data' in response: {response_data}")
            data = response_data['data']
            if (data or '') != 'OK':
                raise ValueError(f"Unexpected response data: {response_data}")
            return

        self.handlers[eventArgs.action](eventArgs.data)
