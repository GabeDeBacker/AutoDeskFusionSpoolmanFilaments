"""Localized text resources and language detection for the add-in UI."""

from log import log

from lang import ensure_lang

LANG_DETECT_ERRORS = (RuntimeError, AttributeError, TypeError, ValueError)

I18N = {
    'en': {
        'select_prompt': 'Select a face or body first.',
        'label_face': 'face(s)',
        'label_body': 'body/object(s)',
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
        'palette_debug_title': 'Filament Debug',
        'palette_actions_title': 'Filament Export',
        'palette_settings_title': 'Filament Settings',
        'command_name': 'SpoolmanDB Filament Colors',
        'command_description': (
            'Apply filament appearances generated from the SpoolmanDB catalog.'
        ),
        'filament_library': '3D Printing Library',
        'force_refresh': 'Forcing refresh of the catalog.',
        'downloading_spoolman_entries': 'Downloading Spoolman entries',
        'preparing_database_for_import': 'Preparing database for import.',
        'creating_filaments_table': 'Creating filaments table.',
        'importing_spoolman_entries': 'Importing Spoolman entries into database.',
        'creating_indexes_for_filaments_table': 'Creating indexes for filaments table.',
        'setting_catalog_metadata': 'Setting catalog metadata.',
        'catalog_outdated_importing_catalog': 'Catalog outdated, importing catalog.',
        'catalog_metadata_missing_importing_catalog': 'Catalog metadata missing, importing catalog.',
        'finished_importing_filaments': 'Finished importing filaments.',
        'material_or_appearance_missing': 'Material or appearance is missing.',
    },
    'fr': {
        'select_prompt': 'Sélectionnez d’abord une face ou un corps.',
        'label_face': 'face(s)',
        'label_body': 'corps/objet(s)',
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
        'palette_debug_title': 'Debug des filaments',
        'command_name': 'Couleurs de filaments SpoolmanDB',
        'command_description': (
            'Apparences de filaments générées depuis le catalogue SpoolmanDB '
            'via des copies de la bibliothèque Autodesk. Raccourci conseillé '
            ': Cmd+B.'
        ),
        'filament_library': '3D Printing Library',
        'force_refresh': 'Actualisation forcée du catalogue.',
        'downloading_spoolman_entries': 'Téléchargement des entrées Spoolman.',
        'preparing_database_for_import': 'Préparation de la base de données pour l’import.',
        'creating_filaments_table': 'Création de la table des filaments.',
        'importing_spoolman_entries': 'Import des entrées Spoolman dans la base de données.',
        'creating_indexes_for_filaments_table': 'Création des index pour la table des filaments.',
        'setting_catalog_metadata': 'Définition des métadonnées du catalogue.',
        'catalog_outdated_importing_catalog': 'Catalogue obsolète, import du catalogue en cours.',
        'catalog_metadata_missing_importing_catalog': 'Métadonnées du catalogue manquantes, import du catalogue en cours.',
        'finished_importing_filaments': 'Import des filaments terminé.',
        'material_or_appearance_missing': 'Le matériau ou l’apparence est manquant.'
    }
}

def get_i18n_text(key, *args, **kwargs):
    """Return localized text for ``key`` with optional format kwargs."""
    lang = ensure_lang()
    table = I18N.get(lang, I18N['en'])
    txt = table.get(key, I18N['en'].get(key, key))
    if txt is None:
        log.write_error("Missing i18n text for key: {}", key)
        return key
    return txt.format(*args, **kwargs) if args or kwargs else txt

__all__ = ['get_i18n_text', 'ensure_lang']
