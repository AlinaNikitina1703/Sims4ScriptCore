import configparser
import os
import random
from os.path import isfile, join

import alarms
import build_buy
import camera
import clock
import date_and_time
import objects
import services
import sims4
from date_and_time import create_time_span
from ensemble.ensemble_service import EnsembleService
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from interactions.interaction_finisher import FinishingType
from objects.components.types import LIGHTING_COMPONENT
from objects.object_enums import ResetReason
from routing import SurfaceIdentifier, SurfaceType
from vfx import PlayEffect

from scripts_core.sc_autonomy import send_sim_home
from scripts_core.sc_bulletin import sc_Bulletin
from scripts_core.sc_input import inputbox, TEXT_INPUT_NAME, input_text
from scripts_core.sc_jobs import get_tag_name, get_sim_info, advance_game_time_and_timeline, \
    advance_game_time, sc_Vars, make_sim_selectable, make_sim_unselectable, remove_sim, remove_all_careers, \
    add_career_to_sim, get_career_name_from_string, get_current_temperature, push_sim_function, distance_to_by_room, \
    assign_role, add_to_inventory, add_to_inventory_by_id, go_here_routine, make_sim_at_work, end_career_session, \
    debugger, clear_sim_instance, assign_role_title, assign_title, remove_sim_from_rabbithole, activate_sim_icon, \
    get_career_name, get_career_level, get_object_info, get_trait_name_from_string, add_trait_by_name
from scripts_core.sc_menu_class import MainMenu
from scripts_core.sc_object_menu import ObjectMenuNoFile
from scripts_core.sc_main import ScriptCoreMain
from scripts_core.sc_routine import ScriptCoreRoutine
from scripts_core.sc_script_vars import sc_Weather
from scripts_core.sc_spawn import sc_Spawn
from scripts_core.sc_util import error_trap, ld_notice, ld_file_loader, clean_string, message_box, init_sim
from server_commands.argument_helpers import get_tunable_instance
from sims.sim_info_types import Species, Age
from sims4.localization import LocalizationHelperTuning
from sims4.math import Location, Transform, Vector3
from sims4.resources import Types
from ui.ui_dialog_notification import UiDialogNotification
from ui.ui_dialog_picker import UiSimPicker, SimPickerRow
from weather.lightning import LightningStrike
from weather.weather_enums import WeatherEffectType, WeatherElementTuple, PrecipitationType, CloudType, GroundCoverType, \
    Temperature


