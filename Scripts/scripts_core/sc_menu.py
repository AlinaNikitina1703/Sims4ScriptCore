import os
import random
import re
from math import atan2
from os.path import isfile, join
from pathlib import Path

import alarms
import build_buy
import camera
import clock
import date_and_time
import objects
import services
import sims4
from ensemble.ensemble_service import EnsembleService
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from interactions.interaction_finisher import FinishingType
from objects.components.types import LIGHTING_COMPONENT
from objects.object_enums import ResetReason
from routing import SurfaceIdentifier, SurfaceType
from seasons import SeasonType
from server_commands.argument_helpers import get_tunable_instance
from sims.sim_info_types import Species, Age
from sims4.localization import LocalizationHelperTuning
from sims4.math import Location, Transform, Vector3, angle_to_yaw_quaternion
from sims4.resources import Types, get_resource_key
from terrain import get_terrain_height
from ui.ui_dialog_generic import UiDialogTextInputOkCancel
from ui.ui_dialog_notification import UiDialogNotification
from ui.ui_dialog_picker import UiSimPicker, SimPickerRow
from vfx import PlayEffect
from weather.lightning import LightningStrike

from scripts_core.sc_affordance import sc_Affordance
from scripts_core.sc_bulletin import sc_Bulletin
from scripts_core.sc_debugger import debugger
from scripts_core.sc_gohere import go_here, send_sim_home
from scripts_core.sc_goto_camera import update_camera, camera_info, sc_GotoCamera
from scripts_core.sc_input import inputbox, TEXT_INPUT_NAME
from scripts_core.sc_jobs import get_sim_info, advance_game_time_and_timeline, \
    advance_game_time, sc_Vars, make_sim_selectable, make_sim_unselectable, remove_sim, remove_all_careers, \
    add_career_to_sim, get_career_name_from_string, push_sim_function, distance_to_by_room, \
    assign_role, add_to_inventory, make_sim_at_work, clear_sim_instance, assign_role_title, \
    assign_title, activate_sim_icon, \
    get_object_info, get_trait_name_from_string, add_trait_by_name, \
    clear_jobs, get_filters, get_sim_posture_target, set_season_and_time, add_sim_buff, get_object_dump, \
    distance_to_by_level, get_private_objects, get_sims_using_object, is_allowed_privacy_role, get_locked_for_sim, \
    unlock_for_sim, debugger_get_object_dump, assign_button, remove_button
from scripts_core.sc_main import ScriptCoreMain
from scripts_core.sc_menu_class import MainMenu
from scripts_core.sc_message_box import message_box
from scripts_core.sc_object_menu import ObjectMenu
from scripts_core.sc_routine import ScriptCoreRoutine
from scripts_core.sc_routing import routing_fix
from scripts_core.sc_script_vars import sc_DisabledAutonomy, AutonomyState
from scripts_core.sc_sim_tracker import load_sim_tracking, save_sim_tracking
from scripts_core.sc_spawn import sc_Spawn
from scripts_core.sc_timeline import sc_Timeline
from scripts_core.sc_util import error_trap, ld_file_loader, clean_string, init_sim


