import os
import sys
from typing import List

import alarms
import build_buy
import interactions
import objects
import routing
import services
import sims4.commands
from autonomy.content_sets import get_valid_aops_gen
from careers.career_ops import CareerTimeOffReason
from module_ai.ai_dialog import display_choices
from module_ai.ai_picker import default_picker
from module_ai.ai_util import error_trap, ld_notice, init_sim, clean_string
from interactions.aop import AffordanceObjectPair
from interactions.context import InteractionContext, QueueInsertStrategy
from interactions.interaction_finisher import FinishingType
from interactions.priority import Priority
from objects.game_object import GameObject
from objects.object_enums import ResetReason
from server.pick_info import PickType
from server_commands.sim_commands import _build_terrain_interaction_target_and_context, CommandTuning
from services.roommate_service import RoommateService
from sims.sim import Sim
from sims.sim_info import SimInfo
from sims.sim_info_types import Age
from sims4 import resources
from sims4.localization import LocalizationHelperTuning
from sims4.resources import Types, get_resource_key
from situations.bouncer.bouncer_request import RequestSpawningOption
from situations.bouncer.bouncer_types import BouncerRequestPriority
from situations.situation_guest_list import SituationGuestList, SituationGuestInfo
from ui.ui_dialog import UiDialogOkCancel
from ui.ui_dialog_notification import UiDialogNotification
from ui.ui_dialog_picker import SimPickerRow, UiSimPicker


class ldJobs:
    def __init__(self, sim_id, job_id):
        self.sim_id = 0
        self.job_id = 0


sim_jobs = []
current_situations = []
interaction_filter = "skate|sit|tv|computer|frontdesk|stereo|dance|sleep|nap"

def object_info(target):
    try:
        zone_id = services.current_zone_id()
        output = ""
        if hasattr(target, "is_sim"):
            if target.is_sim:
                outfit_tracker = target.get_outfits()
                result = outfit_tracker.save_outfits().outfits
                _filename = target.__dict__.get('__file__')
                ns = sys.modules.get(target.__module__).__dict__
                for att in dir(result):
                    if hasattr(result, att):
                        output = output + "\n<b>" + str(att) + "</b>: " + clean_string(str(getattr(result, att)))

        if hasattr(target, "position") and hasattr(target, "level"):
            obj_room_id = build_buy.get_room_id(zone_id, target.position, target.level)
        else:
            obj_room_id = None
        if hasattr(target, "slot_hash"):
            slot_hash = target.slot_hash
        else:
            slot_hash = None
        if hasattr(target, "_opacity"):
            opacity = target._opacity
        else:
            opacity = 1
        if hasattr(target, "scale"):
            scale = target.scale
        else:
            scale = 1
        if hasattr(target, "__file__"):
            filename = target.__file__
        else:
            filename = None
        if hasattr(target, "_location"):
            location_information = clean_string(str(target._location.parent))
            try:
                value = location_information.split("0x")
                parent_title = value[0]
                parent_id = int(value[1], 16)
            except:
                parent_title = None
                parent_id = None
                pass
        else:
            parent_title = None
            parent_id = None

        if hasattr(target, "definition"):
            definition_id = target.definition.id
        else:
            definition_id = None

        info_string = "Object ID: {}\n" \
                      "Object Definition ID: {}\n" \
                      "Object Scale :{}\n" \
                      "Object Room ID:{}\n" \
                      "Object Opacity :{}\n" \
                      "Object Location (Title): {} ID: {}\n" \
                      "Object Slot Hash :{}\n" \
                      "Object POS: X:{} Y:{} Z:{}\n" \
                      "Object ROT: X:{} Y:{} Z:{} W:{}\n" \
                      "Type: {}\n" \
            .format(target.id,
                    definition_id,
                    scale,
                    obj_room_id,
                    opacity,
                    parent_title, parent_id,
                    slot_hash,
                    target.location.transform.translation.x,
                    target.location.transform.translation.y,
                    target.location.transform.translation.z,
                    target.location.transform.orientation.x,
                    target.location.transform.orientation.y,
                    target.location.transform.orientation.z,
                    target.location.transform.orientation.w,
                    target.__class__.__name__)

        if filename is not None:
            info_string += "Filename:{}\n".format(filename)

        info_string += "INFO:\n{}".format(output)

        if target.is_sim:
            sim_info = target.sim_info
            info_string += "Outfit ID: {}\n".format(sim_info._current_outfit)
            for career_id in sim_info.career_tracker._careers:
                career = sim_info.career_tracker._careers[career_id]
                if career is not None:
                    if career._at_work:
                        info_string += "{} At Work: True\n".format(career)
                    else:
                        info_string += "{} At Work: False\n".format(career)
        else:
            if hasattr(target, "get_light_color"):
                color = target.get_light_color()
                if color is not None:
                    r, g, b, _ = sims4.color.to_rgba_as_int(color)
                else:
                    r = g = b = sims4.color.MAX_INT_COLOR_VALUE
                info_string += "Light Color: R:{} G:{} B:{}\n".format(r, g, b)

        urgency = UiDialogNotification.UiDialogNotificationUrgency.DEFAULT
        information_level = UiDialogNotification.UiDialogNotificationLevel.PLAYER
        visual_type = UiDialogNotification.UiDialogNotificationVisualType.INFORMATION
        localized_text = lambda **_: LocalizationHelperTuning.get_raw_text(info_string)
        localized_title = lambda **_: LocalizationHelperTuning.get_object_name(target)
        # localized_title = TunableLocalizedStringFactory._Wrapper(obj_catalog_name)
        notification = UiDialogNotification.TunableFactory().default(None,
                                                                     text=localized_text,
                                                                     title=localized_title,
                                                                     icon=None,
                                                                     secondary_icon=None,
                                                                     urgency=urgency,
                                                                     information_level=information_level,
                                                                     visual_type=visual_type,
                                                                     expand_behavior=1)
        notification.show_dialog()

    except BaseException as e:
        error_trap(e)


