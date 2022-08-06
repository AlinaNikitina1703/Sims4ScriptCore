from scripts_core.sc_autonomy import AutonomyState
from sims.sim_info import SimInfo


class sc_RoutineInfo:
    __slots__ = ("title", "autonomy", "role", "career", "level", "max_staff", "routine", "buffs", "actions", "filtered_actions", "off_lot",
                 "world", "venue", "on_duty", "off_duty", "use_object1", "use_object2", "use_object3", "object_action1",
                 "object_action2", "object_action3")

    def __init__(self, title=None,
                 autonomy=None,
                 role=None,
                 career=None,
                 level=None,
                 max_staff=None,
                 routine=None,
                 buffs=None,
                 actions=None,
                 filtered_actions=None,
                 off_lot=None,
                 world=None,
                 venue=None,
                 on_duty=None,
                 off_duty=None,
                 use_object1=None,
                 use_object2=None,
                 use_object3=None,
                 object_action1=0,
                 object_action2=0,
                 object_action3=0):

        super().__init__()
        self.title = title
        self.autonomy = autonomy
        self.role = role
        self.career = career
        self.level = level
        self.max_staff = max_staff
        self.routine = routine
        self.buffs = buffs
        self.actions = actions
        self.filtered_actions = filtered_actions
        self.off_lot = off_lot
        self.world = world
        self.venue = venue
        self.on_duty = on_duty
        self.off_duty = off_duty
        self.use_object1 = use_object1
        self.use_object2 = use_object2
        self.use_object3 = use_object3
        self.object_action1 = object_action1
        self.object_action2 = object_action2
        self.object_action3 = object_action3


setattr(SimInfo, "routine_info", sc_RoutineInfo())
