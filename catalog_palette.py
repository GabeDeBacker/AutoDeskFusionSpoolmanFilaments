"""Catalog palette management for the Fusion add-in."""

from catalog_database import get_catalog_database
from common import json_text
from text_i18n import get_i18n_text
from app_helpers import get_user_interface
from palette_base import PaletteBase
from ui_state import get_saved_filters, save_filters, save_scope, load_saved_scope
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
                'request_scope': self.handle_request_scope,
                'set_scope': self.handle_set_scope,
                'request_filters': self.handle_request_filters,
                'save_filters': self.handle_save_filters,
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

    def handle_request_scope(self, data):
        """Handle the request to fetch the current scope."""
        del data
        self.send_to_palette('setScope', {'scope': load_saved_scope()})

    def handle_set_scope(self, data):
        """Handle the request to set the current scope."""
        if data.scope in ('body', 'face'):
            save_scope(data.scope)

    def handle_request_filters(self, data):
        """Handle the request to fetch the current filters."""
        del data
        self.send_to_palette('setFilters', get_saved_filters())

    def handle_save_filters(self, data):
        """Handle the request to save the current filters."""
        save_filters(data)

    def handle_apply(self, data):
        """Handle the request to apply the current filament."""
        sel = get_user_interface().activeSelections.all
        status_message = apply_selection(data, load_saved_scope(), sel, get_i18n_text)
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
