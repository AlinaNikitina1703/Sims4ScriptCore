import collections
import time

import alarms
import animation
import autonomy
import autonomy.autonomy_component
import autonomy.autonomy_service
import autonomy.settings
import date_and_time
import distributor.system
import element_utils
import services
import sims
import sims4
import sims4.commands
import sims4.resources
from animation.arb_accumulator import ArbAccumulatorService, _get_actors_for_arb_element_sequence, \
    AnimationSleepElement, ArbSequenceElement
from distributor.system import Journal
from protocolbuffers.Consts_pb2 import MGR_UNMANAGED
from sims.sim_info import SimInfo
from situations.ambient.walkby_ambient_situation import WalkbyAmbientSituation
from time_service import TimeService

from scripts_core.sc_io import inject_to
from scripts_core.sc_util import error_trap

MAX_DISTANCE_SCORE = 5
FULL_AUTONOMY_MULTIPLIER = 0
MULTIPLIER_FOR_HOUSEHOLD_SIMS = 1
last_updated_sim_priorities = time.time()
last_updated_real_time = collections.defaultdict(time.time)
failed_full_autonomy = {}
successful_full_autonomy_times = collections.defaultdict(time.time)
last_obj = None
autonomy_limit_multiplier = 5
current_sims_full_autonomy_limit = 2 * autonomy_limit_multiplier
max_full_autonomy_sims_if_someone_is_pickupping_something = 1 * autonomy_limit_multiplier
max_full_autonomy_sims_when_normal = 2 * autonomy_limit_multiplier

sim_buffer = 1.0
sim_delay = date_and_time.TimeSpan(1)

old_run_gen = ArbSequenceElement._run_gen
old_run_full_autonomy_callback_gen = autonomy.autonomy_component.AutonomyComponent._run_full_autonomy_callback_gen
old_create_full_autonomy_alarm = autonomy.autonomy_component.AutonomyComponent._create_full_autonomy_alarm
old_build_journal_seed = distributor.system.Journal._build_journal_seed

# default is 25
# date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND = 250

def reset_simulation_to_vanilla():
    global old_run_gen, old_run_full_autonomy_callback_gen, old_create_full_autonomy_alarm, old_build_journal_seed
    ArbSequenceElement._run_gen = old_run_gen
    autonomy.autonomy_component.AutonomyComponent._run_full_autonomy_callback_gen = old_run_full_autonomy_callback_gen
    autonomy.autonomy_component.AutonomyComponent._create_full_autonomy_alarm = old_create_full_autonomy_alarm
    distributor.system.Journal._build_journal_seed = old_build_journal_seed

def set_simulation_to_custom():
    ArbSequenceElement._run_gen = arbs_run_gen
    autonomy.autonomy_component.AutonomyComponent._run_full_autonomy_callback_gen = _run_full_autonomy_callback_gen
    autonomy.autonomy_component.AutonomyComponent._create_full_autonomy_alarm = _create_full_autonomy_alarm
    distributor.system.Journal._build_journal_seed = _build_journal_seed

def set_distance_score(score=10):
    global MAX_DISTANCE_SCORE
    MAX_DISTANCE_SCORE = int(score)

def set_autonomy_mult(mult=1):
    global autonomy_limit_multiplier, current_sims_full_autonomy_limit
    global max_full_autonomy_sims_if_someone_is_pickupping_something, max_full_autonomy_sims_when_normal
    autonomy_limit_multiplier = int(mult)
    current_sims_full_autonomy_limit = 2 * autonomy_limit_multiplier
    max_full_autonomy_sims_if_someone_is_pickupping_something = 1 * autonomy_limit_multiplier
    max_full_autonomy_sims_when_normal = 2 * autonomy_limit_multiplier

def set_time_slice(slice=8):
    TimeService.MAX_TIME_SLICE_MILLISECONDS = slice
    time_service = services.time_service()
    time_service.update()

def set_speed_of_time(speed=250):
    date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND = speed

