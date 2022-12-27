import configparser
import math
import os
import random
import sys
import time
from math import fabs, sqrt

import autonomy.settings

import alarms
import build_buy
import caches
import camera
import date_and_time
import element_utils
import interactions
import objects
import routing
import scheduling
import services
import sims4
import sims4.commands
from animation import get_throwaway_animation_context
from animation.animation_utils import create_run_animation
from animation.arb import Arb
from animation.asm import create_asm
from autonomy.autonomy_modes import FullAutonomy
from autonomy.autonomy_request import AutonomyPostureBehavior, AutonomyRequest
from autonomy.content_sets import get_valid_aops_gen
from careers.career_ops import CareerTimeOffReason
from event_testing import test_events
from event_testing.results import EnqueueResult, TestResult, ExecuteResult
from interactions import priority
from interactions.aop import AffordanceObjectPair
from interactions.context import InteractionContext, InteractionBucketType
from interactions.context import QueueInsertStrategy
from interactions.interaction_finisher import FinishingType
from interactions.priority import Priority
from objects.components.portal_lock_data import IndividualSimDoorLockData
from objects.components.portal_locking_enums import LockPriority, LockSide, ClearLock
from objects.components.types import LIGHTING_COMPONENT, PORTAL_LOCKING_COMPONENT
from objects.object_enums import ResetReason
from objects.system import create_script_object
from plex.plex_enums import INVALID_PLEX_ID
from seasons.seasons_enums import SeasonSetSource, SeasonType
from server.pick_info import PickType
from server_commands.argument_helpers import get_tunable_instance, TunableInstanceParam, get_optional_target, \
    OptionalTargetParam
from server_commands.sim_commands import _build_terrain_interaction_target_and_context, CommandTuning
from sims.outfits.outfit_enums import OutfitCategory
from sims.outfits.outfit_tuning import OutfitTuning
from sims.sim_info_lod import SimInfoLODLevel
from sims.sim_info_manager import SimInfoManager
from sims4 import resources
from sims4.color import Color
from sims4.localization import LocalizationHelperTuning
from sims4.math import Location, Transform, Quaternion, Vector3, vector_normalize
from sims4.resources import Types, get_resource_key
from situations.bouncer.bouncer_request import RequestSpawningOption
from situations.bouncer.bouncer_types import BouncerRequestPriority
from situations.situation_guest_list import SituationGuestList, SituationGuestInfo
from tag import Tag
from terrain import get_terrain_height
from traits.trait_type import TraitType
from travel_group.travel_group import TravelGroup
from weather.weather_enums import Temperature

from scripts_core.sc_affordance import sc_Affordance
from scripts_core.sc_debugger import debugger
from scripts_core.sc_file import get_config
from scripts_core.sc_message_box import message_box
from scripts_core.sc_script_vars import sc_Vars, AutonomyState
from scripts_core.sc_util import error_trap, init_sim, clean_string, error_trap_console

try:
    from control_any_sim.services.selection_group import SelectionGroupService
except:
    pass


def get_skill_level(skill_id, sim) -> int:
    try:
        skill = services.statistic_manager().get(skill_id)
        if skill is None:
            return 0
        tracker = sim.sim_info.get_tracker(skill)
        stat = tracker.get_statistic(skill)
        if stat is None:
            return 0
        return stat.get_user_value()
    except BaseException as e:
        error_trap(e)


def remove_annoying_buffs(sim_info):
    sim = init_sim(sim_info)
    remove_sim_buff(212330, sim_info)
    remove_sim_buff(206441, sim_info)
    remove_sim_buff(211347, sim_info)
    remove_sim_buff(212344, sim_info)
    remove_sim_buff(24238, sim_info)
    remove_sim_buff(24312, sim_info)
    remove_sim_buff(28380, sim_info)
    remove_sim_buff(156116, sim_info)
    remove_sim_buff(237919, sim_info)
    remove_sim_buff(180207, sim_info)
    remove_sim_buff(185937, sim_info)
    if is_sim_in_group(sim):
        assign_role(122318, sim_info)


def get_current_temperature():
    from weather.weather_enums import WeatherEffectType, Temperature
    weather_service = services.weather_service()
    if weather_service is not None:
        return Temperature(
            weather_service.get_weather_element_value(WeatherEffectType.TEMPERATURE, default=Temperature.WARM))
    return Temperature.WARM


def assign_situation(potential_key: int, sim_info):
    sim = init_sim(sim_info)
    if services.current_zone().is_zone_shutting_down:
        return
    try:
        clear_jobs(sim_info)
        instance_manager = services.get_instance_manager(Types.SERVICE_NPC)
        situation_manager = services.get_zone_situation_manager()
        if instance_manager is None:
            message_box(sim_info, None, "Assign Job",
                        "instance_manager tuning error for {}!".format(sim_info.first_name), "ORANGE")
            return
        if situation_manager is None:
            message_box(sim_info, None, "Assign Job",
                        "situation_manager tuning error for {}!".format(sim_info.first_name), "ORANGE")
            return
        key = resources.get_resource_key(potential_key, Types.SITUATION_JOB)
        if key is None:
            message_box(sim_info, None, "Assign Job", "key tuning error for {}!".format(sim_info.first_name), "ORANGE")
            return
        job_type = situation_manager.get(key)
        if job_type is None:
            message_box(sim_info, None, "Assign Job", "job_type tuning error for {}!".format(sim_info.first_name),
                        "ORANGE")
            return
        job_list = SituationGuestList(invite_only=True)
        if job_list is None:
            message_box(sim_info, None, "Assign Job", "job_list tuning error for {}!".format(sim_info.first_name),
                        "ORANGE")
            return
        sit_info = SituationGuestInfo(sim.id, job_type.default_job(), RequestSpawningOption.DONT_CARE,
                                      BouncerRequestPriority.EVENT_VIP, reservation=True)
        if sit_info is None:
            message_box(sim_info, None, "Assign Job", "sit_info tuning error for {}!".format(sim_info.first_name),
                        "ORANGE")
            return
        job_list.add_guest_info(sit_info)
        situation_manager.create_situation(job_type, job_list, user_facing=False)
    except BaseException as e:
        error_trap(e)


def do_change_outfit_spinup(sim, category, timeline):
    try:
        did_change = False
        arb = Arb()
        # timeline = scheduling.Timeline(services.time_service().sim_now)
        if not timeline:
            return

        def trigger(*_, **__):
            nonlocal did_change, sim
            if not did_change:
                picked_outfit = (category, 0)
                sim.sim_info._current_outfit = picked_outfit
                sim._apply_on_outfit_changed_loot()
                did_change = True

        arb.register_event_handler(trigger, handler_id=100)
        animation_element_tuning = OutfitTuning.OUTFIT_CHANGE_ANIMATION
        clothing_context = get_throwaway_animation_context()
        clothing_change_asm = create_asm((animation_element_tuning.asm_key), context=clothing_context)
        clothing_change_asm.update_locked_params(sim.get_transition_asm_params())
        sim.posture.setup_asm_interaction(clothing_change_asm, sim, None, animation_element_tuning.actor_name, None)
        sim.set_trait_asm_parameters(clothing_change_asm, animation_element_tuning.actor_name)
        clothing_change_asm.request(animation_element_tuning.begin_states[0], arb)
        if not arb.empty:
            animation_element = create_run_animation(arb)
            element_utils.run_child(timeline, animation_element)
        debugger("Arb: {} Actor: {} Key: {}".format(arb.empty, animation_element_tuning.actor_name,
                                                    animation_element_tuning.asm_key))

    except BaseException as e:
        error_trap(e)

def get_best_outfit_for_clothing_change(sim_info, outfit_change):
    roles = ["bartender", "mail", "butler"]
    t = get_current_temperature()
    sim = init_sim(sim_info)
    if not outfit_change:
        return sim_info._current_outfit
    elif has_role(sim, "patient"):
        return (OutfitCategory.SITUATION, 0)
    elif [role for role in roles if has_role(sim, role)]:
        picked_outfit = (OutfitCategory.CAREER, 0)
        if not sim_info.has_outfit(picked_outfit):
            picked_outfit = (OutfitCategory.SITUATION, 0)
        return picked_outfit
    elif check_action_list(sim, ["swim", "pool"]) and t >= Temperature.WARM and sim.is_outside:
        return sim_info.get_random_outfit((OutfitCategory.SWIMWEAR,))
    elif sim_info._current_outfit[0] == OutfitCategory.BATHING and t < Temperature.WARM and sim.is_outside:
        return sim_info.get_random_outfit((OutfitCategory.COLDWEATHER,))
    elif sim_info._current_outfit[0] == OutfitCategory.SPECIAL and t < Temperature.WARM and sim.is_outside:
        return sim_info.get_random_outfit((OutfitCategory.COLDWEATHER,))
    elif sim_info.is_selectable:
        return sim_info._current_outfit
    elif t < Temperature.WARM and sim_info._current_outfit[0] != OutfitCategory.COLDWEATHER and not sim_info.is_selectable:
        return sim_info.get_random_outfit((OutfitCategory.COLDWEATHER,))
    else:
        return outfit_change

def set_proper_sim_outfit(sim, is_player=False, routine=None, use_buffs=False):
    t = get_current_temperature()
    venue = get_venue()
    robot_traits = sim.trait_tracker.get_traits_of_type(TraitType.ROBOT)
    if robot_traits:
        return
    if use_buffs:
        buff_manager = services.get_instance_manager(Types.BUFF)
        if sim.sim_info.has_buff(buff_manager.get(get_resource_key(180208, Types.BUFF))):
            debugger("Sim: {} is cold".format(sim.first_name))
            remove_sim_buff(180208, sim.sim_info)
            clear_sim_instance(sim.sim_info)
            push_sim_function(sim, sim, 186282, False)
            return

    if check_actions(sim, "wicked") or check_actions(sim, "toilet") or check_actions(sim, "basketball") or \
            check_actions(sim, "workout"):
        return

    if sim.sim_info._current_outfit[0] == OutfitCategory.BATHING and t > Temperature.COOL and sim.is_outside or \
            sim.sim_info._current_outfit[0] == OutfitCategory.BATHING and not sim.is_outside:
        return

    picked_outfit = (OutfitCategory.CURRENT_OUTFIT, 0)
    if routine:
        if routine == "patient":
            picked_outfit = (OutfitCategory.SITUATION, 0)
        else:
            picked_outfit = (OutfitCategory.CAREER, 0)
            if not sim.sim_info.has_outfit(picked_outfit):
                picked_outfit = (OutfitCategory.SITUATION, 0)

    elif sim.sim_info._current_outfit[0] == OutfitCategory.SWIMWEAR and not check_actions(sim, "swim") and \
            "beach" not in venue and "pool" not in venue and t < Temperature.WARM and sim.is_outside or not is_player:
        if t == Temperature.FREEZING:
            picked_outfit = (OutfitCategory.COLDWEATHER, 0)
        elif t == Temperature.COLD:
            picked_outfit = (OutfitCategory.COLDWEATHER, 0)
        elif t == Temperature.COOL:
            picked_outfit = (OutfitCategory.EVERYDAY, 0)
        elif t == Temperature.WARM:
            picked_outfit = (OutfitCategory.EVERYDAY, 0)
        elif t == Temperature.HOT:
            picked_outfit = (OutfitCategory.HOTWEATHER, 0)
        elif t == Temperature.BURNING:
            picked_outfit = (OutfitCategory.HOTWEATHER, 0)

    if not routine and not is_player:
        if has_role(sim, "bartender") or has_role(sim, "mail"):
            picked_outfit = (OutfitCategory.CAREER, 0)

    if sim.sim_info.has_outfit(picked_outfit):
        sim.sim_info._current_outfit = picked_outfit


def max_sims(sim_info, sim_info_list):
    if sim_info.routine_info.max_staff == -1:
        return False
    number_of_sims = [s for s in sim_info_list if sim_info.routine_info.title == s.routine_info.title]
    if len(number_of_sims) > sim_info.routine_info.max_staff:
        return True
    return False


def get_max_sims(sim_info):
    number_of_sims = [sim for sim in services.sim_info_manager().instanced_sims_gen() if
                      sim.sim_info.routine_info.title == sim_info.routine_info.title and sim.sim_info.routine]
    return len(number_of_sims)


def remove_career_from_sim(career_name: str, sim_info):
    try:
        career_names = []
        career_type = None
        career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
        for career_id in career_manager.types:
            type = career_manager.get(career_id)
            career_names.append(type.__name__)
            if career_name == type.__name__:
                career_type = type
        sim_info.career_tracker.remove_career(career_type.guid64)
    except BaseException as e:
        error_trap(e)


