"""Fusion add-in entrypoint that wires palettes, events, and module services."""

import os
import adsk.core

from common import addon_dir
from app_helpers import get_user_interface
from text_i18n import get_i18n_text
from catalog_palette import CatalogPalette

CMD_ID = 'SpoolmanDBFilamentColors'
handlers = []

def get_solid_modify_panel_controls():
    """Get the controls of the Solid Modify panel in the Fusion Solid workspace."""
    # Get the Solid workspace
    solid_workspace = get_user_interface().workspaces.itemById('FusionSolidEnvironment')
    if not solid_workspace:
        return None

    solid_modify_panel = solid_workspace.toolbarPanels.itemById('SolidModifyPanel')
    if not solid_modify_panel:
        return None

    return solid_modify_panel.controls

class ExecuteHandler(adsk.core.CommandEventHandler):
    """Handle execution of the main command by toggling the main palette visibility."""
    def __init__(self):
        super().__init__()
        self.catalog_palette = CatalogPalette()

    def deleteMe(self):
        """Delete the execute handler and close the associated catalog palette."""
        self.catalog_palette.close_palette()
        self.catalog_palette = None

    def notify(self, _eventArgs):
        """Handles command execution by toggling the main palette visibility."""
        del _eventArgs
        self.catalog_palette.open_palette(toggle=True, visible=False)

class CommandHandler(adsk.core.CommandCreatedEventHandler):
    """Handle Fusion command invocation by toggling palette visibility."""

    def deleteMe(self):
        """Delete the command handler."""
        ui = get_user_interface()
        command_definition = ui.commandDefinitions.itemById(CMD_ID)
        if command_definition:
            command_definition.deleteMe()

    def notify(self, _eventArgs):
        """Handles command created event to attach the execute handler to the command."""
        cmd = _eventArgs.command
        on_execute = ExecuteHandler()
        cmd.execute.add(on_execute)
        handlers.append(on_execute)

def run(_context):
    """Fusion add-in startup hook: register command and open the main palette."""
    del _context
    solid_modify_controls = get_solid_modify_panel_controls()
    if not solid_modify_controls:
        return
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

    appearance_control = solid_modify_controls.itemById('AppearanceCommand')

    command_control = solid_modify_controls.itemById(CMD_ID)
    if command_control:
        command_control.deleteMe()

    if appearance_control:
        # Insert after Appearance
        handlers.append(solid_modify_controls.addCommand(command_definition, 'AppearanceCommand', False))
    else:
        # Fallback: append at end
        handlers.append(solid_modify_controls.addCommand(command_definition))

def stop(_context):
    """Fusion add-in shutdown hook: remove palettes, controls, and command."""
    del _context
    for handler in handlers:
        if hasattr(handler, 'deleteMe'):
            handler.deleteMe()
    handlers.clear()
