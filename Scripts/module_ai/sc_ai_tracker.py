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
    find_all_objects_by_title, distance_to_by_room
from scripts_core.sc_sim_tracker import sc_SimTracker
from scripts_core.sc_util import init_sim

def update_sim_ai_info(sim_info):
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
                    debugger("Sim Buff {}: {} {}: Error!".format(buff_id, sim_info.first_name, sim_info.last_name))
                    continue
                add_sim_buff(buff_id, sim_info)

def load_sim_ai(sim_info):
    sim = init_sim(sim_info)
    if not sim:
        return
    sim_id = sim.id
    zone_id = services.current_zone_id()
    sim_name = "{}_{}".format(sim_info.first_name, sim_info.last_name)
    datapath = os.path.abspath(os.path.dirname(__file__))
    filename = datapath + r"\Data\autonomy.ini"
    if not os.path.exists(filename):
        return
    config = configparser.ConfigParser()
    config.read(filename)
    if config.has_section(sim_name):
        position = sim.position
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
            update_sim_ai_info(sim_info)







