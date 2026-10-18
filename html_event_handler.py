"""HTML event handler for the add-in palettes."""

import json
import adsk.core

from catalog_helpers import build_catalog_payload
from catalog_import import import_catalog
from common import addon_dir, json_text
from lang import ensure_lang
from app_helpers import get_user_interface

def handle_request_catalog_for_palette(palette_id, force):
    """Handle the request to fetch the catalog for a specific palette."""
    payload = build_catalog_payload(force)
    if not payload:
        payload = build_catalog_payload(force_refresh=True)
    if payload:
        palette = get_user_interface().palettes.itemById(palette_id)
        if palette:
            palette.sendInfoToHTML('catalog', json_text(payload))

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

        if self.handlers is not None:
            handler = self.handlers.get(eventArgs.action)
            if handler:
                handler(eventArgs.data)
