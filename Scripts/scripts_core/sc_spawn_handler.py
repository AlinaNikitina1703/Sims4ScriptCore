import date_and_time
import gsi_handlers
import services
import sims

from scripts_core.sc_jobs import get_number_of_sims, get_venue, debugger, get_filters
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import init_sim, error_trap
from sims.sim_info_types import SimZoneSpinUpAction
from sims.sim_spawner_service import SimSpawnerService, SimSpawnReason


class sc_SpawnHandler(SimSpawnerService):
    alarm = None
    spawned_sims = []
    time_last_spawned = None

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)

    def _spawn_requested_sim(self, request):
        try:
            sims_on_lot = 0
            sim = None
            current_zone = services.current_zone()
            now = services.time_service().sim_now
            if not sc_Vars.spawn_cooldown:
                sc_Vars.spawn_cooldown = date_and_time.create_time_span(minutes=1.0)

            for other_request in tuple(self._submitted_requests):
                if request._is_request_for_same_sim(other_request):
                    self._submitted_requests.remove(other_request)
                    self._spawning_requests.append(other_request)

            for other_request in tuple(self._listening_requests):
                if request._is_request_for_same_sim(other_request):
                    self._listening_requests.remove(other_request)
                    self._spawning_requests.append(other_request)

            place_strategy = request._place_strategy
            location = place_strategy.location
            sim_info = request._sim_info

            if current_zone.is_zone_running:
                if request._spawn_reason != SimSpawnReason.TRAVELING and request._spawn_reason != SimSpawnReason.DEFAULT:
                    debugger("Sim: {} - Spawn".format(sim_info.first_name))
                    if not sc_SpawnHandler.time_last_spawned:
                        sc_SpawnHandler.time_last_spawned = now
                    elif now - sc_SpawnHandler.time_last_spawned < sc_Vars.spawn_cooldown:
                        debugger("Sim: {} - Spawn Filtered".format(sim_info.first_name))
                        return
                    else:
                        sc_Vars.spawn_cooldown = now

                venue = get_venue()
                sims_on_lot = get_number_of_sims()
                if sc_Vars.DISABLE_SPAWNS:
                    debugger("Sim: {} - Spawn Filtered".format(sim_info.first_name))
                    return
                if services.time_service().sim_now.hour() < sc_Vars.spawn_time_start and sc_Vars.spawn_time_start > 0 or \
                        services.time_service().sim_now.hour() > sc_Vars.spawn_time_end - 1 and sc_Vars.spawn_time_end > 0:
                    debugger("Sim: {} - Spawn Filtered".format(sim_info.first_name))
                    return
                if sims_on_lot >= sc_Vars.MAX_SIMS:
                    debugger("Sim: {} - Spawn Filtered".format(sim_info.first_name))
                    return
                if request._spawn_reason == SimSpawnReason.OPEN_STREETS_SITUATION and sc_Vars.DISABLE_WALKBYS:
                    debugger("Sim: {} - Spawn Filtered".format(sim_info.first_name))
                    return
                if request._spawn_reason == SimSpawnReason.OPEN_STREETS_SITUATION and "venue_doctor" in venue:
                    debugger("Sim: {} - Spawn Filtered".format(sim_info.first_name))
                    return
                filters = get_filters("spawn")
                if filters is not None:
                    name = request._sim_info.first_name.lower() + " " + request._sim_info.last_name.lower()
                    if [f for f in filters if f in name]:
                        return

            success = sims.sim_spawner.SimSpawner.spawn_sim((request._sim_info), sim_position=(place_strategy.position),
              sim_location=location,
              sim_spawner_tags=(place_strategy.spawner_tags),
              spawn_point_option=(place_strategy.spawn_point_option),
              saved_spawner_tags=(place_strategy.saved_spawner_tags),
              spawn_action=(place_strategy.spawn_action),
              from_load=(request._from_load),
              spawn_point=(place_strategy.spawn_point),
              spawn_at_lot=(place_strategy.spawn_at_lot),
              use_random_sim_spawner_tag=(place_strategy.use_random_sim_spawner_tag))
            if success:
                sim_info = request._sim_info
                sim = init_sim(sim_info)
                sc_SpawnHandler.spawned_sims.append(sim_info)

                if services.get_rabbit_hole_service().will_override_spin_up_action(sim_info.id):
                    services.sim_info_manager().schedule_sim_spin_up_action(sim_info, SimZoneSpinUpAction.NONE)
                else:
                    services.sim_info_manager().schedule_sim_spin_up_action(sim_info, request._spin_up_action)
                try:
                    self._next_spawn_time = services.time_service().sim_now + sc_Vars.spawn_cooldown
                except:
                    pass
                message = 'Spawn Start'
            else:
                if request in self._spawning_requests:
                    self._spawning_requests.remove(request)
                message = 'Spawn Failed'
            if gsi_handlers.sim_spawner_service_log.sim_spawner_service_log_archiver.enabled:
                request.log_to_gsi(message)

        except BaseException as e:
            error_trap(e)


SimSpawnerService._spawn_requested_sim = sc_SpawnHandler._spawn_requested_sim
