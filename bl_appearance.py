"""Fusion appearance creation and scope-based application helpers."""

import adsk.core
import adsk.fusion

FUSION_API_ERRORS = (RuntimeError, AttributeError, TypeError, ValueError, IndexError)


def color_from_hex(hex_value, alpha=255):
    """Create a Fusion ``Color`` from a ``#RRGGBB`` string."""
    h = hex_value.lstrip('#')
    return adsk.core.Color.create(int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def find_native_base(translucent=False):
    """Find a suitable native Autodesk base appearance for copy/recolor."""
    app = adsk.core.Application.get()
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


def get_or_create_appearance(design, filament, get_text=None):
    """Return an existing or newly created design appearance for a filament."""
    manufacturer = str(filament.get('manufacturer') or '').strip()
    prefix = (
        get_text('appearance_name_prefix')
        if callable(get_text)
        else 'SpoolmanDB Filament'
    )
    if manufacturer:
        name = (
            f"{prefix} | {manufacturer} | {filament['material']} | "
            f"{filament['color_name']} | {filament['hex']}"
        )
    else:
        name = (
            f"{prefix} | {filament['material']} | "
            f"{filament['color_name']} | {filament['hex']}"
        )
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


def all_visible_bodies(design):
    """Collect visible root and occurrence bodies from the active design."""
    bodies = []
    try:
        root = design.rootComponent
        for i in range(root.bRepBodies.count):
            body = root.bRepBodies.item(i)
            try:
                if body.isVisible:
                    bodies.append(body)
            except FUSION_API_ERRORS:
                bodies.append(body)
        occs = root.allOccurrences
        for i in range(occs.count):
            occ = occs.item(i)
            try:
                if not occ.isVisible:
                    continue
            except FUSION_API_ERRORS:
                pass
            comp = occ.component
            for j in range(comp.bRepBodies.count):
                try:
                    body_proxy = occ.bRepBodies.item(j)
                except FUSION_API_ERRORS:
                    body_proxy = None
                if body_proxy:
                    try:
                        if body_proxy.isVisible:
                            bodies.append(body_proxy)
                    except FUSION_API_ERRORS:
                        bodies.append(body_proxy)
    except FUSION_API_ERRORS:
        pass
    return bodies


def apply_selection(appearance, scope='auto', selection=None, get_text=None):
    """Apply an appearance to selected entities according to requested scope."""
    app = adsk.core.Application.get()
    ui = app.userInterface
    design = adsk.fusion.Design.cast(app.activeProduct)
    active_selection = selection or ui.activeSelections
    count = 0

    if scope == 'all_model':
        for body in all_visible_bodies(design):
            try:
                body.appearance = appearance
                count += 1
            except FUSION_API_ERRORS:
                pass
        return (
            get_text('apply_all_model_success', n=count)
            if count
            else get_text('apply_all_model_none')
        )

    if active_selection.count == 0:
        return get_text('select_prompt')

    for i in range(active_selection.count):
        entity = active_selection.item(i)
        try:
            if scope == 'face':
                if isinstance(entity, adsk.fusion.BRepFace):
                    entity.appearance = appearance
                    count += 1
            elif scope == 'body':
                if isinstance(entity, adsk.fusion.BRepBody):
                    entity.appearance = appearance
                    count += 1
                elif isinstance(entity, adsk.fusion.BRepFace):
                    try:
                        entity.body.appearance = appearance
                        count += 1
                    except FUSION_API_ERRORS:
                        pass
            elif scope == 'component':
                if isinstance(entity, adsk.fusion.Occurrence):
                    try:
                        for j in range(entity.bRepBodies.count):
                            entity.bRepBodies.item(j).appearance = appearance
                            count += 1
                    except FUSION_API_ERRORS:
                        comp = entity.component
                        for j in range(comp.bRepBodies.count):
                            comp.bRepBodies.item(j).appearance = appearance
                            count += 1
                elif isinstance(entity, adsk.fusion.Component):
                    for j in range(entity.bRepBodies.count):
                        entity.bRepBodies.item(j).appearance = appearance
                        count += 1
                elif isinstance(entity, adsk.fusion.BRepBody):
                    try:
                        comp = entity.parentComponent
                        for j in range(comp.bRepBodies.count):
                            comp.bRepBodies.item(j).appearance = appearance
                            count += 1
                    except FUSION_API_ERRORS:
                        entity.appearance = appearance
                        count += 1
            elif scope == 'selected_all':
                if isinstance(entity, adsk.fusion.BRepFace):
                    entity.appearance = appearance
                    count += 1
                elif isinstance(entity, adsk.fusion.BRepBody):
                    entity.appearance = appearance
                    count += 1
                elif isinstance(entity, adsk.fusion.Occurrence):
                    for j in range(entity.bRepBodies.count):
                        entity.bRepBodies.item(j).appearance = appearance
                        count += 1
                elif isinstance(entity, adsk.fusion.Component):
                    for j in range(entity.bRepBodies.count):
                        entity.bRepBodies.item(j).appearance = appearance
                        count += 1
            else:
                if isinstance(
                    entity,
                    (adsk.fusion.BRepBody, adsk.fusion.BRepFace, adsk.fusion.Occurrence),
                ):
                    entity.appearance = appearance
                    count += 1
                elif isinstance(entity, adsk.fusion.Component):
                    for j in range(entity.bRepBodies.count):
                        entity.bRepBodies.item(j).appearance = appearance
                        count += 1
        except FUSION_API_ERRORS:
            pass

    labels = {
        'face': get_text('label_face'),
        'body': get_text('label_body'),
        'component': get_text('label_component'),
        'selected_all': get_text('label_selected_all'),
        'auto': get_text('label_auto'),
    }
    if count:
        return get_text(
            'apply_scope_success',
            n=count,
            label=labels.get(scope, get_text('label_auto')),
        )
    return get_text('selection_mode_mismatch')
