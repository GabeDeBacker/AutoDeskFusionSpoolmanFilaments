# -*- coding: utf-8 -*-
"""Fusion add-in entrypoint that wires palettes, events, and module services."""

import json
import os
import sys
import traceback
import importlib.util

import adsk.core
import adsk.fusion

FUSION_API_ERRORS = (RuntimeError, AttributeError, TypeError, ValueError, KeyError, IndexError)


def _load_i18n_symbols():
    """Load i18n helpers with fallback file-based module import."""
    try:
        from SpoolmanDBFilamentColors_i18n import _getText, _ensure_lang
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

from bl_common import addon_dir, json_text, make_file_url
from bl_ui_state import (
    UI_STATE_FILE,
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


class PH(adsk.core.HTMLEventHandler):
    """Handle incoming HTML events for all add-in palettes."""

    def notify(self, eventArgs):
        """Route a palette action and execute its corresponding operation."""
        try:
            global ACTIVE_SCOPE
            app = adsk.core.Application.get()
            ui = app.userInterface

            if eventArgs.action == 'request_lang':
                lang = _ensure_lang()
                _send_to_palette(ui, PALETTE_ID, 'setLang', lang)
                _send_to_palette(ui, TOOLS_PALETTE_ID, 'setLang', lang)
                _send_to_palette(ui, SETTINGS_PALETTE_ID, 'setLang', lang)
                _set_debug_mode(ui, DEBUG.get_mode())
                _send_debug(ui, 'request_lang', f"lang={lang}")
                adsk.doEvents()
                return

            if eventArgs.action == 'open_debug_palette':
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
                adsk.doEvents()
                return

            if eventArgs.action == 'clear_debug_log':
                DEBUG.clear()
                _send_to_palette(ui, DEBUG_PALETTE_ID, 'debug_cleared', '')
                _push_debug_state(ui)
                adsk.doEvents()
                return

            if eventArgs.action == 'request_debug_snapshot':
                _push_debug_state(ui)
                adsk.doEvents()
                return

            if eventArgs.action == 'open_actions_palette':
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
                adsk.doEvents()
                return

            if eventArgs.action == 'open_settings_palette':
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
                adsk.doEvents()
                return

            if eventArgs.action == 'request_scope':
                _send_to_palette(ui, PALETTE_ID, 'setScope', ACTIVE_SCOPE)
                _send_to_palette(ui, TOOLS_PALETTE_ID, 'setScope', ACTIVE_SCOPE)
                _set_debug_mode(ui, DEBUG.get_mode())
                adsk.doEvents()
                return

            if eventArgs.action == 'set_debug_mode':
                enabled = normalize_debug_flag(eventArgs.data)
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
                adsk.doEvents()
                return

            if eventArgs.action == 'set_scope':
                scope = (eventArgs.data or '').strip()
                if scope in ('body', 'face'):
                    ACTIVE_SCOPE = scope
                    save_scope(scope)
                _send_to_palette(ui, PALETTE_ID, 'setScope', ACTIVE_SCOPE)
                _send_to_palette(ui, TOOLS_PALETTE_ID, 'setScope', ACTIVE_SCOPE)
                adsk.doEvents()
                return

            if eventArgs.action == 'request_filters':
                _send_to_palette(ui, PALETTE_ID, 'setFilters', json_text(get_saved_filters()))
                adsk.doEvents()
                return

            if eventArgs.action == 'save_filters':
                try:
                    payload = json.loads(eventArgs.data or '{}')
                except json.JSONDecodeError:
                    payload = {}
                save_filters(payload)
                adsk.doEvents()
                return

            if eventArgs.action == 'request_catalog':
                payload = build_catalog_payload(force_refresh=False)
                _send_catalog_to_main_palette(ui, payload)
                if DEBUG.get_mode():
                    _send_debug(
                        ui,
                        'request_catalog',
                        f"source={payload.get('source') or 'unknown'} "
                        f"entries={len(payload.get('entries') or [])}",
                    )
                adsk.doEvents()
                return

            if eventArgs.action == 'request_catalog_settings':
                payload = build_catalog_payload(force_refresh=False)
                _send_catalog_to_settings_palette(ui, payload)
                if DEBUG.get_mode():
                    _send_debug(
                        ui,
                        'request_catalog_settings',
                        f"source={payload.get('source') or 'unknown'} "
                        f"entries={len(payload.get('entries') or [])}",
                    )
                adsk.doEvents()
                return

            if eventArgs.action == 'request_catalog_force':
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
                adsk.doEvents()
                return

            if eventArgs.action == 'request_catalog_force_settings':
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
                adsk.doEvents()
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
                adsk.doEvents()
                return

            if eventArgs.action != 'apply':
                return
            sel = adsk.core.Application.get().userInterface.activeSelections.all
            design = adsk.fusion.Design.cast(app.activeProduct)
            filament = json.loads(eventArgs.data)
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
            adsk.doEvents()
            adsk.core.Application.get().userInterface.activeSelections.all = sel
        except FUSION_API_ERRORS:
            tb = traceback.format_exc()
            if DEBUG.get_mode():
                _send_debug_error(ui, 'palette event exception', tb)
            else:
                DEBUG.append_entry('palette event exception', tb, is_error=True)


class CH(adsk.core.CommandCreatedEventHandler):
    """Handle Fusion command invocation by toggling palette visibility."""

    def notify(self, _eventArgs):
        """Open main palette on first call, then toggle it on subsequent calls."""
        del _eventArgs
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
            adsk.doEvents()
        else:
            next_visible = not p_catalog.isVisible
            p_catalog.isVisible = next_visible
            if not next_visible:
                p_tools = _get_palette(ui, TOOLS_PALETTE_ID)
                p_settings = _get_palette(ui, SETTINGS_PALETTE_ID)
                p_debug = _get_palette(ui, DEBUG_PALETTE_ID)
                if p_tools:
                    p_tools.isVisible = False
                if p_settings:
                    p_settings.isVisible = False
                if p_debug:
                    p_debug.isVisible = False


def run(_context):
    """Fusion add-in startup hook: register command and open the main palette."""
    del _context
    global ACTIVE_SCOPE
    ACTIVE_SCOPE = load_saved_scope()
    app = adsk.core.Application.get()
    ui = app.userInterface
    panel = ui.allToolbarPanels.itemById('SolidModifyPanel')
    if panel:
        existing_control = panel.controls.itemById(CMD_ID)
        if existing_control:
            existing_control.deleteMe()
    d = ui.commandDefinitions.itemById(CMD_ID)
    if d:
        d.deleteMe()
    resource_dir = os.path.join(addon_dir(), 'resources', 'spool')
    d = ui.commandDefinitions.addButtonDefinition(
        CMD_ID,
        _getText('command_name'),
        _getText('command_description'),
        resource_dir
    )
    h = CH()
    d.toolClipFilename = os.path.join(addon_dir(), 'resources', 'spool', '32x32@2.png')
    d.commandCreated.add(h)
    handlers.append(h)

    if panel and not panel.controls.itemById(CMD_ID):
        c = panel.controls.addCommand(d)
        try:
            c.isPromoted = True
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        try:
            c.isPromotedByDefault = True
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

    d.execute()


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
