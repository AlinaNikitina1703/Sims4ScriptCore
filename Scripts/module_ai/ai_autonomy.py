import os
import random

import build_buy
import clock
import interactions.aop
import interactions.context
import services
import sims4.localization
import sims4.tuning.tunable
from animation.posture_manifest_constants import ADJUSTMENT_CONSTRAINT
from autonomy.autonomy_modes_tuning import AutonomyModesTuning
from interactions.base.mixer_interaction import MixerInteraction
from interactions.context import QueueInsertStrategy, InteractionContext
from interactions.interaction_finisher import FinishingType
from interactions.priority import can_displace
from interactions.social.greeting_socials import greetings
from interactions.social.social_super_interaction import SocialSuperInteraction, INTENDED_POSITION_LIABILITY, \
    IntendedPositionLiability
from interactions.utils.satisfy_constraint_interaction import SatisfyConstraintSuperInteraction
from primitives.routing_utils import estimate_distance_between_points
from relationships.relationship_track import RelationshipTrack
from sims.sim import LOSAndSocialConstraintTuning
from sims4.resources import Types, get_resource_key

from module_ai.ai_functions import push_sim_function
from module_ai.ai_socials import Behavior
from module_ai.ai_util import error_trap, distance_to
from scripts_core.sc_jobs import debugger
from scripts_core.sc_script_vars import sc_Vars