class CloneWorldModule:
    DIALOG = UiDialogTextInputOkCancel.TunableFactory(text_inputs=(TEXT_INPUT_NAME,))

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
    debug_mode = False
    timeline = None

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.sc_menu_choices = ("<font color='#009900'>Get Info</font>",
                                "<font color='#990000'>Delete Object</font>",
                                "<font color='#000099'>Sims On Lot</font>",
                                "<font color='#000099'>Routine Sims</font>",
                                "<font color='#000000'>Fixes Menu</font>",
                                "<font color='#000000'>Effects Menu</font>",
                                "<font color='#000000'>Sims Menu</font>",
                                "<font color='#000000'>Time Menu</font>",
                                "<font color='#000000'>Control Menu</font>")

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
                                "Set Season And Time",
                                "Game Time Speed",
                                "Reset Timeline")

        self.sc_sims_choices = ("Max Motives",
                                "Remove Sims",
                                "Reset Sims",
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
                            "Add Object To Inventory",
                            "Show Objects In Inventory",
                            "Take Ownership",
                            "Select And Fix Sim Icons",
                            "Remove Jobs From Sims",
                            "Reset All Sims",
                            "Get Posture Target",
                            "Add Private Object",
                            "Clear Private Objects")

        self.sc_control_choices = ("<font color='#990000'>Toggle Directional Controls</font>",
                                "Get Camera Info",
                                "Show Camera Target",
                                "Hide Camera Target",
                                "Push Sim",
                                "Load Config",
                                "Load Routine",
                                "Toggle Routine",
                                "Rename World",
                                "Reload Sims",
                                "Add Career To Sims",
                                "Add Role To Sim",
                                "Add Buff To Sim",
                                "Add Title To Sim",
                                "Remove Career",
                                "Rename World",
                                "Enable Autonomy",
                                "Disable Autonomy",
                                "Set Autonomy")

        self.sc_debug_choices = ("Reload Weather Scripts", "Reload Tracker Scripts", "Reload Simulation Scripts",
                                    "Toggle Debug",
                                    "Tag Sim For Debugging",
                                    "Load Sim Tracking",
                                    "Sims To Camera",
                                    "Debug Error",
                                    "Add Button To Object",
                                    "Get In Use By",
                                    "Check Private Objects",
                                    "List Private Objects",
                                    "Sim Using Objects",
                                    "Sim Unroutable Objects",
                                    "Get Locked For",
                                    "Interaction Objects",
                                    "Indexed Sims",
                                    "Scheduled Sims",
                                    "Autonomy Sims",
                                    "Idle Sims",
                                    "Transmog Objects",
                                    "Reset In Use",
                                    "Find Go Here",
                                    "Reset Lot",
                                    "Object Dump",
                                    "Transform Werewolf",
                                    "Get Timeline Dump",
                                    "Use Custom Arbs",
                                    "Use Vanilla Arbs")

        self.sc_grab_drink_choices = ("Grab Vodka Soda",
                                    "Grab Beer",
                                    "Grab Long Island Iced Tea")

        self.sc_teleport_choices = ("Teleport All",
                                    "Teleport Filtered",
                                    "Teleport Instanced",
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
        self.sc_push_sim_menu = MainMenu(*args, **kwargs)
        self.sc_effects_menu = MainMenu(*args, **kwargs)
        self.sc_time_menu = MainMenu(*args, **kwargs)
        self.sc_sims_menu = MainMenu(*args, **kwargs)
        self.sc_control_menu = MainMenu(*args, **kwargs)
        self.sc_debug_menu = MainMenu(*args, **kwargs)
        self.sc_teleport_menu = MainMenu(*args, **kwargs)
        self.sc_delete_menu = MainMenu(*args, **kwargs)
        self.sc_autonomy_menu = MainMenu(*args, **kwargs)
        self.sc_autonomy_state_menu = MainMenu(*args, **kwargs)
        self.script_choice = MainMenu(*args, **kwargs)
        self.sc_bulletin = sc_Bulletin()
        self.sc_main = ScriptCoreMain()
        self.sc_spawn = sc_Spawn()
        self.object_picker = ObjectMenu(*args, **kwargs)
        self.sc_camera = sc_GotoCamera(*args, **kwargs)

    def _run_interaction_gen(self, timeline):
        self.sc_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_menu.commands = []
        self.sc_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_menu.commands.append("<font color='#990000'>[Debug]</font>")
        self.sc_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_menu.show(timeline, self, 0, self.sc_menu_choices, "Scripts Core Menu", "Make a selection.")

    def _menu(self, timeline):
        self.sc_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_menu.commands = []
        self.sc_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_menu.commands.append("<font color='#990000'>[Debug]</font>")
        self.sc_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_menu.show(timeline, self, 0, self.sc_menu_choices, "Scripts Core Menu", "Make a selection.")

    def fixes_menu(self, timeline):
        self.sc_fixes_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_fixes_menu.commands = []
        self.sc_fixes_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_fixes_menu.commands.append("<font color='#990000'>[Debug]</font>")
        self.sc_fixes_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_fixes_menu.show(timeline, self, 0, self.sc_fixes_choices, "Fixes Menu", "Make a selection.")

    def effects_menu(self, timeline):
        self.sc_effects_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_effects_menu.commands = []
        self.sc_effects_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_effects_menu.commands.append("<font color='#990000'>[Debug]</font>")
        self.sc_effects_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_effects_menu.show(timeline, self, 0, self.sc_effects_choices, "Effects Menu", "Make a selection.")

    def time_menu(self, timeline):
        self.sc_time_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_time_menu.commands = []
        self.sc_time_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_time_menu.commands.append("<font color='#990000'>[Debug]</font>")
        self.sc_time_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_time_menu.show(timeline, self, 0, self.sc_time_choices, "Time Menu", "Make a selection.")

    def sims_menu(self, timeline):
        self.sc_sims_menu.MAX_MENU_ITEMS_TO_LIST = 12
        self.sc_sims_menu.commands = []
        self.sc_sims_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_sims_menu.commands.append("<font color='#990000'>[Debug]</font>")
        self.sc_sims_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")

        menu_choices = []
        for item in self.sc_sims_choices:
            if "Delete Menu" in item and self.target.is_sim:
                item = item.replace("Delete Menu", "Delete Sim")
            menu_choices.append(item)

        self.sc_sims_menu.show(timeline, self, 0, menu_choices, "Sims Menu", "Make a selection.")

    def control_menu(self, timeline):
        self.sc_control_menu.MAX_MENU_ITEMS_TO_LIST = 12
        self.sc_control_menu.commands = []
        self.sc_control_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_control_menu.commands.append("<font color='#990000'>[Debug]</font>")
        self.sc_control_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_control_menu.show(timeline, self, 0, self.sc_control_choices, "Control Menu", "Make a selection.")

    def _debug(self, timeline):
        self.sc_debug_menu.MAX_MENU_ITEMS_TO_LIST = 12
        self.sc_debug_menu.commands = []
        self.sc_debug_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_debug_menu.commands.append("<font color='#990000'>[Debug]</font>")
        self.sc_debug_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_debug_menu.show(timeline, self, 0, self.sc_debug_choices, "Debug Menu", "Make a selection.")

    def teleport_menu(self, timeline):
        self.sc_teleport_menu.MAX_MENU_ITEMS_TO_LIST = 12
        self.sc_teleport_menu.commands = []
        self.sc_teleport_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_teleport_menu.commands.append("<font color='#990000'>[Debug]</font>")
        self.sc_teleport_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_teleport_menu.show(timeline, self, 0, self.sc_teleport_choices, "Teleport Menu", "Make a selection.")

    def delete_menu(self, timeline):
        if self.target.is_sim:
            self.permanently_delete_sims("sim")
            return
        self.sc_delete_menu.MAX_MENU_ITEMS_TO_LIST = 12
        self.sc_delete_menu.commands = []
        self.sc_delete_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_delete_menu.commands.append("<font color='#990000'>[Debug]</font>")
        self.sc_delete_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_delete_menu.show(timeline, self, 0, self.sc_delete_choices, "Delete Sim Menu", "Make a selection.")

    def sims_to_camera(self, timeline):
        for sim in services.sim_info_manager().instanced_sims_gen():
            clear_sim_instance(sim.sim_info)
            go_here(sim, camera._target_position, sim.level, 2.0)

    def get_timeline_dump(self, timeline):
        timeline_dump = sc_Timeline()
        timeline_dump.inverse = False
        timeline_dump.filter = []
        timeline_dump.get_values()
        timeline_dump.dump_values()

    def use_custom_arbs(self, timeline):
        from animation.arb_accumulator import ArbSequenceElement
        from module_simulation.sc_simulation import arbs_run_gen
        ArbSequenceElement._run_gen = arbs_run_gen

    def use_vanilla_arbs(self, timeline):
        from animation.arb_accumulator import ArbSequenceElement
        from module_simulation import sc_simulate
        ArbSequenceElement._run_gen = sc_simulate.vanilla_run_gen

    def transform_werewolf(self, timeline):
        client = services.client_manager().get_first_client()
        target = client.active_sim
        if self.target.is_sim:
            target = self.target
        buff_manager = services.get_instance_manager(Types.BUFF)
        if target.sim_info.has_buff(buff_manager.get(get_resource_key(300835, Types.BUFF))):
            push_sim_function(target, target, 288763, False)
        else:
            push_sim_function(target, target, 291509, False)

    def toggle_directional_controls(self, timeline):
        sc_Vars.directional_controls = not sc_Vars.directional_controls
        directional_info = "Directional controls for sim are set to {}".format(sc_Vars.directional_controls)
        message_box(self.sim, None, "Directional Controls", directional_info)
        if sc_Vars.directional_controls:
            update_camera(self.sim, 2.0, True)

    def get_camera_info(self, timeline):
        camera_info(self.sim)

    def show_camera_target(self, timeline):
        self.sc_camera.show_camera_target()

    def hide_camera_target(self, timeline):
        self.sc_camera.hide_camera_target()

    def go_here(self, timeline):
        go_here(self.sim, self.target.position)

    def go_to_camera(self, timeline):
        camera_target = Vector3(camera._target_position.x,
                                get_terrain_height(camera._target_position.x, camera._target_position.z),
                                camera._target_position.z)

        go_here(self.sim, camera_target)

    def enable_autonomy(self, timeline):
        client = services.client_manager().get_first_client()
        target = client.active_sim
        if self.target.is_sim:
            target = self.target

        if not len(sc_Vars.disabled_autonomy_list):
            message_box(target, None, "No Autonomy For Sim")
            return

        help_text = "{} {} autonomy is currently {}\n\n" \
                    "Enable actions in this list by selecting them. If the action has Enable in front of it, " \
                    "the action will be ADDED to enabled.dat, allowing sims with disabled autonomy to perform " \
                    "that action. If the action has Disable in front of it, the action will be REMOVED from disable.dat, " \
                    "allowing sims with full autonomy to perform that action.".format(target.first_name, target.last_name, target.sim_info.autonomy)

        autonomy_menu_choices = ()
        interaction_manager = services.get_instance_manager(sims4.resources.Types.INTERACTION)
        autonomy_choices = []
        [autonomy_choices.append(x) for x in sc_Vars.disabled_autonomy_list if x not in autonomy_choices and x.sim_info.id == target.id and x.sim_info.autonomy == target.sim_info.autonomy]
        if not len(autonomy_choices):
            message_box(target, None, "No Autonomy For Sim")
            return
        for choice in autonomy_choices:
            interaction = interaction_manager.get(int(choice.interaction))
            if choice.sim_info.autonomy == AutonomyState.DISABLED:
                each_section = "Enable: ({}) {}".format(interaction.guid64, interaction.__name__)
            elif choice.sim_info.autonomy == AutonomyState.FULL or choice.sim_info.autonomy == AutonomyState.LIMITED_ONLY or choice.sim_info.autonomy == AutonomyState.NO_CLEANING:
                each_section = "Disable: ({}) {}".format(interaction.guid64, interaction.__name__)
            else:
                each_section = "Routine: ({}) {}".format(interaction.guid64, interaction.__name__)
            autonomy_menu_choices = autonomy_menu_choices + (each_section,)
        self.sc_autonomy_menu.MAX_MENU_ITEMS_TO_LIST = 12
        self.sc_autonomy_menu.callback = "enable_autonomy_callback"
        self.sc_autonomy_menu.commands = []
        self.sc_autonomy_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_autonomy_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_autonomy_menu.show(timeline, self, 0, autonomy_menu_choices, "Enable Autonomy For {} {}".format(target.first_name, target.last_name), help_text)

    def enable_autonomy_callback(self, option):
        try:
            outer = re.compile("\((.+)\)")
            action_id = outer.search(option)
            if action_id:
                action = re.sub(r'[()]', '', action_id.group(0))
                client = services.client_manager().get_first_client()
                interaction_manager = services.get_instance_manager(sims4.resources.Types.INTERACTION)
                interaction = interaction_manager.get(int(action))

                datapath = sc_Vars.config_data_location
                if "Disable:" in option:
                    filename = datapath + r"\Data\{}.dat".format("disabled")
                    actions = get_filters("disabled")
                    new_list = []
                    for i, action in enumerate(actions):
                        if action not in str(interaction.__name__).lower() and action not in str(interaction.guid64):
                            new_list.append(action)

                    with open(filename, "w") as file:
                        for i, m in enumerate(new_list, 1):
                            file.write(m + ['|', '\n'][i % 10 == 0])

                if "Enable:" in option:
                    filename = datapath + r"\Data\{}.dat".format("enabled")
                    actions = get_filters("enabled")
                    new_list = []
                    for i, action in enumerate(actions):
                        if action not in str(interaction.__name__).lower() or action not in str(interaction.guid64):
                            new_list.append(action)
                    new_list.append(str(interaction.__name__).lower())

                    with open(filename, "w") as file:
                        for i, m in enumerate(new_list, 1):
                            file.write(m + ['|', '\n'][i % 10 == 0])

        except BaseException as e:
            error_trap(e)

    def disable_autonomy(self, timeline):
        client = services.client_manager().get_first_client()
        target = client.active_sim
        if self.target.is_sim:
            target = self.target

        if not len(sc_Vars.non_filtered_autonomy_list):
            message_box(target, None, "No Autonomy For Sim")
            return

        help_text = "{} {} autonomy is currently {}\n\n" \
                    "Disable actions in this list by selecting them. If the action has Enable in front of it, " \
                    "the action will be REMOVED from enabled.dat, disallowing sims with disabled autonomy to perform " \
                    "that action. If the action has Disable in front of it, the action will be ADDED to disable.dat, " \
                    "disallowing sims with full autonomy to perform that action.".format(target.first_name, target.last_name, target.sim_info.autonomy)

        autonomy_menu_choices = ()
        interaction_manager = services.get_instance_manager(sims4.resources.Types.INTERACTION)
        autonomy_choices = []
        for action in target.get_all_running_and_queued_interactions():
            autonomy_choices.insert(0, sc_DisabledAutonomy(target.sim_info, action.guid64))
        [autonomy_choices.append(x) for x in sc_Vars.non_filtered_autonomy_list if x not in autonomy_choices and x.sim_info.id == target.id and x.sim_info.autonomy == target.sim_info.autonomy]
        if not len(autonomy_choices):
            message_box(target, None, "No Autonomy For Sim")
            return
        for choice in autonomy_choices:
            interaction = interaction_manager.get(int(choice.interaction))
            if choice.sim_info.autonomy == AutonomyState.FULL or choice.sim_info.autonomy == AutonomyState.LIMITED_ONLY or choice.sim_info.autonomy == AutonomyState.NO_CLEANING:
                each_section = "Disable: ({}) {}".format(interaction.guid64, interaction.__name__)
            elif choice.sim_info.autonomy == AutonomyState.DISABLED:
                each_section = "Enable: ({}) {}".format(interaction.guid64, interaction.__name__)
            else:
                each_section = "Routine: ({}) {}".format(interaction.guid64, interaction.__name__)
            autonomy_menu_choices = autonomy_menu_choices + (each_section,)
        self.sc_autonomy_menu.MAX_MENU_ITEMS_TO_LIST = 12
        self.sc_autonomy_menu.callback = "disable_autonomy_callback"
        self.sc_autonomy_menu.commands = []
        self.sc_autonomy_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_autonomy_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_autonomy_menu.show(timeline, self, 0, autonomy_menu_choices, "Disable Autonomy For {} {}".format(target.first_name, target.last_name), help_text)

    def disable_autonomy_callback(self, option):
        try:
            outer = re.compile("\((.+)\)")
            action_id = outer.search(option)
            if action_id:
                action = re.sub(r'[()]', '', action_id.group(0))
                client = services.client_manager().get_first_client()
                interaction_manager = services.get_instance_manager(sims4.resources.Types.INTERACTION)
                interaction = interaction_manager.get(int(action))
    
                datapath = sc_Vars.config_data_location
                if "Disable:" in option:
                    filename = datapath + r"\Data\{}.dat".format("disabled")
                    actions = get_filters("disabled")
                    new_list = []
                    for i, action in enumerate(actions):
                        if action not in str(interaction.__name__).lower() and action not in str(interaction.guid64):
                            new_list.append(action)
                    new_list.append(str(interaction.__name__).lower())

                    with open(filename, "w") as file:
                        for i, m in enumerate(new_list, 1):
                            file.write(m + ['|', '\n'][i % 10 == 0])

                if "Enable:" in option:
                    filename = datapath + r"\Data\{}.dat".format("enabled")
                    actions = get_filters("enabled")
                    new_list = []
                    for i, action in enumerate(actions):
                        if action in str(interaction.__name__).lower() or action in str(interaction.guid64):
                            continue
                        new_list.append(action)

                    with open(filename, "w") as file:
                        for i, m in enumerate(new_list, 1):
                            file.write(m + ['|', '\n'][i % 10 == 0])

        except BaseException as e:
            error_trap(e)

    def set_autonomy(self, timeline):
        client = services.client_manager().get_first_client()
        target = client.active_sim
        if self.target.is_sim:
            target = self.target
        autonomy_types = [info for info in AutonomyState]
        autonomy_choices = ()
        for autonomy in autonomy_types:
            autonomy_choices = autonomy_choices + (autonomy.name.lower(),)

        self.sc_autonomy_state_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_autonomy_state_menu.callback = "set_autonomy_callback"
        self.sc_autonomy_state_menu.commands = []
        self.sc_autonomy_state_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_autonomy_state_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_autonomy_state_menu.show(timeline, self, 0, autonomy_choices, "Set Sim Autonomy", "Set Autonomy for sim: {} {}".format(target.first_name, target.last_name))

    def set_autonomy_callback(self, autonomy):
        client = services.client_manager().get_first_client()
        target = client.active_sim
        if self.target.is_sim:
            target = self.target
        autonomy_states = [state for state in AutonomyState if state.name.lower() in autonomy]
        if autonomy_states:
            for state in autonomy_states:
                target.sim_info.autonomy = state
                message_box(target, None, "Autonomy State", "{} {} autonomy state is set to {}".format(target.first_name, target.last_name, target.sim_info.autonomy))

    def remove_jobs_from_sims(self, timeline):
        if self.target.is_sim:
            clear_jobs(self.target.sim_info)
            self.target.sim_info.routine = False
            assign_title(self.target.sim_info, "")

    def load_sim_tracking(self, timeline):
        for sim in services.sim_info_manager().instanced_sims_gen():
            save_sim_tracking(sim.sim_info)
            load_sim_tracking(sim.sim_info)

    def reset_all_sims(self, timeline):
        for sim in services.sim_info_manager().instanced_sims_gen():
            sim.reset(ResetReason.NONE, None, 'Command')
            clear_jobs(sim.sim_info)
            sim.sim_info.routine = False
            assign_title(sim.sim_info, "")

    def reset_lot(self, timeline):
        situation_manager = services.get_zone_situation_manager()
        for situation in situation_manager.get_all():
            job_title = situation.__class__.__name__.lower()
            if (job_title.find('holiday') == -1) and (job_title.find('club') == -1) and (job_title.find('butler') == -1):
                situation_manager.destroy_situation_by_id(situation.id)

    def find_go_here(self, timeline):
        client = services.client_manager().get_first_client()
        if self.target.is_sim:
            target = self.target
        else:
            target = client.active_sim

        gohere = [action for action in target.get_all_running_and_queued_interactions() if "gohere" in action.__class__.__name__.lower()]
        if gohere:
            for action in gohere:
                if hasattr(action.target, "position"):
                    camera.focus_on_position(action.target.position, client)

    def get_in_use_by(self, timeline):
        if not self.target.is_sim and self.target.definition.id != 816:
            self.sc_bulletin.show_sims_using_object(self.target, camera.focus_on_object)

    def sim_using_objects(self, timeline):
        client = services.client_manager().get_first_client()
        if self.target.is_sim:
            target = self.target
        else:
            target = client.active_sim
        if hasattr(target.sim_info, "tracker"):
            if target.sim_info.tracker.objects:
                self.object_picker.title = "Sim Using Object List"
                self.object_picker.show(target.sim_info.tracker.objects, 0, target, 1, True)
                return
        object_list = [interaction.target for interaction in target.get_all_running_and_queued_interactions() if interaction.target]
        if object_list:
            self.object_picker.show(object_list, 0, target, 1, True, debugger_get_object_dump)
            return
        message_box(None, None, "Sim Using Objects", "No objects found!", "GREEN")

    def transmog_objects(self, timeline):
        if sc_Vars.transmog_objects:
            self.object_picker.show(sc_Vars.transmog_objects, 0, self.target, 1, True, debugger_get_object_dump)
            return
        message_box(None, None, "Transmog Objects", "No objects found!", "GREEN")

    def sim_unroutable_objects(self, timeline):
        client = services.client_manager().get_first_client()
        if self.target.is_sim:
            target = self.target
        else:
            target = client.active_sim
        object_list = [route.object for route in sc_Vars.non_routable_obj_list if route.sim == target]
        if len(object_list):
            self.object_picker.title = "Unroutable Object List"
            self.object_picker.show(object_list, 0, target, 1, True)
            return
        message_box(None, None, "Sim Unroutable Objects", "No objects found!", "GREEN")

    def get_locked_for(self, timeline):
        object_list = [sim for sim in services.sim_info_manager().instanced_sims_gen() if get_locked_for_sim(self.target, sim)]
        if len(object_list):
            def unlock_for_sim_callback(sim):
                unlock_for_sim(self.target, sim)

            self.object_picker.title = "Sims Locked Out"
            self.object_picker.show(object_list, 0, self.target, 50, False, unlock_for_sim_callback)
            return
        message_box(None, None, "Sims Locked Out", "No sims found!", "GREEN")

    # New private objects code
    def check_private_objects(self, timeline):
        client = services.client_manager().get_first_client()
        if self.target.is_sim:
            target = self.target
        else:
            target = client.active_sim
        object_list = get_private_objects(target, sc_Vars.private_objects)
        if len(object_list):
            self.object_picker.title = "Private Object List"
            self.object_picker.show(object_list, 0, target, 1, True)
            return
        message_box(None, None, "Private Objects", "No objects found!", "GREEN")

    def list_private_objects(self, timeline):
        object_list = sc_Vars.private_objects
        object_list.sort(key=lambda obj: distance_to_by_level(obj, self.target))
        if len(object_list):
            self.object_picker.title = "Private Object List"
            self.object_picker.show(object_list, 0, self.target, 1, True)
            return
        message_box(None, None, "Private Objects", "No objects found!", "GREEN")

    def interaction_objects(self, timeline):
        client = services.client_manager().get_first_client()
        if self.target.is_sim:
            target = self.target
        else:
            target = client.active_sim

        object_label = []
        object_list = []
        for interaction in target.get_all_running_and_queued_interactions():
            object_list.append(interaction.target)
            object_label.append("Interaction: ({}) Object ID: ({})\n{}\n{}".format(interaction.guid64, interaction.target.definition.id if interaction.target else None, interaction.__class__.__name__, get_object_dump(interaction.target, "interaction_refs")))

        if len(object_list):
            self.object_picker.title = "Interaction Object List"
            self.object_picker.show(object_list, 0, target, 1, True, None, None, object_label)
            return
        message_box(None, None, "Interaction Objects", "No objects found!", "GREEN")

    def reset_in_use(self, timeline):
        if self.target.definition.id != 816:
            if len(self.target.interaction_refs):
                for interaction in tuple(self.target.interaction_refs):
                    interaction.sim.reset(ResetReason.NONE, None, 'Command')
            routing_fix(self.target)
            message_box(self.target, None, "Reset In Use", "A note on using this reset:\nWhen resetting a target object in a slot like the front desk or other objects that require a slotted object to function, use live drag to place the object back into the slot otherwise the object will not function properly and cause routing issues!")

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

            dialog = CloneWorldModule.DIALOG(owner=None)
            dialog.show_dialog(on_response=on_response)
        except BaseException as e:
            error_trap(e)

    def add_object_to_inventory(self, timeline):
        add_to_inventory(self.sim, self.target)

    def place_inventory_callback(self, obj):
        try:
            client = services.client_manager().get_first_client()
            zone_id = services.current_zone_id()
            if self.target.is_sim:
                target = self.target
            else:
                target = client.active_sim
            new_obj = objects.system.create_object(obj.definition.id)
            level = self.target.level
            translation = self.target.position
            point = target.position
            angle = atan2(point.x - translation.x, point.z - translation.z)
            orientation = angle_to_yaw_quaternion(angle)
            routing_surface = SurfaceIdentifier(zone_id, level, SurfaceType.SURFACETYPE_WORLD)
            new_obj.location = Location(Transform(translation, orientation), routing_surface)
            new_obj.update_ownership((target.sim_info), make_sim_owner=True)
        except BaseException as e:
            error_trap(e)

    def show_objects_in_inventory(self, timeline):
        client = services.client_manager().get_first_client()
        if self.target.is_sim:
            target = self.target
        else:
            target = client.active_sim

        if len(target.sim_info.inventory_data.objects):
            definition_manager = services.definition_manager()
            obj_ids = [definition_manager.get(obj.guid) for obj in target.sim_info.inventory_data.objects]
            obj_list = [objects.system.create_script_object(id) for id in obj_ids]
            self.object_picker.title = "Inventory List"
            self.object_picker.show(obj_list, 0, self.target, 1, False, self.place_inventory_callback)
        else:
            message_box(target, None, "Sim Inventory", "No inventory found!", "GREEN")

    def take_ownership(self, timeline):
        client = services.client_manager().get_first_client()
        self.target.update_ownership((client.active_sim.sim_info), make_sim_owner=True)

    def teleport_instanced(self, timeline):
        self.teleport_sims("instanced")

    def teleport_all(self, timeline):
        self.teleport_sims("all", True)

    def teleport_filtered(self, timeline):
        inputbox("Teleport Filtered", "Enter first name or last name of sim(s).", self.teleport_sims_filtered)

    def teleport_metal(self, timeline):
        self.teleport_sims("metal")

    def teleport_routine(self, timeline):
        self.teleport_sims("routine")

    def teleport_traveler(self, timeline):
        self.teleport_sims("traveler")

    def teleport_vendor(self, timeline):
        self.teleport_sims("vendor")

    def debug_error(self, timeline):
        try:
            self.sc_spawn.do_error()
        except BaseException as e:
            error_trap(e)

    def add_button_to_object(self, timeline):
        inputbox("Add Button To Object", "Enter button id to add to object.", self.add_button_to_object_callback, ScriptCoreMenu.last_initial_value)

    def add_button_to_object_callback(self, button_id: str):
        ScriptCoreMenu.last_initial_value = button_id
        if "-" in button_id:
            remove_button(abs(int(button_id)), self.target)
            return
        assign_button(abs(int(button_id)), self.target)

    def delete_object(self, timeline):
        target = services.object_manager().get(self.target.id)
        if target is None:
            return
        target.destroy()

    def delete_sim(self, timeline):
        self.permanently_delete_sims("sim")

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
                datapath = sc_Vars.config_data_location + r"\Data"
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
            elif "sim" in filter:
                all_sims = [self.target.sim_info]
            else:
                all_sims = [sim_info for sim_info in services.sim_info_manager().get_all() if sim_info.species == Species.HUMAN]

            self.picker("Permanently Delete {}".format((filter.title() + " Sims" if "sim" not in filter else self.target.first_name + " " + self.target.last_name)),
                        "There are {} sims.\nPick up to 50 Sims".format(len(all_sims)), 50, get_simpicker_results_callback, all_sims)

        except BaseException as e:
            error_trap(e)

    def goto_sim(self, timeline):
        client = services.client_manager().get_first_client()
        def get_simpicker_results_callback(dialog):
            if not dialog.accepted:
                return
            for sim in dialog.get_result_tags():
                go_here(client.active_sim, sim.position, sim.level)

        self.picker("Goto Sim", "Pick up to 1 Sim", 1, get_simpicker_results_callback)

    def _user_directed(self, timeline):
        ScriptCoreMenu.debug_mode = True
        self.push_sim(timeline)

    def _autonomous(self, timeline):
        ScriptCoreMenu.debug_mode = False
        self.push_sim(timeline)

    def _custom(self, timeline):
        self.push_sim(timeline, True)

    def _filter(self, timeline):
        ScriptCoreMenu.timeline = timeline
        inputbox("Enter filter to lookup interactions.","", self._filter_callback, ScriptCoreMenu.last_initial_value)

    def _filter_callback(self, filter: str):
        ScriptCoreMenu.last_initial_value = filter
        self.push_sim(ScriptCoreMenu.timeline, False, filter)

    def push_sim(self, timeline, custom=False, filter=None):
        if self.target._super_affordances and not custom:
            font_color = "990000"
            if not ScriptCoreMenu.debug_mode:
                font_text = ""
                end_font_text = ""
            else:
                font_text = "<font color='#{}'>".format(font_color)
                end_font_text = "</font>"
            super_affordances = sc_Affordance(self.target)
            action_titles = sorted(super_affordances.affordance_instances, key=(lambda x: x.guid64))
            action_titles = ["{}({}) {}{}".format(font_text, interaction.guid64, super_affordances.affordance_names[interaction.guid64], end_font_text)
                                for interaction in action_titles if not filter or filter and str(filter).lower() in super_affordances.affordance_names[interaction.guid64].lower()]
            if action_titles:
                self.sc_push_sim_menu.MAX_MENU_ITEMS_TO_LIST = 10
                self.sc_push_sim_menu.commands = []
                self.sc_push_sim_menu.commands.append("<font color='#990000'>[Menu]</font>")
                self.sc_push_sim_menu.commands.append("<font color='#990000'>[Custom]</font>")
                self.sc_push_sim_menu.commands.append("<font color='#990000'>[Filter]</font>")
                if not ScriptCoreMenu.debug_mode:
                    self.sc_push_sim_menu.commands.append("<font color='#990000'>[User Directed]</font>")
                else:
                    self.sc_push_sim_menu.commands.append("<font color='#990000'>[Autonomous]</font>")
                self.sc_push_sim_menu.show(timeline, self, 0, action_titles, "Push Sim",
                                          "User Directed set to {}\nMake a selection.".format(ScriptCoreMenu.debug_mode), "push_sim_callback", True)
                return

        inputbox("Enter Interaction ID, Add + to beginning of the ID to push it autonomously.",
                         "\n\nEXAMPLES:\n" \
                         "104626 - Staff Front Desk (Left click on computer ON front desk)\n" \
                         "107093 - Page sim (Left click on front desk, or any desk)\n" \
                         "13094 - Sleep in Bed (Left click on any bed)\n" \
                         "240089 - Listen to METAL (Left click on any stereo)\n" \
                         "254902 - Sit (Left click any chair or sofa)\n" \
                         "13187 - Browse Web (Left click any computer - Must use sitting above first)\n" \
                         "192816 - Use Tablet (Left click on active sim)\n" \
                         "39825 - Hug (Left click target sim)\n" \
                         "228605 - High Five (Left click target sim)\n" \
                         "39848 - Kiss (Left click target sim)\n" \
                         "201152 - Witty Takedown (Left click target sim)\n" \
                         "201727 - Take Picture (Left click object)\n" \
                         "192817 - Take Notes (Left click active sim)\n" \
                         "189332 - Charades/Practice Scene (Left click target sim)\n" \
                         "",
                         self.push_sim_callback, ScriptCoreMenu.last_initial_value)

    def push_sim_callback(self, dc_interaction: str):
        if dc_interaction == "":
            return
        result = dc_interaction.replace(" ", "_")
        clean = re.compile('<.*?>')
        result = re.sub(clean, '', result)
        result = result.replace("[", "_")
        result = result.replace("]", "")
        result = result.replace("*", "_")
        result = result.lower()
        function = re.sub(r'\W+', '', result)

        if hasattr(self, function):
            method = getattr(self, function)
            if method is not None:
                method(None)
                return

        if "(" in dc_interaction:
            dc_interaction = dc_interaction[dc_interaction.find('(')+1:dc_interaction.find(')')]
        elif not dc_interaction.isnumeric():
            return

        autonomous = False
        ScriptCoreMenu.last_initial_value = dc_interaction
        if "+" in dc_interaction:
            autonomous = True
            dc_interaction = dc_interaction.replace("+","")
        else:
            autonomous = False
        if not ScriptCoreMenu.debug_mode:
            autonomous = True

        def get_push_sim_callback(dialog):
            if not dialog.accepted:
                return

            def get_page_sims_callback(dialog):
                if not dialog.accepted:
                    return
                for sim in dialog.get_result_tags():
                    if sc_Vars.DEBUG:
                        debugger("Sim: {} - Go to sim: {}".format(sim.first_name, target_sim.first_name))
                    go_here(sim, target_sim.position, target_sim.level)

            for sim in dialog.get_result_tags():
                if sim is not None:
                    if self.target.definition.id == 816 and "14410" in dc_interaction:
                        clear_sim_instance(sim.sim_info)
                        go_here(sim, self.target.position, self.target.level, 0.5)
                    elif "107093" in dc_interaction:
                        clear_sim_instance(sim.sim_info, "computer|sit|frontdesk", True)
                        target_sim = sim
                        self.picker("Page Sims", "Pick up to 50 Sims", 50, get_page_sims_callback)
                    elif "107083" in dc_interaction:
                        clear_sim_instance(sim.sim_info, "computer|sit|frontdesk", True)
                    else:
                        clear_sim_instance(sim.sim_info)

                    result = push_sim_function(sim, self.target, int(dc_interaction), autonomous)
                    if sc_Vars.DEBUG:
                        debugger("Sim: {} - Push Sim Result: {}".format(sim.first_name, clean_string(str(result))))


        self.picker("Push Sim", "Pick up to 50 Sims", 50, get_push_sim_callback)

    def object_dump(self, timeline):
        inputbox("Object Dump", "Enter attribute or leave blank for all attributes", self.object_dump_callback, ScriptCoreMenu.last_initial_value)

    def object_dump_callback(self, attribute: str):
        ScriptCoreMenu.last_initial_value = attribute
        if "." in attribute:
            keys = attribute.split(".")
            dump = self.target
            for key in keys:
                if hasattr(dump, key):
                    dump = getattr(dump, key)
            debugger("DUMP: {}.{}\n{}".format(self.target.__class__.__name__, attribute, get_object_dump(dump)))
            return
        if len(attribute) and hasattr(self.target, attribute):
            dump = getattr(self.target, attribute)
            debugger("DUMP: {}.{}\n{}".format(self.target.__class__.__name__, attribute, get_object_dump(dump)))
            return
        debugger("DUMP: {}\n{}".format(self.target.__class__.__name__, get_object_dump(self.target)))

    def add_buff_to_sim(self, timeline):
        inputbox("Add Buff To Sim", "Enter the buff id", self._add_buff_to_sim_callback)

    def _add_buff_to_sim_callback(self, id: str):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        if id != "0" and "none" not in id.lower() and id != "":
            add_sim_buff(int(id), sim.sim_info)

    def add_role_to_sim(self, timeline):
        inputbox("Add Role To Sim", "Enter the role id", self._add_role_to_sim_callback)

    def _add_role_to_sim_callback(self, role: str):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        role_tracker = sim.autonomy_component._role_tracker
        role_tracker.reset()
        if role != "0" and "none" not in role.lower() and role != "":
            assign_role(int(role), sim.sim_info)
        assign_role_title(sim)

    def add_title_to_sim(self, timeline):
        if self.target.is_sim:
            inputbox("Add Title To Sim", "Enter the title", self._add_title_to_sim_callback)

    def _add_title_to_sim_callback(self, title: str):
        if self.target.is_sim:
            assign_title(self.target.sim_info, title)

    def max_motives(self, timeline):
        all_motives = ['motive_fun', 'motive_social', 'motive_hygiene', 'motive_hunger', 'motive_energy', 'motive_bladder']
        for sim_info in services.sim_info_manager().get_all():
            for motive in all_motives:
                cur_stat = get_tunable_instance((sims4.resources.Types.STATISTIC), motive, exact_match=True)
                tracker = sim_info.get_tracker(cur_stat)
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

    def reload_sims(self, timeline):
        ScriptCoreMain.check_sims_ini(self)
        ScriptCoreMain.sims_ini(self)

    def remove_career(self, timeline):
        if self.target.is_sim:
            remove_all_careers(self.target.sim_info)

    def teleport_sims_filtered(self, name=""):
        self.teleport_sims("all", True, name)

    def teleport_sims(self, filter="all", clear_role=False, name=""):
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
                    sims = [s for s in services.sim_info_manager().instanced_sims_gen() if s.sim_info == sim_info]
                    if sims:
                        for sim in sims:
                            sim.reset(ResetReason.NONE, None, 'Command')
                            sim.location = sim_location
                    else:
                        sim_info.set_zone_on_spawn()
                        self.sc_spawn.spawn_sim(sim_info, sim_location, level)

                    if sc_Vars.select_when_teleport:
                        make_sim_at_work(sim_info)
                        activate_sim_icon(sim_info)
                    if clear_role:
                        clear_jobs(sim_info)

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
            elif "instanced" in filter:
                all_sims = [sim_info for sim_info in services.sim_info_manager().get_all() if sim_info.is_instanced()]
            else:
                all_sims = [sim_info for sim_info in services.sim_info_manager().get_all() if str(name).lower() in str(sim_info.first_name).lower() or str(name).lower() in str(sim_info.last_name).lower()]

            if all_sims:
                self.picker("Mass Teleport {} Sims".format(filter.title()), "Pick 50 Sim(s) to Teleport", 50, teleport_callback, all_sims)
            else:
                message_box(None, None, "Teleport", "No Sims Found!", "GREEN")

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

        if self.target.is_sim:
            sims = [self.target]
        else:
            sims = [sim_info for sim_info in services.sim_info_manager().get_all() if sim_info.species == Species.HUMAN
                and sim_info.age > Age.TEEN and sim_info._sim_ref]
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
                    push_sim_function(client.active_sim, client.active_sim, 25209, False)
                except BaseException as e:
                    error_trap(e)

            self.picker("Add Sims To Group", "Pick up to 50 Sims", 50, get_simpicker_results_callback)
        except BaseException as e:
            error_trap(e)

    def remove_sims_from_group(self, timeline):
        try:
            client = services.client_manager().get_first_client()
            ensemble_service = services.ensemble_service()
            ensemble = ensemble_service.get_visible_ensemble_for_sim(client.active_sim)
            if ensemble is None:
                return

            def get_simpicker_results_callback(dialog):
                try:
                    if not dialog.accepted:
                        return
                    result_tags = dialog.get_result_tags()
                    instance_manager = services.get_instance_manager(Types.ENSEMBLE)
                    ensemble = ensemble_service.get_visible_ensemble_for_sim(client.active_sim)
                    if ensemble is None:
                        return
                    ensemble_type = instance_manager.get(ensemble.guid64)
                    if ensemble_type is None:
                        return
                    for sim_info in result_tags:
                        sim = init_sim(sim_info)
                        ensemble.remove_sim_from_ensemble(sim)
                    push_sim_function(client.active_sim, client.active_sim, 25209, False)
                except BaseException as e:
                    error_trap(e)

            sims = [sim.sim_info for sim in ensemble]
            self.picker("Remove Sims From Group", "Pick up to 50 Sims", 50, get_simpicker_results_callback, sims)
        except BaseException as e:
            error_trap(e)

    def reset_sims(self, timeline):
        client = services.client_manager().get_first_client()
        try:
            def get_simpicker_results_callback(dialog):
                if not dialog.accepted:
                    return
                try:
                    for sim in dialog.get_result_tags():
                        sim.reset(ResetReason.NONE, None, 'Command')

                except BaseException as e:
                    error_trap(e)

            if not self.target.is_sim:
                self.picker("Remove Sims", "Pick up to 50 Sims", 50, get_simpicker_results_callback)

            elif self.target.is_sim:
                self.target.reset(ResetReason.NONE, None, 'Command')

        except BaseException as e:
            error_trap(e)

    def remove_sims(self, timeline):
        client = services.client_manager().get_first_client()
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
        client = services.client_manager().get_first_client()
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
        client = services.client_manager().get_first_client()
        try:
            def get_simpicker_results_callback(dialog):
                if not dialog.accepted:
                    return
                for sim in dialog.get_result_tags():
                    sim_info = sim.sim_info
                    make_sim_unselectable(sim_info)

            pick_sims = [sim_info for sim_info in client._selectable_sims._selectable_sim_infos]
            self.picker("Unselect Sims", "Pick up to 50 Sims", 50, get_simpicker_results_callback, pick_sims)
        except BaseException as e:
            error_trap(e)

    def unselect_everyone(self, timeline):
        client = services.client_manager().get_first_client()
        try:
            active_sim = services.get_active_sim()
            for sim_info in client.selectable_sims:
                if sim_info not in services.active_household():
                    make_sim_unselectable(sim_info)
        except BaseException as e:
            error_trap(e)
            pass

    def select_everyone(self, timeline):
        client = services.client_manager().get_first_client()
        try:
            for sim in services.sim_info_manager().instanced_sims_gen():
                make_sim_selectable(sim.sim_info)
        except BaseException as e:
            error_trap(e)
            pass

    def reset_timeline(self, timeline):
        timeline = services.time_service().sim_timeline
        debugger(str(len(timeline.heap)))
        for handle in sorted(timeline.heap):
            if handle.element is not None:
                if isinstance(handle.element, alarms.AlarmElement):
                    continue
                timeline.hard_stop(handle)

    def set_season_and_time(self, timeline):
        inputbox("Set Season And Time", "[Season 0-3], [Time in minutes to advance]", self.set_season_and_time_callback)

    def set_season_and_time_callback(self, set_season: str):
        time_seg = set_season.lower().split(",") if "," in set_season else [int(set_season), None]
        season = SeasonType(int(time_seg[0]))
        minutes = int(time_seg[1]) if time_seg[1] is not None else None
        set_season_and_time(season, minutes)

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
        self.sc_main.show_mod_status(True)

    def load_routine(self, timeline):
        sc_Vars._running = False
        sc_Vars._config_loaded = False
        sc_Vars.DISABLE_ROUTINE = False
        sc_Vars.DISABLE_MOD = False

    def toggle_routine(self, timeline):
        sc_Vars.DISABLE_ROUTINE = not sc_Vars.DISABLE_ROUTINE
        sc_Vars.DISABLE_MOD = False
        self.sc_main.show_mod_status(True)

    def toggle_debug(self, timeline):
        client = services.client_manager().get_first_client()
        sc_Vars.DEBUG = not sc_Vars.DEBUG

        if sc_Vars.DEBUG:
            sims4.commands.client_cheat("fps on", client.id)
        else:
            sims4.commands.client_cheat("fps off", client.id)

    def custom_function(self, option):
        if "Time" in option:
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

    def indexed_sims(self, timeline):
        self.sc_bulletin.show_indexed_sims(camera.focus_on_object)

    def scheduled_sims(self, timeline):
        self.sc_bulletin.show_scheduled_sims(camera.focus_on_object)

    def autonomy_sims(self, timeline):
        self.sc_bulletin.show_autonomy_sims(camera.focus_on_object)

    def idle_sims(self, timeline):
        self.sc_bulletin.show_idle_sims(camera.focus_on_object)



    def get_posture_target(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim

        posture_target = get_sim_posture_target(sim)
        message_box(sim, posture_target, "Posture Target", "Posture target for sim", "GREEN")

    # New private objects code
    def add_private_object(self, timeline):
        if not self.target.is_sim and self.target.definition.id != 816:
            sc_Vars.private_objects.append(self.target)
            sims = get_sims_using_object(self.target)
            for sim in sims:
                if not sim.sim_info.is_selectable:
                    for interaction in sim.get_all_running_and_queued_interactions():
                        if interaction.target == self.target and is_allowed_privacy_role(sim) or \
                                distance_to_by_level(interaction.target, self.target) < 10 and is_allowed_privacy_role(sim):
                            interaction.cancel(FinishingType.RESET, 'Stop')

    def clear_private_objects(self, timeline):
        sc_Vars.private_objects = []

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
                message_text = info_string.replace("[", font_text).replace("]", end_font_text)
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

            datapath = sc_Vars.config_data_location
            filename = datapath + r"\{}.log".format("object_info")
            file = open(filename, 'w')
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

    def reload_weather_scripts(self, timeline):
        path = Path(os.path.abspath(os.path.dirname(__file__)))
        directory = str(path.parent.absolute()) + r"\module_weather"
        self._reload_script_callback(directory)

    def reload_tracker_scripts(self, timeline):
        path = Path(os.path.abspath(os.path.dirname(__file__)))
        directory = str(path.parent.absolute()) + r"\module_ai_tracker"
        self._reload_script_callback(directory)

    def reload_simulation_scripts(self, timeline):
        path = Path(os.path.abspath(os.path.dirname(__file__)))
        directory = str(path.parent.absolute()) + r"\module_simulation"
        self._reload_script_callback(directory)

    def _reload_scripts(self, timeline):
        inputbox("Reload Script", "Type in directory to browse or leave blank to list all in current directory", self._reload_script_callback)

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

