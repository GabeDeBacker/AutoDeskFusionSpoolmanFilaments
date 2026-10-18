"""Catalog palette management for the Fusion add-in."""

import json
from common import json_text
from palette_helpers import ensure_palette, send_to_palette
from text_i18n import get_i18n_text
from app_helpers import get_user_interface
from settings_palette import settings_palette
from ui_state import get_saved_filters, save_filters, save_scope, load_saved_scope
from appearance import apply_selection

PALETTE_ID = 'SpoolmanDBFilamentPalette'

def handle_request_scope(data):
    """Handle the request to fetch the current scope."""
    del data
    send_to_palette(PALETTE_ID, 'setScope', load_saved_scope())

def handle_set_scope(data):
    """Handle the request to set the current scope."""
    scope = (data or '').strip()
    if scope in ('body', 'face'):
        save_scope(scope)

    send_to_palette(PALETTE_ID, 'setScope', scope)

def handle_request_filters(data):
    """Handle the request to fetch the current filters."""
    del data
    send_to_palette(PALETTE_ID, 'setFilters', json_text(get_saved_filters()))

def handle_save_filters(data):
    """Handle the request to save the current filters."""
    try:
        payload = json.loads(data or '{}')
    except json.JSONDecodeError:
        payload = {}
    save_filters(payload)

def handle_apply(data):
    """Handle the request to apply the current filament."""
    sel = get_user_interface().activeSelections.all
    filament = json.loads(data)
    status_message = apply_selection(filament, load_saved_scope(), sel, get_i18n_text)
    send_to_palette(PALETTE_ID, 'status', status_message)
    get_user_interface().activeSelections.all = sel

def open_settings_palette(data):
    """Handle the request to open the settings palette."""
    del data
    settings_palette.open_palette(True)

class CatalogPalette:
    """Handle catalog palette interactions."""
    def open_palette(self, toggle = False, visible = False):
        """Handle the request to open the catalog palette."""
        action_handlers = {
            'request_scope': handle_request_scope,
            'set_scope': handle_set_scope,
            'request_filters': handle_request_filters,
            'save_filters': handle_save_filters,
            'apply': handle_apply,
            'open_settings_palette': open_settings_palette,
        }

        p_catalog = ensure_palette(
            PALETTE_ID,
            get_i18n_text('palette_title'),
            'catalog_palette.html',
            520,
            720,
            action_handlers
        )

        if toggle:
            p_catalog.isVisible = not p_catalog.isVisible
        else:
            p_catalog.isVisible = visible

    def close_palette(self):
        """Close the catalog palette by deleting it."""
        palette = get_user_interface().palettes.itemById(PALETTE_ID)
        if palette:
            palette.deleteMe()

catalog_palette = CatalogPalette()
