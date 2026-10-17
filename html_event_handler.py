"""HTML event handler for the add-in palettes."""

import json
from lang import ensure_lang
from app_helpers import get_user_interface
import adsk.core

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

        if eventArgs.action == 'response':
            response_data = json.loads(eventArgs.data)
            if (response_data.data or '') != 'ok':
                raise ValueError(f"Unexpected response data: {response_data}")

        self.handlers[eventArgs.action](eventArgs.data)