def set_sim_delay(delay: date_and_time.TimeSpan):
    global sim_delay
    sim_delay = delay

def set_sim_buffer(buffer=1.0):
    global sim_buffer
    sim_buffer = buffer

def reset_stats(sim: SimInfo):
    successful_full_autonomy_times[sim.sim_id] = time.time()
    failed_full_autonomy[sim.sim_id] = False
    last_updated_real_time[sim.sim_id] = time.time()


@inject_to(sims.sim_info.SimInfo, 'create_sim_instance')
def create_sim_instance(original, *args, **kwargs):
    reset_stats(args[0])
    return original(*args, **kwargs)


def get_default_autonomy(self, setting_class):
    autonomy_service = services.autonomy_service()
    setting = autonomy_service.global_autonomy_settings.get_setting(setting_class,
                                                                    self.get_autonomy_settings_group())
    if setting != setting_class.UNDEFINED:
        return setting
    if self._role_tracker is not None:
        setting = self._role_tracker.get_autonomy_state()
        if setting != setting_class.UNDEFINED:
            return setting
    if services.current_zone().is_zone_running:
        tutorial_service = services.get_tutorial_service()
        if tutorial_service is not None:
            if tutorial_service.is_tutorial_running():
                return autonomy.settings.AutonomyState.FULL
    household = self.owner.household
    if household:
        setting = household.autonomy_settings.get_setting(setting_class, self.get_autonomy_settings_group())
        if setting != setting_class.UNDEFINED:
            return setting
    setting = autonomy_service.default_autonomy_settings.get_setting(setting_class,
                                                                     self.get_autonomy_settings_group())
    return setting


def _build_journal_seed(self, op, obj, manager_id):
    try:
        object_name = None
        if obj is None:
            object_id = 0
            if manager_id is None:
                manager_id = MGR_UNMANAGED
        else:
            object_id = obj.id
            if manager_id is None:
                manager_id = obj.manager.id if obj.manager is not None else MGR_UNMANAGED
        if object_id != 0:
            lod_logic(obj, object_id)
        return Journal.JournalSeed(op, object_id, manager_id, object_name)
    except BaseException as e:
        error_trap(e)
        distributor.system.Journal._build_journal_seed = old_build_journal_seed


def lod_logic(obj, object_id):
    if hasattr(obj, 'is_sim'):
        if obj.is_sim:
            actual_lod_logic(obj, object_id)


def actual_lod_logic(obj, object_id):
    global current_sims_full_autonomy_limit
    global last_updated_real_time
    global last_updated_sim_priorities
    passed_time = time.time() - last_updated_real_time[object_id]
    sim_info_manager = services.sim_info_manager()
    last_obj = object_id
    active_sim = services.get_active_sim()
    if time.time() - last_updated_sim_priorities > 1:
        current_sims_full_autonomy_limit = max_full_autonomy_sims_when_normal
        sims_to_scores = {}
        sims_spawned = list(sim_info_manager.instanced_sims_gen())
        perceptions = {}
        distances = {}
        perceptions_FA = {}
        walkers = []

        def get_current_walking_sims():
            for source in services.current_zone().ambient_service._sources:
                for situation in source.get_running_situations():
                    if isinstance(situation, WalkbyAmbientSituation) and situation._walker is not None:
                        walkers.append(situation._walker.id)

        get_current_walking_sims()
        for sim in sims_spawned:
            sim_id = sim.id
            distance_to_active_sim = calculate_distance(active_sim, MAX_DISTANCE_SCORE, sim)
            failed_cost_multiplier = calculate_failed_cost_multiplier(sim_id)
            sim_score_delay = calculate_general_sim_perception(sim_id)
            full_autonomy_perception_score = calculate_full_autonomy_perception_calculator(sim, sim_id)
            full_autonomy_perception_score = full_autonomy_perception_score_extras_calculator(
                full_autonomy_perception_score, sim, sim_id, walkers)
            lag_perception_score = sim_score_delay + full_autonomy_perception_score
            sim_score = (distance_to_active_sim + lag_perception_score) * failed_cost_multiplier
            if sim.sim_info in services.active_household().sim_infos:
                sim_score *= MULTIPLIER_FOR_HOUSEHOLD_SIMS
            distances[sim] = distance_to_active_sim
            sims_to_scores[sim] = sim_score
            perceptions[sim] = sim_score_delay
            perceptions_FA[sim] = full_autonomy_perception_score

        current_sim = 0
        sorted_sims = sorted(sims_to_scores, key=(sims_to_scores.get), reverse=True)
        while len(sorted_sims) > 0:
            sim = sorted_sims[0]
            if sim.sim_info.is_pet:
                del sorted_sims[0]
                continue
            if current_sim < current_sims_full_autonomy_limit:
                crucial_sims_logic(distances, perceptions, perceptions_FA, sim, sims_to_scores)
                current_sim += 1
                del sorted_sims[0]
            elif current_sim <= 15:
                kinda_important_sims_logic(distances, perceptions, perceptions_FA, sim, sims_to_scores)
                current_sim += 1
                del sorted_sims[0]
            else:
                never_made_a_sound_logic(distances, perceptions, perceptions_FA, sim, sims_to_scores)
                current_sim += 1
                del sorted_sims[0]

        last_updated_sim_priorities = time.time()
    last_updated_real_time[object_id] = time.time()