def remove_all_careers(sim_info, filter=None):
    try:
        career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
        for career in career_manager.types:
            type = career_manager.get(career)
            name = type.__name__.lower()
            id = get_career_id(type.__name__)
            if id in sim_info.career_tracker._careers and str(filter) in name or \
                    id in sim_info.career_tracker._careers and not filter:
                remove_career_from_sim(type.__name__, sim_info)
    except BaseException as e:
        error_trap(e)


def get_career_name_from_string(name: str, not_name=None):
    try:
        career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
        for career in career_manager.types:
            type = career_manager.get(career)
            if name.lower() in type.__name__.lower() and not_name not in type.__name__.lower() and not_name:
                return (type.__name__)
            if name.lower() in type.__name__.lower() and not not_name:
                return (type.__name__)
        return None
    except BaseException as e:
        error_trap(e)


def get_trait_name_from_string(name: str, not_name=None):
    try:
        trait_manager = services.get_instance_manager(sims4.resources.Types.TRAIT)
        for trait in trait_manager.types:
            type = trait_manager.get(trait)
            if name.lower() in type.__name__.lower() and not_name not in type.__name__.lower() and not_name:
                return (type.__name__)
            if name.lower() in type.__name__.lower() and not not_name:
                return (type.__name__)
        return None
    except BaseException as e:
        error_trap(e)


def add_trait(potential_key: int, sim_info):
    try:
        instance_manager = services.get_instance_manager(Types.TRAIT)
        key = instance_manager.get(get_resource_key(potential_key, Types.TRAIT))
        if not sim_info.has_trait(key):
            sim_info.add_trait(key)
    except BaseException as e:
        error_trap(e)


def add_trait_by_name(name: str, sim_info):
    try:
        trait_manager = services.get_instance_manager(sims4.resources.Types.TRAIT)
        traits = [trait for trait in trait_manager.types.values() if
                  not sim_info.has_trait(trait) and name in str(trait)]
        if not traits:
            return
        for trait in traits:
            sim_info.add_trait(trait)
    except BaseException as e:
        error_trap(e)


def remove_trait(potential_key: int, sim_info):
    try:
        instance_manager = services.get_instance_manager(Types.TRAIT)
        key = instance_manager.get(get_resource_key(potential_key, Types.TRAIT))
        if sim_info.has_trait(key):
            sim_info.remove_trait(key)
    except BaseException as e:
        error_trap(e)


def add_career_to_sim(career_name: str, sim_info):
    try:
        career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
        for career_id in career_manager.types:
            type = career_manager.get(career_id)
            name = type.__name__.lower()
            id = get_career_id(type.__name__)
            if career_name.lower() in name:
                if id in sim_info.career_tracker._careers:
                    return None
                sim_info.career_tracker.add_career(type(sim_info))
                return career_name
        return None
    except BaseException as e:
        error_trap(e)


def fade_lights_in_live_mode(all_on=False, height_shift=2.0):
    try:
        CAW_Lights_because_tmex_is_lazy = get_config("lights.ini", "caw", "lights")
        lights = [obj for obj in services.object_manager().valid_objects() if obj.has_component(LIGHTING_COMPONENT) and
                  hasattr(obj, "zone_id") and hasattr(obj, "position")]
        for obj in lights:
            if obj:
                if obj.ceiling_placement:
                    if hasattr(obj, "position"):
                        target = obj.position
                        camera_pos = camera._camera_position
                        if hasattr(target, "y"):
                            if all_on:
                                obj.fade_opacity(1.0, 0.1)
                            elif camera_pos.y - height_shift > target.y:
                                obj.fade_opacity(0.0, 0.1)
                            else:
                                obj.fade_opacity(1.0, 0.1)
                if [light for light in CAW_Lights_because_tmex_is_lazy if
                    light == obj.definition.id or light == obj.id]:
                    if all_on:
                        obj.fade_opacity(1.0, 0.1)
                    else:
                        obj.fade_opacity(0.0, 0.1)
    except:
        pass


def use_uniform(sim, slot=0):
    robot_traits = sim.trait_tracker.get_traits_of_type(TraitType.ROBOT)
    if not robot_traits:
        picked_outfit = (OutfitCategory.CAREER, slot)
        if sim.sim_info.has_outfit(picked_outfit):
            sim.sim_info._current_outfit = picked_outfit


def update_interaction_tuning(id: int, entry: str, value):
    tuning_manager = services.get_instance_manager(Types.INTERACTION)
    # Get the SI tuning from the manager
    si = tuning_manager.get(id)
    if si is not None:
        # And set the allow_autonomous tuning entry
        setattr(si, entry, value)
        return True
    else:
        return False


def get_filters(filename):
    filters = []
    datapath = sc_Vars.config_data_location
    filename = datapath + r"\Data\{}.dat".format(filename)
    with open(filename, 'r') as file:
        data = file.read().replace("\n", "|").strip()
    if not data or not len(data):
        return None
    values = data.split("|")
    if len(values):
        for value in values:
            value = value.strip()
            if len(value):
                filters.append(value)
    else:
        filters.extend(data)
    if len(filters) == 0:
        return None
    return filters


def action_unclogger(sim, filters=None):
    if not filters:
        return
    now = services.time_service().sim_now
    for interaction in sim.get_all_running_and_queued_interactions():
        action = interaction.__class__.__name__.lower()
        if hasattr(interaction, "guid64"):
            action_id = interaction.guid64
        else:
            action_id = interaction.id
        if not hasattr(interaction, "interaction_timeout"):
            setattr(interaction, "interaction_timeout", now)
        elif not interaction.interaction_timeout:
            interaction.interaction_timeout = now
        elif filters:
            if [f for f in filters if f in action or f in str(action_id)] and \
                    now - interaction.interaction_timeout > date_and_time.create_time_span(
                minutes=sc_Vars.interaction_minutes_run):
                if sc_Vars.DEBUG:
                    debugger("Sim: {} - Timeout: {}".format(sim.first_name, action), 2, True)
                interaction.cancel(FinishingType.KILLED, 'Filtered')
        elif now - interaction.interaction_timeout > date_and_time.create_time_span(
                minutes=sc_Vars.interaction_minutes_run):
            if sc_Vars.DEBUG:
                debugger("Sim: {} - Timeout: {}".format(sim.first_name, action))
            interaction.cancel(FinishingType.KILLED, 'Filtered')


def get_action_timestamp(sim, action_id):
    try:
        action = None
        for interaction in sim.get_all_running_and_queued_interactions():
            if isinstance(action_id, int):
                if action_id == interaction.guid64:
                    action = interaction
            else:
                if action_id in str(interaction).lower():
                    action = interaction

        if hasattr(action, "interaction_timeout"):
            return action.interaction_timeout
        return None
    except BaseException as e:
        error_trap(e)


def action_timeout(sim, action_id, mins=3):
    try:
        action = None
        for interaction in sim.get_all_running_and_queued_interactions():
            if isinstance(action_id, int):
                if action_id == interaction.guid64:
                    action = interaction
            else:
                if action_id in str(interaction).lower():
                    action = interaction

        now = services.time_service().sim_now
        if not hasattr(action, "interaction_timeout"):
            setattr(action, "interaction_timeout", now)
        if action.interaction_timeout:
            if now - action.interaction_timeout > date_and_time.create_time_span(minutes=mins):
                if sc_Vars.DEBUG:
                    debugger("Cancel {}".format(str(action)))
                action.cancel(FinishingType.KILLED, 'Filtered')
                return True
        return False
    except BaseException as e:
        error_trap(e)


def remove_object_from_list(target, object_list):
    try:
        make_clean(target)
        new_list = []
        for obj in object_list:
            if obj.definition.id != target.definition.id:
                new_list.append(obj)
        return new_list
    except BaseException as e:
        error_trap(e)


def add_to_inventory(sim, obj):
    try:
        if sim is None:
            message_box(sim, obj, "Sim Inventory", "Can't add inventory of off lot sim!", "GREEN")
            return
        add_obj = objects.system.create_object(obj.definition.id)
        add_obj.set_household_owner_id(sim.household_id)
        if add_obj is None:
            message_box(sim, obj, "Sim Inventory", "Can't add object {}!".format(str(obj)), "GREEN")
            return
        inventory = sim.inventory_component
        if inventory.can_add(add_obj):
            inventory.player_try_add_object(add_obj)
            message_box(sim, add_obj, "Sim Inventory", "1 item(s) added to inventory!", "GREEN")
        else:
            if not build_buy.move_object_to_household_inventory(add_obj):
                message_box(sim, add_obj, "Sim Inventory", "Item NOT added to inventory!", "GREEN")
            else:
                message_box(sim, add_obj, "Sim Inventory", "Item added to household inventory!", "GREEN")
    except BaseException as e:
        error_trap(e)


def add_to_inventory_by_id(sim, obj_id, place_object=False):
    try:
        if sim is None:
            message_box(sim, None, "Sim Inventory", "Can't add inventory of off lot sim!", "GREEN")
            return None
        obj = objects.system.create_object(obj_id)
        if obj is None:
            message_box(sim, None, "Sim Inventory", "Can't add object {}!".format(str(obj)), "GREEN")
            return None
        obj.set_household_owner_id(sim.household_id)
        inventory = sim.inventory_component
        if inventory.can_add(obj):
            inventory.player_try_add_object(obj)
            message_box(sim, obj, "Sim Inventory", "1 item(s) added to inventory!", "GREEN")
            if place_object:
                push_sim_function(sim, obj, 12993, False)
            return obj
        else:
            if not build_buy.move_object_to_household_inventory(obj):
                message_box(sim, obj, "Sim Inventory", "Item NOT added to inventory!", "GREEN")
                return None
            else:
                message_box(sim, obj, "Sim Inventory", "Item added to household inventory!", "GREEN")
                return obj
    except BaseException as e:
        error_trap(e)


def is_in_sim_inventory(sim, id):
    obj = None
    count = 0
    for obj in sim.inventory_component:
        count += 1
        if id.isnumeric():
            if obj.definition.id == int(id):
                return True
        elif id in str(obj).lower():
            return True
    return False


def get_dust_action_and_vacuum(sim):
    if is_in_sim_inventory(sim, "vacuumcleaner"):
        return 257556
    vacuums = find_all_objects_by_title(sim, "vacuumcleaner")
    if vacuums:
        for vacuum in vacuums:
            if vacuum:
                if not is_in_sim_inventory(sim, "vacuumcleaner"):
                    add_to_inventory(sim, vacuum)
                return 257556
    return 13176


def create_dust(target=None):
    dust = objects.system.create_object(262732)

    if dust is not None:
        zone_id = services.current_zone_id()
        lot = services.active_lot()
        if not target:
            level = random.randint(lot.min_level, lot.max_level)
            lot_x_size = int(lot.size_x)
            lot_z_size = int(lot.size_z)
            lot_size = (lot_x_size + lot_z_size) * 0.5
            x = (lot_size * random.uniform(0.1, 0.5)) * math.cos(math.radians(random.uniform(0, 360)))
            z = (lot_size * random.uniform(0.1, 0.5)) * math.sin(math.radians(random.uniform(0, 360)))
            routing_surface = routing.SurfaceIdentifier(zone_id, level, routing.SurfaceType.SURFACETYPE_WORLD)
            y = get_terrain_height(lot.position.x + x, lot.position.z + z, routing_surface)
            translation = Vector3(lot.position.x + x, y, lot.position.z + z)
        else:
            level = target.level
            x = target.position.x
            z = target.position.z
            routing_surface = routing.SurfaceIdentifier(zone_id, level, routing.SurfaceType.SURFACETYPE_WORLD)
            y = get_terrain_height(x, z, routing_surface)
            translation = Vector3(x, y, z)

        orientation = Quaternion.ZERO()
        orientation = Quaternion(orientation.x, orientation.y + random.uniform(-1.0, 1.0),
                                 orientation.z, orientation.w)

        dust.location = Location(Transform(translation, orientation), routing_surface)
        dust.scale = random.uniform(1.0, 2.0)
        room = build_buy.get_room_id(zone_id, dust.position, dust.level)
        if room == 0:
            dust.destroy()
            dust = None
            return dust
        if dust.is_outside:
            dust.destroy()
            dust = None
            return dust
        return dust
    return None


def make_broken(obj):
    for commodity in obj.commodity_tracker:
        if "brokenness" in str(commodity).lower():
            commodity.set_value(0)
        if "calibrate" in str(commodity).lower():
            commodity.set_value(0)


