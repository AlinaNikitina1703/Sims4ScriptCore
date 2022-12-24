import sims4
from distributor.shared_messages import IconInfoData
from sims4.collections import make_immutable_slots_class
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog import UiDialogResponse, ButtonType, CommandArgType
from ui.ui_dialog_notification import UiDialogNotification

class sc_MessageBox:

        def __init__(self, icon_top=None,
                     icon_bottom=None,
                     title="",
                     text="",
                     color="DEFAULT",
                     font_color=None,
                     button_text=None,
                     command='message_box_callback',
                     arg1=None,
                     arg2=None,
                     arg3=None):

            super().__init__()
            self.icon_top = icon_top
            self.icon_bottom = icon_bottom
            self.title = title
            self.text = text
            self.color = color
            self.font_color = font_color
            self.button_text = button_text
            self.command = command
            self.arg1 = arg1
            self.arg2 = arg2
            self.arg3 = arg3

        def show(self):
            message_box(self.icon_top, self.icon_bottom, self.title, self.text, self.color, self.button_text,
                        self.command, self.arg1, self.arg2, self.arg3, self.font_color)


def message_box(icon_top, icon_bottom, title="", text="", color="DEFAULT", button_text=None, command='message_box_callback', arg1=None, arg2=None, arg3=None, font_color=None):
    button_responses = ()
    if button_text is not None:
        arg1 = make_immutable_slots_class(['arg_type', 'arg_value'])({'arg_type': CommandArgType.ARG_TYPE_STRING, 'arg_value': arg1})
        arg2 = make_immutable_slots_class(['arg_type', 'arg_value'])({'arg_type': CommandArgType.ARG_TYPE_STRING, 'arg_value': arg2})
        arg3 = make_immutable_slots_class(['arg_type', 'arg_value'])({'arg_type': CommandArgType.ARG_TYPE_STRING, 'arg_value': arg3})
        button1_response_command = make_immutable_slots_class(['arguments', 'command'])({'arguments': (arg1, arg2, arg3), 'command': command})
        button1_response = UiDialogResponse(dialog_response_id=ButtonType.DIALOG_RESPONSE_OK, ui_request=UiDialogResponse.UiDialogUiRequest.SEND_COMMAND, response_command=button1_response_command, text=lambda **_: LocalizationHelperTuning.get_raw_text(button_text))
        button_responses = (button1_response,)
    if icon_top:
        icon = lambda _: IconInfoData(obj_instance=icon_top)
    else:
        icon = None
    if icon_bottom:
        secondary_icon = lambda _: IconInfoData(obj_instance=icon_bottom)
    else:
        secondary_icon = None
    if color is "PURPLE":
        if not font_color:
            font_color = "#ffffff"
        urgency = UiDialogNotification.UiDialogNotificationUrgency.DEFAULT
        information_level = UiDialogNotification.UiDialogNotificationLevel.SIM
        visual_type = UiDialogNotification.UiDialogNotificationVisualType.SPECIAL_MOMENT
    elif color is "ORANGE":
        if not font_color:
            font_color = "#ffffff"
        urgency = UiDialogNotification.UiDialogNotificationUrgency.URGENT
        information_level = UiDialogNotification.UiDialogNotificationLevel.PLAYER
        visual_type = UiDialogNotification.UiDialogNotificationVisualType.INFORMATION
    elif color is "GREEN":
        if not font_color:
            font_color = "#ffffff"
        urgency = UiDialogNotification.UiDialogNotificationUrgency.DEFAULT
        information_level = UiDialogNotification.UiDialogNotificationLevel.PLAYER
        visual_type = UiDialogNotification.UiDialogNotificationVisualType.INFORMATION
    else:
        if not font_color:
            font_color = "#ffff00"
        urgency = UiDialogNotification.UiDialogNotificationUrgency.DEFAULT
        information_level = UiDialogNotification.UiDialogNotificationLevel.SIM
        visual_type = UiDialogNotification.UiDialogNotificationVisualType.INFORMATION

    notification = UiDialogNotification.TunableFactory().default(icon_top,
         text=lambda **_: LocalizationHelperTuning.get_raw_text(text),
         title=lambda **_: LocalizationHelperTuning.get_raw_text('<font size="20" color="{}"><b>'.format(font_color) + title + '</b></font>'),
         icon=icon,
         secondary_icon=secondary_icon,
         urgency=urgency,
         information_level=information_level,
         visual_type=visual_type,
         expand_behavior=1,
         ui_responses=button_responses,
         dialog_options=0)
    notification.show_dialog()

@sims4.commands.Command('message_box_callback', command_type=sims4.commands.CommandType.Live)
def message_box_callback(value1=None, value2=None, value3=None, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output('value1: {}\nvalue2: {}\nvalue3: {}'.format(value1, value2, value3))
