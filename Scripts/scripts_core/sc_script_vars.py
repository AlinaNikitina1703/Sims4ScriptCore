import os

import enum
from interactions.base.mixer_interaction import MixerInteraction
from interactions.base.super_interaction import SuperInteraction
from sims.sim import Sim
from sims.sim_info import SimInfo

setattr(MixerInteraction, "EXIT_SOCIALS_ENABLED", True)
setattr(SuperInteraction, "FILTER_QUEUE_ENABLED", False)
setattr(MixerInteraction, "DEBUG", False)
setattr(SuperInteraction, "DEBUG", False)
setattr(SuperInteraction, "DEBUG_TRACK", None)
setattr(SuperInteraction, "EXIT_SOCIALS_ENABLED", True)
setattr(SuperInteraction, "FILTER_CLEANUP_ENABLED", True)
setattr(MixerInteraction, "DEBUG_ONLY_MEAN", False)
setattr(MixerInteraction, "DEBUG_TRACK", None)
setattr(SuperInteraction, "interaction_timeout", None)
setattr(MixerInteraction, "interaction_timeout", None)
setattr(Sim, "routine", False)
setattr(Sim, "job", None)
setattr(SimInfo, "routine", False)
setattr(SimInfo, "job", None)
setattr(Sim, "use_object_index", 0)
setattr(SimInfo, "use_object_index", 0)

class AutonomyState(enum.Int):
    UNDEFINED = -1
    DISABLED = 0
    LIMITED_ONLY = 1
    MEDIUM = 2
    FULL = 3
    ROUTINE_MEDICAL = 4
    ROUTINE_ORDERLY = 5
    NO_CLEANING = 6
    ON_BREAK = 7
    ROUTINE_PATIENT = 8
    ROUTINE_FOOD = 9
    ROUTINE_WORKER = 10
    ROUTINE_OFFICE = 11
    ROUTINE_POLICE = 12
    ROUTINE_MILITARY = 14
    CUSTOM_AI = 15


setattr(SimInfo, "autonomy", AutonomyState.FULL)
setattr(SimInfo, "choice", 0)
setattr(Sim, "autonomy", AutonomyState.FULL)


class sc_AutonomyQueue:
    def __init__(self, sim, autonomy, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.autonomy = autonomy
        self.sim = sim

class sc_DisabledAutonomy:
    def __init__(self, sim_info=None,
                 interaction=None):
        super().__init__()
        self.sim_info = sim_info
        self.interaction = interaction

    def __eq__(self, other):
        return self.interaction == other.interaction

class sc_Weather:
    def __init__(self, title=None,
                 duration=120,
                 wind=0.0,
                 window_frost=0.0,
                 water_frozen=0.0,
                 thunder=0.0,
                 lightning=0.0,
                 temperature=0,
                 snow=0.0,
                 snow_accumulation=0.0,
                 rain=0.0,
                 rain_accumulation=0.0,
                 light_snowclouds=0.0,
                 dark_snowclouds=0.0,
                 light_rainclouds=0.0,
                 dark_rainclouds=0.0,
                 cloudy=0.0,
                 heatwave=0.0,
                 partly_cloudy=1.0,
                 clear=0.0,
                 skybox_industrial=0.0,
                 snow_iciness=0.0,
                 snow_freshness=0.0):
        super().__init__()
        self.title = title
        self.duration = duration
        self.WIND = wind
        self.WINDOW_FROST = window_frost
        self.WATER_FROZEN = water_frozen
        self.THUNDER = thunder
        self.LIGHTNING = lightning
        self.TEMPERATURE = temperature
        self.SNOW = snow
        self.SNOW_ACCUMULATION = snow_accumulation
        self.RAIN = rain
        self.RAIN_ACCUMULATION = rain_accumulation
        self.LIGHT_SNOWCLOUDS = light_snowclouds
        self.DARK_SNOWCLOUDS = dark_snowclouds
        self.LIGHT_RAINCLOUDS = light_rainclouds
        self.DARK_RAINCLOUDS = dark_rainclouds
        self.CLOUDY = cloudy
        self.HEATWAVE = heatwave
        self.PARTLY_CLOUDY = partly_cloudy
        self.CLEAR = clear
        self.SKYBOX_INDUSTRIAL = skybox_industrial
        self.SNOW_ICINESS = snow_iciness
        self.SNOW_FRESHNESS = snow_freshness


class sc_Vars:
    TMEX = False
    DEBUG = False
    DEBUG_TIME = False
    DEBUG_AUTONOMY = False
    debug_log_text = ""
    AUTO_SELECTED_SIMS = True
    SELECTED_SIMS_AUTONOMY = 0
    DISABLE_NO_ROLE_ROUTINE = False
    DISABLE_MOD = False
    DISABLE_STAFF_ONLY = False
    DISABLE_PATIENTS = False
    DISABLE_SPAWNS = False
    DISABLE_CULLING = True
    DISABLE_WALKBYS = False
    DISABLE_ROUTINE = False
    DISABLE_SIMULATION = False
    DISABLE_ROLE_TITLES = False
    DISABLE_CAREER_TITLES = False
    MAX_SIMS = 20
    MAX_ZONE_SITUATION_SIMS = 3
    chance_switch_action = 10.0
    chance_role_trait = 20
    interaction_minutes_run = 3.0
    spawn_cooldown = None
    clean_speed = 5.0
    close_lot = 20
    open_lot = 8
    MAX_DISTANCE = 1024
    MAX_LEVEL = 4
    MIN_LEVEL = -4
    update_speed = 0.1
    spawn_time_start = 0
    spawn_time_end = 0
    current_day = 0
    timestamp = None
    routine_start_times = []
    _running = False
    _config_loaded = False
    live_update = False
    tag_sim_for_debugging = None
    exam_list = []
    roles = []
    career_function = None
    weather_function = None
    custom_routine = None
    head_of_household = None
    keep_sims_outside = False
    select_when_teleport = True
    sim_index = 0
    routine_sim_index = 0
    sim_tracker = {}
    wants_and_fears = False
    disable_tracking = False
    dont_sleep_on_lot = False
    current_trans_info = {}
    update_trans_info = {}
    update_trans_duration = 0.1
    update_trans_timestamp = None
    disabled_autonomy_list = []
    non_filtered_autonomy_list = []
    weather_values = []
    config_data_location = os.path.abspath(os.path.dirname(__file__))
    disable_forecasts = False

    def __init__(self):
        super().__init__()
