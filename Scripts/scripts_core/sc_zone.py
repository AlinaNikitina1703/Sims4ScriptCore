import services
from clock import ClockSpeedMode
from filters.tunable import TunableSimFilter

from scripts_core.sc_goto_camera import update_camera
from scripts_core.sc_jobs import pause_routine
from scripts_core.sc_main import ScriptCoreMain
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import error_trap


def sc_zone_update(zone):
    try:
        if zone.is_zone_running:
            is_paused = services.game_clock_service().clock_speed == ClockSpeedMode.PAUSED
            if not is_paused:
                if sc_Vars.disable_new_sims:
                    TunableSimFilter._template_chooser = None
                if not pause_routine(sc_Vars.update_speed):
                    ScriptCoreMain.init(zone)
                    ScriptCoreMain.init_routine(zone)
                if sc_Vars.directional_controls:
                    update_camera(services.get_active_sim())
        else:
            sc_Vars._running = False
            sc_Vars._config_loaded = False
    except BaseException as e:
        error_trap(e)
        pass

def sc_zone_on_build_buy_enter_handler(zone):
    try:
        if zone.is_in_build_buy:
            ScriptCoreMain.on_build_buy_enter_handler(zone)
    except BaseException as e:
        error_trap(e)
        pass

def sc_zone_on_build_buy_exit_handler(zone):
    if not zone.is_in_build_buy:
        sc_Vars._running = False
        sc_Vars._config_loaded = False