def assign_front_desk(sim, target):
    try:
        this_zone = services.current_zone_id()
        path = os.path.abspath(os.path.dirname(__file__)) + "\\Data"
        filename = path + r"\{}.dat".format("front_desk")
        try:
            file = open(filename, "r")
            for line in file.readlines():
                value = line.split(":")
                zone_id = int(value[0])
                sim_id = int(value[1])
                obj_id = int(value[2])
                if zone_id == this_zone and sim_id == sim.id and obj_id == target.id:
                    file.close()
                    return
            file.close()
        except:
            pass
        file = open(filename, "a")
        file.write("{}:{}:{}\n".format(this_zone, sim.id, target.id))
        file.close()
    except BaseException as e:
        file.close()
        error_trap(e)

def unassign_front_desk(target):

    lines_to_write = []
    this_zone = services.current_zone_id()
    path = os.path.abspath(os.path.dirname(__file__)) + "\\Data"
    filename = path + r"\{}.dat".format("front_desk")
    try:
        file = open(filename, "r")
        for line in file.readlines():
            value = line.split(":")
            zone_id = int(value[0])
            sim_id = int(value[1])
            obj_id = int(value[2])
            if zone_id == this_zone and obj_id == target.id:
                continue
            else:
                lines_to_write.append(line)
        file.close()
        file = open(filename, "w")
        #if len(lines_to_write) < 1:
        #    file.write("{}\n".format(""))
        #else:
        for line in lines_to_write:
            file.write("{}".format(line))
        file.close()
    except:
        file.close()
        pass

def push_sim_function(sim, target, dc_interaction: int, autonomous=True):
    try:
        result = False
        if sim is None or target is None:
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
            result = push_super_affordance(sim, affordance_instance, target, context)
        elif affordance_instance.is_social:
            result = push_social_affordance(sim, 13998, dc_interaction, target, context)
        else:
            result = push_mixer_affordance(sim, dc_interaction, target, context)
        return result
    except BaseException as e:
        error_trap(e)

def push_super_affordance(sim, affordance, target=None,
                          interaction_context=InteractionContext.SOURCE_SCRIPT,
                          priority=Priority.High, run_priority=Priority.High,
                          insert_strategy=QueueInsertStrategy.FIRST, must_run_next=False):

    affordance_instance = affordance
    if affordance_instance is None:
        return False
    else:
        context = InteractionContext(sim, interaction_context, priority, run_priority=run_priority,
                                     insert_strategy=insert_strategy, must_run_next=must_run_next)

        result = sim.push_super_affordance(affordance_instance, target, context, picked_object=target)
        return result


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
        si_result = (sim.push_super_affordance)(super_affordance_instance, target, si_context, picked_object=target)
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

