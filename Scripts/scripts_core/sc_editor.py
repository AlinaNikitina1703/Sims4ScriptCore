import services
from objects.object_enums import ResetReason
from scripts_core.sc_util import message_box, error_trap
from scripts_core.sc_script_vars import sc_Vars

try:
    from Tmex_TOOL_InputInteraction import TMToolData
    sc_Vars.TMEX = True
except:
    sc_Vars.TMEX = False
    pass

try:
    from tmex_CAW_Library import TMToolData
    sc_Vars.TMEX = True
except:
    sc_Vars.TMEX = False
    pass

def delete_selected_objects():
    try:
        all_objects = TMToolData.GroupObjects
        count = 0
        for obj in list(all_objects):
            count = count + 1
            obj.destroy()
        TMToolData.GroupObjects.clear()
        message_box(None, None, "Delete Selected Objects", "{} Objects deleted.".format(count), "GREEN")
    except BaseException as e:
        error_trap(e)

def reset_all_objects():
    all_objects = services.object_manager().get_all()
    count = 0
    for obj in list(all_objects):
        if obj.definition.tuning_file_id is not 0:
            count = count + 1
            obj.reset(ResetReason.NONE, None, 'Command')
    message_box(None, None, "Reset Objects", "{} Objects reset.".format(count), "GREEN")


def delete_all_objects(error_objects=False, elevation=120):
    all_objects = services.object_manager().get_all()
    count = 0
    for obj in list(all_objects):
        try:
            if error_objects:
                if obj.location.transform.translation.y < elevation and obj.slot_hash == 0:
                    count = count + 1
                    obj.destroy()
            elif obj.definition.id != 816:
                if not obj.is_sim:
                    if not obj.is_on_active_lot():
                        count = count + 1
                        obj.destroy()

        except BaseException as e:
            message_box(None, None, "Object Error", "Object ID {}".format(obj.definition.id), "ORANGE")
            error_trap(e)
    message_box(None, None, "Delete All Objects", "{} Objects deleted.".format(count), "GREEN")


def delete_objects_on_lot():
    all_objects = services.object_manager().get_all()
    count = 0
    for obj in list(all_objects):
        if not obj.is_sim:
            if obj.is_on_active_lot():
                count = count + 1
                obj.destroy()
    message_box(None, None, "Delete Objects On Lot", "{} Objects deleted.".format(count), "GREEN")