class ScriptCoreMenu(ImmediateSuperInteraction):
    filename = None
    datapath = os.path.join(os.environ['USERPROFILE'], "Data")
    directory = None
    last_initial_value = None
    all_fireworks = []
    firework_index = 0
    firework_random = False
    firework_timeout = 0
    firework_obj = []
    firework_translation = None
    firework_height = 0
    firework_alarm = None
    vfx = None

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.sc_menu_choices = ("<font color='#009900'>Get Info</font>",
                                "<font color='#990000'>Delete Object</font>",
                                "<font color='#000099'>Sims On Lot</font>",
                                "<font color='#000099'>Routine Sims</font>",
                                "<font color='#000000'>Fixes Menu</font>",
                                "<font color='#000000'>Weather Menu</font>",
                                "<font color='#000000'>Effects Menu</font>",
                                "<font color='#000000'>Sims Menu</font>",
                                "<font color='#000000'>Time Menu</font>",
                                "<font color='#000000'>Control Menu</font>")

        self.sc_weather_choices = ()
        self.sc_fixes_choices = ("Grab Drink",
                                "Light Fire",
                                "Extinguish Fire",
                                "Fire Dance",
                                "Hangout Fire",
                                "Dance Around Fire",
                                "Fire Dance",
                                "Add Fuel",
                                "Use Hottub",
                                "Use Skating Rink",
                                "Auto Lights",
                                "Auto Lights All",
                                "Lights On",
                                "Lights Off",
                                "All Lights On",
                                "All Lights Off")
        self.sc_effects_choices = ("Lightning Strike", "Place Fireworks", "Start Fireworks", "Stop Fireworks")
        self.sc_time_choices = ("Advance Game Time",
                            "Game Time Speed",
                            "Reset Timeline")

        self.sc_sims_choices = ("Max Motives",
                                "Remove Sims",
                            "Send Sims Home",
                            "Select Sims",
                            "Select Everyone",
                            "Unselect Sims",
                            "Unselect Everyone",
                            "Add Sims To Group",
                            "Remove Sims From Group",
                            "Teleport Menu",
                            "Delete Menu",
                            "Goto Sim",
                            "Select And Fix Sim Icons")

        self.sc_control_choices = ("Push Sim",
                                "Load Config",
                                "Load Routine",
                                "Toggle Routine",
                                "Toggle Debug",
                                "Rename World",
                                "Reload Sims",
                                "Add Career To Sims",
                                "Add Role To Sim",
                                "Add Title To Sim",
                                "Remove Career",
                                "Tag Sim For Debugging")

        self.sc_grab_drink_choices = ("Grab Vodka Soda",
                                    "Grab Beer",
                                    "Grab Long Island Iced Tea")

        self.sc_teleport_choices = ("Teleport All",
                                    "Teleport Metal",
                                    "Teleport Routine",
                                    "Teleport Traveler",
                                    "Teleport Vendor")

        self.sc_delete_choices = ("Delete All",
                                  "Delete Instanced",
                                  "Delete Metal",
                                  "Delete Routine")

        self.sc_menu = MainMenu(*args, **kwargs)
        self.sc_fixes_menu = MainMenu(*args, **kwargs)
        self.sc_grab_drink_menu = MainMenu(*args, **kwargs)
        self.sc_weather_menu = MainMenu(*args, **kwargs)
        self.sc_effects_menu = MainMenu(*args, **kwargs)
        self.sc_time_menu = MainMenu(*args, **kwargs)
        self.sc_sims_menu = MainMenu(*args, **kwargs)
        self.sc_control_menu = MainMenu(*args, **kwargs)
        self.sc_teleport_menu = MainMenu(*args, **kwargs)
        self.sc_delete_menu = MainMenu(*args, **kwargs)
        self.sc_weather = []
        self.script_choice = MainMenu(*args, **kwargs)
        self.sc_bulletin = sc_Bulletin()
        self.sc_main = ScriptCoreMain()
        self.sc_spawn = sc_Spawn()
        self.object_picker = ObjectMenuNoFile(*args, **kwargs)
        self.weather_ini()

    def _run_interaction_gen(self, timeline):
        self.sc_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_menu.commands = []
        self.sc_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_menu.show(timeline, self, 0, self.sc_menu_choices, "Scripts Core Menu", "Make a selection.")

    def _menu(self, timeline):
        self.sc_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_menu.commands = []
        self.sc_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_menu.show(timeline, self, 0, self.sc_menu_choices, "Scripts Core Menu", "Make a selection.")

    def weather_menu(self, timeline):
        self.sc_weather_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_weather_menu.commands = []
        self.sc_weather_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_weather_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_weather_menu.show(timeline, self, 0, self.sc_weather_choices, "Weather Menu", "Make a selection.")

    def fixes_menu(self, timeline):
        self.sc_fixes_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_fixes_menu.commands = []
        self.sc_fixes_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_fixes_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_fixes_menu.show(timeline, self, 0, self.sc_fixes_choices, "Fixes Menu", "Make a selection.")

    def effects_menu(self, timeline):
        self.sc_effects_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_effects_menu.commands = []
        self.sc_effects_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_effects_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_effects_menu.show(timeline, self, 0, self.sc_effects_choices, "Effects Menu", "Make a selection.")

    def time_menu(self, timeline):
        self.sc_time_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_time_menu.commands = []
        self.sc_time_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_time_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_time_menu.show(timeline, self, 0, self.sc_time_choices, "Time Menu", "Make a selection.")

    def sims_menu(self, timeline):
        self.sc_sims_menu.MAX_MENU_ITEMS_TO_LIST = 12
        self.sc_sims_menu.commands = []
        self.sc_sims_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_sims_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_sims_menu.show(timeline, self, 0, self.sc_sims_choices, "Sims Menu", "Make a selection.")

    def control_menu(self, timeline):
        self.sc_control_menu.MAX_MENU_ITEMS_TO_LIST = 12
        self.sc_control_menu.commands = []
        self.sc_control_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_control_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_control_menu.show(timeline, self, 0, self.sc_control_choices, "Control Menu", "Make a selection.")

    def teleport_menu(self, timeline):
        self.sc_teleport_menu.MAX_MENU_ITEMS_TO_LIST = 12
        self.sc_teleport_menu.commands = []
        self.sc_teleport_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_teleport_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_teleport_menu.show(timeline, self, 0, self.sc_teleport_choices, "Teleport Menu", "Make a selection.")

    def delete_menu(self, timeline):
        self.sc_delete_menu.MAX_MENU_ITEMS_TO_LIST = 12
        self.sc_delete_menu.commands = []
        self.sc_delete_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_delete_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_delete_menu.show(timeline, self, 0, self.sc_delete_choices, "Delete Sim Menu", "Make a selection.")

    def teleport_all(self, timeline):
        self.teleport_sims()

    def teleport_metal(self, timeline):
        self.teleport_sims("metal")

    def teleport_routine(self, timeline):
        self.teleport_sims("routine")

    def teleport_traveler(self, timeline):
        self.teleport_sims("traveler")

    def teleport_vendor(self, timeline):
        self.teleport_sims("vendor")

    def delete_object(self, timeline):
        target = services.object_manager().get(self.target.id)
        if target is None:
            return
        target.destroy()

    def delete_all(self, timeline):
        self.permanently_delete_sims()

    def delete_instanced(self, timeline):
        self.permanently_delete_sims("instanced")

    def delete_metal(self, timeline):
        self.permanently_delete_sims("metal")

    def delete_routine(self, timeline):
        self.permanently_delete_sims("routine")

    def place_fireworks(self, timeline):
        self.get_firework_names()
        self.place_firework_object()
        if not ScriptCoreMenu.firework_alarm:
            self.add_firework_alarm()

    def stop_fireworks(self, timeline):
        if ScriptCoreMenu.firework_alarm:
            self.remove_firework_alarm()
        self.delete_firework_objects()
        ScriptCoreMenu.firework_index = 0
        ScriptCoreMenu.firework_timeout = 0
        ScriptCoreMenu.firework_obj = []
        ScriptCoreMenu.firework_translation = None
        ScriptCoreMenu.firework_height = 0

    def start_fireworks(self, timeline):
        self.get_firework_names()
        self.update_fireworks(len(ScriptCoreMenu.firework_obj) - 1)
        if not ScriptCoreMenu.firework_alarm:
            self.add_firework_alarm()

    def add_firework_alarm(self):
        ScriptCoreMenu.firework_alarm = alarms.add_alarm(self, (date_and_time.TimeSpan(1000)), (self.firework_alarm_callback), repeating=True, cross_zone=False)

    def place_firework_object(self):
        ScriptCoreMenu.firework_obj.append(objects.system.create_object(126977))

        if len(ScriptCoreMenu.firework_obj):
            self.update_fireworks(len(ScriptCoreMenu.firework_obj)-1, self.target)

    def delete_firework_objects(self):
        if len(ScriptCoreMenu.firework_obj):
            for obj in ScriptCoreMenu.firework_obj:
                obj.destroy()

    def update_fireworks(self, index, target=None):
        if not len(ScriptCoreMenu.firework_obj):
            for obj in services.object_manager().get_all():
                if obj.definition.id == 126977:
                    ScriptCoreMenu.firework_obj.append(obj)

        if len(ScriptCoreMenu.firework_obj):
            if not target:
                target = ScriptCoreMenu.firework_obj[index]
            level = target.location.level
            translation = target.location.transform.translation
            translation = sims4.math.Vector3(translation.x,
                                            translation.y + ScriptCoreMenu.firework_height,
                                            translation.z)
            orientation = target.location.transform.orientation
            zone_id = services.current_zone_id()
            routing_surface = SurfaceIdentifier(zone_id, level, SurfaceType.SURFACETYPE_WORLD)
            ScriptCoreMenu.firework_obj[index].location = sims4.math.Location(sims4.math.Transform(translation, orientation), routing_surface)
            ScriptCoreMenu.firework_obj[index].scale = 1.0


    def firework_alarm_callback(self, _):
        try:
            if not len(ScriptCoreMenu.firework_obj):
                return
            ScriptCoreMenu.firework_timeout = int(random.uniform(0,5))
            if ScriptCoreMenu.firework_timeout > 1:
                return

            if ScriptCoreMenu.vfx is not None:
                ScriptCoreMenu.vfx.stop(True)
            joint_hash: int = objects.sims4.hash_util.hash32('b__ROOT__')
            index = int(random.uniform(0, len(ScriptCoreMenu.firework_obj)))
            ScriptCoreMenu.vfx = PlayEffect(ScriptCoreMenu.firework_obj[index], effect_name=ScriptCoreMenu.all_fireworks[ScriptCoreMenu.firework_index], joint_name=joint_hash)
            ScriptCoreMenu.vfx.start()
            ScriptCoreMenu.firework_index = int(random.uniform(0, len(ScriptCoreMenu.all_fireworks)))

            self.update_fireworks(index)
        except BaseException as e:
            self.remove_firework_alarm()
            error_trap(e)

    def remove_firework_alarm(self):
        if ScriptCoreMenu.firework_alarm is None:
            return
        alarms.cancel_alarm(ScriptCoreMenu.firework_alarm)
        ScriptCoreMenu.firework_alarm = None

    def get_firework_names(self):
        try:
            if not len(ScriptCoreMenu.all_fireworks):
                datapath = os.path.abspath(os.path.dirname(__file__)) + r"\Data"
                filename = datapath + r"\fireworks.txt"
                file = open(filename, "r")
                for line in file.readlines():
                    ScriptCoreMenu.all_fireworks.append(str.rstrip(line))
                file.close()
        except BaseException as e:
            error_trap(e)

    def permanently_delete_sims(self, filter="all"):
        try:
            def get_simpicker_results_callback(dialog):
                if not dialog.accepted:
                    return
                try:
                    for sim_info in dialog.get_result_tags():
                        sim = init_sim(sim_info)
                        if sim:
                            for interaction in sim.get_all_running_and_queued_interactions():
                                if interaction is not None:
                                    interaction.cancel(FinishingType.RESET, 'Stop')
                            make_sim_unselectable(sim.sim_info)
                            sim.destroy()
                        services.sim_info_manager().remove_permanently(sim_info)

                except BaseException as e:
                    error_trap(e)

            if "metal" in filter:
                all_sims = [sim_info for sim_info in services.sim_info_manager().get_all() if
                            sim_info.species == Species.HUMAN and [trait for trait in sim_info.trait_tracker
                            if "Trait_SimPreference_Likes_Music_Metal" in str(trait)]]
            elif "routine" in filter:
                all_sims = [sim_info for sim_info in services.sim_info_manager().get_all() if sim_info.routine]
            elif "instanced" in filter:
                all_sims = [sim_info for sim_info in services.sim_info_manager().get_all() if sim_info.is_instanced()]
            else:
                all_sims = [sim_info for sim_info in services.sim_info_manager().get_all() if sim_info.species == Species.HUMAN]

            self.picker("Permanently Delete {} Sims".format(filter.title()), "Pick up to 50 Sims", 50, get_simpicker_results_callback, all_sims)

        except BaseException as e:
            error_trap(e)

    def goto_sim(self, timeline):
        client = services.client_manager().get_first_client()
        def get_simpicker_results_callback(dialog):
            if not dialog.accepted:
                return
            for sim in dialog.get_result_tags():
                go_here_routine(client.active_sim, sim.position, sim.level)

        self.picker("Goto Sim", "Pick up to 1 Sim", 1, get_simpicker_results_callback)

    def push_sim(self, timeline):
        inputbox("Enter Interaction ID, Add + to beginning of the ID to push it autonomously.",
                         "\n\nEXAMPLES:\n" \
                         "104626 - Staff Front Desk (Shift left click on computer ON front desk)\n" \
                         "107093 - Page sim (Shift left click on front desk, or any desk)\n" \
                         "13094 - Sleep in Bed (Shift left click on any bed)\n" \
                         "240089 - Listen to METAL (Shift left click on any stereo)\n" \
                         "254902 - Sit (Shift left click any chair or sofa)\n" \
                         "13187 - Browse Web (Shift left click any computer - Must use sitting above first)\n" \
                         "192816 - Use Tablet (Shift left click on active sim)\n" \
                         "39825 - Hug (Shift left click target sim)\n" \
                         "228605 - High Five (Shift left click target sim)\n" \
                         "39848 - Kiss (Shift left click target sim)\n" \
                         "201152 - Witty Takedown (Shift left click target sim)\n" \
                         "201727 - Take Picture (Shift left click object)\n" \
                         "192817 - Take Notes (Shift left click active sim)\n" \
                         "189332 - Charades/Practice Scene (Shift left click target sim)\n" \
                         "",
                         self.push_sim_callback, ScriptCoreMenu.last_initial_value)

    def push_sim_callback(self, dc_interaction: str):
        target_sim = None
        if dc_interaction == "":
            return
        else:
            autonomous = False
            ScriptCoreMenu.last_initial_value = dc_interaction
            if "+" in dc_interaction:
                autonomous = True
                dc_interaction = dc_interaction.replace("+","")
            else:
                autonomous = False

            def get_push_sim_callback(dialog):
                if not dialog.accepted:
                    return

                def get_page_sims_callback(dialog):
                    if not dialog.accepted:
                        return
                    for sim in dialog.get_result_tags():
                        debugger("Sim: {} - Go to sim: {}".format(sim.first_name, target_sim.first_name))
                        go_here_routine(sim, target_sim.position, target_sim.level)

                for sim in dialog.get_result_tags():
                    if sim is not None:
                        if "107093" in dc_interaction:
                            clear_sim_instance(sim.sim_info, "computer|sit|frontdesk", True)
                            target_sim = sim
                            self.picker("Page Sims", "Pick up to 50 Sims", 50, get_page_sims_callback)
                        elif "107083" in dc_interaction:
                            clear_sim_instance(sim.sim_info, "computer|sit|frontdesk", True)
                        else:
                            clear_sim_instance(sim.sim_info)

                        result = push_sim_function(sim, self.target, int(dc_interaction), autonomous)
                        debugger("Sim: {} - Push Sim Result: {}".format(sim.first_name, clean_string(str(result))))


            self.picker("Push Sim", "Pick up to 50 Sims", 50, get_push_sim_callback)

    def add_role_to_sim(self, timeline):
        if self.target.is_sim:
            inputbox("Add Role To Sim", "Enter the role id", self._add_role_to_sim_callback)

    def _add_role_to_sim_callback(self, role: str):
        if self.target.is_sim:
            role_tracker = self.target.autonomy_component._role_tracker
            role_tracker.reset()
            if "0" not in role and "none" not in role.lower() and role != "":
                assign_role(int(role), self.target.sim_info)
            assign_role_title(self.target)

    def add_title_to_sim(self, timeline):
        if self.target.is_sim:
            inputbox("Add Title To Sim", "Enter the title", self._add_title_to_sim_callback)

    def _add_title_to_sim_callback(self, title: str):
        if self.target.is_sim:
            assign_title(self.target.sim_info, title)

    def max_motives(self, timeline):
        all_motives = ['motive_fun', 'motive_social', 'motive_hygiene', 'motive_hunger', 'motive_energy', 'motive_bladder']
        for sim in services.sim_info_manager().instanced_sims_gen():
            for motive in all_motives:
                cur_stat = get_tunable_instance((sims4.resources.Types.STATISTIC), motive, exact_match=True)
                tracker = sim.get_tracker(cur_stat)
                tracker.set_value(cur_stat, 100)

    def select_and_fix_sim_icons(self, timeline):
        def get_simpicker_results_callback(dialog):
            if not dialog.accepted:
                return
            try:
                for sim in dialog.get_result_tags():
                    make_sim_at_work(sim.sim_info)
                    activate_sim_icon(sim.sim_info)
            except BaseException as e:
                error_trap(e)

        sims = [sim for sim in services.sim_info_manager().instanced_sims_gen() if sim.sim_info.species == Species.HUMAN]
        self.picker("Fix Sim Icons", "Pick up to 50 Sims", 50, get_simpicker_results_callback, sims)

    def grab_drink(self, timeline):
        self.sc_grab_drink_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_grab_drink_menu.commands = []
        self.sc_grab_drink_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_grab_drink_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_grab_drink_menu.show(timeline, self, 0, self.sc_grab_drink_choices, "Grab A Drink",
                                  "Make a selection.")

    def grab_vodka_soda(self, timeline):
        ScriptCoreRoutine.routine_function = "grab_drink_from_cooler"
        ScriptCoreRoutine.routine_option = 8685

    def grab_long_island_iced_tea(self, timeline):
        ScriptCoreRoutine.routine_function = "grab_drink_from_cooler"
        ScriptCoreRoutine.routine_option = 38850

    def grab_beer(self, timeline):
        ScriptCoreRoutine.routine_function = "grab_drink_from_cooler"
        ScriptCoreRoutine.routine_option = 2570001161

    def light_fire(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        object_list = [obj for obj in services.object_manager().get_all()
            if distance_to_by_room(sim, obj) < 25 and not obj.is_sim and "campfire" in str(obj).lower()
            or distance_to_by_room(sim, obj) < 25 and not obj.is_sim and "bonfire" in str(obj).lower()]
        object_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
        if len(object_list):
            campfire = object_list[0]
            if "campfire" in str(campfire).lower():
                push_sim_function(sim, campfire, 101940, False)
            else:
                push_sim_function(sim, campfire, 121477, False)

    def extinguish_fire(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        object_list = [obj for obj in services.object_manager().get_all()
            if distance_to_by_room(sim, obj) < 25 and not obj.is_sim and "fire" in str(obj).lower()]
        object_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
        if len(object_list):
            campfire = object_list[0]
            if "campfire" in str(campfire).lower():
                push_sim_function(sim, campfire, 102353, False)
            elif "fireplace" in str(campfire).lower():
                push_sim_function(sim, campfire, 74759, False)
            else:
                push_sim_function(sim, campfire, 121490, False)

    def hangout_fire(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        object_list = [obj for obj in services.object_manager().get_all()
            if distance_to_by_room(sim, obj) < 25 and not obj.is_sim and "campfire" in str(obj).lower()
            or distance_to_by_room(sim, obj) < 25 and not obj.is_sim and "bonfire" in str(obj).lower()]
        object_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
        if len(object_list):
            campfire = object_list[0]
            if "campfire" in str(campfire).lower():
                push_sim_function(sim, campfire, 121601, False)
            else:
                push_sim_function(sim, campfire, 121601, False)

    def fire_dance(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        object_list = [obj for obj in services.object_manager().get_all()
            if distance_to_by_room(sim, obj) < 25 and not obj.is_sim and "campfire" in str(obj).lower()
            or distance_to_by_room(sim, obj) < 25 and not obj.is_sim and "bonfire" in str(obj).lower()]
        object_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
        if len(object_list):
            campfire = object_list[0]
            if "campfire" in str(campfire).lower():
                push_sim_function(sim, campfire, 121613, False)
            else:
                push_sim_function(sim, campfire, 121613, False)

    def dance_around_fire(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        object_list = [obj for obj in services.object_manager().get_all()
            if distance_to_by_room(sim, obj) < 25 and not obj.is_sim and "campfire" in str(obj).lower()
            or distance_to_by_room(sim, obj) < 25 and not obj.is_sim and "bonfire" in str(obj).lower()]
        object_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
        if len(object_list):
            campfire = object_list[0]
            if "campfire" in str(campfire).lower():
                push_sim_function(sim, campfire, 121610, False)
            else:
                push_sim_function(sim, campfire, 121610, False)

    def add_fuel(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        object_list = [obj for obj in services.object_manager().get_all()
            if distance_to_by_room(sim, obj) < 25 and not obj.is_sim and "campfire" in str(obj).lower()
            or distance_to_by_room(sim, obj) < 25 and not obj.is_sim and "bonfire" in str(obj).lower()]
        object_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
        if len(object_list):
            campfire = object_list[0]
            if "campfire" in str(campfire).lower():
                push_sim_function(sim, campfire, 102352, False)
            else:
                push_sim_function(sim, campfire, 121485, False)

    def use_hottub(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        object_list = [obj for obj in services.object_manager().get_all()
            if distance_to_by_room(sim, obj) < 25 and not obj.is_sim and "hottub" in str(obj).lower()]
        object_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
        if len(object_list):
            hottub = object_list[0]
            push_sim_function(sim, hottub, 117259, False)

    def use_skating_rink(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        object_list = [obj for obj in services.object_manager().get_all()
            if distance_to_by_room(sim, obj) < 25 and not obj.is_sim and "skating" in str(obj).lower()]
        object_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
        if len(object_list):
            skating = object_list[0]
            push_sim_function(sim, skating, 210949, False)

    def auto_lights(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        room = build_buy.get_room_id(sim.zone_id, sim.position, sim.level)
        object_list = [obj for obj in services.object_manager().get_all_objects_with_component_gen(LIGHTING_COMPONENT)
                if distance_to_by_room(sim, obj) < 25]
        object_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
        if len(object_list):
            light = object_list[0]
            push_sim_function(sim, light, 141375, False)

    def auto_lights_all(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        room = build_buy.get_room_id(sim.zone_id, sim.position, sim.level)
        object_list = [obj for obj in services.object_manager().get_all_objects_with_component_gen(LIGHTING_COMPONENT)
                if distance_to_by_room(sim, obj) < 25]
        object_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
        if len(object_list):
            light = object_list[0]
            push_sim_function(sim, light, 13529, False)

    def lights_on(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        object_list = [obj for obj in services.object_manager().get_all_objects_with_component_gen(LIGHTING_COMPONENT)
                if distance_to_by_room(sim, obj) < 25]
        object_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
        if len(object_list):
            light = object_list[0]
            push_sim_function(sim, light, 141377, False)

    def lights_off(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        object_list = [obj for obj in services.object_manager().get_all_objects_with_component_gen(LIGHTING_COMPONENT)
                if distance_to_by_room(sim, obj) < 25]
        object_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
        if len(object_list):
            light = object_list[0]
            push_sim_function(sim, light, 141376, False)

    def all_lights_on(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        object_list = [obj for obj in services.object_manager().get_all_objects_with_component_gen(LIGHTING_COMPONENT)
                if distance_to_by_room(sim, obj) < 25]
        object_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
        if len(object_list):
            light = object_list[0]
            push_sim_function(sim, light, 13532, False)

    def all_lights_off(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        object_list = [obj for obj in services.object_manager().get_all_objects_with_component_gen(LIGHTING_COMPONENT)
                if distance_to_by_room(sim, obj) < 25]
        object_list.sort(key=lambda obj: distance_to_by_room(sim, obj))
        if len(object_list):
            light = object_list[0]
            push_sim_function(sim, light, 13531, False)

    def lightning_strike(self, timeline):
        try:
            translation = self.target.location.transform.translation
            if sims4.math.vector3_almost_equal(Vector3(translation.x, translation.y, translation.z), Vector3.ZERO()):
                LightningStrike.strike_terrain()
            elif self.target.is_sim:
                LightningStrike.strike_sim(self.target)
            elif hasattr(self.target, "definition"):
                LightningStrike.strike_object(self.target)
            else:
                position = Vector3(translation.x, translation.y, translation.z)
                LightningStrike.strike_terrain(position)
        except BaseException as e:
            error_trap(e)

    def rename_world(self, timeline):
        try:
            zone_manager = services.get_zone_manager()
            persistence_service = services.get_persistence_service()
            current_zone = zone_manager.current_zone
            neighborhood = persistence_service.get_neighborhood_proto_buff(current_zone.neighborhood_id)

            def on_response(dialog):
                if not dialog.accepted:
                    return
                neighborhood.name = dialog.text_input_responses.get(TEXT_INPUT_NAME)

            dialog = input_text.DIALOG(owner=None)
            dialog.show_dialog(on_response=on_response)
        except BaseException as e:
            error_trap(e)

    def reload_sims(self, timeline):
        ScriptCoreMain.check_sims_ini(self)
        ScriptCoreMain.sims_ini(self)

    def remove_career(self, timeline):
        if self.target.is_sim:
            remove_all_careers(self.target.sim_info)

    def teleport_sims(self, filter="all"):
        try:
            is_precise = False
            precision = 2.0
            def teleport_callback(dialog):
                if not dialog.accepted:
                    return
                for sim_info in dialog.get_result_tags():
                    translation = self.target.transform.translation
                    orientation = self.target.transform.orientation
                    level = self.target.level
                    if is_precise is True:
                        pos = Vector3(translation.x, translation.y, translation.z)
                    else:
                        pos = Vector3(translation.x + random.uniform(-precision, precision), translation.y,
                                      translation.z + random.uniform(-precision, precision))
                    zone_id = services.current_zone_id()
                    routing_surface = SurfaceIdentifier(zone_id, level, SurfaceType.SURFACETYPE_WORLD)
                    sim_location = Location(Transform(pos, orientation), routing_surface)
                    if sim_info.is_instanced():
                        sim = sim_info.get_sim_instance()
                        sim.reset(ResetReason.NONE, None, 'Command')
                        sim.location = sim_location
                    else:
                        sim_info.set_zone_on_spawn()
                        self.sc_spawn.spawn_sim(sim_info, sim_location, level)
                    make_sim_at_work(sim_info)
                    activate_sim_icon(sim_info)

            if "metal" in filter:
                all_sims = [sim_info for sim_info in services.sim_info_manager().get_all() if
                            sim_info.species == Species.HUMAN and [trait for trait in sim_info.trait_tracker
                            if "Trait_SimPreference_Likes_Music_Metal" in str(trait)]]
            elif "traveler" in filter:
                all_sims = [sim_info for sim_info in services.sim_info_manager().get_all() if
                            sim_info.species == Species.HUMAN and [trait for trait in sim_info.trait_tracker
                            if "trait_Lifestyles_FrequentTraveler" in str(trait)]]
            elif "vendor" in filter:
                all_sims = [sim_info for sim_info in services.sim_info_manager().get_all() if
                            sim_info.species == Species.HUMAN and [career for career in sim_info.career_tracker
                            if "career_Adult_NPC_StallVendor" in str(career)]]
            elif "routine" in filter:
                all_sims = [sim_info for sim_info in services.sim_info_manager().get_all() if sim_info.routine]
            else:
                all_sims = [sim_info for sim_info in services.sim_info_manager().get_all() if sim_info.species == Species.HUMAN]

            self.picker("Mass Teleport {} Sims".format(filter.title()), "Pick 50 Sim(s) to Teleport", 50, teleport_callback, all_sims)
        except BaseException as e:
            error_trap(e)

    def send_sims_home(self, timeline):
        def get_simpicker_results_callback(dialog):
            if not dialog.accepted:
                return
            try:
                for sim in dialog.get_result_tags():
                    sim_info = sim.sim_info
                    make_sim_unselectable(sim_info)
                    send_sim_home(sim)
            except BaseException as e:
                error_trap(e)

        self.picker("Send Sims Home", "Pick up to 50 Sims", 50, get_simpicker_results_callback)

    def tag_sim_for_debugging(self, timeline):
        sc_Vars.tag_sim_for_debugging = None
        def get_simpicker_results_callback(dialog):
            if not dialog.accepted:
                return
            try:
                for sim_info in dialog.get_result_tags():
                    name = "{} {}".format(sim_info.first_name, sim_info.last_name)
                    sc_Vars.tag_sim_for_debugging = name
            except BaseException as e:
                error_trap(e)

        sims = [sim_info for sim_info in services.sim_info_manager().get_all() if sim_info.species == Species.HUMAN
            and sim_info.age > Age.TEEN]
        self.picker("Tag Sim For Debugging", "Pick up to 1 Sim", 1, get_simpicker_results_callback, sims)

    def add_career_to_sims(self, timeline):
        inputbox("Add Career Or Trait To Sims", "Enter full or partial name.", self.add_career_to_sims_callback)

    def add_career_to_sims_callback(self, career: str):
        def get_simpicker_results_callback(dialog):
            if not dialog.accepted:
                return
            try:
                for sim_info in dialog.get_result_tags():
                    if "career" in name.lower():
                        add_career_to_sim(name, sim_info)
                    else:
                        add_trait_by_name(name, sim_info)
            except BaseException as e:
                error_trap(e)

        name = get_career_name_from_string(career, "teen")
        if not name:
            name = get_trait_name_from_string(career, "dislike")
            if not name:
                message_box(None, None, "Career Or Trait Not Found!", "Cannot find full or partial name: {}.".format(career), "GREEN")
                return

        sim_list = [sim_info for sim_info in services.sim_info_manager().get_all()
                if not [career for career in sim_info.career_tracker if name in str(career)]
                and not [trait for trait in sim_info.trait_tracker if name in str(trait)]
                and sim_info.species == Species.HUMAN and sim_info.age > Age.TEEN]

        self.picker("Add {} To Sims".format(name), "Pick up to 50 Sims", 50, get_simpicker_results_callback, sim_list)

    def add_sims_to_group(self, timeline):
        try:
            client = services.client_manager().get_first_client()

            def get_simpicker_results_callback(dialog):
                try:
                    if not dialog.accepted:
                        return
                    result_tags = dialog.get_result_tags()
                    ensemble_service = services.ensemble_service()
                    instance_manager = services.get_instance_manager(Types.ENSEMBLE)
                    object_manager = services.object_manager()
                    ensemble = ensemble_service.get_visible_ensemble_for_sim(client.active_sim)
                    if ensemble is None:
                        sims = []
                        sims.append(client.active_sim)
                        for sim in result_tags:
                            sims.append(sim)
                        ensemble_service.create_ensemble(EnsembleService.DEFAULT_ENSEMBLE_TYPE, sims)
                        ensemble = ensemble_service.get_visible_ensemble_for_sim(client.active_sim)
                        if ensemble is None:
                            return
                    ensemble_type = instance_manager.get(ensemble.guid64)
                    if ensemble_type is None:
                        return
                    for sim in result_tags:
                        ensemble.add_sim_to_ensemble(sim)
                except BaseException as e:
                    error_trap(e)

            self.picker("Add Sims To Group", "Pick up to 50 Sims", 50, get_simpicker_results_callback)
        except BaseException as e:
            error_trap(e)

    def remove_sims_from_group(self, timeline):
        try:
            ensemble_service = services.ensemble_service()
            for sim in services.sim_info_manager().instanced_sims_gen():
                ensemble = ensemble_service.get_visible_ensemble_for_sim(sim)
                if ensemble is not None:
                    ensemble.end_ensemble()
        except BaseException as e:
            error_trap(e)

    def remove_sims(self, timeline):
        try:
            def get_simpicker_results_callback(dialog):
                if not dialog.accepted:
                    return
                try:
                    for sim in dialog.get_result_tags():
                        remove_sim(sim)

                except BaseException as e:
                    error_trap(e)

            if not self.target.is_sim:
                self.picker("Remove Sims", "Pick up to 50 Sims", 50, get_simpicker_results_callback)

            elif self.target.is_sim:
                client = services.client_manager().get_first_client()
                make_sim_unselectable(self.target.sim_info)
                sim_info_home_zone_id = self.target.sim_info.household.home_zone_id
                self.target.sim_info.inject_into_inactive_zone(sim_info_home_zone_id, skip_instanced_check=True)
                self.target.sim_info.save_sim()
                self.target.schedule_destroy_asap(post_delete_func=(client.send_selectable_sims_update),
                                             source=self,
                                             cause='Destroying sim in travel liability')

        except BaseException as e:
            error_trap(e)

    def select_sims(self, timeline):
        try:
            def get_simpicker_results_callback(dialog):
                if not dialog.accepted:
                    return
                for sim in dialog.get_result_tags():
                    sim_info = sim.sim_info
                    make_sim_selectable(sim_info)

            self.picker("Select Sims", "Pick up to 50 Sims", 50, get_simpicker_results_callback)
        except BaseException as e:
            error_trap(e)

    def unselect_sims(self, timeline):
        try:
            def get_simpicker_results_callback(dialog):
                if not dialog.accepted:
                    return
                for sim in dialog.get_result_tags():
                    sim_info = sim.sim_info
                    make_sim_unselectable(sim_info)

            self.picker("Unselect Sims", "Pick up to 50 Sims", 50, get_simpicker_results_callback)
        except BaseException as e:
            error_trap(e)

    def unselect_everyone(self, timeline):
        try:
            client = services.client_manager().get_first_client()
            active_sim = services.get_active_sim()
            for sim_info in client.selectable_sims:
                if sim_info != active_sim.sim_info:
                    make_sim_unselectable(sim_info)
        except BaseException as e:
            error_trap(e)
            pass

    def select_everyone(self, timeline):
        try:
            for sim in services.sim_info_manager().instanced_sims_gen():
                make_sim_selectable(sim.sim_info)
        except BaseException as e:
            error_trap(e)
            pass

    def reset_timeline(self, timeline):
        timeline = services.time_service().sim_timeline
        for handle in sorted(timeline.heap):
            if handle.element is not None:
                if isinstance(handle.element, alarms.AlarmElement):
                    continue
                timeline.hard_stop(handle)

    def advance_game_time(self, timeline):
        try:
            inputbox("Advance Time", "Advance time in [hours] [minutes] [seconds]. Reverse time (negative values) "
                                     "only stops time, don't use it.", self._advance_game_time_callback)

        except BaseException as e:
            error_trap(e)

    def _advance_game_time_callback(self, time_str: str):
        time_seg = time_str.lower().split()
        hours = int(time_seg[0])
        minutes = int(time_seg[1])
        seconds = int(time_seg[2])
        if hours > 1 or hours < 0:
            advance_game_time_and_timeline(hours, minutes, seconds)
        else:
            advance_game_time(hours, minutes, seconds)

    def load_config(self, timeline):
        self.sc_main.config_ini()

    def load_routine(self, timeline):
        sc_Vars._running = False
        sc_Vars._config_loaded = False
        sc_Vars.DISABLE_EMPLOYEES = False

    def toggle_routine(self, timeline):
        sc_Vars._running = False
        sc_Vars._config_loaded = False
        sc_Vars.DISABLE_EMPLOYEES = False
        sc_Vars.DISABLE_MOD = not sc_Vars.DISABLE_MOD

    def toggle_debug(self, timeline):
        client = services.client_manager().get_first_client()
        sc_Vars.DEBUG = not sc_Vars.DEBUG

        if sc_Vars.DEBUG:
            sims4.commands.client_cheat("fps on", client.id)
        else:
            sims4.commands.client_cheat("fps off", client.id)

    def weather_ini(self):
        self.sc_weather_choices = ()
        self.sc_weather_choices = self.sc_weather_choices + ("Reset Weather",)
        self.sc_weather = []
        datapath = os.path.abspath(os.path.dirname(__file__))
        filename = datapath + r"\Data\weather.ini"
        if not os.path.exists(filename):
            return
        config = configparser.ConfigParser()
        config.read(filename)

        for each_section in config.sections():
            duration = config.getfloat(each_section, "duration")
            wind_speed = config.getfloat(each_section, "wind_speed")
            window_frost = config.getfloat(each_section, "window_frost")
            water_frozen = config.getfloat(each_section, "water_frozen")
            thunder = config.getfloat(each_section, "thunder")
            lightning = config.getfloat(each_section, "lightning")
            temperature = config.getint(each_section, "temperature")
            snow_amount = config.getfloat(each_section, "snow_amount")
            snow_depth = config.getfloat(each_section, "snow_depth")
            rain_amount = config.getfloat(each_section, "rain_amount")
            rain_depth = config.getfloat(each_section, "rain_depth")
            light_clouds = config.getfloat(each_section, "light_clouds")
            dark_clouds = config.getfloat(each_section, "dark_clouds")
            light_clouds2 = config.getfloat(each_section, "light_clouds2")
            dark_clouds2 = config.getfloat(each_section, "dark_clouds2")
            cloudy = config.getfloat(each_section, "cloudy")
            heatwave = config.getfloat(each_section, "heatwave")
            partly_cloudy = config.getfloat(each_section, "partly_cloudy")
            clear = config.getfloat(each_section, "clear")

            self.sc_weather_choices = self.sc_weather_choices + (each_section,)
            self.sc_weather.append(sc_Weather(each_section,
                                            duration,
                                            wind_speed,
                                            window_frost,
                                            water_frozen,
                                            thunder,
                                            lightning,
                                            temperature,
                                            snow_amount,
                                            snow_depth,
                                            rain_amount,
                                            rain_depth,
                                            light_clouds,
                                            dark_clouds,
                                            light_clouds2,
                                            dark_clouds2,
                                            cloudy,
                                            heatwave,
                                            partly_cloudy,
                                            clear))

    def reset_weather(self, timeline):
        services.weather_service().reset_forecasts()

    def custom_function(self, option):
        if "weather" in option:
            weather_service = services.weather_service()
            season_service = services.season_service()
            street_service = services.street_service()
            now = services.time_service().sim_now
            selected_weather_list = [weather for weather in self.sc_weather if weather.title == option]
            if selected_weather_list:
                for weather in selected_weather_list:
                    # message_box(None, None, "{}".format(weather.title), "", "GREEN")
                    current_temp = Temperature(weather.temperature)
                    weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
                    weather_service.start_weather_event(weather_event_manager.get(186636), weather.duration)
                    weather_service._trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, 0, current_temp, 0)
                    weather_service._trans_info[int(WeatherEffectType.WIND)] = WeatherElementTuple(weather.wind_speed, 0, weather.wind_speed, 0)
                    weather_service._trans_info[int(WeatherEffectType.WATER_FROZEN)] = WeatherElementTuple(weather.water_frozen, 0, weather.water_frozen, 0)
                    weather_service._trans_info[int(WeatherEffectType.WINDOW_FROST)] = WeatherElementTuple(weather.window_frost, 0, weather.window_frost, 0)
                    weather_service._trans_info[int(WeatherEffectType.THUNDER)] = WeatherElementTuple(weather.thunder, 0, weather.thunder, 0)
                    weather_service._trans_info[int(WeatherEffectType.LIGHTNING)] = WeatherElementTuple(weather.lightning, 0, weather.lightning, 0)
                    weather_service._trans_info[int(PrecipitationType.SNOW)] = WeatherElementTuple(weather.snow_amount, 0, weather.snow_amount, 0)
                    weather_service._trans_info[int(PrecipitationType.RAIN)] = WeatherElementTuple(weather.rain_amount, 0, weather.rain_amount, 0)
                    weather_service._trans_info[int(CloudType.LIGHT_SNOWCLOUDS)] = WeatherElementTuple(weather.light_clouds, 0, weather.light_clouds, 0)
                    weather_service._trans_info[int(CloudType.DARK_SNOWCLOUDS)] = WeatherElementTuple(weather.dark_clouds, 0, weather.dark_clouds, 0)
                    weather_service._trans_info[int(CloudType.LIGHT_RAINCLOUDS)] = WeatherElementTuple(weather.light_clouds2, 0, weather.light_clouds2, 0)
                    weather_service._trans_info[int(CloudType.DARK_RAINCLOUDS)] = WeatherElementTuple(weather.dark_clouds2, 0, weather.dark_clouds2, 0)
                    weather_service._trans_info[int(CloudType.CLOUDY)] = WeatherElementTuple(weather.cloudy, 0, weather.cloudy, 0)
                    weather_service._trans_info[int(CloudType.HEATWAVE)] = WeatherElementTuple(weather.heatwave, 0, weather.heatwave, 0)
                    weather_service._trans_info[int(CloudType.PARTLY_CLOUDY)] = WeatherElementTuple(weather.partly_cloudy, 0, weather.partly_cloudy, 0)
                    weather_service._trans_info[int(CloudType.CLEAR)] = WeatherElementTuple(weather.clear, 0, weather.clear, 0)
                    weather_service._trans_info[int(GroundCoverType.SNOW_ACCUMULATION)] = WeatherElementTuple(weather.snow_depth, 0, weather.snow_depth, 0)
                    weather_service._trans_info[int(GroundCoverType.RAIN_ACCUMULATION)] = WeatherElementTuple(weather.rain_depth, 0, weather.rain_depth, 0)
                    weather_service._send_weather_event_op()
        elif "Time" in option:
            inputbox("Game Speed",
                     "Default is 1. 10 would be 10 times faster. Recommend not using anything above 1000.",
                     self._game_time_speed_callback)

    def _game_time_speed_callback(self, time_str: str):
        try:
              clock.GameClock.NORMAL_SPEED_MULTIPLIER = abs(int(float(time_str)))
        except BaseException as e:
            error_trap(e)

    def sims_on_lot(self, timeline):
        self.sc_bulletin.sims_on_lot(camera.focus_on_object)

    def routine_sims(self, timeline):
        self.sc_bulletin.show_routine_staff(camera.focus_on_object)

    def get_info(self, timeline):
        try:
            output = ""
            font_color = "000000"
            font_text = "<font color='#{}'>".format(font_color)
            end_font_text = "</font>"
            result = self.target
            for att in dir(result):
                if hasattr(result, att):
                    output = output + "\n(" + str(att) + "): " + clean_string(str(getattr(result, att)))

            if self.target.is_sim:
                info_string = get_sim_info(self.target)
                message_text = info_string
            else:
                info_string = get_object_info(self.target)
            message_text = info_string.replace("[", font_text).replace("]", end_font_text)

            urgency = UiDialogNotification.UiDialogNotificationUrgency.DEFAULT
            information_level = UiDialogNotification.UiDialogNotificationLevel.PLAYER
            visual_type = UiDialogNotification.UiDialogNotificationVisualType.INFORMATION
            localized_text = lambda **_: LocalizationHelperTuning.get_raw_text(message_text)
            localized_title = lambda **_: LocalizationHelperTuning.get_object_name(self.target)
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

            datapath = os.path.abspath(os.path.dirname(__file__))
            filename = datapath + r"\{}.log".format("object_info")
            if os.path.exists(filename):
                append_write = 'w'  # append if already exists
            else:
                append_write = 'w'  # make a new file if not
            file = open(filename, append_write)
            file.write("{}\n{}\n\nINFO:\n{}".format(self.target.__class__.__name__, info_string, output))
            file.close()

        except BaseException as e:
            error_trap(e)

    def picker(self, title: str, text: str, max: int = 50, callback=None, sims=None):
        try:
            localized_title = lambda **_: LocalizationHelperTuning.get_raw_text(title)
            localized_text = lambda **_: LocalizationHelperTuning.get_raw_text(text)
            dialog = UiSimPicker.TunableFactory().default(self.sim,
                                                          text=localized_text,
                                                          title=localized_title,
                                                          max_selectable=max,
                                                          min_selectable=1,
                                                          should_show_names=True,
                                                          hide_row_description=False)

            if not sims:
                sims = services.sim_info_manager().instanced_sims_gen()
            for sim in sims:
                dialog.add_row(SimPickerRow(sim.id, False, tag=sim))

            dialog.add_listener(callback)
            dialog.show_dialog()
        except BaseException as e:
            error_trap(e)

    def _delete_filtered_objects(self, timeline):
        inputbox("Search For Object & Delete", "Searches objects on currently loaded lot only. "
                                                      "Full or partial search term. Separate multiple search "
                                                      "terms with a comma. Will search in "
                                                      "tuning files and tags. Only 512 items per search "
                                                      "will be shown.",
                         self._delete_filtered_objects_callback)

    def _delete_filtered_objects_callback(self, search: str):
        try:
            object_list = []
            count = 0
            datapath = os.path.abspath(os.path.dirname(__file__))
            filename = datapath + r"\{}.log".format("search_dump")
            append_write = 'w'  # make a new file if not
            file = open(filename, append_write)
            for obj in services.object_manager().get_all():
                if count < 512:
                    found = False
                    target_object_tags = None
                    object_tuning = services.definition_manager().get(obj.definition.id)
                    if object_tuning is not None:
                        object_class = clean_string(str(object_tuning._cls))
                    else:
                        object_class = ""
                    try:
                        target_object_tags = set(build_buy.get_object_all_tags(obj.definition.id))
                        target_object_tags = clean_string(str(target_object_tags))
                        value = target_object_tags.split(",")
                        target_object_tags = []
                        for v in value:
                            tag = get_tag_name(int(v))
                            target_object_tags.append(tag)
                    except:
                        pass
                    search_value = search.lower().split(",")
                    if target_object_tags is not None:
                        target_object_tags = clean_string(str(target_object_tags))
                        if all((x in target_object_tags.lower() for x in search_value)):
                            found = True
                    if all((x in object_class.lower() for x in search_value)):
                        found = True
                    if found:
                        if obj is not None:
                            if not obj.is_sim:
                                count = count + 1
                                object_list.append(obj)
                                file.write("{}: {} {}\n".format(obj.definition.id, target_object_tags, object_class))

            file.close()
            if len(object_list) > 0:
                ld_notice(None, "Search Objects", "{} object(s) found!".format(len(object_list)), False, "GREEN")
                self.object_picker.show(object_list, 0, self.target, True, 10)
            else:
                ld_notice(None, "Search Objects", "No objects found!", False, "GREEN")

        except BaseException as e:
            error_trap(e)

    def _find_object(self, timeline):
        inputbox("Find Object On Lot", "Searches for object on active lot/zone. "
                                                      "Full or partial search term. Separate multiple search "
                                                      "terms with a comma. Will search in "
                                                      "tuning files and tags.",
                         self._find_object_callback)

    def _find_object_callback(self, search: str):
        try:
            object_list = []
            count = 0
            datapath = os.path.abspath(os.path.dirname(__file__))
            filename = datapath + r"\{}.log".format("search_dump")
            append_write = 'w'  # make a new file if not
            file = open(filename, append_write)
            if search.isnumeric():
                obj = objects.system.find_object(int(search))
                if obj:
                    target_object_tags = None
                    object_tuning = services.definition_manager().get(obj.definition.id)

                    if object_tuning is not None:
                        object_class = clean_string(str(object_tuning._cls))
                    else:
                        object_class = ""
                    try:
                        target_object_tags = set(build_buy.get_object_all_tags(obj.definition.id))
                        target_object_tags = clean_string(str(target_object_tags))
                        value = target_object_tags.split(",")
                        target_object_tags = []
                        for v in value:
                            tag = get_tag_name(int(v))
                            target_object_tags.append(tag)
                    except:
                        pass
                    object_list.append(obj)
                #file.write("{}: {} {}\n".format(obj.definition.id, target_object_tags, object_class))
            else:
                for obj in services.object_manager().get_all():
                    found = False
                    target_object_tags = None
                    object_tuning = services.definition_manager().get(obj.definition.id)
                    if object_tuning is not None:
                        object_class = clean_string(str(object_tuning._cls))
                    else:
                        object_class = ""
                    try:
                        target_object_tags = set(build_buy.get_object_all_tags(obj.definition.id))
                        target_object_tags = clean_string(str(target_object_tags))
                        value = target_object_tags.split(",")
                        target_object_tags = []
                        for v in value:
                            tag = get_tag_name(int(v))
                            target_object_tags.append(tag)
                    except:
                        pass
                    search_value = search.lower().split(",")
                    if target_object_tags is not None:
                        target_object_tags = clean_string(str(target_object_tags))
                        if all((x in target_object_tags.lower() for x in search_value)):
                            found = True
                    if all((x in object_class.lower() for x in search_value)):
                        found = True
                    if found:
                        if obj is not None:
                            if not obj.is_sim:
                                count = count + 1
                                object_list.append(obj)
                                file.write("{}: {} {}\n".format(obj.definition.id, target_object_tags, object_class))

            file.close()
            if len(object_list) > 0:
                ld_notice(None, "Find Object", "{} object(s) found!".format(len(object_list)), False, "GREEN")
                self.object_picker.show(object_list, 0, self.target, False, 1, True)
            else:
                ld_notice(None, "Find Object", "No objects found!", False, "GREEN")
        except BaseException as e:
            error_trap(e)

    def _search_objects(self, timeline):
        inputbox("Search For Object & Place", "Searches ALL game objects. Will take some time. "
                                                      "Full or partial search term. Separate multiple search "
                                                      "terms with a comma. Will search in "
                                                      "tuning files and tags. Only 512 items per search "
                                                      "will be shown.",
                         self._search_objects_callback)

    def _search_objects_callback(self, search: str):
        try:
            object_list = []
            count = 0
            datapath = os.path.abspath(os.path.dirname(__file__))
            filename = datapath + r"\{}.log".format("search_dump")
            append_write = 'w'  # make a new file if not
            file = open(filename, append_write)
            for key in sorted(sims4.resources.list(type=(sims4.resources.Types.OBJECTDEFINITION))):
                if count < 512:
                    found = False
                    target_object_tags = None
                    object_tuning = services.definition_manager().get(key.instance)
                    if object_tuning is not None:
                        object_class = clean_string(str(object_tuning._cls))
                    else:
                        object_class = ""
                    try:
                        target_object_tags = set(build_buy.get_object_all_tags(key.instance))
                        target_object_tags = clean_string(str(target_object_tags))
                        value = target_object_tags.split(",")
                        target_object_tags = []
                        for v in value:
                            tag = get_tag_name(int(v))
                            target_object_tags.append(tag)
                    except:
                        pass
                    search_value = search.lower().split(",")
                    if target_object_tags is not None:
                        target_object_tags = clean_string(str(target_object_tags))
                        if all((x in target_object_tags.lower() for x in search_value)):
                            found = True
                    if all((x in object_class.lower() for x in search_value)):
                        found = True
                    if [x for x in search_value if x in str(key.instance)]:
                        found = True
                    if found:
                        try:
                            obj = objects.system.create_object(key.instance)
                        except:
                            obj = None
                            pass
                        if obj is not None:
                            if not obj.is_sim:
                                count = count + 1
                                object_list.append(obj)
                                file.write("{}: {} {}\n".format(key.instance, target_object_tags, object_class))

            file.close()
            if len(object_list) > 0:
                ld_notice(None, "Search Objects", "{} object(s) found!".format(len(object_list)), False, "GREEN")
                self.object_picker.show(object_list, 0, self.target, False, 1)
            else:
                ld_notice(None, "Search Objects", "No objects found!", False, "GREEN")

        except BaseException as e:
            error_trap(e)

    def _reload_scripts(self, timeline):
        inputbox("Reload Script",
                         "Type in directory to browse or leave blank to list all in current directory", self._reload_script_callback)

    def _reload_script_callback(self, script_dir: str):
        try:
            if script_dir == "" or script_dir is None:
                ScriptCoreMenu.directory = os.path.abspath(os.path.dirname(__file__))
                files = [f for f in os.listdir(ScriptCoreMenu.directory) if isfile(join(ScriptCoreMenu.directory, f))]
            else:
                ScriptCoreMenu.directory = script_dir
                files = [f for f in os.listdir(script_dir) if isfile(join(script_dir, f))]
            files.insert(0, "all")
            self.script_choice.show(None, self, 0, files, "Reload Script",
                                       "Choose a script to reload", "_reload_script_final", True)
        except BaseException as e:
            error_trap(e)

    def _reload_script_final(self, filename: str):
        try:
            if ScriptCoreMenu.directory is None:
                ScriptCoreMenu.directory = os.path.abspath(os.path.dirname(__file__))
            ld_file_loader(ScriptCoreMenu.directory, filename)
        except BaseException as e:
            error_trap(e)

