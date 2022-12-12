import random

import objects
import routing
import services
from interactions.context import InteractionContext
from interactions.priority import Priority
from objects.terrain import TerrainPoint
from server.pick_info import PickType, PickInfo
from server_commands.sim_commands import CommandTuning, _build_terrain_interaction_target_and_context
from sims4.math import Location, Transform, Vector3
from terrain import get_terrain_height

from scripts_core.sc_debugger import debugger
from scripts_core.sc_jobs import distance_to_pos, clear_sim_instance, distance_to_by_level, get_room, \
    set_proper_sim_outfit, assign_role, check_actions, remove_sim, set_autonomy, assign_routine, get_venue, \
    is_allowed_privacy_role, check_private_objects, get_sim_role
from scripts_core.sc_script_vars import AutonomyState, sc_Vars
from scripts_core.sc_util import error_trap


class sc_GoHere:
    success = None

    def __init__(self):
        super().__init__()

    def loop_until_success(self, sim, location, level=0, offset=1.5, distance=64, tries=24):
        index = 0
        while not go_here(sim, location, level, offset) and index < tries:
            index = index + 1
            random.seed(int(sim.id) + index)
            center_pos = services.current_zone().lot.position
            location = get_spawn_point_by_distance(center_pos, distance)


def sc_build_terrain_interaction_target_and_context(sim, pos, routing_surface, pick_type, target_cls):
    try:
        location = Location(Transform(pos), routing_surface)
        target = target_cls(location)
        pick = PickInfo(pick_type=pick_type, target=target, location=pos, routing_surface=routing_surface)
        return (target, InteractionContext(sim, (InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT),
           (Priority.High), pick=pick, group_id=1))
    except BaseException as e:
        error_trap(e)
        return None, None

def keep_sims_outside():
    venue = get_venue()
    if "residential" in venue or "rentable" in venue or "clinic" in venue:
        sims = [sim for sim in services.sim_info_manager().instanced_sims_gen() if sim.sim_info not in
                services.active_household() and not sim.sim_info.routine and not sim.sim_info.is_selectable]
        for sim in sims:
            keep_sim_outside(sim)

def keep_sim_outside(sim, private_objects=None):
    venue = get_venue()
    if sim.sim_info.routine:
        return
    if "residential" in venue or "rentable" in venue or "clinic" in venue:
        if not sim.is_outside:
            if not is_allowed_privacy_role(sim):
                make_sim_goto_spawn(sim)
                return

    # New private objects code
    if private_objects:
        if [obj for obj in private_objects if check_private_objects(sim, obj)]:
            make_sim_goto_spawn(sim)

def send_sim_home(sim):
    try:
        ensemble_service = services.ensemble_service()
        ensemble = ensemble_service.get_visible_ensemble_for_sim(sim)
        if ensemble is not None:
            ensemble.end_ensemble()
        set_autonomy(sim.sim_info, AutonomyState.FULL)
        assign_routine(sim.sim_info, "leave")
        make_sim_leave(sim)

    except BaseException as e:
        error_trap(e)

def make_sim_leave(sim):
    try:
        center_pos = services.current_zone().lot.position
        random.seed(int(sim.id))
        pos = get_spawn_point_by_distance(center_pos, 64)
        set_proper_sim_outfit(sim)
        assign_role(24315, sim.sim_info)
        if not check_actions(sim, "gohere"):
            clear_sim_instance(sim.sim_info, "gohere", True)
            if distance_to_pos(sim.position, pos) < 8:
                try:
                    remove_sim(sim)
                except:
                    zone_director = services.venue_service().get_zone_director()
                    zone_director._send_sim_home(sim.sim_info)
                    pass
            else:
                gohere = sc_GoHere()
                gohere.loop_until_success(sim, pos)

    except BaseException as e:
        remove_sim(sim)
        error_trap(e)

def push_sim_out(sim, dist=10):
    random.seed(int(sim.sim_info.sim_id))
    room_sim_is_in = get_room(sim)
    object_list = [obj for obj in services.object_manager().get_all() if get_room(obj) != room_sim_is_in and
                   distance_to_by_level(obj, sim) > dist]
    random.shuffle(object_list)
    obj = object_list[0]
    gohere = sc_GoHere()
    gohere.loop_until_success(sim, obj.position)

def make_sim_goto_spawn(sim):
    center_pos = services.current_zone().lot.position
    pos = get_spawn_point_by_distance(center_pos, 64)
    if not [action for action in sim.get_all_running_and_queued_interactions() if "gohere" in str(action).lower()]:
        clear_sim_instance(sim.sim_info, "gohere", True)
        gohere = sc_GoHere()
        gohere.loop_until_success(sim, pos)

def get_spawn_point_by_distance(point, dist) -> Vector3:
    zone = services.current_zone()
    for spawn_point in zone.spawn_points_gen():
        if hasattr(spawn_point, "_center"):
            if distance_to_pos(point, spawn_point._center) < dist:
                return spawn_point._center
        elif hasattr(spawn_point, "position"):
            if distance_to_pos(point, spawn_point.position) < dist:
                return spawn_point.position
        elif hasattr(spawn_point, "location"):
            if distance_to_pos(point, spawn_point.location.transform.translation) < dist:
                return spawn_point.location.transform.translation
        else:
            continue
    center_pos = services.current_zone().lot.position
    spawn_point = Vector3(center_pos.x + random.uniform(-dist, dist), center_pos.y,  center_pos.z + random.uniform(-dist, dist))
    spawn_point.y = get_terrain_height(spawn_point.x, spawn_point.z)
    return spawn_point

def go_here(sim, location, level=0, offset=1.5):
    location = Vector3(location.x + random.uniform(-offset, offset), location.y, location.z + random.uniform(-offset, offset))
    routing_surface = routing.SurfaceIdentifier(services.current_zone_id(), level, routing.SurfaceType.SURFACETYPE_WORLD)
    target, context = _build_terrain_interaction_target_and_context(sim, location, routing_surface, PickType.PICK_TERRAIN, objects.terrain.TerrainPoint)
    return sim.push_super_affordance(CommandTuning.TERRAIN_GOHERE_AFFORDANCE, target, context) if target else None

def goto_object(sim, target):
    level = target.location.level
    pos = target.location.transform.translation
    routing_surface = routing.SurfaceIdentifier(services.current_zone_id(), level, routing.SurfaceType.SURFACETYPE_WORLD)
    target, context = _build_terrain_interaction_target_and_context(sim, pos, routing_surface, PickType.PICK_TERRAIN, objects.terrain.TerrainPoint)
    return sim.push_super_affordance(CommandTuning.TERRAIN_GOHERE_AFFORDANCE, target, context) if target else None
