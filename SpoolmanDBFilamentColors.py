"""Fusion add-in entrypoint that wires palettes, events, and module services."""

import json
import os
import sys
import traceback
import importlib.util

import adsk.core
import adsk.fusion

from bl_common import addon_dir, json_text, make_file_url
from bl_ui_state import (
    get_saved_filters,
    load_saved_scope,
    load_ui_state,
    normalize_debug_flag,
    save_filters,
    save_scope,
    save_ui_state,
)
from bl_catalog import build_catalog_payload, catalog_update_status_message
from bl_appearance import apply_selection, get_or_create_appearance
from bl_export import export_parent
from bl_debug import DebugController
from SpoolmanDBFilamentColors_i18n import _getText, _ensure_lang

FUSION_API_ERRORS = (RuntimeError, AttributeError, TypeError, ValueError, KeyError, IndexError)


def _load_i18n_symbols():
    """Load i18n helpers with fallback file-based module import."""
    try:
        return _getText, _ensure_lang
    except ImportError:
        pass

    module_name = 'SpoolmanDBFilamentColors_i18n'
    module_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), module_name + '.py')
    module_dir = os.path.dirname(module_path)
    if module_dir and module_dir not in sys.path:
        sys.path.insert(0, module_dir)

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if not spec or not spec.loader:
        raise ImportError('Could not load i18n module: ' + module_path)

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, '_getText'), getattr(mod, '_ensure_lang')


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


_getText, _ensure_lang = _load_i18n_symbols()

PALETTE_ID = 'SpoolmanDBFilamentPalette'
TOOLS_PALETTE_ID = 'SpoolmanDBFilamentToolsPalette'
SETTINGS_PALETTE_ID = 'SpoolmanDBFilamentSettingsPalette'
DEBUG_PALETTE_ID = 'SpoolmanDBFilamentDebugPalette'
CMD_ID = 'SpoolmanDBFilamentColors'
handlers = []
ACTIVE_SCOPE = 'body'
DEBUG = DebugController(load_ui_state, save_ui_state, normalize_debug_flag)


def _create_appearance(design, filament):
    """Call appearance factory with compatibility for older 2-arg signatures."""
    try:
        return get_or_create_appearance(design, filament, _getText)
    except TypeError as exc:
        message = str(exc)
        if not message.startswith('get_or_create_appearance() takes'):
            raise
        return get_or_create_appearance(design, filament)


def _get_palette(ui, palette_id):
    """Return palette by ID from Fusion UI."""
    return ui.palettes.itemById(palette_id)


def _send_to_palette(ui, palette_id, action, data):
    """Send an action payload to a palette when present."""
    palette = _get_palette(ui, palette_id)
    if palette:
        palette.sendInfoToHTML(action, data)


def _send_catalog_to_main_palette(ui, payload):
    """Send catalog payload to the main filament palette."""
    if not isinstance(payload, dict):
        payload = build_catalog_payload(force_refresh=False)
    _send_to_palette(ui, PALETTE_ID, 'catalog', json_text(payload))


def _send_catalog_to_settings_palette(ui, payload):
    """Send catalog payload to the settings palette."""
    if not isinstance(payload, dict):
        payload = build_catalog_payload(force_refresh=False)
    _send_to_palette(ui, SETTINGS_PALETTE_ID, 'catalog', json_text(payload))


def _broadcast_status(ui, message):
    """Broadcast status text to main, tools, and settings palettes."""
    _send_to_palette(ui, PALETTE_ID, 'status', message)
    _send_to_palette(ui, TOOLS_PALETTE_ID, 'status', message)
    _send_to_palette(ui, SETTINGS_PALETTE_ID, 'status', message)


def _broadcast_catalog_status(ui, message):
    """Broadcast catalog refresh status to tools and settings palettes."""
    _send_to_palette(ui, TOOLS_PALETTE_ID, 'status', message)
    _send_to_palette(ui, SETTINGS_PALETTE_ID, 'status', message)


def _push_debug_state(ui):
    """Push latest debug snapshot into the debug palette."""
    DEBUG.push_state(ui, _send_to_palette, DEBUG_PALETTE_ID, json_text)


def _send_debug(ui, message, detail=None):
    """Record and publish a debug log entry."""
    DEBUG.send(ui, message, detail, _send_to_palette, DEBUG_PALETTE_ID, json_text)


def _send_debug_error(ui, message, detail=None):
    """Record and publish a debug error entry."""
    DEBUG.send_error(ui, message, detail, _send_to_palette, DEBUG_PALETTE_ID, json_text)


