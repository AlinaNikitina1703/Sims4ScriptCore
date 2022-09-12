import ast
import configparser
import os

import routing
import services
from objects.object_enums import ResetReason
from sims.sim_info import SimInfo
from sims4.math import Location, Transform, Quaternion, Vector3
from sims4.resources import Types, get_resource_key

from scripts_core.sc_debugger import debugger
from scripts_core.sc_jobs import add_sim_buff, clear_sim_instance, push_sim_function, get_filters, \
    find_all_objects_by_title, distance_to_by_room, check_actions
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import init_sim


class sc_SimTracker:
    __slots__ = ("position", "level", "actions", "mood", "buffs")

    def __init__(self, position=None, level=0, actions=None, mood=None, buffs=None):
        super().__init__()
        self.position = position
        self.level = level
        self.actions = actions
        self.mood = mood
        self.buffs = buffs

def track_sim(sim_info, mood=None):
    sim = init_sim(sim_info)
    if mood:
        sim_info.tracker.mood = mood
    sim_info.tracker.position = sim.position

def update_sim_tracking_info(sim_info):
    if sim_info.tracker.mood:
        buff_manager = services.get_instance_manager(Types.BUFF)
        buff_component = sim_info.Buffs
        mood = buff_component._active_mood
        buff = buff_manager.get(sim_info.tracker.mood)
        if buff and mood:
            mood_type = str(mood.__name__).replace("Mood_", "")
            visible_buffs = [b for b in buff_manager.types.values() if b.visible and sim_info.has_buff(b)]
            if mood_type.lower() not in str(buff.__name__).lower():
                if visible_buffs:
                    for b in visible_buffs:
                        sim_info.remove_buff_by_type(buff_manager.get(get_resource_key(b.guid64, Types.BUFF)))
        if buff:
            add_sim_buff(sim_info.tracker.mood, sim_info)

    if sim_info.tracker.buffs:
        buff_manager = services.get_instance_manager(Types.BUFF)
        for buff_id in sim_info.tracker.buffs:
            if buff_id:
                buff = buff_manager.get(buff_id)
                if not buff:
                    if sc_Vars.DEBUG:
                        debugger("Sim Buff {}: {} {}: Error!".format(buff_id, sim_info.first_name, sim_info.last_name))
                    continue
                add_sim_buff(buff_id, sim_info)

def save_sim_tracking(sim_info):
    filter_out_actions = [14244, 14310, 13983]
    sim = init_sim(sim_info)
    zone_id = services.current_zone_id()
    position = sim.position
    orientation = sim.orientation
    tracking_position = [position.x, position.y, position.z]
    tracking_orientation = [orientation.x, orientation.y, orientation.z, orientation.w]
    action_list = []
    target_list = []
    for action in sim.get_all_running_and_queued_interactions():
        if hasattr(action, "guid64") and hasattr(action.target, "id"):
            target = action.target
            if [f for f in filter_out_actions if action.guid64 == f]:
                continue
            if action.guid64 == 18240980946975959663:
                client = services.client_manager().get_first_client()
                objs = find_all_objects_by_title(client.active_sim, "stereo")
                if objs:
                    objs.sort(key=lambda obj: distance_to_by_room(obj, client.active_sim))
                    target = objs[0]

                action.guid64 = 18240980946975959664

            action_list.append(action.guid64)
            target_list.append(target.id)

    sim_name = "{}_{}".format(sim_info.first_name, sim_info.last_name)
    datapath = os.path.abspath(os.path.dirname(__file__))
    filename = datapath + r"\Data\tracker.ini"
    if not os.path.exists(filename):
        return
    config = configparser.ConfigParser()
    config.read(filename)
    if not config.has_section(sim_name):
        config.add_section(sim_name)
    config.set(sim_name, "position", str(tracking_position))
    config.set(sim_name, "orientation", str(tracking_orientation))
    config.set(sim_name, "level", str(sim.level))
    config.set(sim_name, "zone", str(zone_id))
    config.set(sim_name, "id", str(sim.id))
    config.set(sim_name, "actions", str(action_list))
    config.set(sim_name, "targets", str(target_list))
    with open(filename, 'w') as configfile:
        config.write(configfile)

def load_sim_tracking(sim_info):
    sim = init_sim(sim_info)
    if not sim:
        return
    sim_id = sim.id
    zone_id = services.current_zone_id()
    sim_name = "{}_{}".format(sim_info.first_name, sim_info.last_name)
    datapath = os.path.abspath(os.path.dirname(__file__))
    filename = datapath + r"\Data\tracker.ini"
    if not os.path.exists(filename):
        return
    config = configparser.ConfigParser()
    config.read(filename)
    if config.has_section(sim_name):
        position = sim.position
        tracking_zone = config.getint(sim_name, "zone")
        if config.has_option(sim_name, "id"):
            sim_id = config.getint(sim_name, "id")

        if sim_id == sim.id:
            if config.has_option(sim_name, "mood"):
                mood = config.getint(sim_name, "mood")
            else:
                mood = None
            if config.has_option(sim_name, "buffs"):
                buffs = ast.literal_eval(config.get(sim_name, "buffs"))
            else:
                buffs = None


            sim_info.tracker = sc_SimTracker(position=sim.position, mood=mood, buffs=buffs)
            update_sim_tracking_info(sim_info)

        if zone_id == tracking_zone and sim_id == sim.id:
            clear_sim_instance(sim_info)
            if config.has_option(sim_name, "position"):
                tracking_position = ast.literal_eval(config.get(sim_name, "position"))
                position = Vector3(float(tracking_position[0]),
                               float(tracking_position[1]),
                               float(tracking_position[2]))
                orientation = Quaternion.ZERO()
                if config.has_option(sim_name, "orientation"):
                    tracking_orientation = ast.literal_eval(config.get(sim_name, "orientation"))
                    orientation = Quaternion(float(tracking_orientation[0]),
                                       float(tracking_orientation[1]),
                                       float(tracking_orientation[2]),
                                       float(tracking_orientation[3]))

                level = config.getint(sim_name, "level")
                routing_surface = routing.SurfaceIdentifier(zone_id, level, routing.SurfaceType.SURFACETYPE_WORLD)
                sim.location = Location(Transform(position, orientation), routing_surface)

            if config.has_option(sim_name, "actions"):
                action_list = ast.literal_eval(config.get(sim_name, "actions"))
                target_list = ast.literal_eval(config.get(sim_name, "targets"))
                clear_sim_instance(sim_info)
                for i, action in enumerate(action_list):
                    if i < len(target_list):
                        obj = services.get_zone(zone_id).find_object(target_list[i])
                        if obj:
                            push_sim_function(sim, obj, action, False)


setattr(SimInfo, "tracker", sc_SimTracker())
