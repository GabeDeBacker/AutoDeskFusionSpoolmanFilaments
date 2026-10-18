"""Settings palette management for the Spoolman Fusion add-in."""

from palette_helpers import ensure_palette
from text_i18n import get_i18n_text
from app_helpers import get_user_interface

SETTINGS_PALETTE_ID = 'SpoolmanDBFilamentSettingsPalette'

class SettingsPalette:
    """Class representing the settings palette."""
    def open_palette(self, visible = False):
        """Handle the request to open the settings palette."""

        p_settings = ensure_palette(
            SETTINGS_PALETTE_ID,
            get_i18n_text('palette_settings_title'),
            'settings_palette.html',
            300,
            280,
            None
        )

        p_settings.isVisible = visible

    def close_palette(self):
        """Close the settings palette by deleting it."""
        palette = get_user_interface().palettes.itemById(SETTINGS_PALETTE_ID)
        if palette:
            palette.deleteMe()

settings_palette = SettingsPalette()