def calculate_general_sim_perception(sim_id):
    sim_score_delay = time.time() - last_updated_real_time[sim_id]
    return sim_score_delay


PICK_INTERACTIONS = [
    13172, 13169, 37819, 77004, 13276]


def full_autonomy_perception_score_extras_calculator(full_autonomy_perception_score, sim, sim_id, walkers):
    global current_sims_full_autonomy_limit
    if sim_id in walkers:
        full_autonomy_perception_score = 0
    running_sis = len(list(sim.interaction_refs))
    if running_sis > 0:
        full_autonomy_perception_score = 0

    for si in sim.si_state.all_guaranteed_si_gen():
        if hasattr(si, 'guid64') and si.guid64 in PICK_INTERACTIONS:
            full_autonomy_perception_score = 100
            current_sims_full_autonomy_limit = max_full_autonomy_sims_if_someone_is_pickupping_something
            break

    if sim.has_trait(services.get_instance_manager(sims4.resources.Types.TRAIT).get(16851)):
        full_autonomy_perception_score = 100
    return full_autonomy_perception_score


def calculate_full_autonomy_perception_calculator(sim, sim_id):
    global successful_full_autonomy_times
    if sim.sleeping:
        full_autonomy_perception_score = 0
    else:
        full_autonomy_perception_score = (time.time() - successful_full_autonomy_times[
            sim_id]) * FULL_AUTONOMY_MULTIPLIER
    if sim.sim_info in services.active_household().sim_infos:
        full_autonomy_perception_score = (time.time() - successful_full_autonomy_times[
            sim_id]) * FULL_AUTONOMY_MULTIPLIER
    return full_autonomy_perception_score


def calculate_failed_cost_multiplier(sim_id):
    global failed_full_autonomy
    failed_cost_multiplier = 1.0
    if sim_id in failed_full_autonomy:
        if failed_full_autonomy[sim_id]:
            failed_cost_multiplier = 1.5
    return failed_cost_multiplier


def calculate_distance(active_sim, maximum_distance_score, sim):
    if active_sim is not None:
        distance_to_active_sim = max(maximum_distance_score - (active_sim.position - sim.position).magnitude_2d(),
                                     0)
    else:
        distance_to_active_sim = maximum_distance_score
    return distance_to_active_sim


def never_made_a_sound_logic(distances, perceptions, perceptions_FA, sim, sims_to_scores):
    if sim.get_autonomy_state_setting() > autonomy.settings.AutonomyState.DISABLED:
        sim.autonomy_settings.set_setting(autonomy.settings.AutonomyState.DISABLED,
                                          sim.get_autonomy_settings_group())