def make_fixed(obj):
    for commodity in obj.commodity_tracker:
        if "brokenness" in str(commodity).lower():
            commodity.set_value(100)
        if "calibrate" in str(commodity).lower():
            commodity.set_value(100)


def set_object_state(obj, state, value):
    for commodity in obj.commodity_tracker:
        if state in str(commodity).lower():
            commodity.set_value(value)


def make_dirty(obj):
    if not obj:
        return
    if not hasattr(obj, "commodity_tracker"):
        return
    if "sink" not in obj.__class__.__name__.lower():
        if [test for test in services.object_manager().get_all() if
            distance_to(test, obj) <= 0.15 and "sink" in test.__class__.__name__.lower()]:
            return
    for commodity in obj.commodity_tracker:
        if "exambed_dirtiness" in str(commodity).lower():
            commodity.set_value(100)
        if "commodity_dirtiness" in str(commodity).lower():
            commodity.set_value(-100)


def make_clean(obj):
    if not obj:
        return
    if not hasattr(obj, "commodity_tracker"):
        return
    for commodity in obj.commodity_tracker:
        if "exambed_dirtiness" in str(commodity).lower():
            commodity.set_value(0)
        if "commodity_dirtiness" in str(commodity).lower():
            commodity.set_value(100)


def object_is_dirty(obj):
    try:
        if not obj:
            return False
        if not hasattr(obj, "commodity_tracker"):
            return False
        if obj.is_sim:
            return False
        if "trash_" in str(obj).lower():
            return True
        if "dustpile" in str(obj).lower():
            return True
        if "puddle" in str(obj).lower():
            return True
        if obj.commodity_tracker is None:
            return False
        for commodity in obj.commodity_tracker:
            value = commodity.get_value()
            if "commodity_freshness" in str(commodity).lower():
                if value < 1.0:
                    return True
            if "commodity_object_consumable" in str(commodity).lower():
                if value < 1.0:
                    return True
            if "exambed_dirtiness" in str(commodity).lower() and "_clean" in str(obj._super_affordances).lower():
                if value > 10:
                    return True
            elif "commodity_dirtiness" in str(commodity).lower() and "_clean" in str(obj._super_affordances).lower():
                if value < 90:
                    return True
        return False
    except BaseException as e:
        error_trap(e)


def find_all_objects_by_id(target,
                           id,
                           level=sc_Vars.MIN_LEVEL,
                           dist_limit=sc_Vars.MAX_DISTANCE,
                           dirty=False):
    try:
        if hasattr(id, "isnumeric"):
            if not id.isnumeric():
                return None
        object_list = [obj for obj in services.object_manager().get_all()
                       if not obj.is_outside and distance_to(target,
                                                             obj) < dist_limit and obj.level >= level and dirty and object_is_dirty(
                obj)
                       or not obj.is_outside and distance_to(target,
                                                             obj) < dist_limit and obj.level >= level and obj.definition.id == int(
                id)]

        if len(object_list):
            object_list.sort(key=lambda obj: distance_to_by_level(obj, target))
            return object_list
        return None
    except BaseException as e:
        error_trap(e)


def find_all_objects_by_title(target,
                              title,
                              level=sc_Vars.MIN_LEVEL,
                              dist_limit=sc_Vars.MAX_DISTANCE,
                              dirty=False):
    try:
        value = []
        if title != "":
            value = title.split("|")
        if len(value) == 0:
            object_list = [obj for obj in services.object_manager().get_all()
                if distance_to(target, obj) < dist_limit and obj.level >= level and title in str(obj).lower() and dirty and object_is_dirty(obj)
                or distance_to(target, obj) < dist_limit and obj.level >= level and title in str(obj).lower()
                or distance_to(target, obj) < dist_limit and obj.level >= level and title in str(obj.definition.id)]
        else:
            object_list = [obj for obj in services.object_manager().get_all()
                if distance_to(target, obj) < dist_limit and obj.level >= level and [v for v in value if v in str(obj).lower()] and dirty and object_is_dirty(obj)
                or distance_to(target, obj) < dist_limit and obj.level >= level and [v for v in value if v in str(obj).lower()]]

        if len(object_list):
            object_list.sort(key=lambda obj: distance_to_by_room(obj, target))
            return object_list
        return None
    except BaseException as e:
        error_trap(e)


def get_awake_hours(sim):
    try:
        random.seed(sim.sim_id)
        start = random.randint(6, 9)
        finish = random.randint(21, 24)
        if services.time_service().sim_now.hour() < start or \
                services.time_service().sim_now.hour() > finish - 1:
            return False
        return True
    except BaseException as e:
        error_trap(e)
        return True


def set_all_motives_by_sim(sim, value=100, motive_name=None):
    all_motives = [
        'motive_fun', 'motive_social', 'motive_hygiene', 'motive_hunger', 'motive_energy', 'motive_bladder']

    if motive_name is not None:
        cur_stat = get_tunable_instance((sims4.resources.Types.STATISTIC), motive_name, exact_match=True)
        tracker = sim.get_tracker(cur_stat)
        tracker.set_value(cur_stat, value)
        return
    for motive in all_motives:
        cur_stat = get_tunable_instance((sims4.resources.Types.STATISTIC), motive, exact_match=True)
        tracker = sim.get_tracker(cur_stat)
        tracker.set_value(cur_stat, value)


def assign_role_old(potential_key: int, sim_info):
    sim = init_sim(sim_info)
    if services.current_zone().is_zone_shutting_down:
        return
    try:
        role_tracker = sim.autonomy_component._role_tracker
        role_tracker.reset()
        new_role = services.role_state_manager().get(potential_key)
        clear_jobs(sim_info)
        if new_role:
            sim.add_role(new_role)
    except:
        clear_jobs(sim_info)
        pass


def assign_role(potential_key: int, sim_info):
    sim = init_sim(sim_info)
    if sim:
        clear_jobs(sim_info)
        new_role = services.role_state_manager().get(potential_key)
        if new_role:
            sim.add_role(new_role)


def assign_button(potential_key: int, obj):
    try:
        affordances = sc_Affordance(obj)
        if affordances.add_instance_id_to_object(potential_key):
            obj._super_affordances = affordances.affordance_instances
    except BaseException as e:
        error_trap(e)


def remove_button(potential_key: int, obj):
    try:
        affordances = sc_Affordance(obj)
        affordances.remove_instance_id_from_object(potential_key)
        obj._super_affordances = affordances.affordance_instances
    except BaseException as e:
        error_trap(e)


def function_options(option, class_name, function_name, suffix="_routine", custom_name="custom"):
    function = function_name.replace(" ", "_").replace("-", "_")
    function = function.lower() + suffix
    try:
        if not class_name:
            class_name = sys.modules[__name__]
        if not hasattr(class_name, function):
            function = custom_name + suffix
        method = getattr(class_name, function)
        result = method(option)
        return result
    except BaseException as e:
        debugger(str(function))
        error_trap(e)


def remove_sim(sim):
    client = services.client_manager().get_first_client()
    clear_sim_instance(sim.sim_info)
    sim_info = sim.sim_info
    sim_info.routine = False
    make_sim_unselectable(sim_info)
    clear_jobs(sim_info)
    assign_title(sim_info, "")
    sim_info_home_zone_id = sim_info.household.home_zone_id
    sim_info.inject_into_inactive_zone(sim_info_home_zone_id, skip_instanced_check=True)
    try:
        sim_info.save_sim()
    except:
        pass
    sim.schedule_destroy_asap(post_delete_func=(client.send_selectable_sims_update),
                              source=remove_sim,
                              cause='Destroying sim in travel liability')


def get_work_hours(start, finish):
    try:
        if sc_Vars.DISABLE_ROUTINE:
            return False
        if start == 0 and finish == 0:
            return True
        if services.time_service().sim_now.hour() < start or \
                services.time_service().sim_now.hour() > finish - 1:
            return False
        return True
    except BaseException as e:
        error_trap(e)
        return True


def add_sim_buff(buff_id: int, sim_info):
    try:
        buff_manager = services.get_instance_manager(Types.BUFF)
        type = buff_manager.get(get_resource_key(buff_id, Types.BUFF))
        if not type:
            return
        if sim_info.has_buff(type):
            return
        else:
            sim_info.debug_add_buff_by_type(type)
    except BaseException as e:
        error_trap(e)


def clear_all_buffs(sim_info):
    try:
        buff_manager = services.get_instance_manager(Types.BUFF)
        buffs = [buff for buff in buff_manager.types.values() if sim_info.has_buff(buff)]
        if not len(buffs):
            return
        for buff in buffs:
            if hasattr(buff, "guid64"):
                sim_info.remove_buff_by_type(buff_manager.get(get_resource_key(buff.guid64, Types.BUFF)))
    except BaseException as e:
        error_trap(e)


def get_room(obj):
    if not obj:
        return -1
    if hasattr(obj, "zone_id") and hasattr(obj, "position") and hasattr(obj, "level"):
        return build_buy.get_block_id(obj.zone_id if obj.zone_id else services.current_zone_id(), obj.position, obj.level)
    else:
        return -1


def get_room_by_position(position, level, x_offset=0.0, y_offset=0.0):
    return build_buy.get_block_id(services.current_zone_id(), Vector3(position.x + x_offset, position.y, position.z + y_offset), level)

def get_polygons():
    plex_service = services.get_plex_service()
    plex_id = plex_service.get_active_zone_plex_id() or INVALID_PLEX_ID
    return build_buy.get_all_block_polygons(plex_id).values()


def get_blocking_objects_gen(obj):
    result, errors, blocking_objects = build_buy.test_location_for_object(obj=obj, return_blocking_object_ids=True)
    if blocking_objects:
        for blocking_obj_id in blocking_objects:
            blocking_obj_id = blocking_obj_id[0]
            blocking_obj = services.object_manager().get(blocking_obj_id)
            yield blocking_obj
    yield None


def get_walls(obj):
    routing_surface = routing.SurfaceIdentifier(services.current_zone_id(), obj.level,
                                                routing.SurfaceType.SURFACETYPE_WORLD)
    return build_buy.get_wall_contours(obj.position.x, obj.position.z, routing_surface, True)


def compare_room(obj1, obj2):
    if get_room(obj1) == get_room(obj2):
        return True
    return False


def focus_camera_on_sim(sim_info):
    sim = sim_info.get_sim_instance()
    if sim is None:
        return
    camera.focus_on_sim(sim, follow=True)


def focus_camera_on_position(pos):
    camera.focus_on_position(pos)


def assign_title(sim_info, title):
    sim_info.sim_headline = LocalizationHelperTuning.get_raw_text(title)


def remove_sim_buff(buff_id: int, sim_info):
    try:
        buff_manager = services.get_instance_manager(Types.BUFF)
        if sim_info.has_buff(buff_manager.get(get_resource_key(buff_id, Types.BUFF))):
            sim_info.remove_buff_by_type(buff_manager.get(buff_id))
    except BaseException as e:
        error_trap(e)


def clear_jobs(sim_info):
    sim = init_sim(sim_info)
    if sim:
        try:
            situation_manager = services.get_zone_situation_manager()

            role_tracker = sim.autonomy_component._role_tracker
            role_tracker.reset()
            for situation in situation_manager.get_situations_sim_is_in(sim):
                job_title = "{}".format(situation.__class__.__name__)
                if (job_title.find('holiday') == -1) and (job_title.find('club') == -1) and (
                        job_title.find('butler') == -1):
                    situation_manager.destroy_situation_by_id(situation.id)
        except BaseException as e:
            error_trap(e)


def get_career_level(sim_info):
    try:
        level = 0
        for career in sim_info.career_tracker:
            if career is not None:
                if career.level > level:
                    level = career.level
        return level
    except BaseException as e:
        error_trap(e)


def set_autonomy(sim_info, routine=4):
    sim_info.autonomy = AutonomyState(routine)

# New private objects code
def get_private_objects(target, private_objects):
    object_list = [obj for obj in private_objects if check_private_objects(target, obj)]
    object_list.sort(key=lambda obj: distance_to_by_level(obj, target))
    return object_list


def is_allowed_privacy_role(sim):
    allowed_roles = get_config("spawn.ini", "spawn", "allowed")
    if [role for role in allowed_roles if has_role(sim, role)]:
        return True
    return False


def check_private_objects(sim, private_object):
    if not private_object:
        return False
    if sim.sim_info.routine:
        return False
    if distance_to_by_level(sim, private_object) < 10 and not is_allowed_privacy_role(sim):
        return True
    interaction_objects = [interaction.target for interaction in sim.get_all_running_and_queued_interactions() if
                           interaction.target]
    if not interaction_objects:
        return False
    if [obj for obj in interaction_objects if
        distance_to_by_level(private_object, obj) < 10] and not is_allowed_privacy_role(sim):
        return True
    return False


