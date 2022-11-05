import os
import random
from os.path import isfile, join

import services
import sims4
from interactions.context import InteractionContext, QueueInsertStrategy
from interactions.priority import Priority

from module_ai.ASM import ASM_PoseSuperInteraction
from module_ai.ai_alarm import AIAlarm
from module_ai.ai_autonomy import AI_Autonomy
from module_ai.ai_functions import push_sim_function, clear_sim_instance
from module_ai.ai_input import inputbox
from module_ai.ai_menu_class import MainMenu
from module_ai.ai_socials import AIBehavior, Behavior
from module_ai.ai_util import error_trap, ld_file_loader, ld_notice, clean_string
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from interactions.base.mixer_interaction import MixerInteraction
from interactions.base.super_interaction import SuperInteraction
from routing.route_events.route_event import RouteEvent
from sims4.localization import LocalizationHelperTuning
from socials.group import SocialGroup
from ui.ui_dialog_picker import UiSimPicker, SimPickerRow

from scripts_core.sc_jobs import do_change_outfit_spinup


class AIMenu(ImmediateSuperInteraction):
    directory = None
    last_initial_value = ""

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)

        self.ai_option_choices = ("Settings", "Emotes", "Friendly", "Mean", "Mischief", "Romance", "Funny", "Chat", "Teach", "*Reload Script")
        self.ai_mean_choices = ("Pick On Sim", "Stop Picking On Sim")
        self.ai_friendly_choices = ("Befriend",)
        self.ai_emotes_choices = ("Cheer", "Shout", "Dance", "Guitar", "Shock", "Cry", "Cackle", "Loathe", "Solve", "Kneel", "Sit On Floor", "Sit In Car", "Bah", "Spin", "Custom")
        self.ai_settings_choices = ("*Enable Debugging",
                                    "*Enable Tracking",
                                    "*Disable Debugging",
                                    "*Enable Group Socials Filter",
                                    "*Disable Group Socials Filter",
                                    "*Enable Cleanup Filter",
                                    "*Disable Cleanup Filter",
                                    "*Disable Autonomy Filter",
                                    "*Keep Sims In Room", "*Free Sims In Room",
                                    "*Reset Adjustment Alarms",
                                    "*Reset Behaviour Queue",
                                    "*Cancel Social Group",
                                    "*Enable Autonomy", "*Disable Autonomy",
                                    "*Force Posture Change",
                                    "Dump Animations")
        self.ai_option = MainMenu(*args, **kwargs)
        self.ai_mean = MainMenu(*args, **kwargs)
        self.ai_friendly = MainMenu(*args, **kwargs)
        self.ai_emotes = MainMenu(*args, **kwargs)
        self.ai_settings = MainMenu(*args, **kwargs)
        self.script_choice = MainMenu(*args, **kwargs)
        self.ai_alarm = AIAlarm(*args, **kwargs)

    def _run_interaction_gen(self, timeline):
        self.ai_option.show(timeline, self, 0, self.ai_option_choices, "AI Social Menu", "Make a selection.")

    def main_menu(self, timeline):
        self.ai_option.show(timeline, self, 0, self.ai_option_choices, "AI Social Menu", "Make a selection.")

    def settings(self, timeline):
        self.ai_settings.show(timeline, self, 0, self.ai_settings_choices, "AI Settings", "Make a selection.", None, False, True)

    def mean(self, timeline):
        self.ai_mean.show(timeline, self, 0, self.ai_mean_choices, "AI Mean", "Make a selection.", None, False, True)

    def friendly(self, timeline):
        self.ai_friendly.show(timeline, self, 0, self.ai_friendly_choices, "AI Friendly", "Make a selection.", None, False, True)

    def emotes(self, timeline):
        self.ai_emotes.show(timeline, self, 0, self.ai_emotes_choices, "AI Emotes", "Make a selection.", None, False, True)

    def cheer(self, timeline):
        if self.target.is_sim:
            target = self.target
        else:
            target = self.sim
        push_sim_function(target, target, 128613, False)

    def shout(self, timeline):
        if self.target.is_sim:
            target = self.target
        else:
            target = self.sim
        push_sim_function(target, target, 162994, False)

    def dance(self, timeline):
        if self.target.is_sim:
            target = self.target
        else:
            target = self.sim
        push_sim_function(target, target, 241743, False)

    def guitar(self, timeline):
        if self.target.is_sim:
            target = self.target
        else:
            target = self.sim
        push_sim_function(target, target, 240761, False)

    def shock(self, timeline):
        if self.target.is_sim:
            target = self.target
        else:
            target = self.sim
        push_sim_function(target, target, 13832, False)

    def cry(self, timeline):
        if self.target.is_sim:
            target = self.target
        else:
            target = self.sim
        push_sim_function(target, target, 199403, False)

    def cackle(self, timeline):
        if self.target.is_sim:
            target = self.target
        else:
            target = self.sim
        push_sim_function(target, target, 190211, False)

    def bah(self, timeline):
        reaction = [125613, 130151]
        if self.target.is_sim:
            target = self.target
        else:
            target = self.sim
        push_sim_function(self.sim, target, reaction[random.randint(0, len(reaction) - 1)], False)

    def loathe(self, timeline):
        if self.target.is_sim:
            target = self.target
        else:
            target = self.sim
        push_sim_function(target, target, 258846, False)

    def solve(self, timeline):
        if self.target.is_sim:
            target = self.target
        else:
            target = self.sim
        clear_sim_instance(target.sim_info)
        push_sim_function(target, target, 258326, False)

    def kneel(self, timeline):
        ASM_PoseSuperInteraction.pose_name = "c_idle_kneel_x"
        if self.target.is_sim:
            target = self.target
        else:
            target = self.sim
        clear_sim_instance(target.sim_info)
        push_sim_function(target, target, 15779027876505748956, False)

    def sit_on_floor(self, timeline):
        ASM_PoseSuperInteraction.pose_name = "Rookie Simmer:PosePack_202010021933046272_set_4"
        if self.target.is_sim:
            target = self.target
        else:
            target = self.sim
        clear_sim_instance(target.sim_info)
        push_sim_function(target, target, 15779027876505748956, False)

    def sit_in_car(self, timeline):
        ASM_PoseSuperInteraction.pose_name = "simsgami:PosePack_202012131939267161_set_1"
        if self.target.is_sim:
            target = self.target
        else:
            target = self.sim
        clear_sim_instance(target.sim_info)
        push_sim_function(target, target, 15779027876505748956, False)

    def spin(self, timeline):
        ASM_PoseSuperInteraction.pose_name = "a_clothesChange_x"
        if self.target.is_sim:
            target = self.target
        else:
            target = self.sim
        clear_sim_instance(target.sim_info)
        push_sim_function(target, target, 15779027876505748956, False)
        #do_change_outfit_spinup(target, target.sim_info._current_outfit[0], timeline)

    def custom(self, timeline):
        inputbox("Custom Emote", "Text names or partial names in lowercase of the animation you want", self.custom_callback, AIMenu.last_initial_value)

    def custom_callback(self, pose):
        AIMenu.last_initial_value = pose
        ASM_PoseSuperInteraction.pose_name = pose
        if self.target.is_sim:
            target = self.target
        else:
            target = self.sim
        clear_sim_instance(target.sim_info)
        push_sim_function(target, target, 15779027876505748956, False)

    def dump_animations(self, timeline):
        clip_text = ""

        for key in sorted(sims4.resources.list()):
            clip = services.get_instance_manager(sims4.resources.Types.ANIMATION).get(key.instance)
            if clip:
                clip = str(clip).replace("<class 'sims4.tuning.instances.", "").replace("'>", "")
                clip_text = clip_text + "{}\n".format(clip)

        datapath = os.path.abspath(os.path.dirname(__file__))
        filename = datapath + r"\{}.log".format("animations")
        file = open(filename, "w")
        file.write(clip_text)
        file.close()

    def picker(self, title: str, text: str, max: int = 50, callback=None):
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

            sims = services.sim_info_manager().instanced_sims_gen()
            for sim in sims:
                dialog.add_row(SimPickerRow(sim.id, False, tag=sim))

            dialog.add_listener(callback)
            dialog.show_dialog()
        except BaseException as e:
            error_trap(e)

    def pick_on_sim(self, timeline):
        def get_simpicker_results_callback(dialog):
            try:
                if not dialog.accepted:
                    return

                for target in dialog.get_result_tags():
                    for queue in AI_Autonomy.behavior_queue:
                        if target == queue.target:
                            AI_Autonomy.behavior_queue.remove(queue)
                    AI_Autonomy.behavior_queue.append(AIBehavior(self.sim, target, Behavior.MEAN))

                self.ai_alarm.pick_on_sim_alarm()

                ld_notice(self.sim.sim_info, "Pick On Sim", "{} {} is picking on {} sims. "
                    "This works best using mean sims. (sims with the mean trait)".
                    format(self.sim.first_name, self.sim.last_name, self.ai_alarm.pick_on_sim_count(self.sim)), True, "GREEN")

            except BaseException as e:
                error_trap(e)

        self.picker("Select Sims To Pick On", "Pick up to 10 Sims", 10, get_simpicker_results_callback)

    def stop_picking_on_sim(self, timeline):
        self.ai_alarm.end_alarm()
        for queue in list(AI_Autonomy.behavior_queue):
            if queue.sim == self.sim:
                clear_sim_instance(queue.sim.sim_info, "sit", True)
                clear_sim_instance(queue.target.sim_info, "sit", True)
                push_sim_function(queue.sim, queue.target, 193802)

    def befriend(self, timeline):
        ld_notice(self.sim.sim_info, "Befriend", "{} {} chooses not to be mean to {} {}. "
                "This works best using mean sims (sims with the mean trait) or angry sims, "
                "disabling their ability to be mean. ".
                format(self.sim.first_name, self.sim.last_name, self.target.first_name, self.target.last_name),
                True, "GREEN")
        AI_Autonomy.behavior_queue.append(AIBehavior(self.sim, self.target, Behavior.FRIENDLY))

    def _enable_debugging(self, timeline):
        setattr(SocialGroup, "DEBUG", True)
        setattr(MixerInteraction, "DEBUG", True)
        setattr(SuperInteraction, "DEBUG", True)
        setattr(SuperInteraction, "DEBUG", True)
        setattr(RouteEvent, "DEBUG", True)

    def _disable_debugging(self, timeline):
        setattr(SocialGroup, "DEBUG", False)
        setattr(MixerInteraction, "DEBUG", False)
        setattr(MixerInteraction, "DEBUG_TRACK", None)
        setattr(SuperInteraction, "DEBUG_TRACK", None)
        setattr(RouteEvent, "DEBUG_TRACK", None)
        setattr(RouteEvent, "DEBUG", False)

    def _enable_tracking(self, timeline):
        setattr(SocialGroup, "DEBUG", True)
        setattr(MixerInteraction, "DEBUG", True)
        setattr(MixerInteraction, "DEBUG_TRACK", self.target)
        setattr(SuperInteraction, "DEBUG", False)
        setattr(SuperInteraction, "DEBUG_TRACK", self.target)
        setattr(RouteEvent, "DEBUG_TRACK", self.target)
        setattr(RouteEvent, "DEBUG", False)

    def _enable_group_socials_filter(self, timeline):
        setattr(SocialGroup, "EXIT_SOCIALS_ENABLED", False)
        setattr(MixerInteraction, "EXIT_SOCIALS_ENABLED", True)
        setattr(SuperInteraction, "EXIT_SOCIALS_ENABLED", True)

    def _disable_group_socials_filter(self, timeline):
        setattr(SocialGroup, "EXIT_SOCIALS_ENABLED", False)
        setattr(MixerInteraction, "EXIT_SOCIALS_ENABLED", False)
        setattr(SuperInteraction, "EXIT_SOCIALS_ENABLED", False)

    def _enable_cleanup_filter(self, timeline):
        setattr(SuperInteraction, "FILTER_CLEANUP_ENABLED", True)

    def _disable_cleanup_filter(self, timeline):
        setattr(SuperInteraction, "FILTER_CLEANUP_ENABLED", False)

    def _disable_autonomy_filter(self, timeline):
        try:
            filters = AI_Autonomy.get_social_filters(self, "disabled")
            filter_text = "|".join(filters)
            AIMenu.last_initial_value = filter_text
            inputbox("Set Disabled Autonomy", "Text names or partial names in lowercase of the autonomy you want "
                "disabled seperated by a '|'", self._disable_autonomy_filter_callback, AIMenu.last_initial_value)
        except BaseException as e:
            error_trap(e)

    def _disable_autonomy_filter_callback(self, filter_text):
        filters = filter_text.split("|")
        filter_text = ""
        for i, filter in enumerate(filters):
            if i % 8 == 0 and i != 0:
                filter_text += '\n'
            elif i != 0:
                filter_text += '|'
            filter_text += filter
        datapath = os.path.abspath(os.path.dirname(__file__))
        filename = datapath + r"\Data\disabled.dat"
        try:
            file = open(filename, "w")
        except:
            return
        file.write(filter_text)
        file.close()

    def _reset_adjustment_alarms(self, timeline):
        try:
            for sim in services.sim_info_manager().instanced_sims_gen():
                for social_group in sim.get_groups_for_sim_gen():
                    if social_group._adjustment_alarm is not None:
                        social_group._adjustment_alarm = None
                        social_group._create_adjustment_alarm()
        except BaseException as e:
            error_trap(e)

    def _cancel_social_group(self, timeline):
        try:
            for sim in services.sim_info_manager().instanced_sims_gen():
                for social_group in sim.get_groups_for_sim_gen():
                    social_group.remove(sim)
                    social_group._resend_members()
        except BaseException as e:
            error_trap(e)

    def _force_posture_change(self, timeline):
        for sim in services.sim_info_manager().instanced_sims_gen():
            for social_group in sim.get_groups_for_sim_gen():
                social_group.execute_adjustment_interaction(sim, True)

    def chat(self, timeline):
        inputbox("Chat", "Type in a direct chat message to your sim", self.chat_response, AIMenu.last_initial_value)

    def chat_response(self, chat_string: str):
        try:
            if self.target is not None:
                if self.target.is_sim:
                    AIMenu.last_initial_value = chat_string
                    push_sim_function(self.sim, self.target, 14704263509489557000)
                    ld_notice(self.target.sim_info, "{} {}".format(self.target.first_name, self.target.last_name), "{}".format(chat_string), True, "GREEN")
                    return
            AIMenu.last_initial_value = ""
        except BaseException as e:
            error_trap(e)

    def _reload_script(self, timeline):
        inputbox("Reload Script",
                         "Type in directory to browse or leave blank to list all in current directory", self._reload_script_callback)

    def _reload_script_callback(self, script_dir: str):
        try:
            if script_dir == "" or script_dir is None:
                AIMenu.directory = os.path.abspath(os.path.dirname(__file__))
                files = [f for f in os.listdir(AIMenu.directory) if isfile(join(AIMenu.directory, f))]
            else:
                AIMenu.directory = script_dir
                files = [f for f in os.listdir(script_dir) if isfile(join(script_dir, f))]
            files.insert(0, "all")
            self.script_choice.show(None, self, 0, files, "Reload Script",
                                       "Choose a script to reload", "_reload_script_final", True)
        except BaseException as e:
            error_trap(e)

    def _reload_script_final(self, filename: str):
        try:
            if AIMenu.directory is None:
                AIMenu.directory = os.path.abspath(os.path.dirname(__file__))
            ld_file_loader(AIMenu.directory, filename)
        except BaseException as e:
            error_trap(e)