def kinda_important_sims_logic(distances, perceptions, perceptions_FA, sim, sims_to_scores):
    if sim.get_autonomy_state_setting() > autonomy.settings.AutonomyState.LIMITED_ONLY:
        sim.autonomy_settings.set_setting(autonomy.settings.AutonomyState.LIMITED_ONLY,
                                          sim.get_autonomy_settings_group())


def crucial_sims_logic(distances, perceptions, perceptions_FA, sim, sims_to_scores):
    if sim.get_autonomy_state_setting() <= autonomy.settings.AutonomyState.FULL:
        old_autonomy_setting = get_default_autonomy(sim.autonomy_component, autonomy.settings.AutonomyState)
        sim.autonomy_settings.set_setting(old_autonomy_setting, sim.get_autonomy_settings_group())


def _run_full_autonomy_callback_gen(self, timeline):
    global sim_delay
    try:
        try:
            autonomy_pushed_interaction = None
            self.set_last_autonomous_action_time(False)
            autonomy_pushed_interaction = yield from self._attempt_full_autonomy_gen(timeline)
            self._last_autonomy_result_was_none = not autonomy_pushed_interaction
            if autonomy_pushed_interaction:
                failed_full_autonomy[self.owner] = True
            else:
                failed_full_autonomy[self.owner] = False
                successful_full_autonomy_times[self.owner.id] = time.time()
        except Exception:
            pass
    finally:
        self._full_autonomy_element_handle = None
        self._schedule_next_full_autonomy_update(sim_delay)

    if False:
        yield None

def _create_full_autonomy_alarm(self, time_until_trigger):
    global sim_delay
    if self._full_autonomy_alarm_handle is not None:
        self._destroy_full_autonomy_alarm()
    time_until_trigger = sim_delay
    self._full_autonomy_alarm_handle = alarms.add_alarm(self, time_until_trigger, (self._on_run_full_autonomy_callback), use_sleep_time=False)

def arbs_run_gen(self, timeline):
    try:
        global sim_buffer, old_run_gen
        if not self._arb_element_sequence:
            return True
        duration_must_run = 0.0
        duration_interrupt = 0.0
        duration_repeat = 0.0
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
                shave_time_actual = arb_accumulator.get_shave_time_given_duration_and_debt(duration_must_run,
                                                                                           time_debt_max)
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
        else:
            arbs = tuple((animation_element.arb for animation_element in self._arb_element_sequence))
            animation_sleep_element = AnimationSleepElement(duration_must_run, duration_interrupt, duration_repeat,
                                                            arbs=arbs)
            try:
                if not self._animate_instantly:
                    yield from element_utils.run_child(timeline, animation_sleep_element)
            except:
                pass
            optional_time_elapsed = animation_sleep_element.optional_time_elapsed
            if ArbAccumulatorService.MAXIMUM_TIME_DEBT > 0 and optional_time_elapsed > 0:
                actors = animation.arb_accumulator.get_actors_for_arb_sequence()
                for actor in actors:
                    time_debt = animation.arb_accumulator.get_time_debt((actor,))
                    new_time_debt = time_debt - optional_time_elapsed
                    new_time_debt = max(new_time_debt, 0)
                    animation.arb_accumulator.set_time_debt((actor,), new_time_debt)

        return True
        if False:
            yield None
    except BaseException as e:
        error_trap(e)
        ArbSequenceElement._run_gen = old_run_gen

ArbSequenceElement._run_gen = arbs_run_gen
autonomy.autonomy_component.AutonomyComponent._run_full_autonomy_callback_gen = _run_full_autonomy_callback_gen
autonomy.autonomy_component.AutonomyComponent._create_full_autonomy_alarm = _create_full_autonomy_alarm
distributor.system.Journal._build_journal_seed = _build_journal_seed