def check_interaction_on_private_objects(sim, target, interaction=None, debug=False):
    for obj in sc_Vars.private_objects:
        if target == obj and not is_allowed_privacy_role(sim) or distance_to_by_level(target, obj) < 10 and not is_allowed_privacy_role(sim):
            if debug:
                message_box(sim, target, str(interaction.__class__.__name__) if interaction else None,
                            str(target.__class__.__name__) if target else None)
            return False
    return True

def camera_is_near_private_objects(distance):
    near_camera_list = [obj for obj in sc_Vars.private_objects if distance_to_pos(obj.position, camera._target_position) < distance]
    if near_camera_list:
        return True
    return False

def unlock_for_sim(door, sim):
    lock_data = IndividualSimDoorLockData(unlock_sim=sim.sim_info, lock_priority=(LockPriority.PLAYER_LOCK),
                                          lock_sides=(LockSide.LOCK_BOTH), should_persist=True)
    door.add_lock_data(lock_data, replace_same_lock_type=False, clear_existing_locks=(ClearLock.CLEAR_NONE))


def get_locked_for_sim(door, sim):
    if sim not in door.get_disallowed_sims():
        return False
    return True


def get_routable_for_sim(target, sim):
    doors = [obj for obj in services.object_manager().get_all() if obj.has_component(PORTAL_LOCKING_COMPONENT)]
    if not doors:
        return False
    doors = [obj for obj in doors if get_room_by_position(obj.position, obj.level, 0.5 * obj.forward.x, 0.5 * obj.forward.z) == get_room(target) or
             get_room_by_position(obj.position, obj.level, -0.5 * obj.forward.x, -0.5 * obj.forward.z) == get_room(target)]
    if doors:
        if any(not get_locked_for_sim(door, sim) for door in doors):
            return True
    return False


def assign_role_title(sim):
    title_filter = ["lt:", "ya ", "littlemssam:", "visiting", "player", "turbodriver:", "wickedwhims", "autonomy",
                    "petworld", " walker", " walk", "rolestates",
                    "rolestate", "basictrait", "island", "situations", "state", "hospital", "generic", "background",
                    "open streets", "openstreets",
                    "openstreet", "master", "fanstan", "sim", "roles", "role", "venue", "start", "playersim",
                    "fleamarket", "openstreets", "marketstalls",
                    "npc", "situation", "dj", "packb"]
    role_name = None
    if not hasattr(sim, "autonomy_component"):
        return
    if not hasattr(sim.autonomy_component, "active_roles"):
        return
    for role in sim.autonomy_component.active_roles():
        role_name = str(role.__class__.__name__)
        if "club_gathering" in role_name.lower():
            return
        role_name = role_name.replace("_", " ").lower()
        role_name = role_name.replace('"', "")
        for title in title_filter:
            role_name = role_name.replace(title, "")
            role_name = role_name.replace("  ", " ").lower()
        role_name = " ".join(set(role_name.split(" ")))
    if role_name:
        assign_title(sim.sim_info, role_name.strip().title())
    else:
        assign_title(sim.sim_info, "")


def assign_routine(sim_info, title, clear_state=True, set_title=True, assign=True):
    roles = [role for role in sc_Vars.roles if title in role.title]
    if roles:
        sim_info.routine_info = roles[0]
        sim_info.choice = 0
        if clear_state:
            sim_info.routine = False
            clear_jobs(sim_info)
            clear_all_buffs(sim_info)
            for button in sim_info.routine_info.role_buttons:
                remove_button(button, sim_info.get_sim_instance())
            assign_title(sim_info, "")
        if assign:
            sim_info.routine = True
            for buff in list(sim_info.routine_info.buffs):
                add_sim_buff(int(buff), sim_info)
            add_sim_buff(182697, sim_info)
            for button in sim_info.routine_info.role_buttons:
                assign_button(button, sim_info.get_sim_instance())
            assign_role(sim_info.routine_info.role, sim_info)
        if set_title:
            assign_title(sim_info, sim_info.routine_info.title.title())


def unassign_role_old(potential_key: int, sim_info):
    sim = init_sim(sim_info)
    if services.current_zone().is_zone_shutting_down:
        return
    try:
        role_tracker = sim.autonomy_component._role_tracker
        role_tracker.reset()
        clear_jobs(sim_info)
        new_role = services.role_state_manager().get(potential_key)
        if new_role:
            sim.remove_role(new_role)
    except:
        pass


def unassign_role(potential_key: int, sim_info):
    sim = init_sim(sim_info)
    if sim:
        roles = sim.autonomy_component.active_roles()
        role_list = []
        for role in roles:
            if potential_key != role.guid64:
                role_list.append(role.guid64)
        role_tracker = sim.autonomy_component._role_tracker
        role_tracker.reset()
        for role in role_list:
            assign_role(role, sim.sim_info)


def clear_leaving(sim):
    if "leave" in get_sim_role(sim):
        remove_sim_role(sim, "leave")
    if check_actions(sim, "leave"):
        clear_sim_instance(sim.sim_info, "leave|gohere")


def pause_routine(timeout):
    now = time.time()
    if not sc_Vars.timestamp:
        sc_Vars.timestamp = now
    if now - sc_Vars.timestamp < (timeout * 60.0):
        return True
    sc_Vars.timestamp = now
    return False


def get_sim_travel_group(sim_info, is_target):
    travel_group = sim_info.travel_group
    if travel_group is None:
        if not is_target:
            travel_group = sim_info.household.get_travel_group()
    if travel_group is not None:
        return travel_group
    return None


def get_number_of_sims(all_sims=False):
    if not all_sims:
        sims = [sim for sim in services.sim_info_manager().instanced_sims_gen() if not has_role(sim, "leave")]
    else:
        sims = [sim for sim in services.sim_info_manager().instanced_sims_gen()]
    return len(sims)


def get_number_of_role_sims():
    sims = [sim for sim in services.sim_info_manager().instanced_sims_gen() if
            not has_role(sim, "leave") and has_role(sim)]
    return len(sims)


def get_number_of_routine_sims(title=None):
    sims = [sim for sim in services.sim_info_manager().instanced_sims_gen() if sim.sim_info.routine]
    sims = [sim for sim in sims if title and title in sim.sim_info.routine_info.title or not title]
    return len(sims)


def get_number_of_non_routine_sims():
    sims = [sim for sim in services.sim_info_manager().instanced_sims_gen() if not sim.sim_info.routine]
    return len(sims)


def get_venue():
    active_venue = services.venue_service().active_venue
    venue_name = clean_string(str(active_venue).lower())
    return venue_name


def check_actions(sim, action):
    for interaction in sim.get_all_running_and_queued_interactions():
        if isinstance(action, int):
            if action == interaction.guid64:
                return True
        else:
            if action in str(interaction).lower():
                return True
    return False


def only_this_action(sim, action):
    if isinstance(action, int):
        if all(str(action) in str(interaction.guid64) for interaction in sim.get_all_running_and_queued_interactions()):
            return True
    else:
        if all(action in str(interaction).lower() for interaction in sim.get_all_running_and_queued_interactions()):
            return True
    return False


def doing_nothing(sim):
    if not sim:
        return False
    if not hasattr(sim, "get_all_running_and_queued_interactions"):
        return False
    if all("sit" in str(interaction).lower() for interaction in sim.get_all_running_and_queued_interactions()) or \
            all("stand" in str(interaction).lower() for interaction in sim.get_all_running_and_queued_interactions()):
        return True
    return False


def check_action_list(sim, action_list):
    if [action for action in action_list if
        [interaction for interaction in sim.get_all_running_and_queued_interactions()
         if action in str(interaction.guid64) or action in str(interaction).lower()]]:
        return True
    return False


def set_all_motives(value=100, motive_name=None):
    all_motives = [
        'motive_fun', 'motive_social', 'motive_hygiene', 'motive_hunger', 'motive_energy', 'motive_bladder']
    all_sims = services.sim_info_manager().instanced_sims_gen()
    for sim in all_sims:
        for motive in all_motives:
            cur_stat = get_tunable_instance((sims4.resources.Types.STATISTIC), motive, exact_match=True)
            tracker = sim.get_tracker(cur_stat)
            if motive == motive_name and motive_name is not None:
                tracker.set_value(cur_stat, value)
            else:
                tracker.set_value(cur_stat, 100)


def clear_all_actions():
    all_sims = services.sim_info_manager().instanced_sims_gen()
    for sim in all_sims:
        clear_sim_instance(sim.sim_info, "skate|sit|tv|computer|frontdesk|stereo|dance|sleep|nap", True)


def reset_all_sims():
    for sim in services.sim_info_manager().instanced_sims_gen(allow_hidden_flags=(objects.ALL_HIDDEN_REASONS)):
        situation_manager = services.get_zone_situation_manager()
        for situation in situation_manager.get_situations_sim_is_in(sim):
            job_title = "{}".format(situation.__class__.__name__)
            if (job_title.find('holiday') == -1) and (job_title.find('club') == -1):
                situation_manager.destroy_situation_by_id(situation.id)
        role_tracker = sim.autonomy_component._role_tracker
        role_tracker.reset()
        situation_manager.create_visit_situation(sim)
        sim.reset(ResetReason.NONE, None, 'Command')


def get_important_objects_on_lot():
    street_slab_ids = [10187084955449712340, 14186679418776011434, 13228907805291488430, 11847614138216790047]
    venue = get_venue()
    sc_Vars.stereos_on_lot = [obj for obj in services.object_manager().get_all() if "stereo" in str(obj).lower()]
    sc_Vars.beds_on_lot = [obj for obj in services.object_manager().get_all() if "object_bed" in str(obj).lower()]
    sc_Vars.street_slabs = [obj for obj in services.object_manager().get_all() if
                            [slab for slab in street_slab_ids if obj.definition.id == slab]]
    # New private objects code
    sc_Vars.private_objects = []
    if "residential" in venue or "rentable" in venue or "clinic" in venue:
        sc_Vars.private_objects = [obj for obj in
                                   services.object_manager().get_all_objects_with_component_gen(LIGHTING_COMPONENT)
                                   if obj.is_on_active_lot() and not obj.is_outside]


@sims4.commands.Command('stats.solve_motive', command_type=(sims4.commands.CommandType.Live))
def solve_motive(stat_type: TunableInstanceParam((sims4.resources.Types.STATISTIC), exact_match=True),
                 opt_sim: OptionalTargetParam = None, _connection=None):
    try:
        sim = get_optional_target(opt_sim, _connection)
        if sim is None or stat_type is None:
            debugger('Unable to identify Sim or Motive - invalid arguments.')
            return
        if sim.commodity_tracker is None:
            debugger('Unable to solve motive - sim info has no commodity tracker.')
            return
        stat = sim.commodity_tracker.get_statistic(stat_type)
        if stat is None:
            debugger('Unable to solve motive {} on the Sim .'.format(stat_type))
            return
        if not sim.queue.can_queue_visible_interaction():
            debugger('Interaction queue is full, cannot add anymore interactions.')
            return
        context = InteractionContext(sim, (InteractionContext.SOURCE_AUTONOMY), (priority.Priority.High),
                                     bucket=(InteractionBucketType.DEFAULT))
        autonomy_request = AutonomyRequest(sim, autonomy_mode=FullAutonomy, commodity_list=[
            stat],
                                           context=context,
                                           consider_scores_of_zero=True,
                                           posture_behavior=(AutonomyPostureBehavior.IGNORE_SI_STATE),
                                           is_script_request=True,
                                           allow_opportunity_cost=False,
                                           autonomy_mode_label_override='AutoSolveMotive')
        selected_interaction = services.autonomy_service().find_best_action(autonomy_request)
        if selected_interaction is None:
            commodity_interaction = stat_type.commodity_autosolve_failure_interaction
            if commodity_interaction is None:
                return
            if not sim.queue.has_duplicate_super_affordance(commodity_interaction, sim, None):
                failure_aop = AffordanceObjectPair(commodity_interaction, None, commodity_interaction, None)
                failure_aop.test_and_execute(context)
            debugger('Could not find a good interaction to solve {}.'.format(stat_type))
            return
        if sim.queue.has_duplicate_super_affordance(selected_interaction.affordance, sim, selected_interaction.target):
            debugger('Duplicate Interaction in the queue.')
            return
        if not AffordanceObjectPair.execute_interaction(selected_interaction):
            debugger('Failed to execute SI {}.'.format(selected_interaction))
            return
        debugger('Successfully executed SI {}.'.format(selected_interaction))
    except BaseException as e:
        error_trap(e)


