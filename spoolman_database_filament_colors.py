"""Fusion add-in entrypoint that wires palettes, events, and module services."""

import os
import sys
import traceback
import adsk.core

# Insert module path into the Python search path for imports.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from common import addon_dir
from app_helpers import get_user_interface
from text_i18n import get_i18n_text
from settings_palette import settings_palette
from catalog_palette import catalog_palette
from debug_palette import debug as DEBUG

CMD_ID = 'SpoolmanDBFilamentColors'
handlers = []

class ExecuteHandler(adsk.core.CommandEventHandler):
    """Handle execution of the main command by toggling the main palette visibility."""
    def notify(self, _eventArgs):
        """Handles command execution by toggling the main palette visibility."""
        del _eventArgs
        catalog_palette.open_palette(False)

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
    command_definition.toolClipFilename = os.path.join(
        addon_dir(),
        'resources',
        'spool',
        '32x32@2.png')
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

    command_control = solid_modify_controls.itemById(CMD_ID)
    if command_control:
        command_control.deleteMe()

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
        catalog_palette.close_palette()
        settings_palette.close_palette()
        DEBUG.close_palette()
        d = ui.commandDefinitions.itemById(CMD_ID)
        if d:
            d.deleteMe()
    except (RuntimeError, AttributeError, TypeError, ValueError):
        DEBUG.append_entry("Error during add-in shutdown", traceback.format_exc(), is_error=True)
