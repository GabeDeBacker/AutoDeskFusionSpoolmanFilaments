"""Fusion export helpers for parent archive and 3MF output."""

import os
import re

import adsk.core
import adsk.fusion

FUSION_API_ERRORS = (RuntimeError, AttributeError, TypeError, ValueError)


def safe_doc_name(name):
    """Sanitize a document name for safe filesystem output names."""
    safe_name = (name or 'Filament_Model').strip()
    safe_name = re.sub(r'[\\/:*?"<>|]+', '-', safe_name)
    return safe_name[:80] or 'Filament_Model'


def pick_folder(ui, get_text):
    """Open a folder picker and return selected directory or ``None``."""
    dlg = ui.createFolderDialog()
    dlg.title = get_text('pick_folder_title')
    if dlg.showDialog() != adsk.core.DialogResults.DialogOK:
        return None
    return dlg.folder


def export_f3d_to(design, filename):
    """Export the design root component as an ``.f3d`` archive."""
    mgr = design.exportManager
    opts = mgr.createFusionArchiveExportOptions(filename, design.rootComponent)
    return bool(mgr.execute(opts))


def export_3mf_to(design, filename):
    """Export the design root component as a single ``.3mf`` file."""
    mgr = design.exportManager
    opts = mgr.createC3MFExportOptions(design.rootComponent, filename)
    opts.sendToPrintUtility = False
    try:
        opts.isOneFilePerBody = False
    except FUSION_API_ERRORS:
        pass
    try:
        opts.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
    except FUSION_API_ERRORS:
        pass
    return bool(mgr.execute(opts))


def export_parent(kind='bundle', get_text=None):
    """Run parent export flow and return ``(success, localized_message)``."""
    app = adsk.core.Application.get()
    ui = app.userInterface
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return False, get_text('open_design')

    folder = pick_folder(ui, get_text)
    if not folder:
        return False, get_text('export_cancelled')

    doc = app.activeDocument
    base = safe_doc_name(doc.name if doc else 'Filament_Model')
    f3d = os.path.join(folder, base + '_PARENT.f3d')
    mf3 = os.path.join(folder, base + '_PARENT.3mf')
    done = []
    failed = []

    if kind in ('f3d', 'bundle'):
        try:
            if export_f3d_to(design, f3d):
                done.append('F3D')
            else:
                failed.append('F3D')
        except (RuntimeError, ValueError, OSError) as ex:
            failed.append('F3D: ' + str(ex))

    if kind in ('3mf', 'bundle'):
        try:
            if export_3mf_to(design, mf3):
                done.append('3MF')
            else:
                failed.append('3MF')
        except (RuntimeError, ValueError, OSError) as ex:
            failed.append('3MF: ' + str(ex))

    if kind == 'bundle':
        try:
            with open(
                os.path.join(folder, 'FILAMENT_PARENT_EXPORT_README.txt'),
                'w',
                encoding='utf-8',
            ) as f:
                f.write(get_text('export_readme', base=base))
        except OSError:
            pass

    message = ''
    if done:
        message += get_text('export_done') + ', '.join(done)
    if failed:
        if message:
            message += ' · '
        message += get_text('export_failed') + ' | '.join(failed)
    message += ' · ' + get_text('export_folder', folder=folder)
    return len(done) > 0, message