def advance_game_time(hours: int = 0, minutes: int = 0, seconds: int = 0, _connection=None):
    services.game_clock_service().advance_game_time(hours, minutes, seconds)
    services.game_clock_service()._sync_clock_and_broadcast_gameclock(True)
    set_all_motives()
    clear_all_actions()


def advance_game_time_and_timeline(hours: int = 0, minutes: int = 0, seconds: int = 0):
    services.game_clock_service().advance_game_time(hours, minutes, seconds)
    services.time_service().sim_timeline = scheduling.Timeline(services.game_clock_service().now())
    services.game_clock_service()._sync_clock_and_broadcast_gameclock(True)
    set_all_motives()
    reset_all_sims()


def advance_game_time_complete(hours: int = 0, minutes: int = 0, seconds: int = 0):
    persistence_service = services.get_persistence_service()
    services.game_clock_service().advance_game_time(hours, minutes, seconds)
    services.time_service().sim_timeline = scheduling.Timeline((services.game_clock_service().now()))
    services.time_service().wall_clock_timeline = scheduling.Timeline((services.server_clock_service().now()))
    services.time_service().sim_timeline.on_time_advanced.append(caches.clear_all_caches)
    persistence_service._destroy_save_timeline(persistence_service.save_timeline)
    persistence_service.save_timeline = scheduling.Timeline(services.time_service().sim_now)
    services.game_clock_service()._sync_clock_and_broadcast_gameclock(True)
    set_all_motives()
    reset_all_sims()


def set_season_and_time(season: SeasonType, time_in_minutes=None):
    services.season_service().reset_region_season_params()
    services.season_service().set_season(season, SeasonSetSource.CHEAT, time_in_minutes)
    services.weather_service().reset_forecasts()


def get_number_of_objects():
    objects = services.object_manager().get_all()
    return len(objects)


def get_object_pos(obj):
    if obj is None:
        return
    translation = obj.location.transform.translation
    return translation


def get_object_rotate(obj):
    if obj is None:
        return
    orientation = obj.location.transform.orientation
    return orientation


def reset_in_use_by(obj):
    translation = obj.location.transform.translation
    level = obj.location.level
    orientation = obj.location.transform.orientation
    zone_id = services.current_zone_id()
    routing_surface = routing.SurfaceIdentifier(zone_id, level, routing.SurfaceType.SURFACETYPE_WORLD)
    clone = objects.system.create_object(obj.definition.id)
    clone.location = sims4.math.Location(sims4.math.Transform(translation, orientation),
                                         routing_surface)

    obj.destroy()


def get_guid64(tunable):
    try:
        return getattr(tunable, 'guid64', 0)
    except:
        return 0
        pass


def search_config_option(filename, search_option, search_value):
    datapath = sc_Vars.config_data_location
    filename = datapath + r"\Data\{}".format(filename)
    if not os.path.exists(filename):
        return None
    config = configparser.ConfigParser()
    config.read(filename)
    for section in config.sections():
        if search_option.lower() in str(section).lower():
            for (option, value) in config.items(section):
                if str(search_value).lower() in str(value).lower():
                    return get_config(filename, section, option)
    return None


def search_config_section(filename, search, option):
    datapath = sc_Vars.config_data_location
    filename = datapath + r"\Data\{}".format(filename)
    if not os.path.exists(filename):
        return None
    config = configparser.ConfigParser()
    config.read(filename)
    sections = [section for section in config.sections() if search.lower() in str(section).lower()]
    if sections:
        for section in sections:
            return get_config(filename, section, option)
    return None


def get_sim_info(sim=None):
    try:
        client = services.client_manager().get_first_client()
        zone = services.current_zone()
        sim_id = None
        if sim is None:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
            sim_info = sim.sim_info
            sim_id = client.id
        elif sim.is_sim:
            client = services.client_manager().get_first_client()
            sim_info = sim.sim_info
            sim_id = client.id

        roleStateName = "None"
        buffStateName = "None"
        intQueue = ""
        activeCareer = ""
        career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
        for career_id in sim_info.career_tracker._careers:
            career = sim_info.career_tracker._careers[career_id]
            if career is not None:
                type = career_manager.get(career_id)
                activeCareer = activeCareer + type.__name__ + " ({}) Level: {} ".format(career_id, career.level)
            else:
                activeCareer = "None"
        activeRoles = sim.autonomy_component.active_roles()
        activeBuffs = sim.sim_info.Buffs
        getInteractions = sim.get_all_running_and_queued_interactions()

        for i, roleState in enumerate(activeRoles):
            if i == 0:
                roleStateName = "({}) {}\n".format(roleState.guid64, roleState.__class__.__name__)
            else:
                roleStateName = roleStateName + "({}) {}\n".format(roleState.guid64, roleState.__class__.__name__)

        for i, BuffList in enumerate(activeBuffs):
            if not hasattr(BuffList, "guid64"):
                setattr(BuffList, "guid64", 0)
            if i == 0:
                buffStateName = "({}) {}\n".format(BuffList.guid64, BuffList.__class__.__name__)
            else:
                buffStateName = buffStateName + "({}) {}\n".format(BuffList.guid64, BuffList.__class__.__name__)

        trait_list = ""
        for i, trait in enumerate(sim_info.trait_tracker):
            if i == 0:
                trait_list = str(trait.__name__)
            else:
                trait_list = trait_list + '\n' + str(trait.__name__)

        for i, interaction in enumerate(getInteractions):
            intQueue = intQueue + "({}/{}) {}\n".format(get_guid64(interaction), interaction.id,
                                                        interaction.__class__.__name__)

        sim_info.update_time_alive()
        time_alive = sim_info._time_alive.in_days()
        feud_target = sim.get_feud_target()
        if feud_target is not None:
            feud_target_name = "{} {}".format(feud_target.first_name, feud_target.last_name)
        else:
            feud_target_name = None
        mood = sim_info.get_mood()
        if mood is not None:
            sim_mood = mood.guid64
        else:
            sim_mood = 0

        try:
            room = build_buy.get_room_id(sim.zone_id, sim.position, sim.level)
        except:
            room = 0
            pass

        selected_sims = [(_info.first_name + " " + _info.last_name) for _info in
                         client._selectable_sims._selectable_sim_infos]
        routine_choice = list(sim_info.routine_info.routine)[sim_info.choice] if sim_info.routine else None

        returnText = "[Name:] {} {}\n" \
                     "[ID:] {}\n" \
                     "[Age:] {}\n" \
                     "[Active Household:] {}\n" \
                     "[Active:] {}\n" \
                     "[Routine:] {}\n" \
                     "[Career:] {}\n" \
                     "[Role({}):] {}\n" \
                     "[Interactions:]\n{}\n" \
                     "[Mood:] {}\n[Age:] {} Days\n[Room:] {}\n[Level:] {}\n[Zone ID:] {}\n" \
                     "[Pos:] {}, {}, {}\n[Orient:] {}\n" \
                     "[Selected Sims:] {}\n" \
                     "[Tracker:] {}\n" \
                     "[Buffs:]\n{}\n" \
            .format(sim_info.first_name, sim_info.last_name, sim_info.sim_id,
                    get_sim_age(sim_info),
                    sim_info.household.home_zone_id,
                    not doing_nothing(sim),
                    routine_choice,
                    activeCareer,
                    len(sim.autonomy_component.active_roles()),
                    roleStateName,
                    intQueue,
                    mood.__name__, time_alive, room, sim.level, zone.id,
                    sim.position.x, sim.position.y, sim.position.z, get_object_rotate(sim),
                    selected_sims,
                    str(sim_info.tracker),
                    buffStateName)

        return returnText
    except BaseException as e:
        error_trap(e)


def get_tag_name(tag):
    if not isinstance(tag, Tag):
        try:
            tag = Tag(tag)
        except:
            return str(tag)
            pass
    return tag.name


def get_tag_ids(id) -> list:
    return list(set(build_buy.get_object_all_tags(id)))


def get_tags_from_id(id) -> str:
    target_object_tags = list(set(build_buy.get_object_all_tags(id)))
    if target_object_tags:
        for tag in target_object_tags:
            tag_title = get_tag_name(tag)
            target_object_tags.append(tag_title)
            return clean_string(str(target_object_tags))
    return ""


def get_tags_from_object(obj) -> str:
    target_object_tags = []
    object_tags_by_name = [str(Tag(object_tag)) if type(object_tag) is int else str(object_tag) for object_tag in
                           obj.get_tags()]
    if object_tags_by_name:
        for tag in object_tags_by_name:
            target_object_tags.append(tag)
            return clean_string(str(target_object_tags))
    return ""


def set_exam_info(sim_info):
    if sim_info.is_instanced():
        exams = [exam for exam in sc_Vars.exam_list if exam.patient == sim_info.get_sim_instance()]
        if exams:
            sim_info.exam_info = exams[0]


def get_career(sim_info):
    try:
        career = None
        # career_id = ld_jobs.get_career_id("career_Adult_Active_Doctor")
        for career_id in sim_info.career_tracker._careers:
            career = sim_info.career_tracker._careers[career_id]
            # ld_notice(sim_info, "get_career", "career_id: {}".format(career_id))
            if career is not None:
                return career_id
        return False
    except BaseException as e:
        error_trap(e)


def get_career_id(career_name: str):
    try:
        career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
        for career_id in career_manager.types:
            type = career_manager.get(career_id)
            if (type.__name__) == career_name:
                return type.guid64
        return False
    except BaseException as e:
        error_trap(e)


def get_career_name(sim_info, return_bool=True):
    try:
        career_info = None
        career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
        for career in career_manager.types:
            type = career_manager.get(career)
            id = get_career_id(type.__name__)
            if id in sim_info.career_tracker._careers and "batuu" not in str(type.__name__).lower():
                career_info = sim_info.career_tracker._careers[id]
                if career_info is not None:
                    return (type.__name__)
        if return_bool:
            return False
        else:
            return "No_Career"
    except BaseException as e:
        error_trap(e)


def has_role(sim, name=""):
    if not hasattr(sim, "autonomy_component"):
        return False
    if not hasattr(sim.autonomy_component, "active_roles"):
        return False
    if name == "":
        if len(sim.autonomy_component.active_roles()):
            return True
        return False
    if [role for role in sim.autonomy_component.active_roles() if name in str(role).lower()]:
        return True
    return False


def get_sim_role(sim) -> str:
    try:
        role_title = ""
        if not hasattr(sim, "autonomy_component"):
            return role_title
        if not hasattr(sim.autonomy_component, "active_roles"):
            return role_title
        if len(sim.autonomy_component.active_roles()):
            roles = sim.autonomy_component.active_roles()
            for role in roles:
                role_title = role_title + "({}) {}\n".format(role.guid64, role.__class__.__name__.lower())
            return role_title
        return "None\n"
    except BaseException as e:
        error_trap(e)


def remove_sim_role(sim, role_title):
    roles = sim.autonomy_component.active_roles()
    role_list = []
    [role_list.append(role.guid64) for role in roles if role_title not in role.__class__.__name__.lower()]
    clear_jobs(sim.sim_info)
    for role in role_list:
        assign_role(role, sim.sim_info)

def create_time_span(days=0, hours=0, minutes=0, seconds=0):
    num_sim_seconds = days * date_and_time.SECONDS_PER_DAY + hours * date_and_time.SECONDS_PER_HOUR + \
        minutes * date_and_time.SECONDS_PER_MINUTE + seconds
    time_in_ticks = num_sim_seconds * date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND
    return date_and_time.TimeSpan(time_in_ticks)

def is_sim_in_group(sim):
    sim_info = None
    if hasattr(sim, "is_instanced"):
        sim_info = sim
        sim = init_sim(sim_info)
    else:
        sim_info = sim.sim_info
    if not sim:
        return False
    ensemble_service = services.ensemble_service()
    ensemble = ensemble_service.get_visible_ensemble_for_sim(sim)
    if ensemble is not None:
        if ensemble.is_sim_in_ensemble(sim):
            return True
    if has_role(sim, "club_gathering"):
        return True
    return False


