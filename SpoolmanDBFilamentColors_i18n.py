"""Localized text resources and language detection for the add-in UI."""

import locale
import os
import adsk.core

LANG_DETECT_ERRORS = (RuntimeError, AttributeError, TypeError, ValueError)

# Fusion exposes userLanguage as an enum member, not a plain string.
# Map its human-readable enum names and numeric values into the keys used
# by our I18N tables. Unsupported languages fall back to French.
FUSION_LANGUAGE_MAP = {
    'EnglishLanguage': 'en',
    'FrenchLanguage': 'fr',
    3: 'en',
    4: 'fr',
}

I18N = {
    'en': {
        'apply_all_model_success': 'Applied to {n} visible body(ies) in the model.',
        'apply_all_model_none': 'No visible bodies found.',
        'select_prompt': 'Select a face, body, or component first.',
        'label_face': 'face(s)',
        'label_body': 'body/object(s)',
        'label_component': 'component body(ies)',
        'label_selected_all': 'selected item(s)',
        'label_auto': 'item(s)',
        'apply_scope_success': 'Applied to {n} {label}.',
        'selection_mode_mismatch': 'Selection does not match the chosen mode.',
        'pick_folder_title': 'Choose export folder for the filament model',
        'open_design': 'Open a Fusion design first.',
        'export_cancelled': 'Export canceled.',
        'export_done': 'Export succeeded: ',
        'export_failed': 'Failed: ',
        'export_folder': 'Folder: {folder}',
        'catalog_update_success': 'Catalog update succeeded ({n} entries).',
        'catalog_update_stale': 'Catalog update failed; using cached data ({n} entries).',
        'catalog_update_failed': 'Catalog update failed and no usable data was returned.',
        'catalog_empty': 'Catalog is empty. Check JSON schema or file availability.',
        'catalog_update_request_failed': 'Catalog update request failed.',
        'export_readme': (
            "FILAMENT COLORS / FUSION - PARENT EXPORT\n\n"
            "Project: {base}\n\n"
            "The *_PARENT.f3d file is the native Fusion parent file.\n"
            "The *_PARENT.3mf file contains the root component exported as a single 3MF.\n\n"
            "To test catalog appearances, check they start with:\n"
            "SpoolmanDB Filament |\n"
        ),
        'appearance_name_prefix': 'SpoolmanDB Filament',
        'appearance_create_failed': 'Could not create the appearance.',
        'native_tag': 'SPOOLMANDB',
        'palette_title': 'Filament Colors',
        'palette_actions_title': 'Filament Export',
        'palette_settings_title': 'Filament Settings',
        'command_name': 'SpoolmanDB Filament Colors',
        'command_description': (
            'Filament appearances generated from the SpoolmanDB catalog '
            'using Autodesk library copies. Suggested shortcut: Cmd+B.'
        )
    },
    'fr': {
        'apply_all_model_success': 'Appliqué à {n} corps visibles dans le modèle.',
        'apply_all_model_none': 'Aucun corps visible trouvé.',
        'select_prompt': 'Sélectionnez d’abord une face, un corps ou un composant.',
        'label_face': 'face(s)',
        'label_body': 'corps/objet(s)',
        'label_component': 'corps de composant(s)',
        'label_selected_all': 'élément(s) sélectionné(s)',
        'label_auto': 'élément(s)',
        'apply_scope_success': 'Appliqué à {n} {label}.',
        'selection_mode_mismatch': 'La sélection ne correspond pas au mode choisi.',
        'pick_folder_title': 'Choisir le dossier d’export du modèle filament',
        'open_design': 'Ouvrez d’abord un modèle Fusion.',
        'export_cancelled': 'Export annulé.',
        'export_done': 'Export réussi : ',
        'export_failed': 'Échec : ',
        'export_folder': 'Dossier : {folder}',
        'catalog_update_success': 'Mise à jour du catalogue réussie ({n} entrées).',
        'catalog_update_stale': 'Échec de la mise à jour ; utilisation du cache ({n} entrées).',
        'catalog_update_failed': (
            'Échec de la mise à jour du catalogue et aucune donnée exploitable '
            'n’a été retournée.'
        ),
        'catalog_empty': (
            'Le catalogue est vide. Vérifiez le schéma JSON et la disponibilité '
            'du fichier.'
        ),
        'catalog_update_request_failed': 'La demande de mise à jour du catalogue a échoué.',
        'export_readme': (
            "FILAMENT COLORS / FUSION - EXPORT PARENT\n\n"
            "Projet : {base}\n\n"
            "Le fichier *_PARENT.f3d est le fichier parent Fusion natif.\n"
            "Le fichier *_PARENT.3mf contient le composant racine exporté dans un seul 3MF.\n\n"
            "Pour tester les apparences du catalogue, vérifiez qu’elles "
            "commencent par :\n"
            "SpoolmanDB Filament |\n"
        ),
        'appearance_name_prefix': 'SpoolmanDB Filament',
        'appearance_create_failed': 'Impossible de créer l’apparence.',
        'native_tag': 'SPOOLMANDB',
        'palette_title': 'Couleurs de filaments',
        'palette_actions_title': 'Export des filaments',
        'palette_settings_title': 'Paramètres des filaments',
        'command_name': 'Couleurs de filaments SpoolmanDB',
        'command_description': (
            'Apparences de filaments générées depuis le catalogue SpoolmanDB '
            'via des copies de la bibliothèque Autodesk. Raccourci conseillé '
            ': Cmd+B.'
        )
    }
}


