# Fusion Filament Colors

**Langues :** [English](README.md) · [Français](README.fr.md)

Complément open source pour **Autodesk Fusion** permettant d'appliquer rapidement des couleurs de filaments à vos modèles 3D depuis un panneau visuel intégré.

> Projet communautaire non officiel. Ce projet n'est affilié à aucun fabricant de filament ni à Autodesk.

## Fonctionnalités

- Catalogue visuel de filaments alimenté par SpoolmanDB
- Plus de **8000 références** réparties entre de nombreux fabricants et gammes
- Recherche par nom de couleur ou matière
- Filtres par fabricant et gamme
- Aperçu visuel des couleurs
- Gestion des matériaux translucides
- Gestion visuelle des gradients et multicolores
- Apparences basées sur des apparences natives Autodesk
- Application à une face, un corps, un composant, une sélection ou tout le modèle visible
- Commande Fusion dédiée
- Raccourci clavier personnalisable, par exemple `⌘B` sur macOS
- Export du modèle complet en `.f3d` et `.3mf`

## Gammes incluses

Les données du catalogue proviennent de [SpoolmanDB par Donkie](https://donkie.github.io/SpoolmanDB/filaments.json). Les fabricants et gammes disponibles suivent donc ce jeu de données amont.

### PLA
PLA Basic, PLA Lite, PLA Matte, PLA Basic Gradient, PLA Glow, PLA Marble, PLA Aero, PLA Sparkle, PLA Metal, PLA Translucent, PLA Silk+, PLA Silk Multi-Color, PLA Galaxy, PLA Wood, PLA-CF, PLA Tough, PLA Tough+, PLA Pure.

### PETG
PETG Basic, PETG HF, PETG Translucent, PETG-CF.

### Matériaux techniques
ABS, ABS-GF, ASA, ASA Aero, ASA-CF, PC, PC FR, TPU for AMS, PAHT-CF, PA6-GF, PPA-CF, PPS-CF.

### Supports
Support pour PLA, Support pour PLA/PETG, Support pour ABS, Support pour PA/PET, PVA.

## Installation

1. Téléchargez ou clonez ce dépôt.
2. Ouvrez Autodesk Fusion.
3. Allez dans `Utilitaires > Scripts et compléments`.
4. Cliquez sur `+`.
5. Choisissez `Script ou complément à partir de l'appareil`.
6. Sélectionnez le dossier du complément.
7. Ouvrez l'onglet **Compléments**.
8. Sélectionnez **Couleurs de filaments SpoolmanDB**.
9. Cliquez sur **Exécuter**.

## Utilisation

1. Sélectionnez une face, un corps ou un composant.
2. Choisissez le niveau d'application dans le panneau.
3. Recherchez un filament.
4. Cliquez sur sa couleur.

Les apparences créées utilisent un nom du type :

```text
SpoolmanDB Filament | Fabricant exemple | PLA Basic | Red | #C12E1F
```

## Niveau d'application

| Mode | Comportement |
| --- | --- |
| Face(s) | Applique uniquement aux faces sélectionnées |
| Corps / objet | Applique au corps sélectionné |
| Composant entier | Applique à tous les corps du composant |
| Toute la sélection | Applique à tous les éléments sélectionnés |
| Tout le modèle visible | Applique à tous les corps visibles |

## Raccourci clavier

Le complément crée une commande Fusion nommée `Couleurs de filaments SpoolmanDB`.

Vous pouvez lui associer un raccourci, par exemple `⌘B` sur macOS.

> L'API Fusion ne permet pas au complément d'imposer automatiquement le raccourci.

## Apparences Autodesk natives

Le complément cherche une apparence compatible dans la bibliothèque Autodesk, la copie dans le design avec `addByCopy()`, puis modifie sa couleur.

Cette approche vise une meilleure compatibilité avec le comportement natif de Fusion.

## Translucence

Les gammes translucides disposent d'un aperçu spécifique dans le panneau.

Exemples :
- PLA Translucent
- PETG Translucent
- PC Transparent

## Export

Le panneau propose :

### Fusion Archive
```text
Projet_PARENT.f3d
```

### 3MF
```text
Projet_PARENT.3mf
```

Le composant racine est exporté dans un seul fichier 3MF avec l'exporteur natif de Fusion.

## À propos du STL

Le STL est adapté au maillage géométrique, mais pas au transport fiable des apparences et couleurs.

Pour conserver davantage d'informations du modèle, privilégiez `.3mf` ou `.f3d`.

## Structure du projet

```text
Fusion-Filament-Colors/
├── SpoolmanDBFilamentColors.py
├── bl_common.py
├── bl_ui_state.py
├── bl_catalog.py
├── bl_appearance.py
├── bl_export.py
├── bl_debug.py
├── SpoolmanDBFilamentColors.manifest
├── palette.html
├── palette_actions.html
├── palette_settings.html
├── README.md
├── README.fr.md
├── LICENSE
└── .gitignore
```

`SpoolmanDBFilamentColors.py` sert désormais de point d'entrée Fusion et de coordinateur d'événements, tandis que la logique catalogue, debug, état UI, apparences et export est répartie dans des modules dédiés pour simplifier la maintenance.

## Catalogue

Au premier lancement, le complément télécharge `https://donkie.github.io/SpoolmanDB/filaments.json`, normalise les données pour le panneau, puis les stocke localement dans `filament_catalog_cache.json`.

Le cache est mis à jour automatiquement au maximum une fois tous les 7 jours. Si la mise à jour échoue (hors ligne/erreur réseau), le complément continue d'utiliser le cache existant.

Le complément inclut un panneau dédié **Paramètres des filaments** avec un bouton **Mettre à jour le catalogue** pour forcer une mise à jour distante à la demande.

Exemple :

```json
{
  "manufacturer": "Fabricant exemple",
  "category": "PLA",
  "material": "PLA Basic",
  "color_name": "Red",
  "hex": "#C12E1F",
  "hexes": ["#C12E1F"],
  "finish": "standard",
  "translucent": false,
  "opacity": 1.0,
  "roughness": 0.44,
  "hex_quality": "exact",
  "search_text": "pla pla basic red"
}
```

Certaines entrées disposent d'un HEX exact ; d'autres utilisent une approximation visuelle lorsqu'une valeur publique fiable n'était pas disponible.

La charge utile normalisée ne conserve que les champs nécessaires à la reconstruction de l'état UI ; les valeurs purement de présentation sont dérivées côté panneau afin de réduire l'empreinte mémoire.

Le complément utilise désormais trois panneaux :
- **Couleurs de filaments** : navigation dans le catalogue et application des couleurs en cliquant les pastilles, avec tri par nom ou spectre de couleur, filtrage par proximité chromatique et sélecteur de portée d'application directement dans le panneau principal.
- **Export des filaments** : actions d'export (ouvert depuis le panneau Couleurs).
- **Paramètres des filaments** : mise à jour du catalogue et contrôles globaux du complément (ouvert depuis le panneau Couleurs).

## Compatibilité

- macOS
- Windows
- Autodesk Fusion avec API Python

## Contribuer

Les contributions sont bienvenues : correction de couleurs, nouvelles gammes, améliorations UI, compatibilité Fusion, gestion des matériaux et exports.

```bash
git clone <url-de-votre-repo>.git
cd Fusion-Filament-Colors
git checkout -b feature/ma-modification
```

Puis ouvrez une Pull Request.

## Signaler un bug

Indiquez si possible :
- version de Fusion ;
- macOS ou Windows ;
- filament concerné ;
- étapes de reproduction ;
- capture d'écran ;
- message d'erreur.

## Roadmap

- amélioration des contrôles de mise à jour du catalogue distant ;
- synchronisation avec les profils de slicer ;
- favoris ;
- historique des couleurs utilisées ;
- rendu amélioré Silk / Sparkle / Galaxy ;
- export avancé vers les slicers ;
- palettes personnalisées ;
- métadonnées enrichies spécifiques aux fabricants.

## Licence

Distribué sous licence **MIT**.

Voir `LICENSE`.

## Auteur

Créé et maintenu par **Gabriel Fourier** ([GAb0222](https://github.com/GAb0222)).

## Marques

Les marques de filaments sont des marques déposées de leurs propriétaires respectifs.

**Autodesk** et **Fusion** sont des marques d'Autodesk, Inc.

Ce projet est communautaire, indépendant et non officiel.

## Attribution des données

Les données du catalogue de filaments sont fournies par **SpoolmanDB**, maintenu par **Donkie** :
- https://donkie.github.io/SpoolmanDB/
- https://donkie.github.io/SpoolmanDB/filaments.json

Ce complément consomme, met en cache et affiche ces données amont ; il ne revendique pas la paternité du jeu de données du catalogue.
