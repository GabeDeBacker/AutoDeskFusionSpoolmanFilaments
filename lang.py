# Language detection and caching for the add-in UI.
import locale
import os
import adsk.core

# Fusion exposes userLanguage as an enum member, not a plain string.
# Map its human-readable enum names and numeric values into the keys used
# by our I18N tables. Unsupported languages fall back to French.
FUSION_LANGUAGE_MAP = {
    'EnglishLanguage': 'en',
    'FrenchLanguage': 'fr',
    3: 'en',
    4: 'fr',
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

    # This should never fail unless the user is using a REALLY old version
    # of Fusion.
    app = adsk.core.Application.get()
    user_lang = app.preferences.generalPreferences.userLanguage
    fused = _to_lang_key(user_lang)
    if fused:
        return fused

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

def ensure_lang():
    """Return cached language key, detecting it on first access."""
    global LANG
    if LANG is None:
        LANG = _detect_lang()
    return LANG
