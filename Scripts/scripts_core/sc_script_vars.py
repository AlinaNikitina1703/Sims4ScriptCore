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

class sc_Weather:
    def __init__(self, title=None,
                duration=120,
                wind_speed=0.0,
                window_frost=0.0,
                water_frozen=0.0,
                thunder=0.0,
                lightning=0.0,
                temperature=0,
                snow_amount=0.0,
                snow_depth=0.0,
                rain_amount=0.0,
                rain_depth=0.0,
                light_clouds=0.0,
                dark_clouds=0.0,
                light_clouds2=0.0,
                dark_clouds2=0.0,
                cloudy=0.0,
                heatwave=0.0,
                partly_cloudy=1.0,
                clear=0.0):

        super().__init__()
        self.title = title
        self.duration = duration
        self.wind_speed = wind_speed
        self.window_frost = window_frost
        self.water_frozen = water_frozen
        self.thunder = thunder
        self.lightning = lightning
        self.temperature = temperature
        self.snow_amount = snow_amount
        self.snow_depth = snow_depth
        self.rain_amount = rain_amount
        self.rain_depth = rain_depth
        self.light_clouds = light_clouds
        self.dark_clouds = dark_clouds
        self.light_clouds2 = light_clouds2
        self.dark_clouds2 = dark_clouds2
        self.cloudy = cloudy
        self.heatwave = heatwave
        self.partly_cloudy = partly_cloudy
        self.clear = clear

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
    custom_routine = None

    def __init__(self):
        super().__init__()