def go_here(sim: Sim, target):
    level = target.location.level
    pos = target.location.transform.translation
    routing_surface = routing.SurfaceIdentifier(services.current_zone_id(), level,
                                                routing.SurfaceType.SURFACETYPE_WORLD)
    target, context = _build_terrain_interaction_target_and_context(sim, pos, routing_surface,
                                                                    PickType.PICK_TERRAIN,
                                                                    objects.terrain.TerrainPoint)
    sim.push_super_affordance(CommandTuning.TERRAIN_GOHERE_AFFORDANCE, target, context)

def get_assigned_bed(sim: Sim):
    zone_id = services.current_zone_id()
    household_id = services.get_persistence_service().get_household_id_from_zone_id(zone_id)
    household = services.household_manager().get(household_id)
    object_preference_tracker = household.object_preference_tracker
    bed_id, _ = object_preference_tracker.get_restricted_object(sim.id, RoommateService.BED_PREFERENCE_TAG)
    return bed_id

def make_sim_leave(sim_info: SimInfo):
    sim = sim_info.get_sim_instance()
    for interaction in sim.get_all_running_and_queued_interactions():
        if interaction is not None:
            interaction.cancel(FinishingType.KILLED, 'Stop')
    assign_job(15815882546800024169, sim_info)
    #setup_alarm_scenerio(make_sim_leave, setup_goodbye_situation)

def clear_sim_queue_of(sim_info: SimInfo, interaction_id: int):
    try:
        sim = init_sim(sim_info)
        for interaction in sim.get_all_running_and_queued_interactions():
            if interaction is not None:
                if interaction.guid64 == interaction_id:
                    interaction.cancel(FinishingType.KILLED, 'Stop')
    except BaseException as e:
        error_trap(e)

def add_trait(potential_key: int, sim_info: SimInfo):
    try:
        instance_manager = services.get_instance_manager(Types.TRAIT)
        key = instance_manager.get(get_resource_key(potential_key, Types.TRAIT))
        if not sim_info.has_trait(key):
            sim_info.add_trait(key)
    except BaseException as e:
        error_trap(e)


def remove_trait(potential_key: int, sim_info: SimInfo):
    try:
        instance_manager = services.get_instance_manager(Types.TRAIT)
        key = instance_manager.get(get_resource_key(potential_key, Types.TRAIT))
        if sim_info.has_trait(key):
            sim_info.remove_trait(key)
    except BaseException as e:
        error_trap(e)

def clear_sim_instance(sim_info: SimInfo, filter=None, all_but_filter=False):
    try:
        sim = init_sim(sim_info)
        if filter is None:
            filter = ""
        filter = filter.lower()
        value = filter.split("|")
        if len(value) == 0:
            value = [filter, ""]
        for interaction in sim.get_all_running_and_queued_interactions():
            if interaction is not None:
                title = interaction.__class__.__name__
                title = title.lower()
                if all_but_filter is False and filter != "":
                    cancel = False
                    for v in value:
                        if v in title and v != "":
                            cancel = True
                    if cancel is True:
                        interaction.cancel(FinishingType.RESET, 'Stop')

                elif filter != "":
                    cancel = True
                    for v in value:
                        if v in title and v != "":
                            cancel = False
                    if cancel is True:
                        interaction.cancel(FinishingType.RESET, 'Stop')
                else:
                    interaction.cancel(FinishingType.RESET, 'Stop')
    except BaseException as e:
        error_trap(e)

def clear_sim_instance_beta(sim_info: SimInfo):
    try:
        sim = init_sim(sim_info)
        _interactions = sim.get_all_running_and_queued_interactions()
        for si_a, si_b in zip(_interactions, list(_interactions)[1:]):
            if si_a.is_finishing or si_b.is_finishing:
                continue
            if si_a.is_super and si_a.collapsible and si_b.is_super and si_b.collapsible:
                si_a.cancel(FinishingType.INTERACTION_QUEUE,
                            'Interaction Queue canceled because interaction is collapsible.')
                break

    except BaseException as e:
        error_trap(e)


