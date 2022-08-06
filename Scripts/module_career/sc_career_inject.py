import services
from clock import ClockSpeedMode
from module_career.sc_career_custom import sc_CareerCustom
from scripts_core.sc_inject import safe_inject
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import error_trap
from zone import Zone


@safe_inject(Zone, 'update')
def sc_career_run_zone_update_module(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    try:
        if self.is_zone_running:
            is_paused = services.game_clock_service().clock_speed == ClockSpeedMode.PAUSED
            if not is_paused:
                sc_CareerCustom.init(self)
        else:
            sc_Vars._running = False
            sc_Vars._config_loaded = False
    except BaseException as e:
        error_trap(e)
        pass

    return result