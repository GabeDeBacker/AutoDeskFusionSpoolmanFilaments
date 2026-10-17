"""Settings palette management for the Spoolman Fusion add-in."""

from palette_helpers import ensure_palette, send_to_palette
from text_i18n import get_i18n_text
from app_helpers import get_user_interface
from debug import debug as DEBUG
from catalog import  handle_request_catalog_for_palette

SETTINGS_PALETTE_ID = 'SpoolmanDBFilamentSettingsPalette'

def handle_request_catalog(data):
    """Handle the request to fetch the catalog settings."""
    del data
    handle_request_catalog_for_palette(SETTINGS_PALETTE_ID, force=False)

def handle_open_debug_palette(data):
    """Handle the request to open the debug palette."""
    del data
    DEBUG.open_palette(visible=True)

def handle_set_debug_mode(data):
    """Handle the request to set the debug mode."""
    enabled = (data or '').lower() == '1' or (data or '').lower() == 'true'
    DEBUG.set_mode(enabled)

def handle_request_debug_mode(data):
    """Handle the request to fetch the current debug mode."""
    del data
    send_to_palette(
        SETTINGS_PALETTE_ID,
        'setDebugMode',
        '1' if DEBUG.get_mode() else '0',
    )

def handle_refresh_catalog(data):
    """Handle the request to refresh the catalog."""
    del data
    handle_request_catalog_for_palette(SETTINGS_PALETTE_ID, force=True)

class SettingsPalette:
    """Class representing the settings palette."""
    def open_palette(self, visible = False):
        """Handle the request to open the settings palette."""

        action_handlers = {
            'request_catalog': handle_request_catalog,
            'open_debug_palette': handle_open_debug_palette,
            'set_debug_mode': handle_set_debug_mode,
            'request_debug_mode': handle_request_debug_mode,
            'refresh_catalog': handle_refresh_catalog
        }

        p_settings = ensure_palette(
            SETTINGS_PALETTE_ID,
            get_i18n_text('palette_settings_title'),
            'palette_settings.html',
            300,
            280,
            action_handlers
        )

        p_settings.isVisible = visible
        send_to_palette(
            SETTINGS_PALETTE_ID,
            'setDebugMode',
            '1' if DEBUG.get_mode() else '0',
        )

    def close_palette(self):
        """Close the settings palette by deleting it."""
        palette = get_user_interface().palettes.itemById(SETTINGS_PALETTE_ID)
        if palette:
            palette.deleteMe()

settings_palette = SettingsPalette()