def _to_lang_key(value):
    """Map Fusion language identifiers to supported language keys."""
    if value is None:
        return 'fr'

    if isinstance(value, str):
        name = value.strip()
        if name in FUSION_LANGUAGE_MAP:
            return FUSION_LANGUAGE_MAP[name]
        if name.lower().startswith('en'):
            return 'en'
        if name.lower().startswith('fr'):
            return 'fr'
        return 'fr'

    if isinstance(value, int):
        return FUSION_LANGUAGE_MAP.get(value, 'fr')

    try:
        name = str(value)
    except (TypeError, ValueError):
        return 'fr'

    if name in FUSION_LANGUAGE_MAP:
        return FUSION_LANGUAGE_MAP[name]
    return 'fr'


def _detect_lang():
    """Detect active UI language using override, Fusion settings, or locale."""
    # FILAMENT_LANG is an optional override for the add-in UI language.
    # Supported values are "fr" and "en". If unset, we check the
    # Fusion user language first, then the runtime environment locale, and
    # finally fall back to French.
    override = (os.environ.get('FILAMENT_LANG') or '').strip().lower()
    if override.startswith('fr'):
        return 'fr'
    if override.startswith('en'):
        return 'en'

    try:
        # This should never fail unless the user is using a REALLY old version
        # of Fusion.
        app = adsk.core.Application.get()
        user_lang = app.preferences.generalPreferences.userLanguage
        fused = _to_lang_key(user_lang)
        if fused in I18N:
            return fused
    except LANG_DETECT_ERRORS:
        pass

    # This is set on "some" platforms. so let's try this as a fallback.
    for env_key in ('LANG', 'LC_ALL', 'LC_CTYPE'):
        val = (os.environ.get(env_key) or '').lower()
        if val.startswith('fr'):
            return 'fr'
        if val.startswith('en'):
            return 'en'

    try:
        loc = locale.getlocale()[0] or ''
    except (ValueError, TypeError):
        loc = ''

    if str(loc).lower().startswith('fr'):
        return 'fr'
    if str(loc).lower().startswith('en'):
        return 'en'
    return 'fr'

LANG = None

def _ensure_lang():
    """Return cached language key, detecting it on first access."""
    global LANG
    if LANG is None:
        LANG = _detect_lang()
    return LANG


def _getText(key, **kwargs):
    """Return localized text for ``key`` with optional format kwargs."""
    lang = _ensure_lang()
    table = I18N.get(lang, I18N['en'])
    txt = table.get(key, I18N['en'].get(key, key))
    return txt.format(**kwargs) if kwargs else txt

__all__ = ['_getText', '_ensure_lang']
