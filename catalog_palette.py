"""Catalog palette management for the Fusion add-in."""

from catalog_database import get_catalog_database
from text_i18n import get_i18n_text
from app_helpers import get_user_interface
from palette_base import PaletteBase
from ui_state import load_ui_state, save_ui_state
from appearance import apply_selection
from settings_palette import SettingsPalette

PALETTE_ID = 'SpoolmanDBFilamentPalette'

class CatalogPalette(PaletteBase):
    """Class representing the catalog palette in the Fusion add-in."""
    def __init__(self):
        """Initialize the CatalogPalette instance."""
        super().__init__(
            PALETTE_ID,
            'palette_title',
            520,
            720,
            'catalog_palette.html',
            {
                'request_ui_state': self.handle_request_ui_state,
                'save_ui_state': self.handle_save_ui_state,
                'apply': self.handle_apply,
                'open_settings_palette': self.open_settings_palette,
                'query_filaments': self.handle_query_filaments,
                'get_filter_lists': self.handle_get_filter_lists,
                'get_catalog_metadata': self.handle_get_catalog_metadata,
                'refresh_catalog': self.handle_refresh_catalog
            }
        )
        self.database = get_catalog_database()
        self.settings_palette = None

    def handle_request_ui_state(self, data):
        """Handle the request to fetch the current UI state."""
        del data
        self.send_to_palette('set_ui_state', load_ui_state())

    def handle_save_ui_state(self, data):
        """Handle the request to save the current UI state."""
        save_ui_state(data)

    def handle_apply(self, data):
        """Handle the request to apply the current filament."""
        sel = get_user_interface().activeSelections.all
        status_message = apply_selection(data, load_ui_state().get('scope', 'body'), sel, get_i18n_text)
        self.send_to_palette('status', status_message)
        get_user_interface().activeSelections.all = sel

    def open_settings_palette(self, data):
        """Handle the request to open the settings palette."""
        del data
        if self.settings_palette is None:
            self.settings_palette = SettingsPalette()
        self.settings_palette.open_palette(True)

    def handle_query_filaments(self, data):
        """Handle the request to query filaments."""
        results = self.database.query_filaments(data)
        self.send_to_palette('filament_query_results', results)

    def handle_get_filter_lists(self, data):
        """Handle the request to get the filter lists."""
        results = self.database.get_filter_lists(data)
        self.send_to_palette('filter_lists_results', results)

    def handle_get_catalog_metadata(self, data):
        """Handle the request to get catalog metadata."""
        del data
        metadata = self.database.get_catalog_metadata()
        self.send_to_palette('catalog_metadata', metadata)

    def handle_refresh_catalog(self, data ):
        """Handle the request to refresh the catalog."""
        self.database.refresh_if_needed(force=data.force)
        self.send_to_palette('refresh_catalog_complete')
