import services
from clock import ClockSpeedMode
from zone import Zone

from module_weather.sc_weather import update_weather, load_weather
from scripts_core.sc_inject import safe_inject
from scripts_core.sc_util import error_trap


@safe_inject(Zone, 'update')
def sc_weather_zone_update_module(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    try:
        is_paused = services.game_clock_service().clock_speed == ClockSpeedMode.PAUSED
        if not is_paused:
            weather_service = services.weather_service()
            update_weather(weather_service)
    except BaseException as e:
        error_trap(e)
        pass

    return result

@safe_inject(Zone, 'on_loading_screen_animation_finished')
def sc_weather_zone_load_module(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    try:
        load_weather(self)
    except BaseException as e:
        error_trap(e)
        pass

    return result