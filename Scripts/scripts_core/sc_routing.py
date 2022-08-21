import camera
import objects
import sims4

import element_utils
import services
from animation.animation_utils import flush_all_animations
from autonomy.autonomy_modes_tuning import AutonomyModesTuning
from balloon.tunable_balloon import TunableBalloon
from interactions.interaction_finisher import FinishingType
from interactions.utils import route_fail
from interactions.utils.route_fail import RouteFailureTunables, ROUTE_FAILURE_OVERRIDE_MAP
from interactions.utils.routing_constants import TransitionFailureReasons
from routing import SurfaceIdentifier, SurfaceType

from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import message_box, error_trap

AutonomyModesTuning.LOCKOUT_TIME = 1

class NonRoutableObject:
    def __init__(self, object, reason, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.object = object
        self.reason = reason

non_routable_obj_list = []

def _route_failure(sim, interaction, failure_reason, failure_object_id):
    global ROUTE_FAILURE_OVERRIDE_MAP
    global non_routable_obj_list

    if not sim.should_route_fail:
        return

    overrides = None
    if failure_reason is not None:
        if ROUTE_FAILURE_OVERRIDE_MAP is None:
            ROUTE_FAILURE_OVERRIDE_MAP = {TransitionFailureReasons.BLOCKING_OBJECT: RouteFailureTunables.route_fail_overrides_object,
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


    # Get rid of or clean unroutable objects
    if len(non_routable_obj_list) > 24:
        non_routable_obj_list = []
    else:
        for route in non_routable_obj_list:
            if route.object == interaction.target:
                non_routable_obj_list.remove(route)

    non_routable_obj_list.append(NonRoutableObject(interaction.target, failure_reason))
    route_obj_list = []
    try:
        for route in non_routable_obj_list:
            route_obj_list.append(str(route.object))
        route_obj_list = "\n".join(route_obj_list)
        if failure_reason == TransitionFailureReasons.PATH_PLAN_FAILED or failure_reason == TransitionFailureReasons.RESERVATION:
            interaction.sim.sim_info.use_object_index += 1
        if sc_Vars.DEBUG:
            now = services.time_service().sim_now
            if hasattr(interaction.target, "definition"):
                obj_id = interaction.target.definition.id
            elif hasattr(interaction.target, "id"):
                obj_id = interaction.target.id
            else:
                obj_id = interaction.target.guid64

            failure = "\n{} {}\nRoute Fail at {}\nBlocking Object: {}\nAction: {}\nReason: {}\nRoute Fail Objects:\n{}".\
                format(interaction.sim.first_name, interaction.sim.last_name, now, obj_id, str(interaction), failure_reason, route_obj_list)
            client = services.client_manager().get_first_client()
            sims4.commands.cheat_output(failure, client.id)
            message_box(interaction.sim, interaction.target, "Route Fail", failure, "GREEN")
            #if hasattr(interaction.target, "position"):
            #    camera.focus_on_position(interaction.target.position, client)

        if "puddle" in str(interaction.target).lower() or "dust" in str(interaction.target).lower():
            interaction.target.destroy()
            return
        if "clean" in str(interaction).lower():
            for commodity in interaction.target.commodity_tracker:
                if "exambed_dirtiness" in str(commodity).lower():
                    commodity.set_value(100)
                if "commodity_dirtiness" in str(commodity).lower():
                    commodity.set_value(100)

        if "xray" in str(interaction.target).lower() or "beachtowel" in str(interaction.target).lower() or \
                "object_door" in str(interaction.target).lower() or "cafeteriastation" in str(interaction.target).lower():
            obj = interaction.target
            translation = obj.location.transform.translation
            level = obj.location.level
            orientation = obj.location.transform.orientation
            zone_id = services.current_zone_id()
            routing_surface = SurfaceIdentifier(zone_id, level, SurfaceType.SURFACETYPE_WORLD)
            interaction.cancel(FinishingType.KILLED, 'Filtered')
            clone = objects.system.create_object(obj.definition.id)
            clone.location = sims4.math.Location(sims4.math.Transform(translation, orientation),
                                                                routing_surface)

            interaction.target.destroy()

    except BaseException as e:
        error_trap(e)
        pass

    route_fail_anim = RouteFailureTunables.route_fail_animation((sim.posture.source_interaction), overrides=overrides, sequence=())
    supported_postures = route_fail_anim.get_supported_postures()
    if supported_postures:
        return element_utils.build_element((route_fail_anim, flush_all_animations))
    balloon_requests = TunableBalloon.get_balloon_requests(interaction, route_fail_anim.overrides)
    return balloon_requests


route_fail.route_failure = _route_failure
