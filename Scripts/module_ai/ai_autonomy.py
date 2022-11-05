import os
import random

import build_buy
import services
from interactions.base.mixer_interaction import MixerInteraction
from interactions.interaction_finisher import FinishingType
from relationships.relationship_track import RelationshipTrack
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

    def notify_queue_head(self: MixerInteraction):
        if sc_Vars.disable_social_autonomy:
            return
        try:
            action = self.__class__.__name__.lower()

            if self.is_finishing:
                return
            if self.target is None:
                return
            if hasattr(self.target, "is_sim"):
                if not self.target.is_sim:
                    return
            if not hasattr(self.target, "is_sim"):
                return

            if self.social_group is not None and self.EXIT_SOCIALS_ENABLED:
                self.social_group.max_radius = 5.0
                self.social_group.time_until_posture_changes = 1

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


                if "social" in action and not self.is_user_directed or "archetype" in action and not self.is_user_directed:
                    if sim_count > 2 and "romance" in action or sim_count > 2 and "kiss" in action:
                        if sc_Vars.DEBUG:
                            debugger("Sim: {} {} - Killed: {}".format(self.sim.first_name, self.sim.last_name, action))
                        self.cancel(FinishingType.KILLED, 'Filtered')
                    elif "mischief" in action and can_be_mean and mischief_value < random.uniform(8, 100):
                        if sc_Vars.DEBUG:
                            debugger("Sim: {} {} - Killed: {}".format(self.sim.first_name, self.sim.last_name, action))
                        self.cancel(FinishingType.KILLED, 'Filtered')
                    elif "mean" not in action and "mischief" not in action and can_be_mean:
                        if sc_Vars.DEBUG:
                            debugger("Sim: {} {} - Killed: {}".format(self.sim.first_name, self.sim.last_name, action))
                        self.cancel(FinishingType.KILLED, 'Filtered')
                    elif "mean" in action and not can_be_mean or "mischief" in action and not can_be_mean:
                        if sc_Vars.DEBUG:
                            debugger("Sim: {} {} - Killed: {}".format(self.sim.first_name, self.sim.last_name, action))
                        self.cancel(FinishingType.KILLED, 'Filtered')
                elif "argument" in action and not self.is_user_directed:
                    if sc_Vars.DEBUG:
                        debugger("Sim: {} {} - Killed: {}".format(self.sim.first_name, self.sim.last_name, action))
                    self.cancel(FinishingType.KILLED, 'Filtered')
                elif "idle_chat" in action and not self.is_user_directed and can_be_mean:
                    if sc_Vars.DEBUG:
                        debugger("Sim: {} {} - Killed: {}".format(self.sim.first_name, self.sim.last_name, action))
                    self.cancel(FinishingType.KILLED, 'Filtered')
        except BaseException as e:
            error_trap(e)

