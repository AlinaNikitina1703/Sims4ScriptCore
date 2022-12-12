import random

import date_and_time
import gsi_handlers
import services
import sims
from sims.sim_info_types import SimZoneSpinUpAction
from sims.sim_spawner_service import SimSpawnerService, SimSpawnReason

from scripts_core.sc_debugger import debugger
from scripts_core.sc_file import get_config
from scripts_core.sc_jobs import get_number_of_sims, get_venue, get_object_dump
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import error_trap


class sc_SpawnHandler(SimSpawnerService):
    alarm = None
    spawned_sims = []
    time_last_spawned = None

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)

    def _spawn_requested_sim(self, request):
        try:
            now = services.time_service().sim_now
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

            spawn_sim = sims.sim_spawner.SimSpawner.spawn_sim((request._sim_info),
                sim_position=(place_strategy.position),
                sim_location=location,
                sim_spawner_tags=(place_strategy.spawner_tags),
                spawn_point_option=(place_strategy.spawn_point_option),
                saved_spawner_tags=(place_strategy.saved_spawner_tags),
                spawn_action=(place_strategy.spawn_action),
                from_load=(request._from_load),
                spawn_point=(place_strategy.spawn_point),
                spawn_at_lot=(place_strategy.spawn_at_lot),
                use_random_sim_spawner_tag=(place_strategy.use_random_sim_spawner_tag))

            if spawn_sim:
                sim_info = request._sim_info
                sc_SpawnHandler.spawned_sims.append(sim_info)

                if services.get_rabbit_hole_service().will_override_spin_up_action(sim_info.id):
                    services.sim_info_manager().schedule_sim_spin_up_action(sim_info, SimZoneSpinUpAction.NONE)
                else:
                    services.sim_info_manager().schedule_sim_spin_up_action(sim_info, request._spin_up_action)

                spawn_time = get_config("spawn.ini", "spawn", "time")
                spawn_time = 5 if not spawn_time else spawn_time
                sc_SpawnHandler.time_last_spawned = now
                sc_Vars.spawn_cooldown = sc_SpawnHandler.time_last_spawned + date_and_time.create_time_span(minutes=spawn_time)
                self._next_spawn_time = sc_Vars.spawn_cooldown

                message = 'Spawn Start'

                if sc_Vars.ai_function:
                    sc_Vars.ai_function.load_sim_ai(sim_info)
                    sc_Vars.ai_function.update_sim_ai_info(sim_info)

            else:
                if request in self._spawning_requests:
                    self._spawning_requests.remove(request)
                message = 'Spawn Failed'
            if gsi_handlers.sim_spawner_service_log.sim_spawner_service_log_archiver.enabled:
                request.log_to_gsi(message)

        except BaseException as e:
            error_trap(e)

    def submit_request(self, request):
        spawn_sim = True
        sim_info = request._sim_info
        situation_name = str(request.customer_data.situation).lower() if hasattr(request.customer_data, "situation") else "None"
        name = sim_info.first_name + " " + sim_info.last_name
        venue = get_venue()
        sims_on_lot = get_number_of_sims(True)

        if sc_Vars.DISABLE_SPAWNS:
            spawn_sim = False

        if sims_on_lot >= sc_Vars.MAX_SIMS:
            spawn_sim = False

        if request._spawn_reason == SimSpawnReason.ZONE_SITUATION or request._spawn_reason == SimSpawnReason.OPEN_STREETS_SITUATION:
            filters = get_config("spawn.ini", "spawn", "sims")
            if filters is not None:
                if [f for f in filters if f.lower() in name.lower()]:
                    spawn_sim = False

            if not sc_Vars.DISABLE_ROUTINE:
                filters = get_config("spawn.ini", "spawn", "roles")
                if filters is not None:
                    if [f for f in filters if f.lower() in situation_name]:
                        spawn_sim = False

        if not sc_Vars.DISABLE_CULLING and services.time_service().sim_now.hour() < sc_Vars.spawn_time_start \
                and sc_Vars.spawn_time_start > 0 or not sc_Vars.DISABLE_CULLING and \
                services.time_service().sim_now.hour() > sc_Vars.spawn_time_end - 1 and sc_Vars.spawn_time_end > 0:
            spawn_sim = False

        if request._spawn_reason == SimSpawnReason.OPEN_STREETS_SITUATION and sc_Vars.DISABLE_WALKBYS:
            spawn_sim = False

        if request._spawn_reason == SimSpawnReason.OPEN_STREETS_SITUATION and "venue_doctor" in venue:
            spawn_sim = False

        if spawn_sim:
            if request in self._submitted_requests:
                return
            self._submitted_requests.append(request)
            self._submitted_needs_sorting = True
            if gsi_handlers.sim_spawner_service_log.sim_spawner_service_log_archiver.enabled:
                request.log_to_gsi('Request Submitted')

        if sc_Vars.DEBUG_SPAWN:
            status = " Success"
            if not spawn_sim:
                status = " Failed"
            debugger("Request{}: {} Situation: {} Reason: {} Spin Up: {}".format(status, name, situation_name, request._spawn_reason, request._spin_up_action))


SimSpawnerService._spawn_requested_sim = sc_SpawnHandler._spawn_requested_sim
SimSpawnerService.submit_request = sc_SpawnHandler.submit_request