def clear_sim_instance(sim_info, filter=None, all_but_filter=False):
    try:
        sim = init_sim(sim_info)
        if not sim:
            return
        if isinstance(filter, str):
            if "|" in filter:
                filter = list(filter.split("|"))
        for i, interaction in enumerate(sim.get_all_running_and_queued_interactions()):
            title = interaction.__class__.__name__
            try:
                if not hasattr(interaction, 'guid64'):
                    interaction.guid64 = sims4.hash_util.hash64(title)
                id = interaction.guid64
            except:
                id = interaction.id
                pass
            title = title.lower()
            if not filter:
                interaction.cancel(FinishingType.RESET, 'Stop')
            elif all_but_filter:
                if isinstance(filter, list):
                    if not [f for f in filter if f in title or f in str(id)]:
                        if sc_Vars.tag_sim_for_debugging:
                            name = "{} {}".format(sim.first_name, sim.last_name)
                            if name in sc_Vars.tag_sim_for_debugging:
                                debugger("All But Filter List: {}".format(title), 2, True)
                        interaction.cancel(FinishingType.RESET, 'Stop')
                elif str(filter) not in title and str(filter) not in str(id):
                    if sc_Vars.tag_sim_for_debugging:
                        name = "{} {}".format(sim.first_name, sim.last_name)
                        if name in sc_Vars.tag_sim_for_debugging:
                            debugger("All But Filter: {}".format(title), 2, True)
                    interaction.cancel(FinishingType.RESET, 'Stop')
            elif isinstance(filter, list):
                if [f for f in filter if f in title or f in str(id)]:
                    if sc_Vars.tag_sim_for_debugging:
                        name = "{} {}".format(sim.first_name, sim.last_name)
                        if name in sc_Vars.tag_sim_for_debugging:
                            debugger("Filter List: {}".format(title), 2, True)
                    interaction.cancel(FinishingType.RESET, 'Stop')
            elif str(filter) in title or str(filter) in str(id):
                if sc_Vars.tag_sim_for_debugging:
                    name = "{} {}".format(sim.first_name, sim.last_name)
                    if name in sc_Vars.tag_sim_for_debugging:
                        debugger("Filter: {}".format(title), 2, True)
                interaction.cancel(FinishingType.RESET, 'Stop')
    except BaseException as e:
        error_trap(e)


def clear_sim_instance_old(sim_info, filter=None, all_but_filter=False):
    try:
        sim = init_sim(sim_info)
        exact_match = False
        action = ""
        if filter is None:
            filter = ""
        if isinstance(filter, int):
            exact_match = True
        else:
            filter = filter.lower()
            value = filter.split("|")
            if len(value) == 0:
                value = [filter, ""]
        if not sim:
            return
        for i, interaction in enumerate(sim.get_all_running_and_queued_interactions()):
            if interaction is not None:
                title = interaction.__class__.__name__
                title = title.lower()
                id = interaction.guid64

                if exact_match and not all_but_filter:
                    if interaction.guid64 == filter:
                        action = action + "{} was cancelled.\n".format(str(interaction))
                        interaction.cancel(FinishingType.RESET, 'Stop')
                elif exact_match and all_but_filter:
                    if interaction.guid64 != filter:
                        action = action + "{} was cancelled.\n".format(str(interaction))
                        interaction.cancel(FinishingType.RESET, 'Stop')
                elif all_but_filter is False and filter != "":
                    cancel = False
                    for v in value:
                        if v in title and v != "" or v in str(id) and v != "":
                            cancel = True
                    if cancel is True:
                        action = action + "{} was cancelled.\n".format(str(interaction))
                        interaction.cancel(FinishingType.RESET, 'Stop')

                elif filter != "":
                    cancel = True
                    for v in value:
                        if v in title and v != "" or v in str(id) and v != "":
                            cancel = False
                    if cancel is True:
                        action = action + "{} was cancelled.\n".format(str(interaction))
                        interaction.cancel(FinishingType.RESET, 'Stop')
                else:
                    action = action + "{} was cancelled.\n".format(str(interaction))
                    interaction.cancel(FinishingType.RESET, 'Stop')
    except BaseException as e:
        error_trap(e)


def clear_queue_of_duplicates(sim):
    try:
        dupes = [action for action in sim.get_all_running_and_queued_interactions() if
                 [i for i in sim.get_all_running_and_queued_interactions() if i.guid64 == action.guid64 and
                  i.id != action.id]]
        for i, interaction in enumerate(dupes):
            name = interaction.__class__.__name__.lower()
            if i > 0:
                interaction.cancel(FinishingType.KILLED, 'Stop')
    except BaseException as e:
        error_trap(e)


def clear_sim_queue_of(sim_info, interaction_name):
    try:
        sim = init_sim(sim_info)
        for interaction in sim.get_all_running_and_queued_interactions():
            name = interaction.__class__.__name__.lower()
            id = interaction.guid64
            if interaction is not None:
                if interaction_name in name or interaction_name in str(id):
                    interaction.cancel(FinishingType.KILLED, 'Stop')
    except BaseException as e:
        error_trap(e)

def get_angle(v1, v2):
    return math.atan2(v1.x - v2.x, v1.z - v2.z)

def vector_magnify(v, m):
    return Vector3(v.x * m, v.y * m, v.z * m)

def point_object_at(orig, target):
    point = target.position
    angle = get_angle(point, orig.position)
    level = orig.level
    orientation = sims4.math.angle_to_yaw_quaternion(angle)
    zone_id = services.current_zone_id()
    routing_surface = routing.SurfaceIdentifier(zone_id, level, routing.SurfaceType.SURFACETYPE_WORLD)
    orig.location = sims4.math.Location(Transform(orig.position, orientation), routing_surface)

def face_sim(sim, target):
    sim_direction = sim.position - target.position
    sim_direction = vector_normalize(sim_direction)
    sim_distance = distance_to_pos(sim.position, target.position)
    sim_move_vector = sim.position - vector_magnify(sim_direction, 0.1 * sim_distance)
    return Vector3(sim_move_vector.x, get_terrain_height(sim_move_vector.x, sim_move_vector.z),
                sim_move_vector.z)

def get_random_radius_position(center, radius):
    alpha = 2 * math.pi * random.random()
    r = radius * math.sqrt(random.random())
    x = r * math.cos(alpha) + center.x
    z = r * math.sin(alpha) + center.z
    y = get_terrain_height(x, z)
    return Vector3(x, y, z)

def distance_to_pos(target, dest):
    return (target - dest).magnitude_2d()


def distance_to_math(target, dest):
    return fabs(sqrt((target.x - dest.x) * (target.x - dest.x) +
                     (target.y - dest.y) * (target.y - dest.y) +
                     (target.z - dest.z) * (target.z - dest.z)))


def distance_to(target, dest):
    if target is None or dest is None:
        return -1
    return (target.position - dest.position).magnitude()


def distance_to_by_room(target, dest):
    if target is None or dest is None:
        return -1
    d = (target.position - dest.position).magnitude_2d()
    try:
        target_room = build_buy.get_room_id(target.zone_id, target.position, target.level)
        dest_room = build_buy.get_room_id(dest.zone_id, dest.position, dest.level)
        if target_room != dest_room:
            d = d + 1024
    except:
        return d
    return d


def objects_by_room(target):
    if target is None:
        return None
    if not hasattr(target, "position"):
        return None
    target_room = get_room_by_position(target.position, target.level)
    return [obj for obj in services.object_manager().valid_objects() if
            get_room_by_position(obj.position, obj.level, 0.5 * obj.forward.x, 0.5 * obj.forward.z) == target_room or
            get_room_by_position(obj.position, obj.level, -0.5 * obj.forward.x, -0.5 * obj.forward.z) == target_room or
            get_room_by_position(obj.position, obj.level) == target_room]


def distance_from_spawn(target, spawn):
    if target is None or spawn is None:
        return -1
    d = (target.position - spawn._center).magnitude_2d()
    if hasattr(target, 'level'):
        if target.level != 0:
            d = d + 1024
    return d


def distance_to_by_level(target, dest):
    if target is None or dest is None:
        return -1
    d = (target.position - dest.position).magnitude_2d()
    if target.level != dest.level:
        d = d + 1024
    return d


def clamp(n, smallest, largest): return max(smallest, min(n, largest))

def get_object_info(target, long_version=False):
    client = services.client_manager().get_first_client()
    zone_id = services.current_zone_id()
    zone_info = services.current_zone_info()
    zone = services.current_zone()
    persistence_service = services.get_persistence_service()
    zone_data = persistence_service.get_zone_proto_buff(zone_id)
    world_id = zone_data.world_id
    region_id = persistence_service.get_region_id_from_world_id(world_id)
    object_tuning = services.definition_manager().get(target.definition.id)
    object_class = clean_string(str(object_tuning._cls))

    obj_room_id = get_room(target)
    dirty = 100
    commodity_list = ""
    if hasattr(target, "commodity_tracker"):
        commodity_tracker = target.commodity_tracker
        if commodity_tracker is None:
            dirty = 100
        else:
            for commodity in target.commodity_tracker:
                commodity_list += str(commodity) + "\n"
                if "commodity_dirtiness" in str(commodity).lower():
                    dirty = commodity.get_value()
    else:
        dirty = 100
    if hasattr(target, "footprint_polygon"):
        object_width = target.footprint_polygon.radius()
    else:
        object_width = 1.0
    if hasattr(target, "slots_resource"):
        slots_resource = None
    else:
        slots_resource = None
    if hasattr(target, "_opacity"):
        opacity = target._opacity
    else:
        opacity = 1
    if hasattr(target, "scale"):
        scale = target.scale
    else:
        scale = 1
    if hasattr(target, "get_disallowed_sims"):
        locked = get_locked_for_sim(target, client.active_sim)
    else:
        locked = None

    routable = get_routable_for_sim(target, client.active_sim)

    if hasattr(target, "__file__"):
        filename = target.__file__
    else:
        filename = None
    if hasattr(target, "parent"):
        location_information = str(target.parent)

        if "[" in location_information:
            value = location_information[location_information.find(":0x") + 3:location_information.rfind("[")]
        else:
            value = location_information[location_information.find(":0x") + 3:len(location_information)]
        try:
            parent_id = int(value, 16)
        except:
            parent_id = 0
            pass
    else:
        parent_id = 0

    try:
        target_object_tags = set(build_buy.get_object_all_tags(target.definition.id))
        target_object_tags = clean_string(str(target_object_tags))
        value = target_object_tags.split(",")
        target_object_tags = []
        for v in value:
            tag = get_tag_name(int(v))
            target_object_tags.append(tag)
    except:
        target_object_tags = None
        pass

    in_use = is_object_in_use(target)
    zone_manager = services.get_zone_manager()
    persistence_service = services.get_persistence_service()
    current_zone = zone_manager.current_zone
    neighborhood = persistence_service.get_neighborhood_proto_buff(current_zone.neighborhood_id)

    info_string = "[Zone Info:] {}\n" \
                    "[{}:] {}\n" \
                    "[Object Name:] {}\n" \
                    "[Object Definition ID:] {} ({})\n" \
                    "[Object Tuning ID:] {}\n" \
                    "[Object Footprint:] {}\n" \
                    "[Object Routable:] {}\n" \
                    "[Sims Using Object:] {}\n" \
                    "[Object Outside:] {}\n" \
                    "[Object In Use:] {}\n" \
                    "[Object Scale:] {}\n" \
                    "[Object Locked:] {}\n" \
                    "[Object Dirty:] {}\n" \
                    "[Object Room ID:] {}\n" \
                    "[Object Level:] {}\n" \
                    "[Object Opacity:] {}\n" \
                    "[Object Location ID:] {}\n" \
                    "[Object POS:] {}, {}, {}\n" \
                    "[Object ROT:] {}, {}, {}, {}\n" \
                    "[Object Facing:] {}\n" \
                    "[Type:] {}\n" \
                    "[Object Slots:] {}\n" \
                    "[Object Tags:] {}\n" \
                    "[Commodities:]\n{}\n" \
                    .format(zone_id,
                    "Object ID" if target.id else "World Name:",
                    target.id if target.id else neighborhood.name,
                    target.__class__.__name__,
                    target.definition.id,
                    hex(target.definition.id),
                    target.tuning_manager._definitions_cache[target.definition.id].tuning_file_id,
                    object_width if object_width > 0 else routing.get_world_size(),
                    routable,
                    [(_info.first_name + " " + _info.last_name) for _info in get_sims_using_object(target)],
                    target.is_outside if hasattr(target, "is_outside") else False,
                    in_use,
                    scale,
                    locked,
                    object_is_dirty(target),
                    obj_room_id,
                    target.level,
                    opacity,
                    parent_id,
                    target.position.x,
                    target.position.y,
                    target.position.z,
                    target.location.transform.orientation.x,
                    target.location.transform.orientation.y,
                    target.location.transform.orientation.z,
                    target.location.transform.orientation.w,
                    target.forward,
                    object_class,
                    slots_resource,
                    clean_string(str(target_object_tags)),
                    commodity_list)

    if filename is not None:
        info_string += "[Filename:] {}\n".format(filename)

    if hasattr(target, "get_light_color"):
        color = target.get_light_color()
        if color is not None:
            r, g, b, _ = sims4.color.to_rgba_as_int(color)
        else:
            r = g = b = sims4.color.MAX_INT_COLOR_VALUE
        info_string += "[Light Color:] R:{} G:{} B:{}\n".format(r, g, b)

    if long_version:
        info_string = info_string + "\n[MORE]\n"
        result = target
        for att in dir(result):
            if hasattr(result, att):
                info_string = info_string + "\n(" + str(att) + "): " + clean_string(str(getattr(result, att)))

    return info_string


