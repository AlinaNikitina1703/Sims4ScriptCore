import time

import autonomy.settings
import camera
import services
import sims4
from autonomy.autonomy_component import AutonomyComponent
from autonomy.autonomy_modes import FullAutonomy
from clock import ClockSpeedMode
from date_and_time import TimeSpan

from scripts_core.sc_debugger import debugger
from scripts_core.sc_jobs import distance_to_pos, set_autonomy, create_time_span, doing_nothing
from scripts_core.sc_script_vars import sc_Vars, AutonomyState

logger = sims4.log.Logger('Autonomy')

last_updated_autonomy = time.time()
autonomy_distance_cutoff = 10.0
update_autonomy = 2
sim_delay = create_time_span(minutes=1)

def get_autonomy_distance(sim):
    return distance_to_pos(sim.position, camera._target_position)

def set_autonomy_distance_cutoff(amount):
    global autonomy_distance_cutoff
    autonomy_distance_cutoff = amount

def get_autonomy_distance_cutoff():
    global autonomy_distance_cutoff
    return autonomy_distance_cutoff

def set_update_autonomy(amount):
    global update_autonomy
    update_autonomy = amount

def set_sim_delay(delay: float):
    global sim_delay
    delay = 60.0 * delay
    sim_delay = create_time_span(seconds=int(delay))

def sc_simulate_update(zone):
    if zone.is_zone_running:
        is_paused = services.game_clock_service().clock_speed == ClockSpeedMode.PAUSED
        if not is_paused:
            sc_calculate_autonomy()

def set_idle_autonomy(sim):
    if doing_nothing(sim):
        return autonomy.settings.AutonomyState.FULL
    return autonomy.settings.AutonomyState.LIMITED_ONLY

def sc_calculate_autonomy():
    global last_updated_autonomy, autonomy_distance_cutoff, update_autonomy
    if not services.get_active_sim():
        return
    if time.time() - last_updated_autonomy > update_autonomy:
        last_updated_autonomy = time.time()
        account_data_msg = services.get_persistence_service().get_account_proto_buff()
        options_proto = account_data_msg.gameplay_account_data.gameplay_options
        spawned = list(services.sim_info_manager().instanced_sims_gen())
        spawned.sort(key=lambda sim: get_autonomy_distance(sim))
        for sim in spawned:
            sim.sim_info.focus = False
            if sim == services.get_active_sim() and not options_proto.selected_sim_autonomy_enabled:
                set_autonomy(sim.sim_info, AutonomyState(sc_Vars.SELECTED_SIMS_AUTONOMY))
            elif sim.sim_info.is_selectable and sim != services.get_active_sim() and options_proto.autonomy_level == options_proto.LIMITED:
                set_autonomy(sim.sim_info, AutonomyState(sc_Vars.SELECTED_SIMS_AUTONOMY))
            elif sim.sim_info.routine:
                set_autonomy(sim.sim_info, sim.sim_info.routine_info.autonomy)
            else:
                set_autonomy(sim.sim_info, AutonomyState.FULL)

            if get_autonomy_distance(sim) < 0.1:
                sim.sim_info.focus = True
                set_game_autonomy(sim, autonomy.settings.AutonomyState.FULL)
                continue

            if get_autonomy_distance(sim) < autonomy_distance_cutoff:
                if sim == services.get_active_sim() and not options_proto.selected_sim_autonomy_enabled:
                    set_game_autonomy(sim, autonomy.settings.AutonomyState.LIMITED_ONLY)
                    continue
                elif sim != services.get_active_sim() and sim.sim_info.is_selectable and options_proto.autonomy_level == options_proto.LIMITED:
                    set_game_autonomy(sim, autonomy.settings.AutonomyState.LIMITED_ONLY)
                    continue
                elif sim.sim_info.routine:
                    set_game_autonomy(sim, set_idle_autonomy(sim))
                    continue
                elif sim.sim_info.is_selectable:
                    set_game_autonomy(sim, set_idle_autonomy(sim))
                    continue
                else:
                    set_game_autonomy(sim, set_idle_autonomy(sim))
                    continue

            if sim == services.get_active_sim() and not options_proto.selected_sim_autonomy_enabled:
                set_game_autonomy(sim, autonomy.settings.AutonomyState.LIMITED_ONLY)
                continue
            elif sim.sim_info.is_selectable and options_proto.autonomy_level == options_proto.LIMITED:
                set_game_autonomy(sim, autonomy.settings.AutonomyState.LIMITED_ONLY)
                continue
            elif sim.sim_info.routine:
                set_game_autonomy(sim, autonomy.settings.AutonomyState.LIMITED_ONLY)
                continue
            else:
                set_game_autonomy(sim, autonomy.settings.AutonomyState.DISABLED)
                continue

