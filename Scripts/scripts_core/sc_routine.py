import alarms
import services
from date_and_time import create_time_span
from scripts_core.sc_jobs import function_options, find_all_objects_by_title, distance_to, check_actions, \
    clear_sim_instance, go_here_routine, add_to_inventory_by_id
from scripts_core.sc_message_box import message_box
from scripts_core.sc_script_vars import sc_Vars


class ScriptCoreRoutine:
    routine_alarm = None
    routine_function = None
    routine_option = None

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)

    def alarm_ini(self):
        self.end_alarm()
        ScriptCoreRoutine.routine_alarm = alarms.add_alarm(self, create_time_span(minutes=sc_Vars.update_speed),
                                        (self.routine_alarm_callback), repeating=True, cross_zone=False)

    def routine_alarm_callback(self, _):
        if ScriptCoreRoutine.routine_alarm is None:
            return
        if ScriptCoreRoutine.routine_function:
            function_options(ScriptCoreRoutine.routine_option, self, ScriptCoreRoutine.routine_function)

    def end_alarm(self):
        if ScriptCoreRoutine.routine_alarm is None:
            return
        alarms.cancel_alarm(ScriptCoreRoutine.routine_alarm)
        ScriptCoreRoutine.routine_alarm = None

    def grab_drink_from_cooler_routine(self, drink):
        client = services.client_manager().get_first_client()
        sim = client.active_sim
        coolers = find_all_objects_by_title(sim, "object_cooler", sim.level, 32, False, True)
        if coolers:
            coolers.sort(key=lambda obj: distance_to(obj, sim))
            cooler = next(iter(coolers))
            if not check_actions(sim, "gohere") and distance_to(sim, cooler) > 1.0:
                clear_sim_instance(sim.sim_info)
                go_here_routine(sim, cooler.position, cooler.level)
            elif distance_to(sim, cooler) < 1.0:
                message_box(sim, cooler, "Grab A Drink",
                            "{} grabs a drink from the cooler.".format(sim.first_name), "PURPLE")
                add_to_inventory_by_id(sim, drink, True)
                ScriptCoreRoutine.routine_function = None
        else:
            message_box(sim, None, "Grab A Drink", "No cooler nearby.", "PURPLE")
            ScriptCoreRoutine.routine_function = None

