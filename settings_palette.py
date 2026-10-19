"""Settings palette management for the Spoolman Fusion add-in."""

from catalog_database import get_catalog_database
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
            {
                'request_catalog_metadata': self.handle_request_catalog_metadata,
                'refresh_catalog': self.handle_refresh_catalog
             }
        )

    def handle_refresh_catalog(self, data):
        """Handle the request to refresh the catalog."""
        force = bool(data.get('force', False))
        get_catalog_database().refresh_if_needed(Force=force)
        self.send_to_palette('catalog_metadata_refreshed', 'OK')

    def handle_request_catalog_metadata(self, data):
        """Handle the request for catalog metadata."""
        del data
        catalog_metadata = get_catalog_database().get_catalog_metadata()
        self.send_to_palette('catalog_metadata', catalog_metadata)