def clear_sim_instance_old(sim_info: SimInfo):
    try:
        sim = init_sim(sim_info)
        interaction_set = set()
        for si in sim.si_state.sis_actor_gen():
            interaction_set.add(si)
        for si in sim.queue:
            interaction_set.add(si)
        for interaction in interaction_set:
            interaction.cancel(FinishingType.KILLED, 'Stop')
    except BaseException as e:
        error_trap(e)


def remove_sim_buff(buff_id: int, sim_info: SimInfo):
    try:
        buff_manager = services.get_instance_manager(Types.BUFF)
        if sim_info.has_buff(buff_manager.get(get_resource_key(buff_id, Types.BUFF))):
            sim_info.remove_buff_by_type(buff_manager.get(buff_id))
    except BaseException as e:
        error_trap(e)


def add_sim_buff(buff_id: int, sim_info: SimInfo):
    try:
        buff_manager = services.get_instance_manager(Types.BUFF)
        type = buff_manager.get(get_resource_key(buff_id, Types.BUFF))
        if sim_info.has_buff(type):
            return
        else:
            sim_info.debug_add_buff_by_type(type)
    except BaseException as e:
        error_trap(e)


def get_career(sim_info: SimInfo):
    try:
        career = None
        for career_id in sim_info.career_tracker._careers:
            career = sim_info.career_tracker._careers[career_id]
            if career is not None:
                return career_id
        return False
    except BaseException as e:
        error_trap(e)

def get_all_careers(sim_info: SimInfo):
    try:
        careers = []
        for career_id in sim_info.career_tracker._careers:
            career = sim_info.career_tracker._careers[career_id]
            if career is not None:
                careers.append(career_id)
        return careers
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


def get_career_name(sim_info: SimInfo):
    try:
        career_info = None
        career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
        for career in career_manager.types:
            type = career_manager.get(career)
            id = get_career_id(type.__name__)
            if id in sim_info.career_tracker._careers:
                career_info = sim_info.career_tracker._careers[id]
            if career_info is not None:
                return (type.__name__)
        return False
    except BaseException as e:
        error_trap(e)


def get_job_id(job_name: str):
    try:
        situation_manager = services.get_zone_situation_manager()
        for situation in situation_manager.running_situations():
            name = format(situation.__class__.__name__)
            if job_name == name:
                return situation.guid64
        return False
    except BaseException as e:
        error_trap(e)


def get_all_situations(sim_info: SimInfo):
    global current_situations
    try:
        current_situations.clear()
        sim = init_sim(sim_info)
        situation_manager = services.get_zone_situation_manager()
        # for situation in situation_manager.running_situations():
        # for situation in situation_manager.get_situations_sim_is_in(sim):
        # default_job = situation.default_job()
        # default_type = type(situation)
        # default_role = situation.get_num_sims_in_role_state(default_type)
        # default_title = situation.situation_display_type.value
        # default_id = situation.id
        # if situation.situation_display_type.value is 0:
        # ld_debug_info(situation, sim_info)
    # situation_manager.destroy_situation_by_id(situation.id)
    # current_situations.append(situation)
    except BaseException as e:
        error_trap(e)


def assign_job(potential_key: int, sim_info: SimInfo):
    sim = init_sim(sim_info)
    if services.current_zone().is_zone_shutting_down:
        return
    try:
        instance_manager = services.get_instance_manager(Types.SITUATION)
        key = resources.get_resource_key(potential_key, Types.SITUATION)
        situation_tuning = instance_manager.get(key)
        if situation_tuning is None:
            ld_notice(sim_info, "Assign Job", "Situation tuning error for {}!".format(sim_info.first_name), True,
                      "ORANGE")
            return
        clear_jobs(sim_info)
        job_type = situation_tuning
        situation_manager = services.get_zone_situation_manager()
        job_list = SituationGuestList(invite_only=True)
        sit_info = SituationGuestInfo((sim.id), (job_type.default_job()), (RequestSpawningOption.CANNOT_SPAWN),
                                      (BouncerRequestPriority.EVENT_VIP), expectation_preference=True)
        job_list.add_guest_info(sit_info)
        situation_id = situation_manager.create_situation(job_type, job_list, user_facing=False)
    except BaseException as e:
        error_trap(e)


