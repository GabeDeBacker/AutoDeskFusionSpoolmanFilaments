"""Helper functions for managing Fusion palettes."""

import os
import adsk.core
from app_helpers import get_user_interface
from common import make_file_url
from html_event_handler import HTMLEventHandler
from lang import ensure_lang

kept_handlers = []

def get_palette(palette_id):
    """Return palette by ID from Fusion UI."""
    return get_user_interface().palettes.itemById(palette_id)

def ensure_palette(palette_id, title, file_name, width, height, handlers, force_refresh=False):
    """Return existing palette or create/configure it with HTML event handler."""
    palette = get_user_interface().palettes.itemById(palette_id)
    file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), file_name)
    palette_path = make_file_url(file_path)

    palette = get_user_interface().palettes.itemById(palette_id)
    if palette:
        if not force_refresh:
            return palette
        palette.close()
        palette.deleteMe()

    palette = get_user_interface().palettes.add(
        palette_id,
        title,
        palette_path,
        False,
        True,
        True,
        width,
        height,
        True,
    )
    palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
    handler = HTMLEventHandler(palette_id, handlers)
    palette.incomingFromHTML.add(handler)

    # Go ahead and give the language to the palette.
    palette.sendInfoToHTML('setLang', ensure_lang())

    kept_handlers.append(handler)
    return palette

def send_to_palette(palette_id, action, data):
    """Send an action payload to a palette when present."""
    palette = get_palette(palette_id)
    if palette:
        palette.sendInfoToHTML(action, data)
