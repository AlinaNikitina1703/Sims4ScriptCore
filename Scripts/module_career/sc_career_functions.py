import random

import services

from scripts_core.sc_jobs import find_all_objects_by_title, find_all_objects_by_id, push_sim_function, \
    is_object_in_use, get_sims_using_object, is_object_in_use_by, get_routable_for_sim, is_unroutable_object, \
    find_empty_chair
from scripts_core.sc_message_box import message_box
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import error_trap


def get_routine_sims():
    return [sim for sim in services.sim_info_manager().instanced_sims_gen() if sim.sim_info.routine]

def get_routine_objects_by_title(title, objects):
    value = []
    if title != "":
        value = title.split("|")
    if len(value) == 0:
        objects = [obj for obj in objects if title in str(obj).lower()]
    else:
        objects = [obj for obj in objects if [v for v in value if v in str(obj).lower()]]
    if objects:
        return objects
    return None

def find_empty_random_bed(sim):
    random.seed(int(sim.sim_info.sim_id))
    beds = find_all_objects_by_title(sim, "object_bed")
    if beds:
        random.shuffle(beds)
        for bed in beds:
            if is_unroutable_object(sim, bed):
                continue
            if not get_routable_for_sim(bed, sim):
                continue
            if "beddouble" in str(bed).lower() and len(get_sims_using_object(bed)) < 2:
                return bed
            if "bedsingle" in str(bed).lower() and len(get_sims_using_object(bed)) < 1:
                return bed
    return None

def find_empty_desk(sim):
    desk = find_empty_objects(sim, "frontdesk")
    if desk:
        chair = find_empty_chair(sim, desk, 1.5)
        if not chair:
            return desk, None
        return desk, chair
    return None, None

def find_empty_objects(sim, title, in_use=True):
    objs = find_all_objects_by_title(sim, title)
    if not objs:
        return None
    for obj in objs:
        if is_unroutable_object(sim, obj):
            continue
        if not get_routable_for_sim(obj, sim):
            continue
        if in_use:
            # Proof EA is super retarded. Only these object types requires 2 sims or less using them or it fires a route fail.
            # Computers and chairs are a given but televisions?
            if "television" in str(obj).lower() and len(get_sims_using_object(obj)) < 2:
                return obj
            elif not is_object_in_use(obj) or is_object_in_use_by(obj, sim):
                return obj
        else:
            return obj
    return None

def find_empty_desk_by_id(sim, id):
    desks = find_all_objects_by_id(sim, id)
    if desks:
        for desk in desks:
            chair = find_empty_chair(sim, desk, 1.5)
            if not chair:
                continue
            return desk, chair
    return None, None

def find_empty_computer(sim):
    computers = find_all_objects_by_title(sim, "computer")
    if computers:
        for computer in computers:
            if not is_object_in_use(computer) or is_object_in_use_by(computer, sim):
                chair = find_empty_chair(sim, computer, 1.5)
                desks = find_all_objects_by_title(computer, "frontdesk", computer.level, 1.5)
                if desks:
                    continue
                if not chair:
                    continue
                if sc_Vars.DEBUG and sim == services.get_active_sim():
                    message_box(sim, computer, "Found Computer", "", "GREEN")
                return computer, chair
    return None, None

def find_empty_bed(sim):
    beds = find_all_objects_by_title(sim, "bed")
    if beds:
        for bed in beds:
            if is_unroutable_object(sim, bed):
                continue
            if not get_routable_for_sim(bed, sim):
                continue
            if "beddouble" in str(bed).lower() and len(get_sims_using_object(bed)) < 2:
                return bed
            if "bedsingle" in str(bed).lower() and len(get_sims_using_object(bed)) < 1:
                return bed
    return None

def find_empty_register(sim):
    registers = find_all_objects_by_title(sim, "storeregister")
    for register in registers:
        if is_unroutable_object(sim, register):
            continue
        if not get_routable_for_sim(register, sim):
            continue
        chair = find_empty_chair(sim, register, 2.0)
        if not chair:
            return register, None
        return register, chair
    return None, None

def choose_role_interaction(sim):
    try:
        if sim.sim_info.routine_info.autonomy_requests:
            index = random.randint(0, len(sim.sim_info.routine_info.autonomy_requests))
            choice = sim.sim_info.routine_info.autonomy_requests[index] if len(sim.sim_info.routine_info.autonomy_requests) > index else sim.sim_info.routine_info.autonomy_requests[0]
            object_choice = sim.sim_info.routine_info.autonomy_objects[index] if len(sim.sim_info.routine_info.autonomy_objects) > index else sim.sim_info.routine_info.autonomy_objects[0]
            obj = find_empty_objects(sim, object_choice)
            if obj:
                push_sim_function(sim, obj, choice, False)
                return True
        return False
    except BaseException as e:
        error_trap(e)
