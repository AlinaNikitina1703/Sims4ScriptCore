import random
import time

import services
import sims4
from relationships.relationship_track import RelationshipTrack
from sims4.math import Vector3
from sims4.resources import Types, get_resource_key

from module_ai.ai_autonomy import AI_Autonomy
from module_ai.ai_socials import Behavior
from scripts_core.sc_gohere import go_here
from scripts_core.sc_jobs import distance_to_by_room, clear_sim_instance, add_sim_buff, \
    push_sim_function, distance_to, point_object_at, check_actions, get_random_radius_position, clear_leaving, \
    find_empty_chair, get_skill_level
from scripts_core.sc_message_box import message_box
from scripts_core.sc_util import error_trap


class AIMain:

    def __init__(self):
        super().__init__()

        self.mean_socials = [27704, 25674, 26151, 26544, 35132, 25888, 26543, 25885, 25886, 25577, 98192, 35124]
        self.do_socials = []
        self.interaction_target = None
        self.time_index = time.time()
        self.score = {}

    def pick_on_sim_count(self, sim):
        try:
            count = 0
            for queue in AI_Autonomy.behavior_queue:
                if queue.sim == sim:
                    count += 1
            return count
        except BaseException as e:
            error_trap(e)

    def get_sim_count_in_social_group(self, sim, target):
        try:
            # EA only counts sims in the active social group that are with a queue.
            # This counts all sims in the target groups that have social ties to each other active or not.
            this_count = 0
            for group in sim.get_groups_for_sim_gen():
                count = sum((1 for sim in group))
                if this_count < count:
                    this_count = count
            if target.is_sim:
                for that_group in target.get_groups_for_sim_gen():
                    if that_group is not None:
                        if that_group != group:
                            that_count = sum((1 for sim in that_group))
                            if that_count > this_count:
                                this_count = that_count
            return this_count
        except BaseException as e:
            error_trap(e)

    def is_sim_in_group(self, sim, target):
        for group in sim.get_groups_for_sim_gen():
            for s in group:
                if s == target:
                    return True
        return False

    def remove_sim_from_group(self, sim, target=None):
        if not target:
            target = sim
        for group in target.get_groups_for_sim_gen():
            if sim in group:
                group.remove(sim)
                group._resend_members()

    def remove_leaving_sims_from_group(self, queue):
        [self.remove_sim_from_group(sim) for sim in services.sim_info_manager().instanced_sims_gen() if
            [role for role in sim.autonomy_component.active_roles() if "leave" in str(role).lower()] and sim not in queue]

    def init_socials(self):
        disallowed_actions = ["fight", "enemy", "feud", "loveguru", "story", "expert", "werewolf", "vampire", "askmovein", "suggest", "batuu", "seeoutfit", "skiing", "folklore", "sex", "providetips", "waitstaff"]
        self.do_socials = []
        socials_manager = services.get_instance_manager(Types.INTERACTION)
        for key in sims4.resources.list():
            interaction = socials_manager.get(key.instance)
            action = str(interaction).lower()
            if "mixer_social" in action and not [a for a in disallowed_actions if a in action]:
                self.do_socials.append(interaction)

    def get_social(self, type="mean"):
        do_socials = []
        do_social_names = []
        for social in self.do_socials:
            action = str(social).lower()
            if type in action:
                do_socials.append(social.guid64)
                do_social_names.append(action)

        random.seed(int(time.process_time()))
        index = random.randint(0, len(do_socials) - 1)
        if len(do_socials):
            return do_socials[index]
        return self.mean_socials[index]

    def get_relationship(self, sim, target):
        return sim.sim_info.relationship_tracker.get_relationship_score(target.id, RelationshipTrack.FRIENDSHIP_TRACK)

    def reset_socials(self):
        allowed_interactions = ["bonfire", "campfire", "sit", "gohere", "stand"]
        sim_queue = []
        [sim_queue.append(queue.sim) for queue in AI_Autonomy.behavior_queue if queue.sim not in sim_queue and
            queue.sim in services.sim_info_manager().instanced_sims_gen()]
        if not sim_queue:
            return
        for sim in sim_queue:
            clear_sim_instance(sim.sim_info, allowed_interactions, True)
            self.remove_sim_from_group(sim)

    def sit_on_socials(self, sim):
        if not check_actions(sim, "sit"):
            clear_sim_instance(sim.sim_info, "sit", True)
            chair = find_empty_chair(sim, None, 3.0)
            if chair:
                if "stool" in str(chair).lower():
                    push_sim_function(sim, chair, 157667, False)
                elif "hospitalexambed" in str(chair).lower():
                    push_sim_function(sim, chair, 107801, False)
                elif "bed" in str(chair).lower():
                    push_sim_function(sim, chair, 288595, False)
                else:
                    push_sim_function(sim, chair, 31564, False)

    def socialize(self, atmos=Behavior.FRIENDLY):
        try:
            allowed_interactions = ["bonfire", "campfire", "sit", "gohere", "frontdesk", "grab", "consume", "drink", "smoke", "sim_chat", "social", "idle_chatting", "friendly", "mean", "stand"]
            sim_queue = []
            now = time.time()
            [sim_queue.append(queue.sim) for queue in AI_Autonomy.behavior_queue if queue.behavior == atmos
                and queue.sim not in sim_queue and queue.sim in services.sim_info_manager().instanced_sims_gen()]
            self.remove_leaving_sims_from_group(sim_queue)

            for sim in sim_queue:
                clear_leaving(sim)
                target_queue = []

                if atmos == Behavior.MEAN and hasattr(self.interaction_target, "is_sim") and self.interaction_target.is_sim and self.interaction_target != sim:
                    target_queue.append(self.interaction_target)
                elif atmos == Behavior.MEAN:
                    [target_queue.append(queue_sim) for queue_sim in sim_queue if queue_sim not in target_queue and
                        queue_sim != sim and self.get_relationship(sim, queue_sim) < 10]
                else:
                    [target_queue.append(queue_sim) for queue_sim in sim_queue if queue_sim not in target_queue and
                        queue_sim != sim]

                if check_actions(sim, "gohere"):
                    clear_sim_instance(sim.sim_info, "gohere", True)
                    continue
                if not target_queue:
                    continue
                if len(sim.get_all_running_and_queued_interactions()) > 4 and distance_to(sim, self.interaction_target) < 5:
                    continue
                if distance_to(sim, self.interaction_target) > 5 and not check_actions(sim, "gohere"):
                    clear_sim_instance(sim.sim_info, "gohere", True)
                    go_here(sim, self.interaction_target.position, self.interaction_target.level, 3.0)
                    continue

                random.shuffle(target_queue)
                target = target_queue[0]
                self.sit_on_socials(sim)

                if atmos == Behavior.MEAN:
                    self.set_sim_mood(sim)
                    self.set_sim_mood(target)
                    social = self.get_social("mean")
                elif atmos == Behavior.ROMANTIC:
                    self.set_sim_mood(sim, Behavior.ROMANTIC)
                    self.set_sim_mood(target, Behavior.ROMANTIC)
                    if self.get_relationship(sim, target) < -25:
                        social = self.get_social("mean")
                    else:
                        social = self.get_social("romance")
                elif self.get_relationship(sim, target) < -25:
                    social = self.get_social("mean")
                else:
                    social = self.get_social("friendly")

                if distance_to(sim, target) < 5:
                    clear_sim_instance(sim.sim_info, allowed_interactions, True)
                    clear_sim_instance(target.sim_info, allowed_interactions, True)
                    push_sim_function(sim, target, social, False)
                    continue

        except BaseException as e:
            error_trap(e)

    def snowball_fight(self):
        try:
            sim_queue = []
            actions = [182908, 182925, 182926, 0]
            [sim_queue.append(queue.sim) for queue in AI_Autonomy.behavior_queue if queue.behavior == Behavior.FRIENDLY
                and queue.sim not in sim_queue and queue.sim in services.sim_info_manager().instanced_sims_gen()]
            for sim in sim_queue:
                clear_leaving(sim)
                target_queue = []
                [target_queue.append(queue_sim) for queue_sim in sim_queue if queue_sim not in target_queue and queue_sim != sim]
                random.shuffle(target_queue)
                target = target_queue[0]
                action = actions[random.randint(0, len(actions) - 1)]

                if check_actions(sim, "gohere") and check_actions(sim, "snowball"):
                    clear_sim_instance(sim.sim_info, "snowball", True)
                    continue
                elif check_actions(sim, "gohere"):
                    clear_sim_instance(sim.sim_info, "gohere", True)
                    continue
                elif distance_to(sim, self.interaction_target) > 6 and not check_actions(sim, "gohere"):
                    clear_sim_instance(sim.sim_info, "gohere", True)
                    go_here(sim, self.interaction_target.position)
                    continue
                elif distance_to_by_room(sim, target) < 3 or not action:
                    clear_sim_instance(sim.sim_info, "gohere", True)
                    clear_sim_instance(target.sim_info, "gohere", True)
                    if not check_actions(sim, "gohere"):
                        pos = get_random_radius_position(target.position, 4)
                        go_here(sim, pos)
                    if not check_actions(target, "gohere"):
                        pos = get_random_radius_position(sim.position, 4)
                        go_here(target, pos)
                    continue
                elif distance_to_by_room(sim, self.interaction_target) < 6:
                    clear_sim_instance(sim.sim_info, "snowball", True)
                    clear_sim_instance(target.sim_info, "snowball", True)
                    point_object_at(sim, target)
                    push_sim_function(sim, target, action, False, 182893)
                    continue

        except BaseException as e:
            error_trap(e)

    def basketball(self):
        try:
            sim_queue = []
            actions = [144911, 147722, 147723, 147724, 144911]
            [sim_queue.append(queue.sim) for queue in AI_Autonomy.behavior_queue if queue.behavior == Behavior.FRIENDLY
                and queue.sim not in sim_queue and queue.sim in services.sim_info_manager().instanced_sims_gen()]
            for sim in sim_queue:
                clear_leaving(sim)
                target = self.interaction_target
                action = actions[random.randint(0, len(actions) - 1)]

                if check_actions(sim, "gohere") and check_actions(sim, "basketball"):
                    clear_sim_instance(sim.sim_info)
                    continue
                elif check_actions(sim, "gohere"):
                    clear_sim_instance(sim.sim_info, "gohere", True)
                    continue
                elif distance_to_by_room(sim, target) > 6 and not check_actions(sim, "gohere"):
                    clear_sim_instance(sim.sim_info, "gohere", True)
                    pos = Vector3(target.position.x + 3 * target.forward.x,
                                  target.position.y,
                                  target.position.z + 3 * target.forward.z)
                    go_here(sim, pos)
                    continue
                elif distance_to_by_room(sim, target) < 6:
                    clear_sim_instance(sim.sim_info)
                    push_sim_function(sim, target, action, False)
                    fitness = get_skill_level(16659, sim)
                    if action == 147722:
                        self.score[sim] += round(3.0 * float(fitness) * 0.1)
                    if action == 147723:
                        self.score[sim] += round(1.0 * float(fitness) * 0.1)
                    continue

        except BaseException as e:
            error_trap(e)

    def set_position(self, target):
        self.interaction_target = target

    def get_position(self):
        return self.interaction_target.position

    def show_scores(self):
        sim_queue = []
        scoreboard = ""
        [sim_queue.append(queue.sim) for queue in AI_Autonomy.behavior_queue if queue.behavior == Behavior.FRIENDLY
            and queue.sim not in sim_queue and queue.sim in services.sim_info_manager().instanced_sims_gen()]
        for sim in sim_queue:
            scoreboard = scoreboard + "Sim: {} Score: {}\n".format(sim.first_name + " " + sim.last_name, self.score[sim])
        message_box(None, None, "Scoreboard", scoreboard)

    def set_sim_mood(self, sim, atmos=Behavior.MEAN):
        buff_manager = services.get_instance_manager(Types.BUFF)
        buff_component = sim.sim_info.Buffs
        mood = buff_component._active_mood
        buff = None
        if atmos == Behavior.MEAN:
            buff = buff_manager.get(27207)
        elif atmos == Behavior.ROMANTIC:
            buff = buff_manager.get(9305)
        if buff and mood:
            mood_type = str(mood.__name__).replace("Mood_", "")
            visible_buffs = [b for b in buff_manager.types.values() if sim.sim_info.has_buff(b)]
            if mood_type.lower() not in str(buff.__name__).lower():
                if visible_buffs:
                    for b in visible_buffs:
                        sim.sim_info.remove_buff_by_type(buff_manager.get(get_resource_key(b.guid64, Types.BUFF)))
        if buff and atmos == Behavior.MEAN:
            add_sim_buff(27207, sim.sim_info)
        elif buff and atmos == Behavior.ROMANTIC:
            add_sim_buff(9305, sim.sim_info)
