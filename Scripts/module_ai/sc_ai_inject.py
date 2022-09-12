import services
from zone import Zone

from module_ai.sc_ai_tracker import load_sim_ai, update_sim_ai_info
from scripts_core.sc_inject import safe_inject
from scripts_core.sc_jobs import pause_routine
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import error_trap


@safe_inject(Zone, 'on_loading_screen_animation_finished')
def sc_ai_run_zone_load_module(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    try:
        for sim_info in services.sim_info_manager().get_all():
            load_sim_ai(sim_info)
    except BaseException as e:
        error_trap(e)
        pass

    return result

@safe_inject(Zone, 'update')
def sc_ai_run_zone_update_module(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    try:
        if not sc_Vars._config_loaded and not sc_Vars._running:
            for sim_info in services.sim_info_manager().get_all():
                load_sim_ai(sim_info)
        if not pause_routine(sc_Vars.update_speed):
            sims = [sim_info for sim_info in services.sim_info_manager().get_all() if sim_info.is_instanced()]
            for sim_info in sims:
                update_sim_ai_info(sim_info)
    except BaseException as e:
        error_trap(e)
        pass
    return result