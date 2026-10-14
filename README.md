# Fusion Filament Colors

**Languages:** [English](README.md) · [Français](README.fr.md)

Open-source **Autodesk Fusion** add-in to quickly apply filament colors to your 3D models from a built-in visual panel.

> Unofficial community project. Not affiliated with, endorsed by, or maintained by any filament manufacturer or Autodesk.

## Features

- Visual filament catalog powered by SpoolmanDB
- **8000+** references across many manufacturers and product lines
- Search by color name or material
- Filters by manufacturer and product line
- Visual color preview
- Translucent material handling
- Visual handling of gradients and multi-colors
- Appearances based on native Autodesk appearances
- Apply to a face, body, component, selection, or the entire visible model
- Dedicated Fusion command
- Customizable keyboard shortcut, e.g. `⌘B` on macOS
- Full model export to `.f3d` and `.3mf`

## Included product lines

Catalog data is sourced from [SpoolmanDB by Donkie](https://donkie.github.io/SpoolmanDB/filaments.json), so available manufacturers and product lines are driven by that upstream dataset.

### PLA
PLA Basic, PLA Lite, PLA Matte, PLA Basic Gradient, PLA Glow, PLA Marble, PLA Aero, PLA Sparkle, PLA Metal, PLA Translucent, PLA Silk+, PLA Silk Multi-Color, PLA Galaxy, PLA Wood, PLA-CF, PLA Tough, PLA Tough+, PLA Pure.

### PETG
PETG Basic, PETG HF, PETG Translucent, PETG-CF.

### Engineering materials
ABS, ABS-GF, ASA, ASA Aero, ASA-CF, PC, PC FR, TPU for AMS, PAHT-CF, PA6-GF, PPA-CF, PPS-CF.

### Supports
Support for PLA, Support for PLA/PETG, Support for ABS, Support for PA/PET, PVA.

## Installation

1. Download or clone this repository.
2. Open Autodesk Fusion.
3. Go to `Utilities > Scripts and Add-Ins`.
4. Click `+`.
5. Choose `Script or add-in from device`.
6. Select the add-in folder.
7. Open the **Add-Ins** tab.
8. Select **SpoolmanDB Filament Colors**.
9. Click **Run**.

## Usage

1. Select a face, body, or component.
2. Choose the application level in the panel.
3. Search for a filament.
4. Click its color.

Created appearances use names like:

```text
SpoolmanDB Filament | Example Manufacturer | PLA Basic | Red | #C12E1F
```

## Application level

| Mode | Behavior |
| --- | --- |
| Face(s) | Applies only to selected faces |
| Body / object | Applies to the selected body |
| Entire component | Applies to all bodies in the component |
| Entire selection | Applies to all selected items |
| Entire visible model | Applies to all visible bodies |

## Keyboard shortcut

The add-in creates a Fusion command named `SpoolmanDB Filament Colors`.

You can assign a shortcut to it, for example `⌘B` on macOS.

> The Fusion API does not allow the add-in to set the shortcut automatically.

## Autodesk appearance strategy

The add-in finds a compatible appearance in the Autodesk library, copies it into the design with `addByCopy()`, then updates its color.

This approach aims for better compatibility with Fusion’s native behavior.

## Translucency

Translucent product lines have a dedicated preview in the panel.

Examples:
- PLA Translucent
- PETG Translucent
- PC Transparent

## Export

The panel offers:

### Fusion Archive
```text
Project_PARENT.f3d
```

### 3MF
```text
Project_PARENT.3mf
```

The root component is exported as a single 3MF file using Fusion’s native exporter.

## About STL

STL is fine for geometry meshes, but not reliable for appearances and colors.

Prefer `.3mf` or `.f3d` to keep more model information.

## Project structure

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

`SpoolmanDBFilamentColors.py` now acts as the Fusion entry point and event coordinator, while catalog, debug, UI-state, appearance, and export logic are split into focused modules for easier maintenance.

## Catalog

On first run, the add-in downloads `https://donkie.github.io/SpoolmanDB/filaments.json`, normalizes it to the panel format, and stores a local cache file named `filament_catalog_cache.json`.

The cache refreshes automatically at most once every 7 days. If refresh fails (offline/network error), the add-in keeps using the cached data.

The add-in includes a dedicated **Filament Settings** palette with a manual **Update catalog** button to force a remote refresh on demand.

Example:

```json
{
  "manufacturer": "Example Manufacturer",
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

Some entries have an exact HEX value; others use a visual approximation when no reliable public value was available.

The normalized cache payload keeps only fields needed to reconstruct the UI state, and derives presentation-only values in the palette to reduce memory overhead.

The add-in now uses three palettes:
- **Filament Colors**: catalog browsing and color application by clicking swatches, with sorting by name or color spectrum plus proximity-based color filtering, and the apply scope selector directly in the main palette.
- **Filament Export**: export actions (opened from the Colors palette).
- **Filament Settings**: catalog refresh and add-in-level controls (opened from the Colors palette).

## Compatibility

- macOS
- Windows
- Autodesk Fusion with Python API

## Contributing

Contributions are welcome: color fixes, new product lines, UI improvements, Fusion compatibility, material handling, and exports.

```bash
git clone <your-repository-url>.git
cd Fusion-Filament-Colors
git checkout -b feature/my-change
```

Then open a Pull Request.

## Report a bug

Please include when possible:
- Fusion version
- macOS or Windows
- filament involved
- steps to reproduce
- screenshot
- error message

## Roadmap

- improve remote catalog refresh controls
- sync with slicer profiles
- favorites
- recently used colors
- improved Silk / Sparkle / Galaxy rendering
- advanced export to slicers
- custom palettes
- richer manufacturer-specific metadata

## License

Distributed under the **MIT** license.

See `LICENSE`.

## Author

Created and maintained by **Gabriel Fourier** ([GAb0222](https://github.com/GAb0222)).

## Trademarks

Filament brand names are trademarks of their respective owners.

**Autodesk** and **Fusion** are trademarks of Autodesk, Inc.

This is an independent, unofficial community project.

## Data attribution

Filament catalog data is provided by **SpoolmanDB** maintained by **Donkie**:
- https://donkie.github.io/SpoolmanDB/
- https://donkie.github.io/SpoolmanDB/filaments.json

This add-in consumes, caches, and displays that upstream data; it does not claim authorship of the catalog dataset.