def append_job(potential_key: int, sim_info: SimInfo):
    sim = init_sim(sim_info)
    if services.current_zone().is_zone_shutting_down:
        return
    try:
        instance_manager = services.get_instance_manager(Types.SITUATION)
        key = resources.get_resource_key(potential_key, Types.SITUATION)
        situation_tuning = instance_manager.get(key)
        if situation_tuning is None:
            ld_notice(sim_info, "Append Job", "Situation tuning error for {}!".format(sim_info.first_name), True,
                      "ORANGE")
            return
        job_type = situation_tuning
        situation_manager = services.get_zone_situation_manager()
        job_list = SituationGuestList(invite_only=True)
        sit_info = SituationGuestInfo((sim.id), (job_type.default_job()), (RequestSpawningOption.CANNOT_SPAWN),
                                      (BouncerRequestPriority.EVENT_VIP), expectation_preference=True)
        job_list.add_guest_info(sit_info)
        situation_id = situation_manager.create_situation(job_type, job_list, user_facing=False)
    except BaseException as e:
        error_trap(e)


def assign_role(potential_key: int, sim_info: SimInfo):
    sim = init_sim(sim_info)
    if services.current_zone().is_zone_shutting_down:
        return
    try:
        role_tracker = sim.autonomy_component._role_tracker
        role_tracker.reset()
        new_role = services.role_state_manager().get(potential_key)  # debug_guest_role3
        clear_jobs(sim_info)
        sim.add_role(new_role)
    except BaseException as e:
        error_trap(e)


def reset_sim_situations(sim_info: SimInfo):
    sim = init_sim(sim_info)
    situation_manager = services.get_zone_situation_manager()
    situation_manager.on_sim_reset(sim)


def destroy_situation(situation_id: int):
    try:
        situation_manager = services.get_zone_situation_manager()
        all_situations = tuple(situation_manager.values())
        for situation in all_situations:
            if situation.id == situation_id:
                situation_manager.destroy_situation_by_id(situation.id)
    except BaseException as e:
        error_trap(e)


def clear_everything(sim_info: SimInfo):
    sim = init_sim(sim_info)
    try:
        reset_sim_situations(sim_info)
        situation_manager = services.get_zone_situation_manager()
        for situation in situation_manager.get_situations_sim_is_in(sim):
            situation_manager.remove_sim_from_situation(sim, situation.id)
        role_tracker = sim.autonomy_component._role_tracker
        role_tracker.reset()
        sim.reset(ResetReason.NONE, None, 'Command')
        situation_manager.create_visit_situation(sim)
    except BaseException as e:
        error_trap(e)


def clear_jobs(sim_info: SimInfo):
    sim = init_sim(sim_info)
    try:
        # get_all_situations(sim_info)
        situation_manager = services.get_zone_situation_manager()
        role_tracker = sim.autonomy_component._role_tracker
        role_tracker.reset()
        for situation in situation_manager.get_situations_sim_is_in(sim):
            job_title = "{}".format(situation.__class__.__name__)
            if (job_title.find('holiday') == -1) and (job_title.find('club') == -1):
                situation_manager.destroy_situation_by_id(situation.id)
    # ld_notice(sim_info, "clear_jobs", "# of situations: {} for {}".format(count, sim_info.first_name))
    except BaseException as e:
        error_trap(e)


def job_picker(pick_title: str, job_key: int, trait_key: int, trait_jobs: List[int]):
    def get_simpicker_results_callback(dialog):
        if not dialog.accepted:
            return
        try:
            result_tags = dialog.get_result_tags()
            for tags in dialog.get_result_tags():
                sim_info = services.sim_info_manager().get(tags)
                for trait in trait_jobs:
                    remove_trait(trait, sim_info)
                assign_job(job_key, sim_info)
                add_trait(trait_key, sim_info)
        except BaseException as e:
            error_trap(e)

    default_picker(pick_title, "Pick up to 50 Sims", 50, False, get_simpicker_results_callback)


def role_picker(pick_title: str, role_key: int):
    def get_simpicker_results_callback(dialog):
        if not dialog.accepted:
            return
        try:
            result_tags = dialog.get_result_tags()
            for tags in dialog.get_result_tags():
                sim_info = services.sim_info_manager().get(tags)
                assign_role(role_key, sim_info)
        except BaseException as e:
            error_trap(e)

    default_picker(pick_title, "Pick up to 50 Sims", 50, False, get_simpicker_results_callback)


