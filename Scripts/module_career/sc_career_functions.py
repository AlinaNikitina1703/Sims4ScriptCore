import random

import services

from scripts_core.sc_debugger import debugger
from scripts_core.sc_jobs import find_all_objects_by_title, find_all_objects_by_id, distance_to, push_sim_function, \
    is_object_in_use
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
    now = services.time_service().sim_now
    random.seed(int(now.second()))
    beds = find_all_objects_by_title(sim, "object_bed")
    if beds:
        index = random.randint(0, len(beds))
        for i, bed in enumerate(beds):
            if not bed.self_or_part_in_use and i == index:
                return bed
    return None

def find_empty_desk(sim):
    desks = find_all_objects_by_title(sim, "frontdesk")
    if desks:
        for desk in desks:
            chairs = find_all_objects_by_title(desk, "sitliving|sitdining|sitsofa|chair|stool", desk.level, 1.5)
            if not chairs:
                return desk, None
            for chair in chairs:
                if not is_object_in_use(chair) and not chair.in_use_by(sim) or chair.in_use_by(sim):
                    return desk, chair
    return None, None

def find_empty_chair(sim):
    chairs = find_all_objects_by_title(sim, "sitliving|sitdining|sitsofa|sitlove|chair|stool|hospitalexambed", sim.level)
    if not chairs:
        return None
    for chair in chairs:
        if not is_object_in_use(chair) and not chair.in_use_by(sim) or chair.in_use_by(sim):
            return chair
    return None

def find_empty_objects(sim, title, in_use=True):
    objs = find_all_objects_by_title(sim, title, sim.level)
    if not objs:
        return None
    for obj in objs:
        if in_use:
            if not is_object_in_use(obj) and not obj.in_use_by(sim) or obj.in_use_by(sim):
                return obj
        else:
            return obj
    return None

def find_empty_desk_by_id(sim, id):
    desks = find_all_objects_by_id(sim, id)
    if desks:
        for desk in desks:
            chairs = find_all_objects_by_title(desk, "sitliving|sitdining|sitsofa|chair|stool", desk.level, 1.5)
            if not chairs:
                return desk, None
            for chair in chairs:
                if not is_object_in_use(chair) and not chair.in_use_by(sim) or chair.in_use_by(sim):
                    return desk, chair
    return None, None

def find_empty_computer(sim):
    computers = find_all_objects_by_title(sim, "computer")
    if computers:
        for computer in computers:
            if not is_object_in_use(computer) and not computer.in_use_by(sim) or computer.in_use_by(sim):
                chairs = find_all_objects_by_title(computer, "sitliving|sitdining|sitsofa|chair|stool", computer.level, 1.5)
                desks = find_all_objects_by_title(computer, "frontdesk", computer.level, 1.5)
                if desks:
                    continue
                if not chairs:
                    continue
                for chair in chairs:
                    if not is_object_in_use(chair) and not chair.in_use_by(sim) or chair.in_use_by(sim):
                        if sc_Vars.DEBUG and sim == services.get_active_sim():
                            message_box(sim, computer, "Found Computer", "", "GREEN")
                        return computer, chair
    return None, None

def find_empty_bed(sim):
    beds = find_all_objects_by_title(sim, "bed")
    if beds:
        for bed in beds:
            if not bed.self_or_part_in_use:
                return bed
    return None

def find_empty_register(sim):
    registers = find_all_objects_by_title(sim, "storeregister")
    for register in registers:
        chairs = find_all_objects_by_title(register, "sitliving|sitdining|sitsofa|chair|stool", register.level, 2.0)
        if not chairs:
            return register, None
        for chair in chairs:
            if not is_object_in_use(chair) and not chair.in_use_by(sim) or chair.in_use_by(sim):
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
                return
    except BaseException as e:
        error_trap(e)
