import ast
import configparser
import os

import objects
import services
from sims4.resources import Types, get_resource_key
from vfx import PlayEffect
from sims4.math import Location, Transform, Vector3
from scripts_core.sc_debugger import debugger
from scripts_core.sc_jobs import add_sim_buff, assign_title
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_sim_tracker import sc_SimTracker
from scripts_core.sc_util import init_sim


class sc_AiFunctions:
    def __init__(self):
        super().__init__()

    def update_sim_ai_info(self, sim_info):
        update_sim_ai_info(sim_info)

    def load_sim_ai(self, sim_info):
        load_sim_ai(sim_info)


sc_Vars.ai_function = sc_AiFunctions()

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
                        if hasattr(b, "guid64"):
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

    if sim_info.tracker.effect:
        joint_hash: int = objects.sims4.hash_util.hash32(sim_info.tracker.vfx_joint)
        if not sim_info.tracker.vfx:
            sim_info.tracker.vfx = PlayEffect(sim_info.get_sim_instance(), effect_name=sim_info.tracker.effect, joint_name=joint_hash, mirror_effect=True)
            sim_info.tracker.vfx.start()
        elif sim_info.tracker.vfx.effect_name not in sim_info.tracker.effect and sim_info.tracker.vfx:
            sim_info.tracker.vfx.stop(immediate=True)
            sim_info.tracker.vfx = PlayEffect(sim_info.get_sim_instance(), effect_name=sim_info.tracker.effect, joint_name=joint_hash)
            sim_info.tracker.vfx.start()
        elif sim_info.tracker.vfx:
            sim_info.tracker.vfx.start()
    else:
        if sim_info.tracker.vfx:
            sim_info.tracker.vfx.stop(immediate=True)
            sim_info.tracker.vfx = None

    if sim_info.tracker.title:
        assign_title(sim_info, sim_info.tracker.title)

def load_sim_ai(sim_info):
    sim = init_sim(sim_info)
    if not sim:
        return
    sim_id = sim.id
    zone_id = services.current_zone_id()
    sim_name = "{}_{}".format(sim_info.first_name, sim_info.last_name)
    datapath = sc_Vars.config_data_location
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
            if config.has_option(sim_name, "effect"):
                effect = config.get(sim_name, "effect")
            else:
                effect = None
            if config.has_option(sim_name, "joint"):
                joint = config.get(sim_name, "joint")
            else:
                joint = "b__Head__"
            if config.has_option(sim_name, "title"):
                title = config.get(sim_name, "title")
            else:
                title = ""

            if sim_info.tracker.vfx:
                sim_info.tracker.vfx.stop(immediate=True)
                sim_info.tracker.vfx = None

            sim_info.tracker = sc_SimTracker(position=sim.position, mood=mood, buffs=buffs, effect=effect, vfx=None, vfx_joint=joint, title=title)
            update_sim_ai_info(sim_info)







