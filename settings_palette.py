"""Settings palette management for the Spoolman Fusion add-in."""

from palette_base import PaletteBase

SETTINGS_PALETTE_ID = 'SpoolmanDBFilamentSettingsPalette'

class SettingsPalette(PaletteBase):
    """Class representing the settings palette."""
    def __init__(self):
        """Initialize the SettingsPalette instance."""
        super().__init__(
            SETTINGS_PALETTE_ID,
            'palette_settings_title',
            300,
            280,
            'settings_palette.html',
            None
        )