def _set_debug_mode(ui, enabled):
    """Synchronize debug mode state across palettes and debug visibility."""
    if ui is None:
        return
    flag = bool(enabled)
    _send_to_palette(ui, PALETTE_ID, 'setDebugMode', '1' if flag else '0')
    _send_to_palette(ui, TOOLS_PALETTE_ID, 'setDebugMode', '1' if flag else '0')
    _send_to_palette(ui, SETTINGS_PALETTE_ID, 'setDebugMode', '1' if flag else '0')
    p_debug = _get_palette(ui, DEBUG_PALETTE_ID)
    if p_debug:
        p_debug.isVisible = flag
    if flag:
        _push_debug_state(ui)


def _ensure_palette(ui, palette_id, title, file_name, width, height):
    """Return existing palette or create/configure it with HTML event handler."""
    palette = _get_palette(ui, palette_id)
    if palette:
        try:
            palette.name = title
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        return palette
    file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), file_name)
    palette_path = make_file_url(file_path)
    palette = ui.palettes.add(
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
    handler = PH()
    palette.incomingFromHTML.add(handler)
    handlers.append(handler)
    return palette

def handle_request_catalog(ui, data):
    """Handle the request to fetch the catalog."""
    del data
    payload = build_catalog_payload(force_refresh=False)
    _send_catalog_to_main_palette(ui, payload)
    if DEBUG.get_mode():
        _send_debug(
            ui,
            'request_catalog',
            f"source={payload.get('source') or 'unknown'} "
            f"entries={len(payload.get('entries') or [])}",
        )

def handle_request_lang(ui, data):
    """Handle the request to fetch the language setting."""
    del data
    lang = _ensure_lang()
    _send_to_palette(ui, PALETTE_ID, 'setLang', lang)
    _send_to_palette(ui, TOOLS_PALETTE_ID, 'setLang', lang)
    _send_to_palette(ui, SETTINGS_PALETTE_ID, 'setLang', lang)
    _set_debug_mode(ui, DEBUG.get_mode())
    _send_debug(ui, 'request_lang', f"lang={lang}")

def handle_open_debug_palette(ui, data):
    """Handle the request to open the debug palette."""
    del data
    p_debug = _ensure_palette(
        ui,
        DEBUG_PALETTE_ID,
        'Filaments Debug',
        'palette_debug.html',
        360,
        420,
    )
    p_debug.isVisible = True
    _push_debug_state(ui)

def handle_clear_debug_log(ui, data):
    """Handle the request to clear the debug log."""
    del data
    DEBUG.clear()
    _send_to_palette(ui, DEBUG_PALETTE_ID, 'debug_cleared', '')
    _push_debug_state(ui)

def handle_request_debug_snapshot(ui, data):
    """Handle the request to fetch a debug snapshot."""
    del data
    _push_debug_state(ui)

def handle_open_actions_palette(ui, data):
    """Handle the request to open the actions palette."""
    del data
    p_tools = _ensure_palette(
        ui,
        TOOLS_PALETTE_ID,
        _getText('palette_actions_title'),
        'palette_actions.html',
        360,
        420,
    )
    p_tools.isVisible = True
    _send_to_palette(ui, TOOLS_PALETTE_ID, 'setLang', _ensure_lang())

def open_settings_palette(ui, data):
    """Handle the request to open the settings palette."""
    del data
    p_settings = _ensure_palette(
        ui,
        SETTINGS_PALETTE_ID,
        _getText('palette_settings_title'),
        'palette_settings.html',
        300,
        280,
    )
    p_settings.isVisible = True
    _send_to_palette(ui, SETTINGS_PALETTE_ID, 'setLang', _ensure_lang())
    _send_to_palette(
        ui,
        SETTINGS_PALETTE_ID,
        'setDebugMode',
        '1' if DEBUG.get_mode() else '0',
    )

def handle_request_scope(ui, data):
    """Handle the request to fetch the current scope."""
    del data
    _send_to_palette(ui, PALETTE_ID, 'setScope', ACTIVE_SCOPE)
    _send_to_palette(ui, TOOLS_PALETTE_ID, 'setScope', ACTIVE_SCOPE)
    _send_to_palette(ui, SETTINGS_PALETTE_ID, 'setScope', ACTIVE_SCOPE)
    _send_to_palette(ui, DEBUG_PALETTE_ID, 'setScope', ACTIVE_SCOPE)
    _set_debug_mode(ui, DEBUG.get_mode())

def handle_set_debug_mode(ui, data):
    """Handle the request to set the debug mode."""
    enabled = normalize_debug_flag(data)
    DEBUG.save_mode(enabled)
    if enabled:
        _send_debug(ui, 'debug mode enabled', 'debug palette active')
        p_debug = _ensure_palette(
            ui,
            DEBUG_PALETTE_ID,
            'Filaments Debug',
            'palette_debug.html',
            360,
            420,
        )
        p_debug.isVisible = True
    else:
        p_debug = _get_palette(ui, DEBUG_PALETTE_ID)
        if p_debug:
            p_debug.isVisible = False
        _send_debug(ui, 'debug mode disabled', '')
    _set_debug_mode(ui, enabled)
    _push_debug_state(ui)

def handle_set_scope(ui, data):
    """Handle the request to set the current scope."""
    del data
    scope = (data or '').strip()
    if scope in ('body', 'face'):
        global ACTIVE_SCOPE
        ACTIVE_SCOPE = scope
        save_scope(scope)
    _send_to_palette(ui, PALETTE_ID, 'setScope', ACTIVE_SCOPE)
    _send_to_palette(ui, TOOLS_PALETTE_ID, 'setScope', ACTIVE_SCOPE)

def handle_request_filters(ui, data):
    """Handle the request to fetch the current filters."""
    del data
    _send_to_palette(ui, PALETTE_ID, 'setFilters', json_text(get_saved_filters()))

def handle_save_filters(ui, data):
    """Handle the request to save the current filters."""
    del ui
    try:
        payload = json.loads(data or '{}')
    except json.JSONDecodeError:
        payload = {}
    save_filters(payload)

def handle_request_catalog_settings(ui, data):
    """Handle the request to fetch the catalog settings."""
    del data
    payload = build_catalog_payload(force_refresh=False)
    _send_catalog_to_settings_palette(ui, payload)
    if DEBUG.get_mode():
        _send_debug(
            ui,
            'request_catalog_settings',
            f"source={payload.get('source') or 'unknown'} "
            f"entries={len(payload.get('entries') or [])}",
        )

def handle_request_catalog_force(ui, data):
    """Handle the request to force a refresh of the catalog."""
    del data
    payload = build_catalog_payload(force_refresh=True)
    _send_catalog_to_main_palette(ui, payload)
    _broadcast_catalog_status(ui, catalog_update_status_message(payload, _getText))
    if DEBUG.get_mode():
        _send_debug(
            ui,
            'request_catalog_force',
            f"source={payload.get('source') or 'unknown'} "
            f"entries={len(payload.get('entries') or [])}",
        )

def request_catalog_force_settings(ui, data):
    """Handle the request to force a refresh of the catalog for the settings palette."""
    del data
    payload = build_catalog_payload(force_refresh=True)
    _send_catalog_to_settings_palette(ui, payload)
    _send_to_palette(
        ui,
        SETTINGS_PALETTE_ID,
        'status',
        catalog_update_status_message(payload, _getText),
    )
    if DEBUG.get_mode():
        _send_debug(
            ui,
            'request_catalog_force_settings',
            f"source={payload.get('source') or 'unknown'} "
            f"entries={len(payload.get('entries') or [])}",
        )

def handle_apply(ui, data):
    """Handle the request to apply the current filament."""
    app = adsk.core.Application.get()
    sel = app.userInterface.activeSelections.all
    design = adsk.fusion.Design.cast(app.activeProduct)
    filament = json.loads(data)
    appearance = _create_appearance(design, filament)
    msg = (
        apply_selection(appearance, ACTIVE_SCOPE, sel, _getText)
        if appearance
        else _getText('appearance_create_failed')
    )
    _broadcast_status(
        ui,
        f"{_getText('native_tag')} · {filament['material']} · "
        f"{filament['color_name']} - {msg}",
    )
    adsk.core.Application.get().userInterface.activeSelections.all = sel

def handle_response(ui, data):
    """Handle a generic response from the palette."""
    del ui, data


ACTION_HANDLERS = {
    'request_catalog': handle_request_catalog,
    'request_lang': handle_request_lang,
    'open_debug_palette': handle_open_debug_palette,
    'clear_debug_log': handle_clear_debug_log,
    'request_debug_snapshot': handle_request_debug_snapshot,
    'open_actions_palette': handle_open_actions_palette,
    'open_settings_palette': open_settings_palette,
    'request_scope': handle_request_scope,
    'set_debug_mode': handle_set_debug_mode,
    'set_scope': handle_set_scope,
    'request_filters': handle_request_filters,
    'save_filters': handle_save_filters,
    'request_catalog_settings': handle_request_catalog_settings,
    'request_catalog_force': handle_request_catalog_force,
    'request_catalog_force_settings': request_catalog_force_settings,
    'apply': handle_apply,
    'response': handle_response,
}

class PH(adsk.core.HTMLEventHandler):
    """Handle incoming HTML events for all add-in palettes."""

    def notify(self, eventArgs):
        """Route a palette action and execute its corresponding operation."""
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface

            if eventArgs.action in ACTION_HANDLERS:
                ACTION_HANDLERS[eventArgs.action](ui, eventArgs.data)
                return

            if eventArgs.action in (
                'export_parent_f3d',
                'export_parent_3mf',
                'export_parent_bundle',
            ):
                kind = (
                    'f3d'
                    if eventArgs.action == 'export_parent_f3d'
                    else ('3mf' if eventArgs.action == 'export_parent_3mf' else 'bundle')
                )
                _, msg = export_parent(kind, _getText)
                _broadcast_status(ui, msg)
                if DEBUG.get_mode():
                    _send_debug(ui, 'export_parent', f"kind={kind} message={msg}")
                return

            _send_debug_error(ui, 'unhandled palette action', eventArgs.action)

        except FUSION_API_ERRORS:
            tb = traceback.format_exc()
            if DEBUG.get_mode():
                _send_debug_error(ui, 'palette event exception', tb)
            else:
                DEBUG.append_entry('palette event exception', tb, is_error=True)

class ExecuteHandler(adsk.core.CommandEventHandler):
    """Handle execution of the main command by toggling the main palette visibility."""
    def notify(self, _eventArgs):
        """Handles command execution by toggling the main palette visibility."""
        del _eventArgs
        global ACTIVE_SCOPE
        ACTIVE_SCOPE = load_saved_scope()
        ui = adsk.core.Application.get().userInterface
        p_catalog = _get_palette(ui, PALETTE_ID)
        if not p_catalog:
            p_catalog = _ensure_palette(
                ui,
                PALETTE_ID,
                _getText('palette_title'),
                'palette.html',
                520,
                720,
            )

        next_visible = not p_catalog.isVisible
        p_catalog.isVisible = next_visible
        if not next_visible:
            p_tools = _get_palette(ui, TOOLS_PALETTE_ID)
            p_settings = _get_palette(ui, SETTINGS_PALETTE_ID)
            if p_tools:
                p_tools.isVisible = False
            if p_settings:
                p_settings.isVisible = False
        elif DEBUG.get_mode():
            handle_open_debug_palette(ui, None)

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
    app = adsk.core.Application.get()
    ui = app.userInterface
    panel = ui.allToolbarPanels.itemById('SolidModifyPanel')
    if panel:
        existing_control = panel.controls.itemById(CMD_ID)
        if existing_control:
            existing_control.deleteMe()
    command = ui.commandDefinitions.itemById(CMD_ID)
    if command:
        command.deleteMe()
    resource_dir = os.path.join(addon_dir(), 'resources', 'spool')
    command = ui.commandDefinitions.addButtonDefinition(
        CMD_ID,
        _getText('command_name'),
        _getText('command_description'),
        resource_dir
    )
    command_handler = CommandHandler()
    command.toolClipFilename = os.path.join(addon_dir(), 'resources', 'spool', '32x32@2.png')
    command.commandCreated.add(command_handler)
    handlers.append(command_handler)

    if panel and not panel.controls.itemById(CMD_ID):
        c = panel.controls.addCommand(command)
        try:
            c.isPromoted = True
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        try:
            c.isPromotedByDefault = True
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

def stop(_context):
    """Fusion add-in shutdown hook: remove palettes, controls, and command."""
    del _context
    try:
        ui = adsk.core.Application.get().userInterface
        p = ui.palettes.itemById(PALETTE_ID)
        if p:
            p.deleteMe()
        p_tools = ui.palettes.itemById(TOOLS_PALETTE_ID)
        if p_tools:
            p_tools.deleteMe()
        p_settings = ui.palettes.itemById(SETTINGS_PALETTE_ID)
        if p_settings:
            p_settings.deleteMe()
        p_debug = ui.palettes.itemById(DEBUG_PALETTE_ID)
        if p_debug:
            p_debug.deleteMe()
        panel = ui.allToolbarPanels.itemById('SolidModifyPanel')
        if panel:
            c = panel.controls.itemById(CMD_ID)
            if c:
                c.deleteMe()
        d = ui.commandDefinitions.itemById(CMD_ID)
        if d:
            d.deleteMe()
    except (RuntimeError, AttributeError, TypeError, ValueError):
        pass
