import animation
import date_and_time
import element_utils
import services
import sims4
from animation.arb_accumulator import ArbAccumulatorService, _get_actors_for_arb_element_sequence, \
    AnimationSleepElement, ArbSequenceElement
from time_service import TimeService

from module_simulation import sc_simulate
from scripts_core.sc_message_box import message_box
from scripts_core.sc_util import error_trap

sim_buffer = 1.0

# default is 25
# date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND = 250
TimeService.MAX_TIME_SLICE_MILLISECONDS = 8

def set_time_slice(slice=8):
    TimeService.MAX_TIME_SLICE_MILLISECONDS = slice
    time_service = services.time_service()
    time_service.update()

def set_speed_of_time(speed=250):
    date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND = speed

def set_sim_buffer(buffer=1.0):
    global sim_buffer
    sim_buffer = buffer

@sims4.commands.Command('arbs_run_gen_exception', command_type=sims4.commands.CommandType.Live)
def arbs_run_gen_exception(e=None, value2=None, value3=None, _connection=None):
    return

def arbs_run_gen(self, timeline):
    try:
        global sim_buffer
        if not self._arb_element_sequence:
            return None
        duration_must_run = 0.0
        arb_duration_interrupt = 0.0
        arb_duration_repeat = 0.0
        for arb_element in self._arb_element_sequence:
            arb_duration_total, arb_duration_must_run, arb_duration_repeat = arb_element.arb.get_timing()
            arb_duration_interrupt = arb_duration_total - arb_duration_must_run
            duration_must_run += arb_duration_must_run * sim_buffer
            arb_element.distribute()
        duration_interrupt = arb_duration_interrupt
        duration_repeat = arb_duration_repeat
        if ArbAccumulatorService.MAXIMUM_TIME_DEBT > 0:
            actors = _get_actors_for_arb_element_sequence((self._arb_element_sequence), main_timeline_only=True)
            arb_accumulator = services.current_zone().arb_accumulator_service
            time_debt_max = arb_accumulator.get_time_debt(actors)
            shave_time_actual = arb_accumulator.get_shave_time_given_duration_and_debt(duration_must_run, time_debt_max)
            duration_must_run -= shave_time_actual
            if shave_time_actual:
                for actor in actors:
                    time_debt = arb_accumulator.get_time_debt((actor,))
                    time_debt += shave_time_actual
                    arb_accumulator.set_time_debt((actor,), time_debt)

            else:
                last_arb = self._arb_element_sequence[(-1)].arb
                if all((last_arb._normal_timeline_ends_in_looping_content(actor.id) for actor in actors)):
                    duration_must_run += time_debt_max
                    arb_accumulator.set_time_debt(actors, 0)

        arbs = tuple((animation_element.arb for animation_element in self._arb_element_sequence))
        animation_sleep_element = AnimationSleepElement(duration_must_run, duration_interrupt, duration_repeat, arbs=arbs)

        if not self._animate_instantly:
            return element_utils.run_child(timeline, animation_sleep_element)

        optional_time_elapsed = animation_sleep_element.optional_time_elapsed
        if ArbAccumulatorService.MAXIMUM_TIME_DEBT > 0 and optional_time_elapsed > 0:
            actors = animation.arb_accumulator.get_actors_for_arb_sequence()
            for actor in actors:
                time_debt = animation.arb_accumulator.get_time_debt((actor,))
                new_time_debt = time_debt - optional_time_elapsed
                new_time_debt = max(new_time_debt, 0)
                animation.arb_accumulator.set_time_debt((actor,), new_time_debt)

        return None

    except BaseException as e:
        error_trap(e)
        message_box(None, None, "Arbs Element Autonomy", "Custom Arbs activated with errors!\n"
            "_run_gen is a generator and needs to yield non bool type variables. Smooth Llama implimented a"
            " version of this without proper coding and it never worked. New coding needs to be implimented."
            " Reverting back to vanilla code.", "DEFAULT")
        ArbSequenceElement._run_gen = sc_simulate.vanilla_run_gen
        pass