def is_object_in_use(obj):
    interaction_refs = obj.interaction_refs if hasattr(obj, "interaction_refs") else None
    if interaction_refs:
        return True
    return obj.in_use if hasattr(obj, "in_use") else False


def is_object_in_use_by(obj, sim):
    if obj.in_use_by(sim):
        return True
    if any(sim == sim_using for sim_using in get_sims_using_object(obj)):
        return True
    return False


def does_object_have_action(obj, action):
    interaction_refs = obj.interaction_refs if hasattr(obj, "interaction_refs") else None
    if interaction_refs:
        for interaction in interaction_refs:
            if action in str(interaction.__class__.__name__).lower():
                return True
    return False


def is_object_type_in_use_by(type_string, sim):
    objs = [obj for obj in services.object_manager().valid_objects() if
            type_string in str(obj).lower() and [obj_sim for obj_sim in get_sims_using_object(obj) if obj_sim == sim]]
    if objs:
        return True
    return False


def get_objects_used_by_sim(sim):
    return [obj for obj in services.object_manager().valid_objects() if
            [obj_sim for obj_sim in get_sims_using_object(obj) if obj_sim == sim]]


def get_sims_using_object(obj):
    interaction_refs = obj.interaction_refs if hasattr(obj, "interaction_refs") else None
    if interaction_refs:
        return set([interaction.sim for interaction in interaction_refs])
    return []


def debugger_get_object_dump(obj, filter=None):
    debugger(get_object_dump(obj, filter))


def get_object_dump(obj, filter=None):
    info_string = ""
    result = obj
    for att in dir(result):
        if hasattr(result, att):
            attribute = getattr(result, att)
            if filter:
                if not attribute:
                    continue
                if filter not in str(att).lower():
                    continue
            info_string = info_string + "\n(" + str(att) + "): " + clean_string(str(getattr(result, att)))
    return info_string


def get_instance_tuning(id):
    # Get the tuning manager for interaction instance types
    tuning_manager = services.get_instance_manager(Types.INTERACTION)
    # Return the SI tuning from the manager
    return tuning_manager.get(id)


def push_sim_function(sim, target, dc_interaction: int, autonomous=True, init_chat=13998):
    try:
        if sim is None or target is None:
            return False

        if sc_Vars.tag_sim_for_debugging:
            name = "{} {}".format(sim.first_name, sim.last_name)
            if name in sc_Vars.tag_sim_for_debugging:
                debugger("Sim: {} Target: {} Interaction: {}".format(name, target.__class__.__name__, dc_interaction))
        if sc_Vars.DEBUG_FULL:
            name = "{} {}".format(sim.first_name, sim.last_name)
            debugger("Sim: {} Target: {} Interaction: {}".format(name, target.__class__.__name__, dc_interaction))

        zone = services.current_zone()
        if not hasattr(target, "definition"):
            return False
        if target.definition.id != 816:
            target = services.get_zone(zone.id).find_object(target.id)
            if not target:
                return False
        sim = services.get_zone(zone.id).find_object(sim.id)
        if not sim:
            return False

        affordance_manager = services.affordance_manager()
        if autonomous:
            context = InteractionContext.SOURCE_SCRIPT
        else:
            context = InteractionContext.SOURCE_PIE_MENU
        affordance_instance = affordance_manager.get(dc_interaction)
        if affordance_instance is None:
            return False
        if affordance_instance.is_super:
            result = push_super_affordance(sim, affordance_instance, target, context, autonomous=autonomous)
        elif affordance_instance.is_social:
            result = push_social_affordance(sim, init_chat, dc_interaction, target, context)
        else:
            result = push_mixer_affordance(sim, dc_interaction, target, context)
        return result
    except BaseException as e:
        error_trap(e)
        if sim:
            name = "{} {}".format(sim.first_name, sim.last_name)
            debugger("Sim: {} Target: {} Interaction: {}".format(name, target.__class__.__name__, dc_interaction), 0,
                     True)
            sim.reset(ResetReason.RESET_ON_ERROR, None, 'Interaction killed on error.')
        pass


def push_super_affordance(sim, affordance, target=None,
                          interaction_context=InteractionContext.SOURCE_SCRIPT,
                          priority=Priority.High, run_priority=Priority.High,
                          insert_strategy=QueueInsertStrategy.FIRST, must_run_next=False, autonomous=True):
    try:
        affordance_instance = affordance
        if affordance_instance is None:
            return False
        else:
            context = InteractionContext(sim, interaction_context, priority, run_priority=run_priority,
                                         insert_strategy=insert_strategy, must_run_next=must_run_next)
            if not context:
                return False

            result = sc_push_super_affordance(sim, affordance_instance, target, context, picked_object=target,
                                              time_overhead=1, autonomous=autonomous)
            return result
    except BaseException as e:
        error_trap(e)


def get_posture_target(sim, interaction):
    for si in sim.si_state:
        if si.guid64 == interaction:
            return si.get_participant(interactions.ParticipantType.ActorPostureTarget)
    return None

def get_posture_target_by_name(sim, name):
    for si in sim.si_state:
        if name in str(si).lower():
            return si.get_participant(interactions.ParticipantType.ActorPostureTarget)
    return None

def get_interaction_target_by_name(sim, name):
    for interaction in sim.get_all_running_and_queued_interactions():
        if name in str(interaction).lower():
            return interaction.target
    return None

def dump_interaction_object_by_name(sim, name) -> str:
    for interaction in sim.get_all_running_and_queued_interactions():
        if name in str(interaction).lower():
            return get_object_dump(interaction)
    return ""

def get_sim_posture_target(sim):
    return sim.posture.target


def set_sim_posture_target(sim, target):
    sim.posture.target = target


def sc_push_super_affordance(sim, super_affordance, target, context, autonomous=True, **kwargs):
    try:
        if autonomous:
            if check_interaction_on_private_objects(sim, target, super_affordance):
                return sim.push_super_affordance(super_affordance, target, context, picked_object=target,
                                                 time_overhead=1)
            return EnqueueResult(TestResult.NONE, ExecuteResult.NONE)
        if isinstance(super_affordance, str):
            super_affordance = services.get_instance_manager(Types.INTERACTION).get(super_affordance)
            if not super_affordance:
                raise ValueError('{0} is not a super affordance'.format(super_affordance))
        aop = (AffordanceObjectPair)(super_affordance, target, super_affordance, None, **kwargs)
        res = aop.test_and_execute(context)
        return res
    except BaseException as e:
        error_trap(e)
        name = "{} {}".format(sim.first_name, sim.last_name)
        debugger("Sim: {} Target: {} Interaction: {}".format(name, target.__class__.__name__, super_affordance), 0,
                 True)
        return EnqueueResult(TestResult.NONE, ExecuteResult.NONE)


def push_social_affordance(sim, social_super_affordance, mixer_affordance, target, interaction_context,
                           priority=Priority.High, run_priority=Priority.High,
                           insert_strategy=QueueInsertStrategy.FIRST, must_run_next=False):
    affordance_manager = services.affordance_manager()
    super_affordance_instance = affordance_manager.get(social_super_affordance)
    mixer_affordance_instance = affordance_manager.get(mixer_affordance)
    if super_affordance_instance is None:
        return False
    if mixer_affordance_instance is None:
        return False

    def _get_existing_ssi(si_iter):
        for si in si_iter:
            if si.super_affordance == super_affordance_instance:
                if si.social_group is None:
                    pass
                else:
                    if target is not None:
                        if target not in si.social_group:
                            continue
                        return si.super_interaction

    super_interaction = _get_existing_ssi(sim.si_state) or _get_existing_ssi(sim.queue)
    if super_interaction is None:
        si_context = InteractionContext(sim, interaction_context, priority, run_priority=run_priority,
                                        insert_strategy=insert_strategy, must_run_next=must_run_next)
        si_result = sc_push_super_affordance(sim, super_affordance_instance, target, si_context, picked_object=target)
        if not si_result:
            return False
        super_interaction = si_result.interaction
    pick = super_interaction.context.pick
    preferred_objects = super_interaction.context.preferred_objects
    context = super_interaction.context.clone_for_continuation(super_interaction, insert_strategy=insert_strategy,
                                                               source_interaction_id=(super_interaction.id),
                                                               source_interaction_sim_id=(sim.id),
                                                               pick=pick, preferred_objects=preferred_objects,
                                                               must_run_next=must_run_next)
    aop = AffordanceObjectPair(mixer_affordance_instance, target, super_affordance_instance,
                               super_interaction, picked_object=target, push_super_on_prepare=True)
    return aop.test_and_execute(context)


def push_mixer_affordance(sim, affordance, target=None,
                          interaction_context=InteractionContext.SOURCE_SCRIPT,
                          priority=Priority.High, run_priority=Priority.High,
                          insert_strategy=QueueInsertStrategy.FIRST, must_run_next=False):
    affordance_manager = services.affordance_manager()
    affordance_instance = affordance_manager.get(affordance)
    if affordance_instance is None:
        return False
    source_interaction = sim.posture.source_interaction
    if source_interaction is None:
        return False
    sim_specific_lockout = affordance_instance.lock_out_time.target_based_lock_out if affordance_instance.lock_out_time else False
    if sim_specific_lockout:
        if sim.is_sub_action_locked_out(affordance_instance):
            return False
        super_affordance_instance = source_interaction.super_affordance
        context = InteractionContext(sim, interaction_context, priority, run_priority=run_priority,
                                     insert_strategy=insert_strategy, must_run_next=must_run_next)
        for aop, test_result in get_valid_aops_gen(target, affordance_instance, super_affordance_instance,
                                                   source_interaction, context, False, push_super_on_prepare=False):
            interaction_constraint = aop.constraint_intersection(sim=sim, posture_state=None)
            posture_constraint = sim.posture_state.posture_constraint_strict
            constraint_intersection = interaction_constraint.intersect(posture_constraint)
            if constraint_intersection.valid:
                return aop.execute(context)


def make_sim_selectable(sim_info):
    client = services.client_manager().get_first_client()
    if len(client._selectable_sims._selectable_sim_infos):
        if client._selectable_sims._selectable_sim_infos[0].is_in_travel_group() and \
                client._selectable_sims._selectable_sim_infos[0] in services.active_household():
            travel_group = get_sim_travel_group(client.active_sim, False)
            sim_info.assign_to_travel_group(travel_group)
    try:
        SelectionGroupService \
            .get(services.active_household_id()) \
            .make_sim_selectable(sim_info)
    except:

        if sim_info.is_selectable:
            return

        # request lod before adding to make sure everything is loaded
        sim_info.request_lod(SimInfoLODLevel.ACTIVE)

        client.add_selectable_sim_info(sim_info)

        currently_active_sim = client.active_sim_info

        # force the game to update now selectable NPC tracker information
        client.set_active_sim_by_id(sim_info.id)
        client.set_active_sim_by_id(currently_active_sim.id)
        pass


def make_sim_unselectable(sim_info):
    if sim_info is None:
        return
    client = services.client_manager().get_first_client()
    if len(client._selectable_sims._selectable_sim_infos):
        if client._selectable_sims._selectable_sim_infos[0].is_in_travel_group() and \
                client._selectable_sims._selectable_sim_infos[0] in services.active_household():
            travel_group = get_sim_travel_group(client.active_sim, False)
            sim_info.remove_from_travel_group(travel_group)
    try:
        SelectionGroupService \
            .get(services.active_household_id()) \
            .remove_sim(sim_info)
    except:
        client.remove_selectable_sim_by_id(sim_info.id)
        pass


def get_all_careers(sim_info):
    try:
        careers = []
        for career_id in sim_info.career_tracker._careers:
            career = sim_info.career_tracker._careers[career_id]
            if career is not None:
                careers.append(career_id)
        return careers
    except BaseException as e:
        error_trap(e)


