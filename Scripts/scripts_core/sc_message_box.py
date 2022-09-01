from distributor.shared_messages import IconInfoData
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_notification import UiDialogNotification


def message_box(icon_top, icon_bottom, title, text, color="DEFAULT"):
    if icon_top:
        icon = lambda _: IconInfoData(obj_instance=icon_top)
    else:
        icon = None
    if icon_bottom:
        secondary_icon = lambda _: IconInfoData(obj_instance=icon_bottom)
    else:
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
                                                                 text=lambda
                                                                     **_: LocalizationHelperTuning.get_raw_text(
                                                                     text),
                                                                 title=lambda
                                                                     **_: LocalizationHelperTuning.get_raw_text(
                                                                     '<font size="20" color="#ffffff"><b>' + title + '</b></font>'),
                                                                 icon=icon,
                                                                 secondary_icon=secondary_icon,
                                                                 urgency=urgency,
                                                                 information_level=information_level,
                                                                 visual_type=visual_type,
                                                                 expand_behavior=1, dialog_options=0)
    notification.show_dialog()
