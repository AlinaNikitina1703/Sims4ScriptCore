import random

import alarms
import build_buy
import services
from careers.career_base import CareerBase
from careers.career_event import CareerEvent
from careers.career_event_manager import CareerEventManager
from careers.career_event_zone_requirement import RequiredCareerEventZoneCustomerLot, RequiredCareerEventZoneRandom, \
    RequiredCareerEventZoneLotDescription
from careers.career_ops import CareerTimeOffReason
from event_testing import test_events
from module_career.sc_career_functions import get_routine_objects_by_title, find_empty_random_bed, find_empty_computer, \
    find_empty_register, find_empty_desk_by_id, find_empty_desk
from objects import ALL_HIDDEN_REASONS
from scripts_core.sc_jobs import distance_to, check_actions, clear_sim_instance, go_here_routine, push_sim_function, \
    debugger, set_all_motives_by_sim, clear_jobs, get_sleep_hours, make_clean, \
    object_is_dirty, make_dirty, create_dust, get_dust_action_and_vacuum, remove_object_from_list, check_action_list, \
    find_all_objects_by_title, distance_to_by_level, push_sim_out, remove_sim, make_sim_leave, \
    get_spawn_point_by_distance, distance_to_pos, distance_to_by_room, assign_routine
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import init_sim, message_box, error_trap, clean_string
from server_commands.argument_helpers import get_tunable_instance
from sims.sim_spawner import SimSpawner
from sims4.math import Vector3
from sims4.random import weighted_random_item
from sims4.resources import Types
from terrain import get_terrain_center, get_terrain_height
from world import get_lot_id_from_instance_id
from world.travel_service import travel_sim_to_zone
from world.travel_tuning import TravelSimLiability


