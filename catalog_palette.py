"""Catalog palette management for the Fusion add-in."""

import json
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
        self.send_to_palette('setScope', load_saved_scope())

    def handle_set_scope(self, data):
        """Handle the request to set the current scope."""
        scope = (data or '').strip()
        if scope in ('body', 'face'):
            save_scope(scope)

        self.send_to_palette('setScope', scope)

    def handle_request_filters(self, data):
        """Handle the request to fetch the current filters."""
        del data
        self.send_to_palette('setFilters', json_text(get_saved_filters()))

    def handle_save_filters(self, data):
        """Handle the request to save the current filters."""
        try:
            payload = json.loads(data or '{}')
        except json.JSONDecodeError:
            payload = {}
        save_filters(payload)

    def handle_apply(self, data):
        """Handle the request to apply the current filament."""
        sel = get_user_interface().activeSelections.all
        filament = json.loads(data)
        status_message = apply_selection(filament, load_saved_scope(), sel, get_i18n_text)
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
        query = json.loads(data)
        results = self.database.query_filaments(query)
        self.send_to_palette('filament_query_results', json_text(results))

    def handle_get_filter_lists(self, data):
        """Handle the request to get the filter lists."""
        query = json.loads(data)
        results = self.database.get_filter_lists(query)
        self.send_to_palette('filter_lists_results', json_text(results))

    def handle_get_catalog_metadata(self, data):
        """Handle the request to get catalog metadata."""
        del data
        metadata = self.database.get_catalog_metadata()
        self.send_to_palette('catalog_metadata', json_text(metadata))

    def handle_refresh_catalog(self, data):
        """Handle the request to refresh the catalog."""
        force_payload = json.loads(data)
        force = False
        if force_payload and force_payload['force']:
            force = bool(force_payload['force'])
        self.database.refresh_if_needed(Force=force)
        self.send_to_palette('refresh_catalog_complete', 'OK')