def add_career_to_sim(career_name: str, sim_info: SimInfo):
    sim = init_sim(sim_info)
    if sim is None:
        ld_notice(sim_info, "Add Career", "Cannot add career! Teleport sim to lot first!", True, "GREEN")
        return
    try:
        career_names = []
        career_type = None
        career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
        for career_id in career_manager.types:
            type = career_manager.get(career_id)
            career_names.append(type.__name__)
            # ld_notice(sim_info, "add_career_to_sim", "Career: {}".format(type.__name__))
            if career_name == type.__name__:
                career_type = type
        all_careers_str = '\n'.join(career_names)
        # ld_notice(sim_info, "add_career_to_sim", "Careers:\n{}".format(all_careers_str))
        if career_type is not None:
            sim.sim_info.career_tracker.add_career(career_type(sim.sim_info))
    except BaseException as e:
        error_trap(e)


def remove_career_from_sim(career_name: str, sim_info: SimInfo):
    sim = init_sim(sim_info)
    try:
        if sim is not None:
            career_names = []
            career_type = None
            career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
            for career_id in career_manager.types:
                type = career_manager.get(career_id)
                career_names.append(type.__name__)
                if career_name == type.__name__:
                    career_type = type
            sim.sim_info.career_tracker.remove_career(career_type.guid64)
    except BaseException as e:
        error_trap(e)


def career_picker(pick_title: str, career_name: str, remove=False):
    def get_simpicker_results_callback(dialog):
        if not dialog.accepted:
            return
        try:
            result_tags = dialog.get_result_tags()
            for tags in dialog.get_result_tags():
                sim_info = services.sim_info_manager().get(tags)
                if remove is False:
                    # ww.stripclub_hire_dancer_sim
                    add_career_to_sim(career_name, sim_info)
                else:
                    remove_career_from_sim(career_name, sim_info)
        except BaseException as e:
            error_trap(e)

    default_picker(pick_title, "Pick up to 50 Sims", 50, False, get_simpicker_results_callback)


def add_affordance(affordance_id: int, sim, target_sim):
    try:
        context = InteractionContext(sim, (InteractionContext.SOURCE_SCRIPT), (Priority.High),
                                     insert_strategy=(QueueInsertStrategy.NEXT))
        super_affordance = services.get_instance_manager(sims4.resources.Types.INTERACTION).get(affordance_id)
        if not super_affordance:
            ld_notice(sim.sim_info, "add_affordance", "{0} is not a super affordance".format(super_affordance), True,
                      "GREEN")
            return False
        aop = (interactions.aop.AffordanceObjectPair)(super_affordance, target_sim, super_affordance, None)
        res = aop.test_and_execute(context)
        if not res:
            ld_notice(sim.sim_info, "add_affordance", "Could not add affordance to sim!", True, "GREEN")
            return False
        else:
            return True
    except BaseException as e:
        error_trap(e)


def affordance_picker(title: str, client_affordance_id: int, target_affordance_id: int = None, max: int = 50):
    try:
        client = services.client_manager().get_first_client()
        sim = client.active_sim
        sim_ids = []
        for sim_info in services.sim_info_manager().instanced_sims_gen():
            if sim_info.age != Age.BABY and sim_info.age != Age.CHILD and sim_info.age != Age.TEEN and sim_info.age != Age.TODDLER:
                sim_ids.append((sim_info.sim_id, sim_info.last_name, sim_info.first_name))
        sim_ids.sort(key=(lambda s: s[2]))
        sim_ids.sort(key=(lambda s: s[1]))

        def get_simpicker_results_callback(dialog):
            if not dialog.accepted:
                return
            try:
                result_tags = dialog.get_result_tags()
                for tags in result_tags:
                    sim_info = services.sim_info_manager().get(tags)
                    clear_sim_instance(sim_info)
                    clear_sim_instance(sim.sim_info)
                    if target_affordance_id is not None:
                        add_affordance(client_affordance_id, sim, sim_info.get_sim_instance())
                        add_affordance(target_affordance_id, sim_info.get_sim_instance(), sim)
                    else:
                        add_affordance(client_affordance_id, sim, sim_info.get_sim_instance())
            except BaseException as e:
                error_trap(e)

        localized_title = lambda **_: LocalizationHelperTuning.get_raw_text(title)
        localized_text = lambda **_: LocalizationHelperTuning.get_raw_text("Pick up to {} Sims".format(max))
        dialog = UiSimPicker.TunableFactory().default(sim,
                                                      text=localized_text,
                                                      title=localized_title,
                                                      max_selectable=max,
                                                      min_selectable=1,
                                                      should_show_names=True,
                                                      hide_row_description=False)
        for s in sim_ids:
            dialog.add_row(SimPickerRow((s[0]), False, tag=(s[0])))
        dialog.add_listener(get_simpicker_results_callback)
        dialog.show_dialog()
    except BaseException as e:
        error_trap(e)


