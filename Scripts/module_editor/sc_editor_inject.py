from zone import Zone

from module_editor.sc_editor_functions import zone_object_override, zone_object_override_save_state
from scripts_core.sc_inject import safe_inject
from scripts_core.sc_util import error_trap


@safe_inject(Zone, 'on_loading_screen_animation_finished')
def sc_edit_zone_load_module(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    try:
        zone_object_override(self)
    except BaseException as e:
        error_trap(e)
        pass

    return result

@safe_inject(Zone, 'on_teardown')
def sc_edit_zone_teardown(original, self, client, *args, **kwargs):
    try:
        zone_object_override_save_state(self)
    except BaseException as e:
        error_trap(e)
        pass

    result = original(self, client, *args, **kwargs)
    return result
