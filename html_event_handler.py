"""HTML event handler for the add-in palettes."""

import json
from types import SimpleNamespace
from typing import Callable, Any, Dict
import adsk.core
from log import log

Handler = Callable[[Any], None]
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

    def notify(self, eventArgs):
        """Route a palette action and execute its corresponding operation."""  

        # Convert the incoming data to a JSON object for easier handling
        try:
            json_object = (eventArgs and eventArgs.data and json.loads(eventArgs.data, object_hook=lambda d: SimpleNamespace(**d))) or {}
        except json.JSONDecodeError:
            log.writeError("Failed to decode JSON from event data: {}", eventArgs.data)
            json_object = {}

        # Need to handle the response action appropriately
        if eventArgs.action == 'response':
            return

        if self.handlers is not None:
            handler = self.handlers.get(eventArgs.action)
            if handler:
                try:
                    handler(json_object)
                except Exception as e:
                    log.writeError("Error handling action '{}': {}", eventArgs.action, str(e))
