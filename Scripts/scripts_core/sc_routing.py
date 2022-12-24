import random

import element_utils
import objects
import routing
import services
import sims4
from animation.animation_utils import flush_all_animations
from autonomy.autonomy_modes_tuning import AutonomyModesTuning
from balloon.tunable_balloon import TunableBalloon
from interactions.interaction_finisher import FinishingType
from interactions.utils import route_fail
from interactions.utils.route_fail import RouteFailureTunables
from interactions.utils.routing_constants import TransitionFailureReasons
from objects.object_enums import ResetReason
from postures.posture_graph import EMPTY_PATH_SPEC
from routing import SurfaceIdentifier, SurfaceType
from sims4.math import Location, Transform, Quaternion

from scripts_core.sc_debugger import debugger
from scripts_core.sc_gohere import get_spawn_by_distance
from scripts_core.sc_jobs import distance_to_by_room, make_clean, get_sim_posture_target, remove_sim
from scripts_core.sc_message_box import message_box
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_spawn import sc_Spawn
from scripts_core.sc_util import error_trap

AutonomyModesTuning.LOCKOUT_TIME = 1


class NonRoutableObject:
    def __init__(self, sim, action, object, reason, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.sim = sim
        self.action = action
        self.object = object
        self.reason = reason


ROUTE_FAILURE_OVERRIDE_MAP = None


def add_unroutable_object(sim, target, interaction_id, failure_reason=None):
    if not sc_Vars.non_routable_obj_list:
        sc_Vars.non_routable_obj_list = []
    if not [obj for obj in sc_Vars.non_routable_obj_list if obj.object == target and obj.sim == sim]:
        sc_Vars.non_routable_obj_list.append(NonRoutableObject(sim, interaction_id, target, failure_reason))

def handle_unroutable_object(sim):
    if not sc_Vars.non_routable_obj_list or sim.sim_info.is_selectable:
        return
    if sim.sim_info.routine:
        if "leave" not in sim.sim_info.routine_info.title:
            return
    unroutable_sim = [obj for obj in sc_Vars.non_routable_obj_list if obj.sim == sim]
    if unroutable_sim and len(unroutable_sim) > 2:
        routing_surface = routing.SurfaceIdentifier(services.current_zone_id(), 0, routing.SurfaceType.SURFACETYPE_WORLD)
        location = Location(Transform(services.current_zone().active_lot_arrival_spawn_point._center, Quaternion.ZERO()), routing_surface)
        spawn = sc_Spawn()
        spawn.spawn_sim(sim.sim_info, location, sim.level, False, False)

def _route_failure(sim, interaction, failure_reason, failure_object_id):
    global ROUTE_FAILURE_OVERRIDE_MAP

    if not sim.should_route_fail:
        return
    try:
        add_unroutable_object(interaction.sim, interaction.target, interaction.guid64, failure_reason)

        overrides = None
        if failure_reason is not None:
            if ROUTE_FAILURE_OVERRIDE_MAP is None:
                ROUTE_FAILURE_OVERRIDE_MAP = {
                    TransitionFailureReasons.BLOCKING_OBJECT: RouteFailureTunables.route_fail_overrides_object,
                    TransitionFailureReasons.RESERVATION: RouteFailureTunables.route_fail_overrides_reservation,
                    TransitionFailureReasons.BUILD_BUY: RouteFailureTunables.route_fail_overrides_build,
                    TransitionFailureReasons.NO_DESTINATION_NODE: RouteFailureTunables.route_fail_overrides_no_dest_node,
                    TransitionFailureReasons.NO_PATH_FOUND: RouteFailureTunables.route_fail_overrides_no_path_found,
                    TransitionFailureReasons.NO_VALID_INTERSECTION: RouteFailureTunables.route_fail_overrides_no_valid_intersection,
                    TransitionFailureReasons.NO_GOALS_GENERATED: RouteFailureTunables.route_fail_overrides_no_goals_generated,
                    TransitionFailureReasons.NO_CONNECTIVITY_TO_GOALS: RouteFailureTunables.route_fail_overrides_no_connectivity,
                    TransitionFailureReasons.PATH_PLAN_FAILED: RouteFailureTunables.route_fail_overrides_path_plan_fail,
                    TransitionFailureReasons.GOAL_ON_SLOPE: RouteFailureTunables.route_fail_overrides_goal_on_slope,
                    TransitionFailureReasons.INSUFFICIENT_HEAD_CLEARANCE: RouteFailureTunables.route_fail_overrides_insufficient_head_clearance}
            if failure_reason in ROUTE_FAILURE_OVERRIDE_MAP:
                overrides = ROUTE_FAILURE_OVERRIDE_MAP[failure_reason]()
                if failure_object_id is not None:
                    fail_obj = services.object_manager().get(failure_object_id)
                    if fail_obj is not None:
                        if fail_obj.blocking_balloon_overrides is not None:
                            overrides.balloons = fail_obj.blocking_balloon_overrides
                        else:
                            overrides.balloon_target_override = fail_obj

        route_obj_list = []

        if interaction:
            action = interaction.__class__.__name__.lower()
            route_obj_list = [str(route.object) for route in sc_Vars.non_routable_obj_list if route.sim == interaction.sim]
            route_obj_list = "\n".join(route_obj_list)
            if failure_reason == TransitionFailureReasons.PATH_PLAN_FAILED or failure_reason == TransitionFailureReasons.RESERVATION:
                interaction.sim.sim_info.use_object_index += 1
            if sc_Vars.DEBUG or sc_Vars.DEBUG_ROUTING:
                now = services.time_service().sim_now
                blocking_object = get_sim_posture_target(interaction.sim)

                failure = "\n{} {}\nRoute Fail at {}\nBlocking Object: {}\nAction: {}\nReason: {}\nRoute Fail Objects:\n{}". \
                    format(interaction.sim.first_name, interaction.sim.last_name, now, blocking_object.definition.id if blocking_object else None, str(interaction), failure_reason, route_obj_list)
                client = services.client_manager().get_first_client()
                sims4.commands.cheat_output(failure, client.id)
                message_box(interaction.sim, interaction.target, "Route Fail", failure, "GREEN")

            #if "puddle" in str(interaction.target).lower() or "dust" in str(interaction.target).lower():
            #    target = interaction.target
            #    interaction.cancel(FinishingType.KILLED, 'Filtered')
            #    target.destroy()
            #    return
            if "clean" in str(interaction).lower():
                make_clean(interaction.target)
            #if "dish" in str(interaction).lower():
            #    target = interaction.target
            #    interaction.cancel(FinishingType.KILLED, 'Filtered')
            #    target.destroy()
            #    return

            if "xray" in action and "calibrate" not in action or \
                    "beachtowel" in str(interaction.target).lower() or "object_door" in str(
                interaction.target).lower() or \
                    "cafeteriastation" in str(interaction.target).lower():
                try:
                    obj = interaction.target
                    translation = obj.location.transform.translation
                    level = obj.location.level
                    orientation = obj.location.transform.orientation
                    zone_id = services.current_zone_id()
                    routing_surface = SurfaceIdentifier(zone_id, level, SurfaceType.SURFACETYPE_WORLD)
                    interaction.cancel(FinishingType.KILLED, 'Filtered')
                    clone = objects.system.create_object(obj.definition.id)
                    clone.location = Location(Transform(translation, orientation), routing_surface)

                    interaction.target.destroy()
                except:
                    pass

        handle_unroutable_object(interaction.sim)
    except BaseException as e:
        error_trap(e)
        #message_box(interaction.sim, interaction.target, "Error Object", "", "ORANGE")
        pass

    route_fail_anim = RouteFailureTunables.route_fail_animation((sim.posture.source_interaction), overrides=overrides,
                                                                sequence=())
    supported_postures = route_fail_anim.get_supported_postures()
    if supported_postures:
        return element_utils.build_element((route_fail_anim, flush_all_animations))
    if interaction:
        balloon_requests = TunableBalloon.get_balloon_requests(interaction, route_fail_anim.overrides)
        return balloon_requests
    return None


def get_violators(sim):
    transition_controller = sim.queue.transition_controller
    excluded_sims = transition_controller.get_transitioning_sims() if transition_controller is not None else ()
    violators = sim.routing_component.get_stand_slot_reservation_violators(excluded_sims=excluded_sims)
    if violators:
        violators = [violator for violator in violators if violator.parent not in excluded_sims]
    if violators:
        return violators
    return None


def routing_fix(target):
    try:
        if not target:
            return
        if target.definition.id == 816 or not target.id or target.is_sim:
            return
        zone_id = services.current_zone_id()
        object_list = [target]
        close_objects = [obj for obj in services.object_manager().get_all() if
                         distance_to_by_room(obj, target) < 5 and obj.id != target.id]
        for obj in close_objects:
            parent_id = 0
            if hasattr(obj, "parent"):
                information = str(obj.parent)
                if "[" in information:
                    value = information[information.find(":0x") + 3:information.rfind("[")]
                else:
                    value = information[information.find(":0x") + 3:len(information)]
                try:
                    parent_id = int(value, 16)
                except:
                    parent_id = 0
                    pass

            if target.id == parent_id:
                if hasattr(obj, "position"):
                    object_list.append(obj)

        for obj in list(object_list):
            obj.reset(ResetReason.NONE, None, 'Command')
            routing_surface = SurfaceIdentifier(zone_id, obj.level, SurfaceType.SURFACETYPE_WORLD)
            clone = objects.system.create_object(obj.definition.id)
            clone.location = Location(Transform(obj.position, obj.orientation), routing_surface)
            clone.scale = obj.scale
            obj.destroy()

    except BaseException as e:
        error_trap(e)
        pass


def debug_transition(self, timeline):
    try:
        if not sc_Vars.DEBUG_ROUTING:
            return

        interaction = self.interaction if self.interaction is not None else None
        _id = interaction.guid64 if hasattr(interaction, "guid64") else 0
        sim = interaction.sim
        self._validate_transitions()
        target_si, test_result = interaction.get_target_si()

        debugger(
            "Sim: {} Interaction: {} Target: {} Test Result: {}".format(sim.first_name, _id, target_si, test_result))
    except BaseException as e:
        error_trap(e)
        pass


def is_location_routable(location):
    return routing.test_point_placement_in_navmesh(location.routing_surface, location.transform.translation)


def is_position_routable(routing_surface, position):
    return routing.test_point_placement_in_navmesh(routing_surface, position)


def get_path_fail(interaction):
    path_spec = interaction.transition._get_path_spec(interaction.sim)
    if path_spec is EMPTY_PATH_SPEC or path_spec.is_failure_path:
        return True
    return False


route_fail.route_failure = _route_failure
route_fail.ROUTE_FAILURE_OVERRIDE_MAP = ROUTE_FAILURE_OVERRIDE_MAP
