import sys

import clock
import sims4.reload as r
import os
import sims4
import re
import traceback
import services
from distributor.shared_messages import IconInfoData
from objects import ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED, ALL_HIDDEN_REASONS
from sims.sim_info import SimInfo
from sims4.collections import make_immutable_slots_class
from sims4.localization import LocalizationHelperTuning
from sims4.resources import get_resource_key, Types
from ui.ui_dialog import UiDialogResponse, ButtonType
from ui.ui_dialog_notification import UiDialogNotification
from os.path import isfile, join

from scripts_core.sc_debugger import debugger
from scripts_core.sc_message_box import message_box

string_filter = ("Active",
                 "active",
                 "ldCareer",
                 "Career",
                 "career",
                 "NPC",
                 "TURBODRIVER",
                 "WickedWhims",
                 "child",
                 "s_",
                 "_1",
                 "PP",
                 "GTW")


@sims4.commands.Command('music.load', command_type=sims4.commands.CommandType.Live)
def ld_file_loader(dirname: str, module: str, _connection=None):
    filetitle = module
    if filetitle == "all":
        try:
            file_list = [f for f in os.listdir(dirname) if isfile(join(dirname, f))]
            list = ""
            for file in file_list:
                if ".py" in file:
                    file = file.replace(".py", "")
                    if ld_file_loader(file):
                        list = list + file + "\n"
            ld_notice(None, "Load Script", "Files:\n{}reloaded!".format(list), False, "PURPLE")
        except BaseException as e:
            error_trap(e)
    else:
        try:
            filename = os.path.join(dirname, filetitle) + ".py"
            if "simulation.py" in filename:
                ld_notice(None, "Load Script", "Error loading simulation module. Access denied".format(filename), False,
                          "ORANGE")
                return False
            reloaded_module = r.reload_file(filename)
            if reloaded_module is not None:
                ld_notice(None, "Load Script", "Module {} loaded successfully!".format(filetitle), False, "PURPLE")
                return True
            else:
                ld_notice(None, "Load Script", "Error loading {} or module does not exist".format(filename), False,
                          "ORANGE")
                return False
        except BaseException as e:
            error_trap(e)


@sims4.commands.Command('music.reload', command_type=sims4.commands.CommandType.Live)
def ld_reload(_connection=None):
    try:
        datapath = os.path.abspath(os.path.dirname(__file__))
        file_list = [f for f in os.listdir(datapath) if isfile(join(datapath, f))]
        list = ""
        for file in file_list:
            if ".py" in file:
                file = file.replace(".py", "")
                if ld_file_loader(file):
                    list = list + file + "\n"
        ld_notice(None, "Load Script", "Files:\n{}reloaded!".format(list), False, "PURPLE")
    except BaseException as e:
        error_trap(e)
        return


def ld_notice(sim_info: SimInfo, title, text, show_icon=True, color="DEFAULT", icon_hash=None, button_text=None,
              button_response="notif_button1_clicked"):
    button_responses = []
    try:
        if button_text is not None:
            button1_response_command = make_immutable_slots_class(set(['arguments', 'command']))(
                {'arguments': (), 'command': button_response})
            button1_response = UiDialogResponse(dialog_response_id=ButtonType.DIALOG_RESPONSE_OK,
                                                ui_request=UiDialogResponse.UiDialogUiRequest.SEND_COMMAND,
                                                response_command=button1_response_command,
                                                text=lambda **_: LocalizationHelperTuning.get_raw_text(button_text))
            button_responses.append(button1_response)
        if show_icon:
            icon = lambda _: IconInfoData(obj_instance=sim_info)
            secondary_icon = None
        elif icon_hash is not None:
            icon_key = get_resource_key(icon_hash, Types.PNG)
            icon = lambda _: IconInfoData(icon_resource=icon_key)
            secondary_icon = None
        else:
            icon_key = None
            icon = None
            secondary_icon = None
        if color is "PURPLE":
            urgency = UiDialogNotification.UiDialogNotificationUrgency.DEFAULT
            information_level = UiDialogNotification.UiDialogNotificationLevel.SIM
            visual_type = UiDialogNotification.UiDialogNotificationVisualType.SPECIAL_MOMENT
        elif color is "ORANGE":
            urgency = UiDialogNotification.UiDialogNotificationUrgency.URGENT
            information_level = UiDialogNotification.UiDialogNotificationLevel.PLAYER
            visual_type = UiDialogNotification.UiDialogNotificationVisualType.INFORMATION
        elif color is "GREEN":
            urgency = UiDialogNotification.UiDialogNotificationUrgency.DEFAULT
            information_level = UiDialogNotification.UiDialogNotificationLevel.PLAYER
            visual_type = UiDialogNotification.UiDialogNotificationVisualType.INFORMATION
        else:
            urgency = UiDialogNotification.UiDialogNotificationUrgency.DEFAULT
            information_level = UiDialogNotification.UiDialogNotificationLevel.SIM
            visual_type = UiDialogNotification.UiDialogNotificationVisualType.INFORMATION

        notification = UiDialogNotification.TunableFactory().default(sim_info,
                                                                     text=lambda
                                                                         **_: LocalizationHelperTuning.get_raw_text(
                                                                         text),
                                                                     title=lambda
                                                                         **_: LocalizationHelperTuning.get_raw_text(
                                                                         '<font size="20" color="#ffffff"><b>' + title + '</b></font>'),
                                                                     icon=icon,
                                                                     secondary_icon=None,
                                                                     urgency=urgency,
                                                                     information_level=information_level,
                                                                     visual_type=visual_type,
                                                                     expand_behavior=1, ui_responses=button_responses,
                                                                     dialog_options=0)
        notification.show_dialog(on_response=(notif_button1_clicked))
    except BaseException as e:
        error_trap_console(e)

