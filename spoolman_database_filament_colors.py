"""Fusion add-in entrypoint that wires palettes, events, and module services."""

import json
import os
import sys
import traceback

import adsk.core
import adsk.fusion

# Insert module path into the Python search path for imports.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

# pylint: disable-next=wrong-import-position
from common import addon_dir, json_text
# pylint: disable-next=wrong-import-position
from debug import debug as DEBUG
# pylint: disable-next=wrong-import-position
from palette_helpers import ensure_palette, send_to_palette
# pylint: disable-next=wrong-import-position
from app_helpers import get_user_interface
# pylint: disable-next=wrong-import-position
from ui_state import get_saved_filters, load_saved_scope, save_filters, save_scope
# pylint: disable-next=wrong-import-position
from catalog import build_catalog_payload
# pylint: disable-next=wrong-import-position
from appearance import apply_selection
# pylint: disable-next=wrong-import-position
from text_i18n import get_i18n_text
# pylint: disable-next=wrong-import-position
from settings import settings_palette

PALETTE_ID = 'SpoolmanDBFilamentPalette'
CMD_ID = 'SpoolmanDBFilamentColors'
handlers = []
ACTIVE_SCOPE = 'body'

def handle_request_catalog(data):
    """Handle the request to fetch the catalog."""
    del data
    payload = build_catalog_payload(force_refresh=False)
    if not payload:
        payload = build_catalog_payload(force_refresh=True)
    else:
        send_to_palette(PALETTE_ID, 'catalog', json_text(payload))

    if DEBUG.get_mode():
        DEBUG.send(
            "request_catalog",
            f"source={payload.get('source') or 'unknown'} "
            f"entries={len(payload.get('entries') or [])}")

def handle_request_scope(data):
    """Handle the request to fetch the current scope."""
    del data
    send_to_palette(PALETTE_ID, 'setScope', ACTIVE_SCOPE)

def handle_set_scope(data):
    """Handle the request to set the current scope."""
    del data
    scope = (data or '').strip()
    if scope in ('body', 'face'):
        global ACTIVE_SCOPE
        ACTIVE_SCOPE = scope
        save_scope(scope)
    send_to_palette(PALETTE_ID, 'setScope', ACTIVE_SCOPE)

def handle_request_filters(data):
    """Handle the request to fetch the current filters."""
    del data
    send_to_palette(PALETTE_ID, 'setFilters', json_text(get_saved_filters()))

def handle_save_filters(data):
    """Handle the request to save the current filters."""
    try:
        payload = json.loads(data or '{}')
    except json.JSONDecodeError:
        payload = {}
    save_filters(payload)

def handle_apply(data):
    """Handle the request to apply the current filament."""
    sel = get_user_interface().activeSelections.all
    filament = json.loads(data)
    status_message = apply_selection(filament, ACTIVE_SCOPE, sel, get_i18n_text)
    send_to_palette(PALETTE_ID, 'status', status_message)
    get_user_interface().activeSelections.all = sel

def handle_open_debug_palette(data):
    """Handle the request to open the debug palette."""
    del data
    DEBUG.open_palette(True)

def open_settings_palette(data):
    """Handle the request to open the settings palette."""
    del data
    settings_palette.open_palette(True)

ACTION_HANDLERS = {
    'request_catalog': handle_request_catalog,
    'request_scope': handle_request_scope,
    'set_scope': handle_set_scope,
    'request_filters': handle_request_filters,
    'save_filters': handle_save_filters,
    'apply': handle_apply,
    'open_settings_palette': open_settings_palette,
}

class ExecuteHandler(adsk.core.CommandEventHandler):
    """Handle execution of the main command by toggling the main palette visibility."""
    def notify(self, _eventArgs):
        """Handles command execution by toggling the main palette visibility."""
        del _eventArgs
        global ACTIVE_SCOPE
        ACTIVE_SCOPE = load_saved_scope()
        p_catalog = ensure_palette(
            PALETTE_ID,
            get_i18n_text('palette_title'),
            'palette.html',
            520,
            720,
            ACTION_HANDLERS
        )

        next_visible = not p_catalog.isVisible
        p_catalog.isVisible = next_visible
        if not next_visible:
            settings_palette.close_palette()
            DEBUG.close_palette()

class CommandHandler(adsk.core.CommandCreatedEventHandler):
    """Handle Fusion command invocation by toggling palette visibility."""

    def notify(self, _eventArgs):
        """Handles command created event to attach the execute handler to the command."""
        cmd = _eventArgs.command
        on_execute = ExecuteHandler()
        cmd.execute.add(on_execute)
        handlers.append(on_execute)

def run(_context):
    """Fusion add-in startup hook: register command and open the main palette."""
    del _context
    ui = get_user_interface()

    # Create button definition
    command_definition = ui.commandDefinitions.itemById(CMD_ID)
    if command_definition:
        command_definition.deleteMe()
    resource_dir = os.path.join(addon_dir(), 'resources', 'spool')
    command_definition = ui.commandDefinitions.addButtonDefinition(
        CMD_ID,
        get_i18n_text('command_name'),
        get_i18n_text('command_description'),
        resource_dir
    )

    command_handler = CommandHandler()
    command_definition.toolClipFilename = os.path.join(addon_dir(), 'resources', 'spool', '32x32@2.png')
    command_definition.commandCreated.add(command_handler)
    handlers.append(command_handler)

    # Get the Solid workspace
    solid_workspace = ui.workspaces.itemById('FusionSolidEnvironment')
    if not solid_workspace:
        return

    solid_modify_panel = solid_workspace.toolbarPanels.itemById('SolidModifyPanel')
    if not solid_modify_panel:
        return

    solid_modify_controls = solid_modify_panel.controls
    if not solid_modify_controls:
        return

    appearance_control = solid_modify_controls.itemById('AppearanceCommand')

    if appearance_control:
        # Insert after Appearance
        solid_modify_controls.addCommand(command_definition, 'AppearanceCommand', False)
    else:
        # Fallback: append at end
        solid_modify_controls.addCommand(command_definition)

def stop(_context):
    """Fusion add-in shutdown hook: remove palettes, controls, and command."""
    del _context
    try:
        ui = get_user_interface()
        p = ui.palettes.itemById(PALETTE_ID)
        if p:
            p.deleteMe()
        settings_palette.close_palette()
        DEBUG.close_palette()
        panel = ui.allToolbarPanels.itemById('SolidModifyPanel')
        if panel:
            c = panel.controls.itemById(CMD_ID)
            if c:
                c.deleteMe()
        d = ui.commandDefinitions.itemById(CMD_ID)
        if d:
            d.deleteMe()
    except (RuntimeError, AttributeError, TypeError, ValueError):
        DEBUG.append_entry("Error during add-in shutdown", traceback.format_exc(), is_error=True)
