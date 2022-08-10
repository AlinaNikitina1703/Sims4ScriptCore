import random

import services
from scripts_core.sc_jobs import find_all_objects_by_title, find_all_objects_by_id
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import message_box

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
    beds = find_all_objects_by_title(sim, "bed")
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
                if not chair.in_use and not chair.in_use_by(sim) or chair.in_use_by(sim):
                    return desk, chair
    return None, None

def find_empty_desk_by_id(sim, id):
    desks = find_all_objects_by_id(sim, id)
    if desks:
        for desk in desks:
            chairs = find_all_objects_by_title(desk, "sitliving|sitdining|sitsofa|chair|stool", desk.level, 1.5)
            if not chairs:
                return desk, None
            for chair in chairs:
                if not chair.in_use and not chair.in_use_by(sim) or chair.in_use_by(sim):
                    return desk, chair
    return None, None

def find_empty_computer(sim):
    computers = find_all_objects_by_title(sim, "computer")
    if computers:
        for computer in computers:
            chairs = find_all_objects_by_title(computer, "sitliving|sitdining|sitsofa|chair|stool", computer.level, 1.5)
            desks = find_all_objects_by_title(computer, "frontdesk", computer.level, 1.5)
            if desks:
                continue
            if not chairs:
                continue
            for chair in chairs:
                if not chair.in_use and not chair.in_use_by(sim) or chair.in_use_by(sim):
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
            if not chair.in_use and not chair.in_use_by(sim) or chair.in_use_by(sim):
                return register, chair
    return None, None
