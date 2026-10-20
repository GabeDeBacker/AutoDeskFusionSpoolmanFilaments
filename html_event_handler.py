"""HTML event handler for the add-in palettes."""

import json
from types import SimpleNamespace
from typing import Callable, Any, Dict
import adsk.core

from catalog_database import get_catalog_database
from common import json_text
from lang import ensure_lang
from app_helpers import get_user_interface

Handler = Callable[[Any], None] # Eventually we should pass the action too, just in case someone wants to handle 2 actions in the same handler
Handlers = Dict[str, Handler]

class HTMLEventHandler(adsk.core.HTMLEventHandler):
    """Handle incoming HTML events for all add-in palettes."""
    def __init__(self,
                 palette_id,
                 handlers: Handlers):
        """Initialize controller with UI-state accessors and normalizer."""
        super().__init__()
        self.handlers = handlers
        self.palette_id = palette_id
        self.catalog_database = get_catalog_database()

    def notify(self, eventArgs):
        """Route a palette action and execute its corresponding operation."""  

        # Convert the incoming data to a JSON object for easier handling
        try:
            json_object = (eventArgs and eventArgs.data and json.loads(eventArgs.data, object_hook=lambda d: SimpleNamespace(**d))) or {}
        except json.JSONDecodeError:
            json_object = {}

        if eventArgs.action == 'request_lang':
            palette = get_user_interface().palettes.itemById(self.palette_id)
            palette.sendInfoToHTML('setLang', json_text({ 'lang': ensure_lang() }))
            return

        # Need to handle the response action appropriately
        if eventArgs.action == 'response':
            return

        if self.handlers is not None:
            handler = self.handlers.get(eventArgs.action)
            if handler:
                handler(json_object)