class AI_Autonomy:
    behavior_queue = []
    action_queue = []
    autonomy_queue = []
    sim_callback_queue = []
    keep_in_room = []
    posture_target_list = []

    def __init__(self):
        super().__init__()

    def sleeping_in_room(self, sim):
        interactions = sim.get_all_running_and_queued_interactions()
        room = build_buy.get_room_id(sim.zone_id, sim.position, sim.level)
        if [action for action in interactions if "sleep" in str(action).lower()]:
            return room
        return -2

    def can_do_in_room(self):
        try:
            room = build_buy.get_room_id(self.target.zone_id, self.target.position, self.target.level)
        except:
            room = -1
            pass
        if [sim for sim in services.sim_info_manager().instanced_sims_gen() if
            AI_Autonomy.sleeping_in_room(self, sim) == room and room > 0]:
            if "clean" in str(self).lower():
                for commodity in self.target.commodity_tracker:
                    if "exambed_dirtiness" in str(commodity).lower():
                        commodity.set_value(100)
                    if "commodity_dirtiness" in str(commodity).lower():
                        commodity.set_value(100)
            elif "puddle" in str(self.target).lower() or "dust" in str(self.target).lower():
                self.target.destroy()
            elif "seating_sit" in str(self).lower():
                for obj in services.object_manager().get_all():
                    if "sit" in str(obj).lower() or "chair" in str(obj).lower() or "sofa" in str(obj).lower():
                        obj_room = build_buy.get_room_id(obj.zone_id, obj.position, obj.level)
                        dist = distance_to(self.sim, obj)
                        if dist < 10:
                            if not [s for s in services.sim_info_manager().instanced_sims_gen() if
                                    AI_Autonomy.sleeping_in_room(self, s) == obj_room]:
                                self.cancel(FinishingType.KILLED, 'Filtered')
                                push_sim_function(self.sim, obj, 31564)
                                return True
            return False
        return True

    def get_si(self, guid64):
        # Get the tuning manager for interaction instance types
        tuning_manager = services.get_instance_manager(Types.INTERACTION)
        # Return the SI tuning from the manager
        return tuning_manager.get(guid64)

    def get_social_filters(self, filename):
        filters = []
        datapath = os.path.abspath(os.path.dirname(__file__))
        filename = datapath + r"\Data\{}.dat".format(filename)
        try:
            file = open(filename, "r")
        except:
            return None
        lines = file.readlines()
        for line in lines:
            line = line.strip('\n')
            values = line.split("|")
            if len(values):
                filters.extend(values)
            else:
                filters.extend(line)
        file.close()
        if len(filters) == 0:
            return None
        return filters

    def get_sim_count_in_social_group(self, target):
        # EA only counts sims in the active social group that are with a queue.
        # This counts all sims in the target groups that have social ties to each other active or not.
        this_count = sum((1 for sim in self.social_group))
        if target.is_sim:
            for that_group in target.get_groups_for_sim_gen():
                if that_group is not None:
                    if that_group != self.social_group:
                        that_count = sum((1 for sim in that_group))
                        if that_count > this_count:
                            this_count = that_count
        return this_count

    def _get_close_to_target_and_greet(self: SocialSuperInteraction, force=True):
        now = services.time_service().sim_now
        if self._last_go_nearby_time is not None:
            minimum_delay_between_attempts = LOSAndSocialConstraintTuning.minimum_delay_between_route_nearby_attempts
            if now - self._last_go_nearby_time < clock.interval_in_sim_minutes(minimum_delay_between_attempts):
                return False
        self._last_go_nearby_time = now
        if self._trying_to_go_nearby_target:
            return False
        if self._target_was_going_far_away:
            return False
        if self._go_nearby_interaction is not None:
            if not self._go_nearby_interaction.is_finishing:
                return False
        target_sim = self.target_sim
        if target_sim is None:
            return False
        social_group = self._get_social_group_for_this_interaction()
        if social_group is not None:
            if not social_group.can_get_close_and_wait(self.sim, target_sim):
                return False
        if self._greet_sim(target_sim, social_group):
            force = True
        self._trying_to_go_nearby_target = True
        try:
            result = None
            if self._go_nearby_interaction is not None:
                transition_failed = self._go_nearby_interaction.transition_failed
                self._interactions.discard(self._go_nearby_interaction)
                self._go_nearby_interaction = None
                if transition_failed:
                    self.sim.add_lockout(target_sim, AutonomyModesTuning.LOCKOUT_TIME)
                    self.cancel(FinishingType.TRANSITION_FAILURE, 'SocialSuperInteraction: Failed to _get_close_to_target_and_greet.')
                return False
            if target_sim.intended_location is not None:
                try:
                    distance_to_intended = estimate_distance_between_points(target_sim.position, target_sim.routing_surface, target_sim.intended_location.transform.translation, target_sim.intended_location.routing_surface)
                except:
                    return False
                else:
                    if distance_to_intended is not None:
                        if distance_to_intended > LOSAndSocialConstraintTuning.maximum_intended_distance_to_route_nearby:
                            target_running = target_sim.queue.running
                            if not target_running is None:
                                if can_displace(self, target_running):
                                    self._target_was_going_far_away = True
                                    return False
                    target_sim_position = target_sim.intended_location.transform.translation
                    target_sim_routing_surface = target_sim.intended_location.routing_surface
            else:
                target_sim_position = target_sim.position
                target_sim_routing_surface = target_sim.routing_surface
            if not force:
                distance = (self.sim.position - target_sim_position).magnitude()
                if distance < LOSAndSocialConstraintTuning.constraint_expansion_amount:
                    if target_sim.can_see(self.sim):
                        return False
            sim_posture = self.sim.posture_state.body
            if sim_posture.multi_sim:
                if sim_posture.linked_sim is target_sim:
                    return False
            constraint_cone = greetings.GreetingsSatisfyContraintTuning.CONE_CONSTRAINT.create_constraint((self.sim), target_sim,
              target_position=target_sim_position,
              target_forward=(target_sim.intended_forward),
              routing_surface=target_sim_routing_surface)
            constraint_facing = interactions.constraints.Facing(target_sim, target_position=target_sim_position, facing_range=(sims4.math.PI / 2.0))
            constraint_los = target_sim.los_constraint
            total_constraint = constraint_cone.intersect(constraint_facing).intersect(constraint_los)
            total_constraint = total_constraint.intersect(ADJUSTMENT_CONSTRAINT)
            if not total_constraint.valid:
                return False
            context = InteractionContext((self.sim), (InteractionContext.SOURCE_SCRIPT),
              (self.priority),
              insert_strategy=(QueueInsertStrategy.FIRST),
              cancel_if_incompatible_in_queue=True,
              must_run_next=True)
            result = self.sim.push_super_affordance(SatisfyConstraintSuperInteraction, None, context, constraint_to_satisfy=total_constraint,
              allow_posture_changes=True,
              set_work_timestamp=False,
              name_override='WaitNearby')
            interaction = result.interaction if result else None
            if interaction is None or interaction.is_finishing:
                return False
            intended_position_liability = IntendedPositionLiability(interaction, target_sim)
            interaction.add_liability(INTENDED_POSITION_LIABILITY, intended_position_liability)
            self._go_nearby_interaction = interaction
            self._interactions.add(interaction)
            return True
        finally:
            self._trying_to_go_nearby_target = False

    def notify_queue_head(self: MixerInteraction):
        if sc_Vars.disable_social_autonomy:
            return
        try:
            if self.is_finishing:
                return
            if self.target is None:
                return

            if hasattr(self.target, "is_sim"):
                if not self.target.is_sim:
                    return
            if not hasattr(self.target, "is_sim"):
                return

            action = self.__class__.__name__.lower()
            target_name = self.target.first_name + " " + self.target.last_name

            if self.social_group is not None and self.EXIT_SOCIALS_ENABLED:
                self.social_group.max_radius = 5.0
                self.social_group.time_until_posture_changes = 1200

                sim_count = AI_Autonomy.get_sim_count_in_social_group(self, self.target)
                mood = self.sim.sim_info.get_mood()
                mood_intensity = self.sim.sim_info.get_mood_intensity()

                if mood is not None:
                    sim_mood = mood.guid64
                else:
                    sim_mood = 0

                relationship_value = self.sim.sim_info.relationship_tracker.get_relationship_score(self.target.id,
                                                                                                   RelationshipTrack.FRIENDSHIP_TRACK)
                relationship_value += self.sim.sim_info.relationship_tracker.get_relationship_score(self.target.id,
                                                                                                    RelationshipTrack.ROMANCE_TRACK)

                mean_value = (0 - relationship_value)
                if sim_mood == 14632:
                    mean_value += (25 + (50 * mood_intensity))
                instance_manager = services.get_instance_manager(Types.TRAIT)
                key = instance_manager.get(get_resource_key(16857, Types.TRAIT))
                if self.sim.sim_info.has_trait(key):
                    mean_value += 25
                key = instance_manager.get(get_resource_key(16836, Types.TRAIT))
                if self.sim.sim_info.has_trait(key):
                    mean_value += 50
                if mean_value > 100:
                    mean_value = 100

                mischief_value = (100 - random.uniform(mean_value, 100)) + random.uniform(0, 10)

                mean_chance = random.uniform(0, 100)

                if mean_chance < mean_value:
                    can_be_mean = True
                else:
                    can_be_mean = False

                for b in AI_Autonomy.behavior_queue:
                    if b.sim == self.sim and b.target == self.target and b.behavior == Behavior.MEAN:
                        can_be_mean = True
                    elif b.sim == self.sim and b.target == self.target and b.behavior == Behavior.FRIENDLY:
                        can_be_mean = False
                    elif b.target == self.sim and b.sim == self.target and b.behavior == Behavior.MEAN:
                        can_be_mean = True
                    elif b.target == self.sim and b.sim == self.target and b.behavior == Behavior.FRIENDLY:
                        can_be_mean = False

                if sc_Vars.DEBUG_SOCIALS:
                    debugger("Sim: {} {} - Queue: {} - Target: {}".format(self.sim.first_name, self.sim.last_name, action, target_name))

                if "social" in action and not self.is_user_directed or "archetype" in action and not self.is_user_directed:
                    if sim_count > 2 and "romance" in action or sim_count > 2 and "kiss" in action:
                        if sc_Vars.DEBUG_SOCIALS:
                            debugger("Sim: {} {} - Killed: {} - Target: {}".format(self.sim.first_name, self.sim.last_name, action, target_name))
                        self.cancel(FinishingType.KILLED, 'Filtered')
                    elif "mischief" in action and can_be_mean and mischief_value < random.uniform(8, 100):
                        if sc_Vars.DEBUG_SOCIALS:
                            debugger("Sim: {} {} - Killed: {} - Target: {}".format(self.sim.first_name, self.sim.last_name, action, target_name))
                        self.cancel(FinishingType.KILLED, 'Filtered')
                    elif "mean" not in action and "mischief" not in action and can_be_mean:
                        if sc_Vars.DEBUG_SOCIALS:
                            debugger("Sim: {} {} - Killed: {} - Target: {}".format(self.sim.first_name, self.sim.last_name, action, target_name))
                        self.cancel(FinishingType.KILLED, 'Filtered')
                    elif "mean" in action and not can_be_mean or "mischief" in action and not can_be_mean:
                        if sc_Vars.DEBUG_SOCIALS:
                            debugger("Sim: {} {} - Killed: {} - Target: {}".format(self.sim.first_name, self.sim.last_name, action, target_name))
                        self.cancel(FinishingType.KILLED, 'Filtered')
                elif "argument" in action and not self.is_user_directed:
                    if sc_Vars.DEBUG_SOCIALS:
                        debugger("Sim: {} {} - Killed: {} - Target: {}".format(self.sim.first_name, self.sim.last_name, action, target_name))
                    self.cancel(FinishingType.KILLED, 'Filtered')
                elif "idle_chat" in action and not self.is_user_directed and can_be_mean:
                    if sc_Vars.DEBUG_SOCIALS:
                        debugger("Sim: {} {} - Killed: {} - Target: {}".format(self.sim.first_name, self.sim.last_name, action, target_name))
                    self.cancel(FinishingType.KILLED, 'Filtered')
        except BaseException as e:
            error_trap(e)


SocialSuperInteraction._get_close_to_target_and_greet = AI_Autonomy._get_close_to_target_and_greet