def set_game_autonomy(sim, autonomy):
    sim.autonomy_settings.set_setting(autonomy, sim.get_autonomy_settings_group())
    sc_Vars.sorted_autonomy_sims.append(sim)

def get_game_autonomy(sim):
    return sim.autonomy_settings.get_setting(autonomy.settings.AutonomyState, sim.get_autonomy_settings_group())

def max_setting(setting, max):
    if setting >= max:
        return max - 1
    return setting

def get_time_until_next_update(self, mode=FullAutonomy):
    global sim_delay
    if self.is_player_active():
        time_to_run_autonomy = self._get_last_user_directed_action_time() + mode.get_autonomy_delay_after_user_interaction()
    elif self._last_autonomy_result_was_none:
        time_to_run_autonomy = self._get_last_no_result_time() + mode.get_no_result_delay_time()
    elif self.owner.has_any_pending_or_running_interactions():
        time_to_run_autonomy = self._get_last_autonomous_action_time() + mode.get_autonomous_delay_time()
    else:
        time_to_run_autonomy = self._get_last_autonomous_action_time() + mode.get_autonomous_update_delay_with_no_primary_sis()
    delta_time = time_to_run_autonomy - services.time_service().sim_now
    if delta_time.in_ticks() <= 0:
        delta_time = create_time_span(minutes=1)
    if delta_time > sim_delay:
        delta_time = sim_delay

    if sc_Vars.DEBUG_AUTONOMY:
        sim = self.owner
        profiler = "Sim: {}\n".format(sim.first_name + " " + sim.last_name)
        profiler = profiler + "_get_last_user_directed_action_time: {}\n".format(self._get_last_user_directed_action_time())
        profiler = profiler + "get_autonomy_delay_after_user_interaction: {}\n".format(mode.get_autonomy_delay_after_user_interaction())
        profiler = profiler + "_get_last_no_result_time: {}\n".format(self._get_last_no_result_time())
        profiler = profiler + "get_no_result_delay_time: {}\n".format(mode.get_no_result_delay_time())
        profiler = profiler + "_get_last_autonomous_action_time: {}\n".format(self._get_last_autonomous_action_time())
        profiler = profiler + "get_autonomous_delay_time: {}\n".format(mode.get_autonomous_delay_time())
        profiler = profiler + "get_autonomous_update_delay_with_no_primary_sis: {}\n".format(mode.get_autonomous_update_delay_with_no_primary_sis())
        profiler = profiler + "delta_time (sim_delay): {} ({})\n".format(delta_time, sim_delay)
        debugger(profiler)

    return delta_time

def _schedule_next_full_autonomy_update(self, delay_in_sim_minutes=None):
    if not self._autonomy_enabled:
        return
    try:
        if delay_in_sim_minutes is None:
            delay_in_sim_minutes = get_time_until_next_update(self)
        logger.assert_log((isinstance(delay_in_sim_minutes, TimeSpan)), 'delay_in_sim_minutes is not a TimeSpan object in _schedule_next_full_autonomy_update()', owner='rez')
        logger.debug('Scheduling next autonomy update for {} for {}', self.owner, delay_in_sim_minutes)
        self._create_full_autonomy_alarm(delay_in_sim_minutes)
    except Exception:
        logger.exception('Exception hit while attempting to schedule FullAutonomy for {}:', self.owner)


AutonomyComponent._schedule_next_full_autonomy_update = _schedule_next_full_autonomy_update
