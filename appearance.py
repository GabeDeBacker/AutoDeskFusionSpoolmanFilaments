"""Fusion appearance creation and scope-based application helpers."""
# adsk.fusion only available when Fusion is running
# pylint: disable-next=import-error
import traceback
import adsk.core
import adsk.fusion
from app_helpers import get_design, get_user_interface
from filament_helpers import find_native_base, get_or_create_material, set_native_copied_color
from log import log

FUSION_API_ERRORS = (RuntimeError, AttributeError, TypeError, ValueError, IndexError)

def apply_selection(filament, scope, selection, get_text, apply_material):
    """Apply a filament's appearance and material to the selected entities."""
    active_selection = selection or get_user_interface().activeSelections
    active_scope = scope if scope in ('body', 'face') else 'body'
    count = 0

    if active_selection.count == 0:
        return get_text('select_prompt')

    three_d_printing_material, appearance = get_or_create_material(get_design(), filament, apply_material)
    if appearance is None and three_d_printing_material is None:
        return get_text('material_or_appearance_missing')

    for i in range(active_selection.count):
        entity = active_selection.item(i)
        # This happens when you select a "collection" (such as a group) from the browser window.
        # It's unfortunate that Fusion does not handle this correctly.
        if (entity is None):
            continue

        if active_scope == 'face' and isinstance(entity, adsk.fusion.BRepFace):
            if apply_material and three_d_printing_material is not None:
                entity.material = three_d_printing_material
            if appearance is not None:
                entity.appearance = appearance
            count += 1
        if active_scope == 'body' and isinstance(entity, adsk.fusion.BRepBody):
            if apply_material and not entity.isTransient and three_d_printing_material is not None:
                entity.material = three_d_printing_material
            if appearance is not None:
                entity.appearance = appearance
            count += 1

    base_appearance = find_native_base(filament)
    if base_appearance:
        for prop in appearance.appearanceProperties:

            # Skip the color
            if adsk.core.ColorProperty.classType() == prop.classType():
                continue

            if prop and not prop.isReadOnly:
                try:
                    if hasattr(prop, 'hasMultipleValues') and callable(getattr(prop, 'hasMultipleValues')):
                        prop.values = base_appearance.appearanceProperties.itemById(prop.id).values
                    else:
                        prop.value = base_appearance.appearanceProperties.itemById(prop.id).value

                except FUSION_API_ERRORS:
                    log.writeError(f"Failed to set property {prop.id} from base appearance. {traceback.format_exc()}")

    set_native_copied_color(appearance, filament)

    if count:
        labels = {
            'face': get_text('label_face'),
            'body': get_text('label_body'),
        }
        return get_text(
            'apply_scope_success',
            n=count,
            label=labels.get(active_scope, get_text('label_body')),
        )
    return get_text('selection_mode_mismatch')
