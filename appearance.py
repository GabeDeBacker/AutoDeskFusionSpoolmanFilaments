"""Fusion appearance creation and scope-based application helpers."""
import adsk.fusion
from app_helpers import get_design, get_user_interface
from filament_helpers import get_or_create_material
FUSION_API_ERRORS = (RuntimeError, AttributeError, TypeError, ValueError, IndexError)

def apply_selection(filament, scope='body', selection=None, get_text=None):
    """Apply a filament's appearance and material to the selected entities."""
    active_selection = selection or get_user_interface().activeSelections
    active_scope = scope if scope in ('body', 'face') else 'body'
    count = 0

    if active_selection.count == 0:
        return get_text('select_prompt')

    three_d_printing_material, appearance = get_or_create_material(get_design(), filament)

    for i in range(active_selection.count):
        entity = active_selection.item(i)
        try:
            if active_scope == 'face' and isinstance(entity, adsk.fusion.BRepFace):
                if three_d_printing_material is not None:
                    entity.material = three_d_printing_material
                entity.appearance = appearance
                count += 1
            if active_scope == 'body' and isinstance(entity, adsk.fusion.BRepBody):
                if three_d_printing_material is not None:
                    entity.material = three_d_printing_material
                entity.appearance = appearance
                count += 1
        except FUSION_API_ERRORS:
            pass

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