def make_sim_at_work(sim_info):
    careers = get_all_careers(sim_info)
    for c in careers:
        career = sim_info.career_tracker.get_career_by_uid(c)
        if career is None:
            return False
        career._at_work = False
        try:
            career.days_worked_statistic.add_value(1)
            gig = career.get_current_gig()
            if gig is not None:
                gig.notify_gig_attended()
            career._taking_day_off_reason = CareerTimeOffReason.NO_TIME_OFF
            career.add_pto(career._pto_taken * -1)
            career._pto_taken = 0
            career.career_stop()
            career.resend_career_data()
            career.resend_at_work_info()
        except:
            pass
            return


def start_career(sim_info):
    try:
        careers = get_all_careers(sim_info)
        for c in careers:
            career = sim_info.career_tracker.get_career_by_uid(c)
            if career is None:
                continue
            if career._at_work:
                continue
            career._at_work = True
            if career._late_for_work_handle is not None:
                alarms.cancel_alarm(career._late_for_work_handle)
                career._late_for_work_handle = None

            career.days_worked_statistic.add_value(1)
            gig = career.get_current_gig()
            if gig is not None:
                gig.notify_gig_attended()
            career._taking_day_off_reason = CareerTimeOffReason.NO_TIME_OFF
            career.add_pto(career._pto_taken * -1)
            career._pto_taken = 0
            career.on_assignment or career.send_career_message(career.career_messages.career_daily_start_notification)
            career.resend_career_data()
            career.resend_at_work_info()
            services.get_event_manager().process_event((test_events.TestEvent.WorkdayStart), sim_info=(sim_info),
                                                       career=career)

    except BaseException as e:
        error_trap_console(e)
        pass
        return


def end_career_session(sim_info):
    careers = get_all_careers(sim_info)
    for c in careers:
        career = sim_info.career_tracker.get_career_by_uid(c)
        if career:
            career._at_work = False
            career.career_stop()
            career.add_pto(1)
            career.request_day_off(CareerTimeOffReason.PTO)
            career.add_pto(-1)
            career._clear_career_alarms()
            career._current_work_start = None
            career._current_work_end = None
            career._current_work_duration = None
            career._rabbit_hole_id = None
            career._career_session_extended = False
            career._taking_day_off_reason = CareerTimeOffReason.NO_TIME_OFF
            career._pto_taken = 0
            career._clear_current_gig()
            career.resend_career_data()
            career.resend_at_work_info()


def remove_sim_from_rabbithole(sim_info, select=True):
    make_sim_unselectable(sim_info)
    rabbit_hole = services.get_rabbit_hole_service()
    if rabbit_hole.is_in_rabbit_hole(sim_info.sim_id):
        rid = rabbit_hole.get_head_rabbit_hole_id(sim_info.sim_id)
        rabbit_hole.remove_sim_from_rabbit_hole(sim_info.sim_id, rid)
    if select:
        make_sim_selectable(sim_info)


def activate_sim_icon(sim_info, select=True):
    rabbit_hole = services.get_rabbit_hole_service()
    if rabbit_hole.is_in_rabbit_hole(sim_info.sim_id):
        rid = rabbit_hole.get_head_rabbit_hole_id(sim_info.sim_id)
        rabbit_hole.remove_sim_from_rabbit_hole(sim_info.sim_id, rid)
    make_sim_unselectable(sim_info)
    careers = get_all_careers(sim_info)
    for c in careers:
        career = sim_info.career_tracker.get_career_by_uid(c)
        if career is not None:
            try:
                end_career_session(sim_info)
            except:
                pass
    if select:
        make_sim_selectable(sim_info)


def end_career(sim_info, select=True):
    careers = get_all_careers(sim_info)
    for c in careers:
        career = sim_info.career_tracker.get_career_by_uid(c)
        if career is not None:
            try:
                end_career_session(sim_info)
            except:
                pass
    if select:
        make_sim_selectable(sim_info)


def _instanced_sims_gen(self, allow_hidden_flags=0):
    return [sim_info.get_sim_instance(allow_hidden_flags=allow_hidden_flags) for sim_info in self._objects.values()
            if sim_info.get_sim_instance(allow_hidden_flags=allow_hidden_flags) is not None]


def _travel_instanced_sims_gen(self, allow_hidden_flags=0):
    return [sim_info.get_sim_instance(allow_hidden_flags=allow_hidden_flags) for sim_info in self._sim_infos
            if sim_info.is_instanced(allow_hidden_flags=allow_hidden_flags) is not None]


def get_sim_age(sim_info):
    if sim_info.age_progress:
        return sim_info.age_progress
    return sim_info._time_alive

def is_unroutable_object(sim, obj):
    if [unroutable for unroutable in sc_Vars.non_routable_obj_list if unroutable.object == obj and unroutable.sim == sim]:
        return True
    return False

def find_empty_chair(sim, obj=None, dist=sc_Vars.MAX_DISTANCE, index=0, no_computer=False, is_outside=True):
    if obj:
        search = obj
    else:
        search = sim
    chairs = find_all_objects_by_title(search, "sitliving|sitdining|sitsofa|sitlove|sitdeco|bench|beddouble|bedsingle|chair|stool|hospitalexambed", search.level, dist)
    if not chairs:
        return None
    for i, chair in enumerate(chairs):
        inside_chairs = [oc for oc in chairs if not oc.is_outside]
        if inside_chairs and chair.is_outside and not is_outside:
            continue
        if no_computer:
            computers = find_all_objects_by_title(chair, "computer", chair.level, 1.5)
            if computers:
                continue
        if i >= index:
            if is_unroutable_object(sim, chair):
                continue
            if not get_routable_for_sim(chair, sim):
                continue
            if "sitsofa" in str(chair).lower() and len(get_sims_using_object(chair)) < 3:
                return chair
            if "sitlove" in str(chair).lower() or "beddouble" in str(chair).lower() or "bedsingle" in str(chair).lower():
                if len(get_sims_using_object(chair)) < 2:
                    return chair
            if not is_object_in_use(chair) or is_object_in_use_by(chair, sim):
                return chair
    return None

@sims4.commands.Command('distance_autonomy_callback', command_type=sims4.commands.CommandType.Live)
def distance_autonomy_callback(value1=None, value2=None, value3=None, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    sim = services.object_manager().get(int(value1))
    target = services.object_manager().get(int(value2))
    action = int(value3)
    result = push_sim_function(sim, target, action, False)
    output('Sim: {}\nTarget: {}\nAction: {}\n'.format(value1, value2, value3))
    output("Result from distance autonomy callback:\n{}\n".format(result))

# New code to disable autonomy based on distance.
def enable_distance_autonomy(interaction, action_dist=12.0, chat_dist=6.0, message=False):
    action = interaction.__class__.__name__.lower()
    if not interaction.is_user_directed and interaction.sim.sim_info.is_selectable:
        if distance_to_by_level(interaction.sim, interaction.target) > action_dist:
            clear_sim_instance(interaction.sim.sim_info, [action, "stand"])
            if message and interaction.sim == services.get_active_sim():
                message_box(interaction.sim, interaction.target, "Distance Autonomy", "Distance autonomy activated!\n"
                    "<font color='#ffff00'>config.ini\n[distance_autonomy]\nenable_distance_autonomy = True\n</font>"
                    "Target is outside of reach when distance autonomy is enabled regardless of sim autonomy. Disable "
                    "this feature in the config. Furthermore, IF sim autonomy is disabled. Activate certain actions "
                    "using enabled.dat, placing the name, or partial name of the action seperated by | or use the "
                    "script core menu under control. Select enable autonomy then look for the action you need enabled "
                    "and click it. This adds the action to enabled.dat. Routine sims are excluded from this.\n"
                    "Disabled action: {}".format(action),
                    "DEFAULT", "Execute Disabled Action", 'distance_autonomy_callback',
                    str(interaction.sim.id), str(interaction.target.id), str(interaction.guid64))
            return True

    if "chat" in action and not interaction.is_user_directed or "social" in action and not interaction.is_user_directed:
        if distance_to_by_room(interaction.sim, interaction.target) > chat_dist:
            for group in interaction.sim.get_groups_for_sim_gen():
                group.remove(interaction.target)
                group._resend_members()
            if check_actions(interaction.sim, "sit"):
                clear_sim_instance(interaction.sim.sim_info, ["chat", "social", "stand"])
            else:
                clear_sim_instance(interaction.sim.sim_info, ["chat", "social"])
            if message and interaction.sim == services.get_active_sim():
                message_box(interaction.sim, interaction.target, "Distance Autonomy", "Distance autonomy activated!\n"
                    "<font color='#ffff00'>config.ini\n[distance_autonomy]\nenable_distance_autonomy = True\n</font>"
                    "Target is outside of reach when distance autonomy is enabled. Disable this feature in the config. "
                    "Furthermore, chatting is distanced based using this feature regardless of sim autonomy.",
                    "DEFAULT", "Chat With Sim", 'distance_autonomy_callback',
                    str(interaction.sim.id), str(interaction.target.id), str(interaction.guid64))
            return True
    if check_actions(interaction.sim, "greet") and check_actions(interaction.sim, "sit"):
        target = get_interaction_target_by_name(interaction.sim, "greet")
        clear_sim_instance(interaction.sim.sim_info, ["stand", "greet"])
        push_sim_function(target, interaction.sim, 13998)
        if message and interaction.sim == services.get_active_sim():
            debugger("Distance Autonomy: Distance autonomy activated for Sim: {} action: {}".format(interaction.sim.first_name + " " + interaction.sim.last_name, action))
        return True
    if "stand" in action and check_actions(interaction.sim, "sit") and check_actions(interaction.sim, "chat"):
        target = get_interaction_target_by_name(interaction.sim, "social")
        clear_sim_instance(interaction.sim.sim_info, ["chat", "social", "stand"])
        push_sim_function(target, interaction.sim, 13998)
        if message and interaction.sim == services.get_active_sim():
            debugger("Distance Autonomy: Distance autonomy activated for Sim: {} action: {}".format(interaction.sim.first_name + " " + interaction.sim.last_name, action))
        return True
    return False

def create_trauma(target):
    amount_puddle = int(random.uniform(1, 5))
    for i in range(amount_puddle):
        puddle = objects.system.create_object(12827615789269726318 + int(random.uniform(0, 5)))

        if puddle is not None:
            level = target.location.level
            translation = target.location.transform.translation
            orientation = target.location.transform.orientation
            orientation = sims4.math.Quaternion(orientation.x, orientation.y + random.uniform(-1.0, 1.0),
                                                orientation.z, orientation.w)
            puddle_pos = sims4.math.Vector3(translation.x + random.uniform(-2.0, 2.0), translation.y,
                                            translation.z + random.uniform(-2.0, 2.0))
            zone_id = services.current_zone_id()
            routing_surface = routing.SurfaceIdentifier(zone_id, level, routing.SurfaceType.SURFACETYPE_WORLD)
            puddle.location = sims4.math.Location(sims4.math.Transform(puddle_pos, orientation), routing_surface)
            puddle.scale = random.uniform(0.5, 1.5)

            amount_gibs = int(random.uniform(2, 20))

            for i in range(amount_gibs):
                chance = int(random.uniform(0, 100))
                if chance < 95:
                    gibs = objects.system.create_object(10761987401480754687)
                    gibs.scale = random.uniform(0.5, 1.25)
                elif chance < 98:
                    gibs = objects.system.create_object(10508265801663426570)
                    gibs.scale = 1
                elif chance < 100:
                    gibs = objects.system.create_object(13369015814250387783)
                    gibs.scale = 1

                if gibs is not None:
                    level = target.location.level
                    orientation = target.location.transform.orientation
                    orientation = sims4.math.Quaternion(orientation.x, orientation.y + random.uniform(-1.0, 1.0),
                                                        orientation.z, orientation.w)
                    pos = sims4.math.Vector3(puddle_pos.x + random.uniform(-0.35, 0.35), puddle_pos.y,
                                             puddle_pos.z + random.uniform(-0.35, 0.35))
                    zone_id = services.current_zone_id()
                    routing_surface = routing.SurfaceIdentifier(zone_id, level, routing.SurfaceType.SURFACETYPE_WORLD)
                    gibs.location = sims4.math.Location(sims4.math.Transform(pos, orientation), routing_surface)


SimInfoManager.instanced_sims_gen = _instanced_sims_gen
TravelGroup.instanced_sims_gen = _instanced_sims_gen