def get_object_pos(obj: GameObject):
    if obj is None:
        return
    translation = obj.location.transform.translation
    return translation


def get_object_rotate(obj: GameObject):
    if obj is None:
        return
    orientation = obj.location.transform.orientation
    return orientation

def delete_que_menu(index: int):
    try:
        job_names = []
        job_sims = []
        job_ids = []
        job_type = None

        def handle_result(result):
            count = 0
            if result == None:
                return
            for choice in job_names:
                if result == choice:
                    delete_que_menu_callback(job_sims[count], job_ids[count])
                count = count + 1
                if count is 8:
                    break
            if result == "More":
                delete_que_menu(index + 8)
            elif index is not 0 and result == "Back":
                delete_que_menu(index - 8)
            else:
                return

        count = 0
        for sim in services.sim_info_manager().instanced_sims_gen():
            sim_info = sim.sim_info
            for interaction in sim.get_all_running_and_queued_interactions():
                job_type = type(interaction)
                if count >= index:
                    job_ids.append(interaction)
                    job_sims.append(sim_info)
                    title = interaction.__class__.__name__
                    job_names.append("{} {}: ({}) {}".format(sim_info.first_name, sim_info.last_name, interaction.group_id, title))
                count = count + 1
                if count is 8 + index:
                    job_names.append("More")
                    break
            if count is 8 + index:
                break

        job_names.append("Back")
        display_choices(job_names, handle_result, text="Pick an interaction to cancel from a sims queue",
                        title="Delete an Interaction")

    except BaseException as e:
        error_trap(e)

def delete_que_menu_callback(sim_info: SimInfo, interaction):
    sim = sim_info.get_sim_instance()

    def delete_que_menu_callback_choice(dialog):
        if dialog.accepted:
            interaction.cancel(FinishingType.USER_CANCEL, 'Stop')
            # sim.clear_interaction(interaction)
            ld_notice(sim_info, "Delete An Interaction",
                      "Interaction {} deleted!".format(interaction.__class__.__name__), True, "PURPLE")
        else:
            return

    title = interaction.__class__.__name__
    text = "Please press OK to delete this interaction, or Cancel."
    client = services.client_manager().get_first_client()
    dialog = UiDialogOkCancel.TunableFactory().default(client.active_sim,
                                                       text=lambda **_: LocalizationHelperTuning.get_raw_text(text),
                                                       title=lambda **_: LocalizationHelperTuning.get_raw_text(title))
    dialog.add_listener(delete_que_menu_callback_choice)
    dialog.show_dialog()

def make_sim_at_work(sim_info: SimInfo):
    careers = get_all_careers(sim_info)
    for c in careers:
        career = sim_info.career_tracker.get_career_by_uid(c)
        if career is None:
            return False
        career._at_work = False
        try:
            if career._late_for_work_handle is not None:
                alarms.cancel_alarm(career._late_for_work_handle)
                career._late_for_work_handle = None
            else:
                career.add_pto(1)
                career.request_day_off(CareerTimeOffReason.PTO)
                career.add_pto(-1)
            career.resend_career_data()
            career.resend_at_work_info()
        except:
            pass

def end_career_session(sim_info: SimInfo):
    careers = get_all_careers(sim_info)
    for c in careers:
        career = sim_info.career_tracker.get_career_by_uid(c)
        career._clear_career_alarms()
        career._current_work_start = None
        career._current_work_end = None
        career._current_work_duration = None
        career._at_work = False
        career._rabbit_hole_id = None
        career._career_session_extended = False
        career._taking_day_off_reason = CareerTimeOffReason.NO_TIME_OFF
        career._pto_taken = 0
        career._clear_current_gig()
        career.resend_career_data()
        career.resend_at_work_info()


