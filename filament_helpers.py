"""Helper functions for managing filament appearances in Fusion 360."""
import os
import shutil
import adsk.core
from app_helpers import get_application
from common import FUSION_API_ERRORS
from text_i18n import get_i18n_text

def color_from_hex(hex_value, alpha=255):
    """Create a Fusion ``Color`` from a ``#RRGGBB`` string."""
    h = hex_value.lstrip('#')
    return adsk.core.Color.create(int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)

def find_native_base(translucent=False):
    """Find a suitable native Autodesk base appearance for copy/recolor."""
    app = get_application()
    libs = app.materialLibraries
    candidates = []

    for i in range(libs.count):
        try:
            lib = libs.item(i)
            native_score = 0 if getattr(lib, 'isNative', False) else 1
            for j in range(lib.appearances.count):
                try:
                    appearance = lib.appearances.item(j)
                    props = appearance.appearanceProperties
                    if not props:
                        continue

                    if translucent:
                        if props.itemById('transparent_color'):
                            name = (appearance.name or '').lower()
                            name_score = (
                                0
                                if any(
                                    k in name for k in ('glass', 'clear', 'transparent', 'plastic')
                                )
                                else 1
                            )
                            candidates.append((native_score, name_score, appearance))
                    else:
                        if props.itemById('opaque_albedo'):
                            name = (appearance.name or '').lower()
                            good = any(k in name for k in ('plastic', 'generic', 'smooth', 'matte'))
                            bad = any(
                                k in name
                                for k in (
                                    'wood',
                                    'oak',
                                    'walnut',
                                    'stone',
                                    'brick',
                                    'fabric',
                                    'leather',
                                    'marble',
                                )
                            )
                            name_score = 0 if good and not bad else (2 if bad else 1)
                            candidates.append((native_score, name_score, appearance))
                except FUSION_API_ERRORS:
                    pass
        except FUSION_API_ERRORS:
            pass

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[0], x[1]))
    return candidates[0][2]

def set_native_copied_color(appearance, filament):
    """Apply filament color/roughness/transparency onto a copied appearance."""
    color = color_from_hex(filament['hex'])
    props = appearance.appearanceProperties

    for pid in ('opaque_albedo', 'transparent_color', 'generic_diffuse'):
        try:
            prop = props.itemById(pid)
            if not prop:
                continue
            try:
                if prop.hasConnectedTexture:
                    prop.hasConnectedTexture = False
            except FUSION_API_ERRORS:
                pass
            if not prop.isReadOnly:
                prop.value = color
        except FUSION_API_ERRORS:
            pass

    try:
        appearance.color = color
    except FUSION_API_ERRORS:
        pass

    roughness = float(filament.get('roughness', 0.44))
    for rid in ('surface_roughness', 'opaque_roughness', 'generic_roughness'):
        try:
            rough_prop = props.itemById(rid)
            if rough_prop and not rough_prop.isReadOnly:
                rough_prop.value = roughness
                break
        except FUSION_API_ERRORS:
            pass

    if filament.get('translucent'):
        opacity = float(filament.get('opacity', 0.45))
        for pid in ('transparency', 'generic_transparency', 'transparent_transparency'):
            try:
                prop = props.itemById(pid)
                if prop and not prop.isReadOnly:
                    prop.value = max(0.0, min(1.0, 1.0 - opacity))
            except FUSION_API_ERRORS:
                pass


def get_or_create_appearance(design, filament):
    """Return an existing or newly created design appearance for a filament."""
    name = get_appearance_name(filament)
    existing = design.appearances.itemByName(name)
    if existing:
        return existing

    base = find_native_base(bool(filament.get('translucent')))
    if not base:
        return None

    try:
        copied = design.appearances.addByCopy(base, name)
        set_native_copied_color(copied, filament)
        return copied
    except FUSION_API_ERRORS:
        return None

def get_appearance_name(filament):
    """Generate a unique appearance name for a filament."""
    manufacturer = str(filament.get('manufacturer') or '').strip()
    if manufacturer:
        return (
            f"{manufacturer} | {filament['material']} | "
            f"{filament['color_name']} | {filament['hex']}"
        )
    else:
        return (
            f"{filament['material']} | "
            f"{filament['color_name']} | {filament['hex']}"
        )

def get_or_create_material(design, filament):
    """Return an existing or newly created design material for a filament."""
    design = adsk.fusion.Design.cast(get_application().activeProduct)
    material_libraries = get_application().materialLibraries
    filament_material_name = f"Plastic/{filament['material']}/{filament['color_name']}"
    three_d_printing_material = design.materials.itemByName(filament_material_name)
    if not three_d_printing_material:
        fusion_library = material_libraries.itemById('C1EEA57C-3F56-45FC-B8CB-A9EC46A9994C')
        if  fusion_library:
            # General Plastic
            plastic = fusion_library.materials.itemById('PrismMaterial-012')
            three_d_printing_material = design.materials.addByCopy(
            plastic,
            filament_material_name)

    appearance = get_or_create_appearance(design, filament)

    return three_d_printing_material, appearance
