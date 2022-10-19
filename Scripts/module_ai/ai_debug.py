import alarms
import build_buy
import camera
import date_and_time
import objects
import objects.system
import services
import sims4.commands
from module_ai.ai_functions import clear_sim_instance, get_object_pos, get_object_rotate, interaction_filter
from module_ai.ai_picker import default_picker
from module_ai.ai_util import error_trap, ld_notice, init_sim
from distributor.shared_messages import IconInfoData
from interactions.interaction_finisher import FinishingType
from objects import ALL_HIDDEN_REASONS
from objects.game_object import GameObject
from objects.object_enums import ResetReason
from protocolbuffers import Consts_pb2
from server_commands.argument_helpers import get_tunable_instance
from sims.sim_info import SimInfo
from sims.sim_info_types import Age
from sims.sim_spawner_service import SimSpawnerService
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_picker import UiObjectPicker, ObjectPickerRow, ObjectPickerType

CONNECT_TO_CONSOLE = None

@sims4.commands.Command('ld.timeline', command_type=(sims4.commands.CommandType.Live))
def ld_timeline(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    timeline = services.time_service().sim_timeline
    try:
        for handle in sorted(timeline.heap):
            if handle.element is not None:
                if isinstance(handle.element, alarms.AlarmElement):
                    continue
                parent_handle = handle
                output('\nElement scheduled at {} ({})'.format(handle.when, abs(handle.ix)))
                child_name = None
                names = []
                while parent_handle is not None:
                    name = str(parent_handle.element)
                    if child_name is not None:
                        short_name = name.replace(child_name, '$child')
                    else:
                        short_name = name
                    if short_name.find('running') is not -1:
                        names.append(short_name)
                    parent_handle = parent_handle.element._parent_handle
                    child_name = name

                for i, name in enumerate(reversed(names), 1):
                    output('{} {}'.format('*' * i, name))
    except BaseException as e:
        error_trap(e)

@sims4.commands.Command('ld.timeline.clear', command_type=(sims4.commands.CommandType.Live))
def ld_timeline_clear(_connection=None):
    timeline = services.time_service().sim_timeline
    for handle in sorted(timeline.heap):
        if handle.element is not None:
            if isinstance(handle.element, alarms.AlarmElement):
                continue
            timeline.hard_stop(handle)

@sims4.commands.Command('ld.objinfo', command_type=(sims4.commands.CommandType.Live))
def ld_objinfo(object: str, _connection=None):
    try:
        output = sims4.commands.CheatOutput(_connection)
        result = eval(object)
        output('\n\nObject {}:\n\n'.format(result.__str__))
        for att in dir(result):
            output(str(att) + ": " + str(getattr(result, att)))
        output('\n\nObject {}:\n\n'.format(result[0].__str__))
        for att in dir(result[0]):
            output(str(att) + ": " + str(getattr(result[0], att)))
    except BaseException as e:
        error_trap(e)

def focus_camera_on_sim(sim_info: SimInfo):
    sim = sim_info.get_sim_instance()
    if sim is None:
        return
    camera.focus_on_sim(sim, follow=True)

def get_number_of_objects(_connection=None):
    objects = services.object_manager().get_all()
    return len(objects)

def reset_all_objects(_connection=None):
    all_objects = services.object_manager().get_all()
    for obj in all_objects:
        if obj.definition.tuning_file_id is not 0:
            if not obj.is_sim:
                obj.reset(ResetReason.NONE, None, 'Command')

def get_number_of_sims(_connection=None):
    count = 0
    for sim_info in services.sim_info_manager().instanced_sims_gen():
        if sim_info is not None:
            count += 1
    return count

@sims4.commands.Command('ld.siminfo', command_type=(sims4.commands.CommandType.Live))
def log_sim_info(_connection=None):
    try:
        output = sims4.commands.CheatOutput(_connection)
        tgt_client = services.client_manager().get(_connection)
        sim_info = tgt_client.active_sim_info
        sim = sim_info.get_sim_instance()
        situation_manager = services.get_zone_situation_manager()

        output('commodity_tracker: {}'.format(sim_info.commodity_tracker))
        output('commodity_tracker_lod: {}'.format(sim_info.commodity_tracker
                                                  .simulation_level))
        output('is npc: {}'.format(sim_info.is_npc))
        output('is_selected: {}'.format(sim_info.is_selected))
        output('is_selectable: {}'.format(sim_info.is_selectable))
        output('get_active_buff_types: {}'.format(sim.get_active_buff_types()))
        output('get_all_running_and_queued_interactions: {}'.format(sim.get_all_running_and_queued_interactions()))
        output('get_situations_sim_is_in: {}'.format(situation_manager.get_situations_sim_is_in(sim)))
        output('REAL_MILLISECONDS_PER_SIM_SECOND: {0}'.format(date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND))
        output('_connection: {0}'.format(_connection))
        output('can away actions: {}'
               .format(sim_info.away_action_tracker
                       .is_sim_info_valid_to_run_away_actions()))
    except BaseException as e:
        error_trap(e)

def get_sim_info(sim=None):
    try:
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
        intQueue = "None"
        activeCareer = ""
        career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
        for career_id in sim_info.career_tracker._careers:
            career = sim_info.career_tracker._careers[career_id]
            if career is not None:
                type = career_manager.get(career_id)
                activeCareer = activeCareer + type.__name__ + " ({})\n".format(career_id)
        activeRoles = sim.autonomy_component.active_roles()
        getInteractions = sim.get_all_running_and_queued_interactions()

        for i, roleState in enumerate(activeRoles):
            if i == 0:
                roleStateName = roleState.__class__.__name__
            else:
                roleStateName = roleStateName + ', ' + roleState.__class__.__name__
        for i, interaction in enumerate(getInteractions):
            intQueue = intQueue + '\n' + "({}) ".format(interaction.guid64) + interaction.__class__.__name__

        sim_info.update_time_alive()
        time_alive = sim_info._time_alive.in_ticks()

        returnText = "Objects on lot: {}\nSims on lot: {}/{}\nCareer for {} {} ({}):\n{}Role for {} {} ({}):\n{}"\
                     "\nInteractions:\n{}\nSkin Tone: {}\nMood: {}\nAge: {} Hours\nZone ID: {}\nPos: {}\nOrient: {}".format(
            get_number_of_objects(None), get_number_of_sims(None),
            SimSpawnerService.NPC_SOFT_CAP, sim_info.first_name, sim_info.last_name, sim_info.sim_id, activeCareer, sim_info.first_name,
                sim_info.last_name, sim_info.sim_id, roleStateName, intQueue, sim_info.skin_tone, sim.get_mood_intensity(),
            time_alive * 0.001 * 0.0167 * 0.0167, sim_info.household.home_zone_id, get_object_pos(sim), get_object_rotate(sim))
        return returnText
    except BaseException as e:
        error_trap(e)


@sims4.commands.Command('ld.simque', command_type=(sims4.commands.CommandType.Live))
def log_all_sim_interactions(_connection=None):
    try:
        output = sims4.commands.CheatOutput(_connection)
        interaction_text = ""
        for sim in services.sim_info_manager().instanced_sims_gen():
            sim_info = sim.sim_info
            interaction_text = interaction_text + "{} {}:\n".format(sim_info.first_name, sim_info.last_name)
            for interaction in sim.get_all_running_and_queued_interactions():
                interaction_format = interaction.__class__.__name__
                interaction_text = interaction_text + "--{}\n".format(interaction_format)
        output("All Sim Interactions:\n" + interaction_text)
    except BaseException as e:
        error_trap(e)

def set_all_motives(value = 100, motive_name = None):
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
        clear_sim_instance(sim.sim_info, interaction_filter, True)

@sims4.commands.Command('ld.set_time', command_type=(sims4.commands.CommandType.Live))
def advance_game_time_ex(hours: int = 0, minutes: int = 0, seconds: int = 0, _connection=None):
    services.game_clock_service().advance_game_time(hours, minutes, seconds)
    set_all_motives(0, 'motive_energy')
    clear_all_actions()

@sims4.commands.Command('ld._delete_sim_object', command_type=(sims4.commands.CommandType.Live))
def delete_sim_object(obj_id: int, _connection=None):
    try:
        def get_simpicker_results_callback(dialog):
            if not dialog.accepted:
                return
            try:
                result_tags = dialog.get_result_tags()
                for tags in dialog.get_result_tags():
                    sim_info = services.sim_info_manager().get(tags)
                    sim = init_sim(sim_info)
                    sim.destroy()
            except BaseException as e:
                error_trap(e)

        default_picker("Delete Sim Object", "Pick up to 50 Sims", 50, False, get_simpicker_results_callback)
    except BaseException as e:
        error_trap(e)

def delete_household_inv(sim_info: SimInfo):
    try:
        sim = sim_info.get_sim_instance()
        householdid = sim_info.household_id
        household = services.household_manager().get(householdid)
        funds = household.funds.money
        household_msg = services.get_persistence_service().get_household_proto_buff(householdid)
        count = 0
        if build_buy.is_household_inventory_available(household.id):
            for object in household_msg.inventory.objects:
                try:
                    # object_data = build_buy._get_object_data_from_household_inventory(object.object_id, householdid)
                    # object_str = object_data.__str__()
                    # ld_notice(sim_info, "Household Inventory", "Object str: {}!".format(object_str))
                    if build_buy.object_exists_in_household_inventory(object.object_id, householdid):
                        build_buy.remove_object_from_household_inventory(object.object_id, household)
                except BaseException as e:
                    error_trap(e)
                    pass
                count = count + 1
        # household.funds.add(value, Consts_pb2.TELEMETRY_MONEY_CAREER, sim)
        else:
            ld_notice(sim_info, "Household Inventory", "Household inventory not available!", True, "GREEN")
            return
        sold = household.funds.money - funds
        ld_notice(sim_info, "Household Inventory",
                  "All {} inventory items sold for {}!\nRemaining funds {}!".format(count, sold, funds), True, "GREEN")
    except BaseException as e:
        error_trap(e)


def delete_sim_inv(sim_info: SimInfo):
    try:
        sim = sim_info.get_sim_instance()
        if sim is None:
            ld_notice(sim_info, "Sim Inventory", "Can't delete inventory of off lot sim!", True, "GREEN")
            return
        value = sim_info.inventory_value()
        count = len(sim_info.inventory_data.objects)
        sim.family_funds.add(value, Consts_pb2.TELEMETRY_MONEY_CAREER, sim)
        funds = sim.family_funds.money
        sim.inventory_component.purge_inventory()
        ld_notice(sim_info, "Sim Inventory",
                  "All {} inventory items sold for {}!\nRemaining funds {}!".format(count, value, funds), True, "GREEN")
    except BaseException as e:
        error_trap(e)

def add_to_inv(sim_info: SimInfo, obj: int, index=1, amount=1):
    try:
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is None:
            ld_notice(sim_info, "Sim Inventory", "Can't add inventory of off lot sim!", True, "GREEN")
            return
        add_obj = objects.system.create_object(obj)
        add_obj.set_household_owner_id(sim.household_id)
        if add_obj is None:
            ld_notice(sim_info, "Sim Inventory", "Can't add object {}!".format(obj), True, "GREEN")
            return
        inventory = sim.inventory_component
        if inventory.can_add(add_obj):
            inventory.player_try_add_object(add_obj)
            if index == amount:
                ld_notice(sim_info, "Sim Inventory", "{} item(s) added to inventory!".format(amount), True, "GREEN")
        else:
            if not build_buy.move_object_to_household_inventory(add_obj):
                ld_notice(sim_info, "Sim Inventory", "Item NOT added to inventory!", True, "GREEN")
            else:
                ld_notice(sim_info, "Sim Inventory", "Item added to household inventory!", True, "GREEN")
    except BaseException as e:
        error_trap(e)


def get_icon_info_data(obj: GameObject):
    return IconInfoData(obj_instance=obj, obj_def_id=(obj.definition.id),
                        obj_geo_hash=(obj.geometry_state),
                        obj_material_hash=(obj.material_hash),
                        obj_name=(LocalizationHelperTuning.get_object_name(obj)))

def show_household_inv(sim_info: SimInfo, target: GameObject, is_delete=False):
    try:
        def get_picker_results_callback(dialog):
            try:
                if not dialog.accepted:
                    return
                result_tags = dialog.get_result_tags()
                for tags in result_tags:
                    if is_delete and inventory_available:
                        household = services.household_manager().get(householdid)
                        _ids = build_buy.get_object_ids_in_household_inventory(householdid)
                        if len(_ids):
                            for _object_id in _ids:
                                _obj_data = build_buy.get_object_in_household_inventory(_object_id, householdid)
                                if _obj_data.definition.id == tags.definition.id:
                                    build_buy.remove_object_from_household_inventory(_object_id, household)
                                    ld_notice(sim_info, "Household Inventory",
                                              "Deleted object ID: {}".format(_object_id), True, "GREEN")
                    elif not is_delete:
                        new_obj = objects.system.find_object(tags.definition.id)
                        if new_obj is None:
                            new_obj = objects.system.create_object(tags.definition.id)
                        if new_obj is not None:
                            new_obj.location = target.location
                        else:
                            ld_notice(sim_info, "Household Inventory", "Unable to place object {}".format(tags.definition.id), True, "GREEN")
                    else:
                        ld_notice(sim_info, "Household Inventory", "Household inventory not available!", True, "GREEN")
                        return
            except BaseException as e:
                error_trap(e)

        localized_title = lambda **_: LocalizationHelperTuning.get_raw_text("Household Inventory")
        localized_text = lambda **_: LocalizationHelperTuning.get_raw_text("")
        dialog = UiObjectPicker.TunableFactory().default(sim_info,
                                                      text=localized_text,
                                                      title=localized_title,
                                                      max_selectable=10,
                                                      min_selectable=1,
                                                      picker_type=ObjectPickerType.OBJECT)

        householdid = sim_info.household_id
        zone = services.current_zone()
        obj_manager = services.object_manager()
        inventory_available = build_buy.is_household_inventory_available(householdid)
        object_ids = build_buy.get_object_ids_in_household_inventory(householdid)
        inventory = sim_info.get_sim_instance().inventory_component
        for obj in inventory:
            object_ids.append(obj.id)
        if len(object_ids) and inventory_available:
            for object_id in object_ids:
                obj_data = build_buy.get_object_in_household_inventory(object_id, householdid)
                if obj_data is None:
                    obj_data = zone.find_object(object_id, include_household=True)
                if obj_data is None:
                    obj_data = obj_manager.get(object_id)
                if obj_data is not None:
                    obj_name = LocalizationHelperTuning.get_object_name(obj_data)
                    obj_label = LocalizationHelperTuning.get_raw_text("Object ID: ({})".format(obj_data.definition.id))
                    dialog.add_row(ObjectPickerRow(name=obj_name, row_description=obj_label, icon_info=get_icon_info_data(obj_data), tag=obj_data))
                else:
                    ld_notice(sim_info, "Household Item", "Household item {} not available!".format(object_id), True, "GREEN")
        elif not inventory_available:
            household_msg = services.get_persistence_service().get_household_proto_buff(householdid)
            for object_data in household_msg.inventory.objects:
                obj = services.object_manager().get(object_data.guid)
                if obj is None:
                    obj = objects.system.find_object(object_data.guid)
                if obj is None:
                    obj = objects.system.create_object(object_data.guid)
                if obj is not None:
                    obj_name = LocalizationHelperTuning.get_object_name(obj)
                    obj_label = LocalizationHelperTuning.get_raw_text("Object ID: ({})".format(obj.definition.id))
                    dialog.add_row(ObjectPickerRow(name=obj_name, row_description=obj_label, icon_info=get_icon_info_data(obj), tag=obj))
                else:
                    ld_notice(sim_info, "Household Item", "Household item {} not available!".format(object_data.guid), True, "GREEN")
        else:
            ld_notice(sim_info, "Household Inventory", "Household inventory not available!", True, "GREEN")
            return

        dialog.add_listener(get_picker_results_callback)
        dialog.show_dialog()

    except BaseException as e:
        error_trap(e)

def delete_household_inv_old(sim_info: SimInfo):
    try:
        sim = sim_info.get_sim_instance()
        householdid = sim_info.household_id
        household = services.household_manager().get(householdid)
        funds = household.funds.money
        manager = services.object_manager()
        count = 0
        if build_buy.is_household_inventory_available(household.id):
            try:
                for (def_id, obj_state), definition in services.definition_manager()._definitions_cache.items():
                    obj_ids = build_buy.find_objects_in_household_inventory((def_id,), household.id)
                    for obj_ids in obj_ids:
                        build_buy.remove_object_from_household_inventory(obj_ids, household)
            except:
                ld_notice(sim_info, "Household Inventory", "Object id: {} error!".format(object.object_id), True, "ORANGE")
                pass
            count = count + 1
        sold = household.funds.money - funds
        ld_notice(sim_info, "Household Inventory",
                  "All {} inventory items sold for {}!\nRemaining funds {}!".format(count, sold, funds), True, "GREEN")
    except BaseException as e:
        error_trap(e)


@sims4.commands.Command('ld._delete_household_inventory', command_type=(sims4.commands.CommandType.Live))
def _delete_household_inventory(obj_id: int, _connection=None):
    try:
        def get_simpicker_results_callback(dialog):
            if not dialog.accepted:
                return
            result_tags = dialog.get_result_tags()
            for tags in result_tags:
                sim_info = services.sim_info_manager().get(tags)
                show_household_inv(sim_info, None, True)

        default_picker("Delete Household Inventory", "Pick up to 1 Sim", 1, False, get_simpicker_results_callback)
    except BaseException as e:
        error_trap(e)


@sims4.commands.Command('ld._delete_sim_inventory', command_type=(sims4.commands.CommandType.Live))
def _delete_sim_inventory(obj_id: int, _connection=None):
    try:
        client = services.client_manager().get_first_client()
        sim_ids = []
        for sim_info in services.sim_info_manager().instanced_sims_gen():
            if sim_info.age != Age.BABY:
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
                    delete_sim_inv(sim_info)
            except BaseException as e:
                error_trap(e)

        default_picker("Delete Sim Inventory", "Pick up to 50 Sims", 50, False, get_simpicker_results_callback)
    except BaseException as e:
        error_trap(e)

@sims4.commands.Command('ld._delete_sim_inventory', command_type=(sims4.commands.CommandType.Live))
def _add_to_sim_inventory(obj_id: int, amount=1, _connection=None):
    try:
        if amount == 0:
            amount = 1
        client = services.client_manager().get_first_client()
        sim_ids = []
        for sim_info in services.sim_info_manager().instanced_sims_gen():
            if sim_info.age != Age.BABY:
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
                    index = 0
                    while index < amount:
                        index = index + 1
                        add_to_inv(sim_info, obj_id, index, amount)

            except BaseException as e:
                error_trap(e)

        default_picker("Add To Sim Inventory", "Pick up to 1 Sim", 1, False, get_simpicker_results_callback)
    except BaseException as e:
        error_trap(e)

def _place_household_inventory(obj: GameObject, _connection=None):
    try:
        client = services.client_manager().get_first_client()
        sim_ids = []
        for sim_info in services.sim_info_manager().instanced_sims_gen():
            if sim_info.age != Age.BABY:
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
                    show_household_inv(sim_info, obj, False)
            except BaseException as e:
                error_trap(e)

        default_picker("Show Household Inventory", "Pick up to 1 Sim", 1, False, get_simpicker_results_callback)
    except BaseException as e:
        error_trap(e)

@sims4.commands.Command('dcc.find_sim', command_type=(sims4.commands.CommandType.Live))
def find_sim(obj_id: int, _connection=None):
    try:
        client = services.client_manager().get_first_client()
        sim_ids = []
        for sim_info in services.sim_info_manager().instanced_sims_gen():
            if sim_info.age != Age.BABY:
                sim_ids.append((sim_info.sim_id, sim_info.last_name, sim_info.first_name))

        sim_ids.sort(key=(lambda s: s[2]))
        sim_ids.sort(key=(lambda s: s[1]))

        def get_simpicker_results_callback(dialog):
            if not dialog.accepted:
                return
            result_tags = dialog.get_result_tags()
            sim_info = services.sim_info_manager().get(result_tags[0])
            focus_camera_on_sim(sim_info)

        default_picker("Find Sim", "Pick up to 1 Sim to Find", 1, False, get_simpicker_results_callback)
    except BaseException as e:
        error_trap(e)


@sims4.commands.Command('ld.reset_sit', command_type=(sims4.commands.CommandType.Live))
def reset_all_situations(obj_id: int, _connection=None):
    situation_manager = services.get_zone_situation_manager()
    for situation in situation_manager.running_situations():
        job_title = "{}".format(situation.__class__.__name__)
        if (job_title.find('holiday') == -1) and (job_title.find('club') == -1):
            situation_manager.destroy_situation_by_id(situation.id)


def reset_sim_situations(sim_info: SimInfo):
    sim = init_sim(sim_info)
    situation_manager = services.get_zone_situation_manager()
    situation_manager.on_sim_reset(sim)


@sims4.commands.Command('ld.reset', command_type=(sims4.commands.CommandType.Live))
def reset_sim_picker(_connection=None):
    try:
        def get_simpicker_results_callback(dialog):
            if not dialog.accepted:
                return
            try:
                result_tags = dialog.get_result_tags()
                for tags in dialog.get_result_tags():
                    sim_info = services.sim_info_manager().get(tags)
                    sim = init_sim(sim_info)
                    situation_manager = services.get_zone_situation_manager()
                    for situation in situation_manager.get_situations_sim_is_in(sim):
                        job_title = "{}".format(situation.__class__.__name__)
                        if (job_title.find('holiday') == -1) and (job_title.find('club') == -1):
                            situation_manager.destroy_situation_by_id(situation.id)
                    role_tracker = sim.autonomy_component._role_tracker
                    role_tracker.reset()
                    situation_manager.create_visit_situation(sim)
                    sim.reset(ResetReason.NONE, None, 'Command')
            except BaseException as e:
                error_trap(e)

        default_picker("Reset Sims", "Pick up to 50 Sims", 50, False, get_simpicker_results_callback)
    except BaseException as e:
        error_trap(e)

@sims4.commands.Command('ld.reset_all', command_type=(sims4.commands.CommandType.Live))
def reset_all_sims(obj_id: int, _connection=None):
    try:
        sims = services.sim_info_manager().instanced_sims_gen(allow_hidden_flags=(objects.ALL_HIDDEN_REASONS))
        services.get_reset_and_delete_service().trigger_batch_reset(sims)
    except BaseException as e:
        error_trap(e)

def _clear_interactions_for_sims(filter=None):
    try:
        def get_simpicker_results_callback(dialog):
            if not dialog.accepted:
                return
            try:
                result_tags = dialog.get_result_tags()
                for tags in result_tags:
                    sim_info = services.sim_info_manager().get(tags)
                    clear_sim_instance(sim_info, filter, True)
            except BaseException as e:
                error_trap(e)

        default_picker("Clear Interactions For Sims", "Pick up to 50 Sims", 50, False, get_simpicker_results_callback)
    except BaseException as e:
        error_trap(e)