class sc_CareerRoutine:
    objects = []
    dirty_objects = []
    def __init__(self):
        super().__init__()
        self.cleaning_job_list = {"object": ["trash_",
                                        "dustpile",
                                        "puddle",
                                        "food",
                                        "drink_",
                                        ":drink",
                                        "hospitalexambed",
                                        "steamroom",
                                        "grill",
                                        "coffee",
                                        "tabledining",
                                        "microwave",
                                        "object_desk",
                                        "toilet",
                                        "sink_counter",
                                        "sinkcounter",
                                        "sinkpedg",
                                        "sinkpeds",
                                        "sink",
                                        "shower",
                                        "analyzer",
                                        "counter"],

                             "action": [13175,
                                        0,
                                        13835,
                                        13169,
                                        13169,
                                        13169,
                                        107425,  # hospitalexambed
                                        118731,
                                        35024,
                                        13163,
                                        14354,
                                        13599,
                                        100035,
                                        14431,
                                        29854,  # sink_counter
                                        29854,
                                        29854,
                                        29854,
                                        14239,
                                        13949,
                                        107798,
                                        29829]}

    def _travel_sim(self):
        client = services.client_manager().get_first_client()
        self.sim_info.inject_into_inactive_zone((self.to_zone_id), skip_instanced_check=True)
        for sim in self.additional_sims:
            sim.sim_info.inject_into_inactive_zone((self.to_zone_id), skip_instanced_check=True)
            sim.sim_info.save_sim()
            sim.schedule_destroy_asap(post_delete_func=(client.send_selectable_sims_update), source=self, cause='Destroying sim in travel liability')

        sim = self.sim_info.get_sim_instance()
        if sim is not None:
            next_sim_info = client.selectable_sims.get_next_selectable(self.sim_info)
            next_sim = next_sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if next_sim is not sim:
                if self.is_attend_career:
                    self._attend_career()
                if sim.is_selected:
                    client.set_next_sim_or_none()
                self.sim_info.save_sim()
                sim.schedule_destroy_asap(post_delete_func=(client.send_selectable_sims_update), source=self, cause='Destroying sim in travel liability')
            else:
                sim.fade_in()

    def get_required_zone_id_description(self, sim_info):
        name = "{} {}".format(sim_info.first_name, sim_info.last_name)
        if "Robyn" in name:
            zone_id = 378036983767272018
        else:
            lot_id = get_lot_id_from_instance_id(self.lot_description)
            if self.house_description is not None:
                for zone_proto in services.get_persistence_service().zone_proto_buffs_gen():
                    if zone_proto.lot_description_id == self.lot_description:
                        zone_proto.pending_house_desc_id = self.house_description
                        break

            zone_id = services.get_persistence_service().resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True)
        return zone_id

    def get_required_zone_id_random(self, sim_info):
        name = "{} {}".format(sim_info.first_name, sim_info.last_name)
        if "Robyn" in name:
            zone_id = 378036983767272018
        else:
            zone_ids = [(self._get_random_weight(zone_proto), zone_proto.zone_id) for zone_proto in services.get_persistence_service().zone_proto_buffs_gen()]
            zone_reservation_service = services.get_zone_reservation_service()
            zone_ids = [(x, zone_id) for x, zone_id in zone_ids if not zone_reservation_service.is_reserved(zone_id)]
            zone_id = weighted_random_item(zone_ids)
            if zone_id is None:
                return
        return zone_id

    def get_required_zone_id_customer_lot(self, sim_info):
        career = sim_info.careers.get(self.career.guid64, None)
        if career is None:
            return 0
        name = "{} {}".format(sim_info.first_name, sim_info.last_name)
        if "Robyn" in name:
            customer_lot_id = 378036983767272018
        else:
            customer_lot_id = career.get_customer_lot_id()
            if not customer_lot_id:
                return 0
        return customer_lot_id

    def get_required_zone_id(self):
        sim_info = self._career.sim_info
        name = "{} {}".format(sim_info.first_name, sim_info.last_name)
        if "Robyn" in name:
            self._required_zone_id = 378036983767272018
        return self._required_zone_id

    def start_top_career_event(self, start_situation_fn=None):
        career_event = self._get_top_career_event()
        target_zone_id = career_event.get_required_zone_id()
        sim_info = self._career.sim_info
        if start_situation_fn is not None:

            def _start_travel():
                event_situation_id = start_situation_fn(target_zone_id)
                career_event.set_event_situation_id(event_situation_id)

        else:

            def _start_travel():
                return travel_sim_to_zone(sim_info.id, target_zone_id)

        def _start_event():
            self.start_immediately(career_event)
            if start_situation_fn is not None:
                event_situation_id = start_situation_fn(target_zone_id)
                career_event.set_event_situation_id(event_situation_id)

        if target_zone_id is None:
            target_zone_id = 0
            _start_event()
        else:
            if sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
                if sim_info.zone_id == target_zone_id:
                    _start_event()
                else:
                    _start_travel()
            elif services.current_zone_id() == target_zone_id:
                SimSpawner.spawn_sim(sim_info, spawn_action=(lambda sim: _start_event()))
            else:
                if sim_info.zone_id != target_zone_id:
                    sim_info.inject_into_inactive_zone(target_zone_id)
                _start_travel()

    def attend_work(self, interaction=None, start_tones=True):
        try:
            sim_info = self._sim_info
            if sc_Vars.tag_sim_for_debugging:
                name = "{} {}".format(sim_info.first_name, sim_info.last_name)
                if name in sc_Vars.tag_sim_for_debugging:
                    debugger("Sent sim: {} to work".format(name), 0, True)

            if not self._has_attended_first_day:
                self._has_attended_first_day = True
            else:
                if self._at_work:
                    return
                self.days_worked_statistic.add_value(1)
                self._at_work = True
                gig = self.get_current_gig()
                if gig is not None:
                    gig.notify_gig_attended()
                self._taking_day_off_reason = CareerTimeOffReason.NO_TIME_OFF
                self.add_pto(self._pto_taken * -1)
                self._pto_taken = 0
                if self._late_for_work_handle is not None:
                    alarms.cancel_alarm(self._late_for_work_handle)
                    self._late_for_work_handle = None
                self.on_assignment or self.send_career_message(self.career_messages.career_daily_start_notification)
                self.resend_career_data()
                self.resend_at_work_info()
            if start_tones:
                self.start_tones()
            services.get_event_manager().process_event((test_events.TestEvent.WorkdayStart), sim_info=(self._sim_info),
              career=self)
        except BaseException as e:
            error_trap(e)

    def custom_routine(self, sim_info):
        sim = init_sim(sim_info)
        if sim:
            lot = services.current_zone().lot
            objs = get_routine_objects_by_title(sim_info.routine_info.use_object1, sc_CareerRoutine.objects)
            if objs:
                objs.sort(key=lambda obj: distance_to(obj, lot))
                if sim_info.use_object_index >= len(objs):
                    sim_info.use_object_index = 0
                obj = objs[sim_info.use_object_index]
                if obj:
                    if not check_actions(sim, "gohere") and distance_to(sim, obj) > 5:
                        clear_sim_instance(sim_info)
                        go_here_routine(sim, obj.position, obj.level, 2.0)
                        if sc_Vars.DEBUG:
                            debugger("Sim: {} - Obj: {} Action: gohere".format(sim_info.first_name, str(obj)))
                        return True
                    if check_actions(sim, "clean") and distance_to(sim, obj) < 5:
                        clear_sim_instance(sim_info, "clean", True)
                        if sc_Vars.DEBUG:
                            debugger("Sim: {} - Obj: {} Action: clean".format(sim_info.first_name, str(obj)))
                        return True
                    if sim_info.routine_info.actions:
                        if check_actions(sim, "chat") and distance_to(sim, obj) < 5:
                            clear_sim_instance(sim_info, "|".join(sim_info.routine_info.actions))
                            if sim_info.routine_info.object_action1 and not check_actions(sim, sim_info.routine_info.object_action1):
                                push_sim_function(sim, obj, sim_info.routine_info.object_action1, False)
                            if sc_Vars.DEBUG:
                                debugger("Sim: {} - Obj: {} Action: chat".format(sim_info.first_name, str(obj)))
                            return True
                        if check_action_list(sim, sim_info.routine_info.actions) and distance_to(sim, obj) < 5:
                            if sim_info.routine_info.object_action1:
                                clear_sim_instance(sim_info, sim_info.routine_info.object_action1)
                            if sc_Vars.DEBUG:
                                debugger("Sim: {} - Obj: {} Action: actions".format(sim_info.first_name, str(obj)))
                            return True
                    if sim_info.routine_info.object_action1:
                        if obj.in_use and not obj.in_use_by(sim):
                            sim_info.use_object_index += 1
                            if sc_Vars.DEBUG:
                                debugger("Sim: {} - Obj Index: {}".format(sim_info.first_name, sim_info.use_object_index))
                            return True
                        if not check_actions(sim, sim_info.routine_info.object_action1) and distance_to(sim, obj) < 5:
                            clear_sim_instance(sim_info, "stand|wicked|social|chat", True)
                            push_sim_function(sim, obj, sim_info.routine_info.object_action1, False)
                            if sc_Vars.DEBUG:
                                debugger("Sim: {} - Obj: {} Action1: {}".format(sim_info.first_name, str(obj), sim_info.routine_info.object_action1))
                            return True

                    if sim_info.routine_info.object_action2:
                        if "object_sim" in sim_info.routine_info.use_object2:
                            objs2 = [sim, ]
                        else:
                            objs2 = find_all_objects_by_title(sim, sim_info.routine_info.use_object2, sc_Vars.MIN_LEVEL, sc_Vars.MAX_DISTANCE, False, True)

                        if objs2:
                            obj2 = objs2[0]
                            if not check_actions(sim, sim_info.routine_info.object_action2) and distance_to(sim, obj2) < 5:
                                clear_sim_instance(sim_info, "stand|wicked|social|chat", True)
                                push_sim_function(sim, obj2, sim_info.routine_info.object_action2, False)
                                if sc_Vars.DEBUG:
                                    debugger("Sim: {} - Obj: {} Action2: {}".format(sim_info.first_name, str(obj2), sim_info.routine_info.object_action2))
                                return True
        return True

    def metalhead_routine(self, sim_info):
        sim = init_sim(sim_info)
        if sim:
            lot = services.current_zone().lot
            objs = [obj for obj in services.object_manager().get_all() if distance_to(lot, obj) <
                    sc_Vars.MAX_DISTANCE and obj.level >= sc_Vars.MIN_LEVEL and sim_info.routine_info.use_object1 in
                    str(obj).lower() and "broadcaster_Stereo_Metal" in str(obj._on_location_changed_callbacks)]
            if objs:
                objs.sort(key=lambda obj: distance_to(obj, lot))
                obj = objs[0]
                if obj:
                    if not check_actions(sim, "gohere") and distance_to_by_room(sim, obj) > 5:
                        clear_sim_instance(sim_info)
                        go_here_routine(sim, obj.position, obj.level, 2.0)
                        if sc_Vars.DEBUG:
                            debugger("Sim: {} - Obj: {} Action: gohere".format(sim_info.first_name, str(obj)))
                        return True
                    if sim_info.routine_info.actions:
                        if check_action_list(sim, sim_info.routine_info.actions) and distance_to_by_room(sim, obj) < 5:
                            if sim_info.routine_info.object_action1:
                                clear_sim_instance(sim_info, sim_info.routine_info.object_action1)
                            if sc_Vars.DEBUG:
                                debugger("Sim: {} - Obj: {} Action: actions".format(sim_info.first_name, str(obj)))
                            return True

                    if sim_info.routine_info.object_action1:
                        if not check_actions(sim, sim_info.routine_info.object_action1) and distance_to_by_room(sim, obj) < 5:
                            clear_sim_instance(sim_info, "stand|wicked|social|chat", True)
                            push_sim_function(sim, obj, sim_info.routine_info.object_action1, False)
                            if sc_Vars.DEBUG:
                                debugger("Sim: {} - Obj: {} Action1: {}".format(sim_info.first_name, str(obj), sim_info.routine_info.object_action1))
                            return True

                    if sim_info.routine_info.object_action2:
                        if "object_sim" in sim_info.routine_info.use_object2:
                            objs2 = [sim, ]
                        else:
                            objs2 = [obj, ]

                        if objs2:
                            obj2 = objs2[0]
                            if not check_actions(sim, sim_info.routine_info.object_action2) and distance_to_by_room(sim, obj2) < 5:
                                clear_sim_instance(sim_info)
                                push_sim_function(sim, obj2, sim_info.routine_info.object_action2, False)
                                if sc_Vars.DEBUG:
                                    debugger("Sim: {} - Obj: {} Action2: {}".format(sim_info.first_name, str(obj2), sim_info.routine_info.object_action2))
                                return True

            else:
                clear_sim_instance(sim_info)
                assign_routine(sim_info, "leave")
                return True
        return True

    def fire_dance_routine(self, sim_info):
        sim = init_sim(sim_info)
        if sim:
            object_list = [obj for obj in services.object_manager().get_all() if distance_to_by_room(sim, obj) < 10 and
                not obj.is_sim and "bonfire" in str(obj).lower()]
            object_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
            if len(object_list):
                fire = object_list[0]
                if "unlit" in str(fire.material_state).lower():
                    clear_sim_instance(sim_info)
                    push_sim_function(sim, fire, 121477, False)
                    return True
                elif not check_actions(sim, "dance"):
                    clear_sim_instance(sim_info)
                    push_sim_function(sim, fire, 121613, False)
                    return True
        return False

    def dance_around_fire_routine(self, sim_info):
        sim = init_sim(sim_info)
        if sim:
            object_list = [obj for obj in services.object_manager().get_all() if distance_to_by_room(sim, obj) < 10 and
                not obj.is_sim and "bonfire" in str(obj).lower()]
            object_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
            if len(object_list):
                fire = object_list[0]
                if "unlit" in str(fire.material_state).lower():
                    clear_sim_instance(sim_info)
                    push_sim_function(sim, fire, 121477, False)
                    return True
                elif not check_actions(sim, "dance"):
                    clear_sim_instance(sim_info)
                    push_sim_function(sim, fire, 121610, False)
                    return True
        return False

    def hangout_fire_routine(self, sim_info):
        sim = init_sim(sim_info)
        if sim:
            object_list = [obj for obj in services.object_manager().get_all() if distance_to_by_room(sim, obj) < 10 and
                not obj.is_sim and "bonfire" in str(obj).lower()]
            object_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
            if len(object_list):
                fire = object_list[0]
                if "unlit" in str(fire.material_state).lower():
                    clear_sim_instance(sim_info)
                    push_sim_function(sim, fire, 121477, False)
                    return True
                elif not check_actions(sim, "hangout"):
                    clear_sim_instance(sim_info)
                    push_sim_function(sim, fire, 129617, False)
                    return True
                else:
                    sim_list = [s for s in services.sim_info_manager().instanced_sims_gen() if s != sim]
                    if sim_list:
                        sim_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
                        target = sim_list[0]
                        push_sim_function(sim, target, 27173, False)
                        return True
        return False

    def socialize_routine(self, sim_info):
        sim = init_sim(sim_info)
        if sim:
            sim_list = [s for s in services.sim_info_manager().instanced_sims_gen() if s != sim]
            if sim_list:
                sim_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
                target = sim_list[0]
                if not check_actions(sim, "chat"):
                    clear_sim_instance(sim_info)
                    push_sim_function(sim, target, 27173, False)
                    if sc_Vars.DEBUG:
                        debugger("Sim {} - Socialize with: {}".format(sim.first_name, target.first_name))
        return False

    def go_home_routine(self, sim_info):
        sim = init_sim(sim_info)
        if sim:
            center_pos = services.current_zone().lot.position
            spawn_point = get_spawn_point_by_distance(center_pos, 64)
            if hasattr(spawn_point, "_center"):
                pos = spawn_point._center
            else:
                pos = get_terrain_center()
                pos.y = get_terrain_height(pos.x, pos.z)

            if not check_actions(sim, "gohere") and distance_to_pos(sim.position, pos) > 8:
                make_sim_leave(sim)
                if sc_Vars.DEBUG:
                    debugger("Sim: {} - Going Home".format(sim_info.first_name))
                return True
            elif distance_to_pos(sim.position, pos) < 8:
                clear_sim_instance(sim_info)
                remove_sim(sim)
        return True

    def room_check_routine(self, sim_info):
        sim = init_sim(sim_info)
        if sim:
            if check_actions(sim, "treadmill"):
                return True
            if check_actions(sim, "xray"):
                return True

            slab = None
            xray = None
            room_slab_is_in = -1
            room_xray_is_in = -1

            slabs = find_all_objects_by_title(sim, "mortuaryslab")
            if slabs:
                slab = next(iter(slabs))
                room_slab_is_in = build_buy.get_room_id(slab.zone_id, slab.position, slab.level)
            xrays = find_all_objects_by_title(sim, "xray")
            if xrays:
                xray = next(iter(xrays))
                room_xray_is_in = build_buy.get_room_id(xray.zone_id, xray.position, xray.level)
            room_sim_is_in = build_buy.get_room_id(sim.zone_id, sim.position, sim.level)

            if slab:
                dist = distance_to_by_level(sim, slab)

                if sc_Vars.DEBUG:
                    debugger("Sim: {} {} - Slab: {} - Dist: {} - Sim Room: {} - Slab Room: {}".format(
                        sim.first_name,
                        sim.last_name,
                        str(slab), dist, room_sim_is_in,
                        room_slab_is_in))

                if sim_info.routine_info.title == "pathologist" or sim_info.routine_info.title == "pathologist":
                    if dist > 10 and room_sim_is_in != room_slab_is_in:
                        if not check_actions(sim, "gohere"):
                            clear_sim_instance(sim.sim_info, "gohere", True)
                            go_here_routine(sim, slab.position, slab.level)
                else:
                    if dist < 10 and room_sim_is_in == room_slab_is_in:
                        if not check_actions(sim, "gohere"):
                            clear_sim_instance(sim.sim_info, "gohere", True)
                            push_sim_out(sim, 24)
    
            if xray:
                dist = distance_to_by_level(sim, xray)
                if sim_info.routine_info.title == "radiologist" or sim_info.routine_info.title == "radiologist":
                    if dist > 15 and room_sim_is_in != room_xray_is_in:
                        chairs = find_all_objects_by_title(xray, "sitliving|sitdining|sitsofa|chair|stool",xray.level)
                        if chairs:
                            chair = next(iter(chairs))
                            clear_sim_instance(sim.sim_info)
                            if "stool" in str(chair).lower():
                                push_sim_function(sim, chair, 157667)
                            else:
                                push_sim_function(sim, chair, 31564)
        return True

    def sleep_routine(self, sim_info):
        sim = init_sim(sim_info)
        if sim:
            if not get_sleep_hours(sim):
                clear_jobs(sim_info)
                set_all_motives_by_sim(sim, 100, 'motive_fun')
                set_all_motives_by_sim(sim, 100, 'motive_social')
                set_all_motives_by_sim(sim, 100, 'motive_hygiene')
                set_all_motives_by_sim(sim, 100, 'motive_hunger')
                set_all_motives_by_sim(sim, -50, 'motive_energy')
                set_all_motives_by_sim(sim, 100, 'motive_bladder')
            else:
                set_all_motives_by_sim(sim, 100, 'motive_energy')

            if check_actions(sim, "sleep"):
                cur_stat = get_tunable_instance((Types.STATISTIC), 'motive_energy', exact_match=True)
                tracker = sim.get_tracker(cur_stat)
                cur_value = tracker.get_value(cur_stat) if tracker is not None else 0
                if cur_value < 95:
                    clear_sim_instance(sim_info, "sleep", True)
                    return True
                else:
                    clear_sim_instance(sim_info)
                    return True
            if not check_actions(sim, "sleep"):
                cur_stat = get_tunable_instance((Types.STATISTIC), 'motive_energy', exact_match=True)
                tracker = sim.get_tracker(cur_stat)
                cur_value = tracker.get_value(cur_stat) if tracker is not None else 0
                if cur_value < 0:
                    bed = find_empty_random_bed(sim)
                    if bed:
                        clear_sim_instance(sim_info)
                        push_sim_function(sim, bed, 13094, False)
                        return True
                    else:
                        set_all_motives_by_sim(sim)
        return True

    def browse_web_routine(self, sim_info):
        sim = init_sim(sim_info)
        if sim:
            random.seed(int(sim.sim_id))
            if not check_actions(sim, "browse_web") and not check_actions(sim, "sit"):
                object1, object2 = find_empty_computer(sim)
                if object1 and object2:
                    clear_sim_instance(sim_info, "chat|browse|sit", True)
                    if sc_Vars.DEBUG and sim == services.get_active_sim():
                        message_box(sim, object2, "Found Seat", "", "GREEN")
                    if "stool" in str(object2).lower():
                        push_sim_function(sim, object2, 157667, False)
                    else:
                        push_sim_function(sim, object2, 31564, False)
            elif check_actions(sim, "sit") and not check_actions(sim, "browse_web"):
                object1, object2 = find_empty_computer(sim)
                if distance_to(sim, object1) > 2:
                    go_here_routine(sim, object1.position, object1.level)
                    return True
                clear_sim_instance(sim_info, "chat|browse|sit", True)
                push_sim_function(sim, object1, 13187, False)
        return True

    def cashier_routine(self, sim_info):
        sim = init_sim(sim_info)
        if sim:
            register, chair = find_empty_register(sim)
            if register and chair:
                choice = 0
                if check_actions(sim, "sit"):
                    choice = 0
                    if random.uniform(0, 100) < 25:
                        choice = random.randint(0, 1)
                elif check_actions(sim, "clockin"):
                    choice = 1
                    if random.uniform(0, 100) < 25:
                        choice = random.randint(0, 1)

                if not check_actions(sim, "sit") and choice == 0:
                    clear_sim_instance(sim_info)
                    if "stool" in str(chair).lower():
                        push_sim_function(sim, chair, 157667, False)
                    else:
                        push_sim_function(sim, chair, 31564, False)
                elif not check_actions(sim, "clockin") and choice == 1:
                    clear_sim_instance(sim_info)
                    push_sim_function(sim, register, 109691, False)

            elif register:
                if not check_actions(sim, "clockin"):
                    clear_sim_instance(sim_info)
                    push_sim_function(sim, register, 109691, False)
        return True

    def security_check_lot_routine(self, sim_info):
        sim = init_sim(sim_info)
        if sim:
            now = services.time_service().sim_now
            random.seed(int(now.second()))
            lot = services.current_zone().lot
            center_pos = lot.position
            lot_x_size = int(lot.size_x)
            lot_z_size = int(lot.size_z)
            lot_size = (lot_x_size + lot_z_size) * 0.5 - 10
            check_point = Vector3(center_pos.x + random.uniform(-lot_size, lot_size),
                                  center_pos.y,
                                  center_pos.z + random.uniform(-lot_size, lot_size))
            if not check_actions(sim, "gohere") and not check_actions(sim, "chat"):
                clear_sim_instance(sim_info)
                go_here_routine(sim, check_point)
        return True

    def janitor_routine(self, sim_info):
        sim = init_sim(sim_info)
        if sim:
            lot = services.active_lot()
            lot_x_size = int(services.current_zone().lot.size_x)
            lot_z_size = int(services.current_zone().lot.size_z)
            lot_size = lot_x_size + lot_z_size * 0.5
            if not check_actions(sim, "gohere") and distance_to(sim, lot) > lot_size * 0.5:
                clear_sim_instance(sim_info, "gohere", True)
                go_here_routine(sim, lot.position, 0)
            else:
                self.cleaning_routine(sim_info)
        return True

    def faster_cleanup(self, sim):
        for action in sim.get_all_running_and_queued_interactions():
            if hasattr(action.target, "commodity_tracker"):
                if "vacuum" in str(action).lower() and "dust" in str(action.target).lower():
                    for commodity in action.target.commodity_tracker:
                        if "dustpile" in str(commodity).lower():
                            dust = commodity.get_value()
                            dust = dust + random.uniform(2 * sc_Vars.clean_speed, 6 * sc_Vars.clean_speed)
                            commodity.set_value(dust)
                            return
                if "mop" in str(action).lower() and "puddle" in str(action.target).lower():
                    for commodity in action.target.commodity_tracker:
                        if "evaporation" in str(commodity).lower():
                            evap = commodity.get_value()
                            evap = evap - random.uniform(2 * sc_Vars.clean_speed, 6 * sc_Vars.clean_speed)
                            commodity.set_value(evap)
                            return
                if "clean" in str(action).lower():
                    for commodity in action.target.commodity_tracker:
                        if "dirtiness" in str(commodity).lower():
                            dirt = commodity.get_value()
                            if dirt > 50:
                                make_clean(action.target)
                                return
                            dirt = dirt + random.uniform(2 * sc_Vars.clean_speed, 6 * sc_Vars.clean_speed)
                            commodity.set_value(dirt)
                            return

    def cleaning_routine(self, sim_info):
        sim = init_sim(sim_info)
        if sim:
            try:
                if [action for action in sim.get_all_running_and_queued_interactions()
                    if "vacuum" in str(action).lower() or
                       "mop" in str(action).lower() or
                       "goto" in str(action).lower() or
                       "trash_" in str(action).lower() or
                       "throw_away" in str(action).lower() or
                       "wash" in str(action).lower() or
                       "dish" in str(action).lower() or
                       "clean" in str(action).lower()]:
                    self.faster_cleanup(sim)
                else:
                    self.cleaning_job(sim)

            except BaseException as e:
                error_trap(e)

    def cleaning_job(self, sim, target=None):
        try:
            if not target:
                # TODO Write a function that stores all dirty objects on zone load instead
                if sc_CareerRoutine.dirty_objects:
                    if random.uniform(0, 100) < 75:
                        obj = sc_CareerRoutine.dirty_objects[random.randint(0, len(sc_CareerRoutine.dirty_objects) - 1)]
                    else:
                        obj = create_dust()
                    if obj is None:
                        obj = create_dust()
                    if not object_is_dirty(obj):
                        make_dirty(obj)
                else:
                    obj = create_dust()
            else:
                obj = target

            for i, title in enumerate(self.cleaning_job_list["object"]):
                if title in str(obj).lower():
                    if self.cleaning_job_list["action"][i] == 0:
                        push_sim_function(sim, obj, get_dust_action_and_vacuum(sim), False)
                    else:
                        result = push_sim_function(sim, obj, self.cleaning_job_list["action"][i], False)
                        if "executeresult: false" in str(result).lower():
                            sc_CareerRoutine.dirty_objects = remove_object_from_list(obj, sc_CareerRoutine.dirty_objects)
                            if sim == services.get_active_sim():
                                message_box(sim, obj, "cleaning_job", "Result: {}".format(clean_string(str(result))), "GREEN")
                    if sim == services.get_active_sim():
                        message_box(sim, obj, "Job Found", "Object: {}".format(str(obj)), "PURPLE")
                        return
            if sim == services.get_active_sim():
                obj = create_dust()
                push_sim_function(sim, obj, get_dust_action_and_vacuum(sim), False)
        except BaseException as e:
            error_trap(e)

    def staff_routine(self, sim_info):
        sim = init_sim(sim_info)
        if sim:
            if check_actions(sim, "xray"):
                return True
            if hasattr(sim_info.routine_info.use_object1, "isnumeric"):
                if sim_info.routine_info.use_object1.isnumeric():
                    desk, chair = find_empty_desk_by_id(sim, sim_info.routine_info.use_object1)
                else:
                    desk, chair = find_empty_desk(sim)
            else:
                desk, chair = find_empty_desk(sim)
            if desk and chair:
                computers = find_all_objects_by_title(desk, "computer", desk.level, 1.0)
                for computer in computers:
                    if sc_Vars.DEBUG:
                        debugger("Front Desk - {}".format(sim.first_name))
                    if not check_actions(sim, "frontdesk"):
                        clear_sim_instance(sim.sim_info, "frontdesk", True)
                        push_sim_function(sim, computer, 104626, False)
        return True


CareerBase.attend_work = sc_CareerRoutine.attend_work
TravelSimLiability._travel_sim = sc_CareerRoutine._travel_sim
CareerEventManager.start_top_career_event = sc_CareerRoutine.start_top_career_event
CareerEvent.get_required_zone_id = sc_CareerRoutine.get_required_zone_id
RequiredCareerEventZoneCustomerLot.get_required_zone_id = sc_CareerRoutine.get_required_zone_id_customer_lot
RequiredCareerEventZoneRandom.get_required_zone_id = sc_CareerRoutine.get_required_zone_id_random
RequiredCareerEventZoneLotDescription.get_required_zone_id = sc_CareerRoutine.get_required_zone_id_description