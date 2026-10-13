# BambuLab Fusion Filament Colors

**Langues :** [English](README.md) · [Français](README.fr.md)

Complément open source pour **Autodesk Fusion** permettant d'appliquer rapidement des couleurs de filaments **Bambu Lab** à vos modèles 3D depuis un panneau visuel intégré.

> Projet communautaire non officiel. Ce projet n'est ni affilié, ni approuvé, ni maintenu par Bambu Lab ou Autodesk.

## Fonctionnalités

- Catalogue visuel des filaments Bambu Lab
- Plus de **270 références** réparties dans de nombreuses gammes
- Recherche par nom de couleur ou matière
- Filtres par famille et gamme
- Aperçu visuel des couleurs
- Gestion des matériaux translucides
- Gestion visuelle des gradients et multicolores
- Apparences basées sur des apparences natives Autodesk
- Application à une face, un corps, un composant, une sélection ou tout le modèle visible
- Commande Fusion dédiée
- Raccourci clavier personnalisable, par exemple `⌘B` sur macOS
- Export du modèle complet en `.f3d` et `.3mf`

## Gammes incluses

### PLA
PLA Basic, PLA Lite, PLA Matte, PLA Basic Gradient, PLA Glow, PLA Marble, PLA Aero, PLA Sparkle, PLA Metal, PLA Translucent, PLA Silk+, PLA Silk Multi-Color, PLA Galaxy, PLA Wood, PLA-CF, PLA Tough, PLA Tough+, PLA Pure.

### PETG
PETG Basic, PETG HF, PETG Translucent, PETG-CF.

### Matériaux techniques
ABS, ABS-GF, ASA, ASA Aero, ASA-CF, PC, PC FR, TPU for AMS, PAHT-CF, PA6-GF, PPA-CF, PPS-CF.

### Supports
Support for PLA, Support for PLA/PETG, Support for ABS, Support for PA/PET, PVA.

## Installation

1. Téléchargez ou clonez ce dépôt.
2. Ouvrez Autodesk Fusion.
3. Allez dans `Utilitaires > Scripts et compléments`.
4. Cliquez sur `+`.
5. Choisissez `Script ou complément à partir de l'appareil`.
6. Sélectionnez le dossier du complément.
7. Ouvrez l'onglet **Compléments**.
8. Sélectionnez **Bambu Lab Filaments**.
9. Cliquez sur **Exécuter**.

## Utilisation

1. Sélectionnez une face, un corps ou un composant.
2. Choisissez le niveau d'application dans le panneau.
3. Recherchez un filament.
4. Cliquez sur sa couleur.

Les apparences créées utilisent un nom du type :

```text
Bambu Native | PLA Basic | Red | #C12E1F
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

Le complément crée une commande Fusion nommée `Bambu Lab Filaments`.

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
BambuLab-Fusion-Filament-Colors/
├── BambuLabNativeV10.py
├── BambuLabNativeV10.manifest
├── bambulab_full_catalog.json
├── palette.html
├── README.md
├── README.fr.md
├── LICENSE
└── .gitignore
```

## Catalogue

Les données sont stockées dans `bambulab_full_catalog.json`.

Exemple :

```json
{
  "manufacturer": "Bambu Lab",
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
  "category_i18n": { "en": "PLA", "fr": "PLA" },
  "material_i18n": { "en": "PLA Basic", "fr": "PLA Basic" },
  "color_name_i18n": { "en": "Red", "fr": "Red" },
  "is_multi_color": false,
  "ui_badges": [],
  "search_text": "pla pla basic red"
}
```

Certaines entrées disposent d'un HEX exact ; d'autres utilisent une approximation visuelle lorsqu'une valeur publique fiable n'était pas disponible.

Les champs utiles a l'UI sont maintenant explicites dans le catalogue (`*_i18n`, `is_multi_color`, `ui_badges`, `search_text`) pour pouvoir generer le panneau depuis le JSON sans duplication HTML.

## Compatibilité

- macOS
- Windows
- Autodesk Fusion avec API Python

## Contribuer

Les contributions sont bienvenues : correction de couleurs, nouvelles gammes, améliorations UI, compatibilité Fusion, gestion des matériaux et exports.

```bash
git clone https://github.com/GAb0222/BambuLab-Fusion-Filament-Colors.git
cd BambuLab-Fusion-Filament-Colors
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

- mise à jour automatique du catalogue Bambu Lab ;
- synchronisation avec les profils Bambu Studio ;
- favoris ;
- historique des couleurs utilisées ;
- rendu amélioré Silk / Sparkle / Galaxy ;
- export avancé vers Bambu Studio ;
- palettes personnalisées ;
- support d'autres fabricants.

## Licence

Distribué sous licence **MIT**.

Voir `LICENSE`.

## Auteur

Créé et maintenu par **Gabriel Fourier** ([GAb0222](https://github.com/GAb0222)).

## Marques

**Bambu Lab** est une marque de ses propriétaires respectifs.

**Autodesk** et **Fusion** sont des marques d'Autodesk, Inc.

Ce projet est communautaire, indépendant et non officiel.