def get_icon_info_data(obj):
    if hasattr(obj, "definition"):
        id = obj.definition.id
    elif hasattr(obj, "id"):
        id = obj.id
    elif hasattr(obj, "sim_id"):
        id = obj.sim_id
    else:
        id = None
    if hasattr(obj, "geometry_state"):
        geometry_state = obj.geometry_state
    else:
        geometry_state = None
    if hasattr(obj, "material_hash"):
        material_hash = obj.material_hash
    else:
        material_hash = None

    if id is None:
        info = IconInfoData(obj_instance=obj, obj_name=(LocalizationHelperTuning.get_object_name(obj)))
    else:
        info = IconInfoData(obj_instance=obj, obj_def_id=id,
                        obj_geo_hash=(geometry_state),
                        obj_material_hash=(material_hash),
                        obj_name=(LocalizationHelperTuning.get_object_name(obj)))
    return info

@sims4.commands.Command('notif_icon_clicked', command_type=sims4.commands.CommandType.Live)
def notif_icon_clicked(sim_id: int, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    sim_info = services.sim_info_manager().get(sim_id)
    output('The icon in the notification was of {} {}'.format(sim_info.first_name, sim_info.last_name))


@sims4.commands.Command('notif_button1_clicked', command_type=sims4.commands.CommandType.Live)
def notif_button1_clicked(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    import subprocess
    cmd = "C:/Windows/System32/notepad.exe"
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, creationflags=0x08000000)
    process.wait()


def error_trap(e: BaseException, file=__file__):
    err = "(Error also reported in console. To open the console, press CTRL + SHIFT + C. To show previous messages in console, type help and enter, then scroll up.)\n\n"
    err = err + "Script failed: {} \n"
    error_traceback = str(sys.exc_info()) + "\n\n"
    for v in e.args:
        err = err + format(v) + "\n"
    err = err.replace('"', '`').replace("<", "-=").replace(">", "=-").replace("@", "At:")
    lines = traceback.format_exc().splitlines()
    for line in lines:
        error_traceback = error_traceback + "[" + re.sub(r'File ".*[\\/]([^\\/]+.py)"', r'File "\1"', line) + "]\n"
    error_traceback = error_traceback.replace('"', '`').replace("<", "-=").replace(">", "=-").replace("@", "At:")
    if "object_terrain" in error_traceback:
        debugger("{}\n{}\n".format(err, error_traceback), 0, True, True, True, False, file)
        return
    try:
        debugger("{}\n{}\n".format(err, error_traceback), 0, True, True, False, True, file)
        error_trap_console(e)
    except:
        message_box(None, None, "Error!", "Error reported in console. To open the console, press CTRL + SHIFT + C. "
                                          "To show previous messages in console, type help and enter, then scroll up.", "ORANGE")
        error_trap_console(e)
        pass


def error_trap_console(e: BaseException):
    client = services.client_manager().get_first_client()
    output = sims4.commands.CheatOutput(client.id)
    err = "Script failed: {} \n"
    error_traceback = ""
    for v in e.args:
        err = err + format(v) + "\n"
    lines = traceback.format_exc().splitlines()
    for line in lines:
        error_traceback = error_traceback + re.sub(r'File ".*[\\/]([^\\/]+.py)"', r'File "\1"', line)
    debugger("{}\n{}\n\n[{}]\n".format(err, sys.exc_info(), error_traceback), 0, True)


# This function defines sim_info in the sim object after spawn and destroy
def init_sim(sim_info: SimInfo, sim_id=None):
    if sim_info.is_instanced():
        sim = sim_info.get_sim_instance()
    else:
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED)
    if sim is None:
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
    return sim


# This function is my alternative to using a tuning file string table
def clean_string(string: str, replace=False):
    global string_filter
    if replace:
        for s in string_filter:
            string = string.replace(s, "")
        string = re.sub(r'[_(),.:-]', ' ', string)
        string = re.sub(r"(\w)([A-Z])", r"\1 \2", string)
        string = string.strip()
        string = string.title()
    string = re.sub(r'[^A-Za-z0-9 _(),.:-]+', '', string)
    return string


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

def update_clock_speed_to_scale(self, clock_speed):
    if clock_speed == clock.ClockSpeedMode.PAUSED:
        return self.PAUSED_SPEED_MULTIPLIER
    if clock_speed == clock.ClockSpeedMode.NORMAL:
        return self.NORMAL_SPEED_MULTIPLIER
    if clock_speed == clock.ClockSpeedMode.SPEED2:
        return self.NORMAL_SPEED_MULTIPLIER * 25
    if clock_speed == clock.ClockSpeedMode.SPEED3:
        return self.NORMAL_SPEED_MULTIPLIER * 50
    if clock_speed == clock.ClockSpeedMode.SUPER_SPEED3:
        return self.NORMAL_SPEED_MULTIPLIER * 100
    if clock_speed == clock.ClockSpeedMode.INTERACTION_STARTUP_SPEED:
        return clock.ClockSpeedMultipliers.get_interaction_startup_speed_multiplier()


clock.GameClock._clock_speed_to_scale = update_clock_speed_to_scale