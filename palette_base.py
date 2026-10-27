"""Base class for managing palettes in the Fusion add-in."""
import os
import adsk.core
from app_helpers import get_user_interface
from html_event_handler import HTMLEventHandler
from lang import ensure_lang    
from text_i18n import get_i18n_text
from common import json_text, make_file_url
from catalog_database import CatalogDatabase, get_catalog_database

kept_handlers = []
all_palettes = []

class PaletteBase:
    """Base class for managing palettes in the Fusion add-in."""

    def __init__(self, palette_id, title_resource, width, height, html_file, action_handlers):
        """Initialize the PaletteBase instance."""
        handlers = {**action_handlers,
                    'request_lang': self.handle_request_lang, 
                    'refresh_catalog': self.handle_refresh_catalog,
                    'request_catalog_metadata': self.request_catalog_metadata,
                    }

        self.palette = None
        self.palette_id = palette_id
        self.title_resource = get_i18n_text(title_resource)
        self.width = width
        self.height = height
        self.html_file = os.path.join(os.path.dirname(__file__), html_file)
        self.action_handlers = handlers
        self.database : CatalogDatabase = get_catalog_database()
        self.html_event_handler = None
        all_palettes.append(self)

    def handle_request_lang(self, data):
        """Handle the handle_request_lang action from the palette."""
        del data
        if (self.palette):
            self.palette.sendInfoToHTML('setLang', json_text({ 'lang': ensure_lang() }))
        else:
            palette = get_user_interface().palettes.itemById(self.palette_id)
            if palette:
                palette.sendInfoToHTML('setLang', json_text({ 'lang': ensure_lang() }))

    def request_catalog_metadata(self, data):
        """Handle the request to get catalog metadata."""
        del data
        metadata = self.database.get_catalog_metadata()
        self.send_to_all_palettes('catalog_metadata', metadata)

    def handle_refresh_catalog(self, data ):
        """Handle the request to refresh the catalog."""
        self.database.refresh_if_needed(self.handle_status, force=data.force)
        self.send_to_all_palettes('refresh_catalog_complete')

    def handle_status(self, status: str, *args, **kwargs):
        """Handle the request to get the current status."""
        i18n_status = get_i18n_text(status, *args, **kwargs)
        self.send_to_all_palettes('status', {'status': i18n_status})

    def open_palette(self, toggle = False, visible = False):
        """Open the palette, optionally toggling its visibility."""
        self.ensure_palette()
        if toggle:
            self.palette.isVisible = not self.palette.isVisible
        else:
            self.palette.isVisible = visible

    def close_palette(self):
        """Close the palette by deleting it."""
        if self.palette and not self.palette.isNative:
            self.palette.deleteMe()
            self.palette = None

        fusion_palette = get_user_interface().palettes.itemById(self.palette_id)
        if fusion_palette and not fusion_palette.isNative:
            fusion_palette.deleteMe()

        if self.html_event_handler in kept_handlers:
            kept_handlers.remove(self.html_event_handler)
        self.html_event_handler = None

        if self in all_palettes:
            all_palettes.remove(self)

    def ensure_palette(self, force_refresh=False):
        """Return existing palette  or create/configure it with HTML event handler."""
        if not self.palette:
            file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.html_file)
            palette_path = make_file_url(file_path)

            self.palette = get_user_interface().palettes.itemById(self.palette_id)
            if self.palette:
                if not force_refresh:
                    return self.palette

            if self.palette:
                self.palette.deleteMe()
            self.palette = get_user_interface().palettes.add(
                self.palette_id,
                self.title_resource,
                palette_path,
                False,
                True,
                True,
                self.width,
                self.height,
                True,
            )
            self.palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
            self.html_event_handler = HTMLEventHandler(self.palette_id, self.action_handlers)
            self.palette.incomingFromHTML.add(self.html_event_handler)

            # Go ahead and give the language to the palette.
            self.palette.sendInfoToHTML('setLang', ensure_lang())

            kept_handlers.append(self.html_event_handler)
        return self.palette

    def get_palette(self):
        """Return the current palette instance."""
        return self.palette

    def send_to_palette(self, action, data = None):
        """Send an action payload to a palette when present."""
        if self.palette:
            self.palette.sendInfoToHTML(action, json_text(data or {}))

    def send_to_all_palettes(self, action, data = None):
        """Send an action payload to all palettes."""
        for palette in all_palettes:
            if palette:
                palette.send_to_palette(action, data or {})
