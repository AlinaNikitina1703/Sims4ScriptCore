import inspect
import os
import re
import traceback
try:
    from interactions.base.immediate_interaction import ImmediateSuperInteraction
    from interactions.context import QueueInsertStrategy
    from interactions.utils.tunable import TunableContinuation
    from interactions import ParticipantType
except:
    pass
import services
import sims4
import sims4.commands
import sims4.log
import sims4.resources
import sims4.tuning.instances
import sims4.utils
from distributor.shared_messages import IconInfoData
from sims4.localization import LocalizationHelperTuning
from sims4.tuning.tunable import OptionalTunable
from ui.ui_dialog_notification import UiDialogNotification


def message_box(icon_top, icon_bottom, title, text, show_icon=True, color="DEFAULT"):
    if show_icon:
        icon = lambda _: IconInfoData(obj_instance=icon_top)
        secondary_icon = lambda _: IconInfoData(obj_instance=icon_bottom)
    else:
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

    notification = UiDialogNotification.TunableFactory().default(icon_top,
        text=lambda**_: LocalizationHelperTuning.get_raw_text(text),
        title=lambda **_: LocalizationHelperTuning.get_raw_text('<font size="20" color="#ffffff"><b>' + title + '</b></font>'),
        icon=icon,
        secondary_icon=secondary_icon,
        urgency=urgency, information_level=information_level, visual_type=visual_type,
        expand_behavior=1, dialog_options=0)
    notification.show_dialog()

def clean_string(string: str, replace=False):
    global string_filter
    if replace:
        for s in string_filter:
            string = string.replace(s,"")
        string = re.sub(r'[_(),.:-]', ' ', string)
        string = re.sub(r"(\w)([A-Z])", r"\1 \2", string)
        string = string.strip()
        string = string.title()
    string = re.sub(r'[^A-Za-z0-9 _(),.:-]+', '', string)
    return string

def error_trap(e: BaseException):
    err = "Script failed: {} \n"
    for v in e.args:
        err = err + format(v) + "\n"
    message_box(None, None, "Error", "{}\n{}".format(err, traceback.format_exc()), False, "ORANGE")
    datapath = os.path.abspath(os.path.dirname(__file__))
    filename = datapath + r"\{}.log".format("debugger")
    file = open(filename, "w")
    file.write("{}\n{}".format(err, traceback.format_exc()))
    file.close()

def debugger(debug_text, frame=1, full_frame=False, write=False):
    try:
        # 0 is root function info, 1 is function info from where its running and 2 is parent calling function
        now = services.time_service().sim_now
        total_stack = inspect.stack()  # total complete stack
        total_depth = len(total_stack)  # length of total stack
        frameinfo = total_stack[frame][0]  # info on rel frame

        func_name = frameinfo.f_code.co_name
        filename = os.path.basename(frameinfo.f_code.co_filename)
        line_number = frameinfo.f_lineno  # of the call
        func_firstlineno = frameinfo.f_code.co_firstlineno

        debug_text = "\n{}\n".format(now) + debug_text
        if full_frame:
            for stack in total_stack:
                frameinfo = stack[0]
                func_name = frameinfo.f_code.co_name
                filename = os.path.basename(frameinfo.f_code.co_filename)
                line_number = frameinfo.f_lineno
                debug_text = debug_text + "\n@{} - {} - {}".format(line_number, filename, func_name)
        else:
            debug_text = debug_text + "\n@{} - {} - {}".format(line_number, filename, func_name)
        if write:
            datapath = os.path.abspath(os.path.dirname(__file__))
            filename = datapath + r"\{}.log".format("debugger")
            if os.path.exists(filename):
                append_write = 'a'  # append if already exists
            else:
                append_write = 'w'  # make a new file if not
            file = open(filename, append_write)
            file.write("\n{}".format(debug_text))
            file.close()
        else:
            client = services.client_manager().get_first_client()
            sims4.commands.cheat_output(debug_text, client.id)
    except BaseException as e:
        error_trap(e)

class ASM_PoseSuperInteraction(ImmediateSuperInteraction):
    pose_name = "a2a_mischief_NT_youFarted_fail_x"
    __qualname__ = 'ASM_PoseSuperInteraction'
    TEXT_INPUT_POSE_NAME = 'pose_name'
    INSTANCE_TUNABLES = {'actor_continuation':OptionalTunable(tunable=TunableContinuation(locked_args={'actor': ParticipantType.Actor}))}

    def _run_interaction_gen(self, timeline):
        try:
            self.interaction_parameters['pose_name'] = ASM_PoseSuperInteraction.pose_name
            self.push_tunable_continuation((self.actor_continuation), pose_name=ASM_PoseSuperInteraction.pose_name,
                                           insert_strategy=(QueueInsertStrategy.LAST),
                                           actor=(self.target))
        except BaseException as e:
            error_trap(e)