import configparser
import os

import services
import sims4
from date_and_time import create_time_span
from sims4.resources import Types
from weather.weather_enums import WeatherElementTuple, Temperature, WeatherEffectType, PrecipitationType, CloudType, \
    GroundCoverType
from weather.weather_service import get_street_or_region_id_with_weather_tuning

from scripts_core.sc_main import ScriptCoreMain
from scripts_core.sc_message_box import message_box
from scripts_core.sc_script_vars import sc_Vars, sc_Weather
from scripts_core.sc_util import error_trap


class sc_WeatherFunctions:
    def __init__(self):
        super().__init__()

    def add_weather(self, section, duration):
        add_weather(section, duration)

    def get_weather(self):
        get_weather()

    def load_weather(self):
        zone = services.current_zone()
        load_weather(zone)

    def weather_function(self, option, duration=1.0, instant=False):
        weather_function(option, duration, instant)


sc_Vars.weather_function = sc_WeatherFunctions()

def set_forecast_to_weather(weather):
    weather_service = services.weather_service()
    forecast_list = []
    forecast_manager = services.get_instance_manager(Types.WEATHER_FORECAST)
    for key in sims4.resources.list(type=Types.WEATHER_FORECAST):
        forecast = forecast_manager.get(key.instance)
        forecast_list.append(forecast)

    forecasts = [forecast for forecast in forecast_list if filter_forecast(forecast.__name__.lower(), weather)]

    if len(forecasts):
        street_or_region_id = get_street_or_region_id_with_weather_tuning()
        weather_service._weather_info[street_or_region_id]._forecasts.clear()
        weather_service._weather_info[street_or_region_id]._forecasts.append(forecasts[0])
        weather_service._send_ui_weather_message()
        weather_service._send_ui_weather_forecast()

def filter_forecast(forecast, weather):
    weather = weather.replace("weather_", "")
    forecast = forecast.replace("forecast_", "")
    weather = weather.replace("foggy", "fog")
    weather = weather.replace("stormy", "storm")
    weather = weather.replace("rainy", "rain")
    weather = weather.replace("snowy", "snow")
    weather = weather.replace("heavy_", "heavy")
    forecast = forecast.replace("heavy_", "heavy")
    weather = weather.replace("light_", "light")
    forecast = forecast.replace("light_", "light")
    weather = weather.replace("partly_", "partly")
    forecast = forecast.replace("partly_", "partly")
    forecast_words = forecast.split("_")
    weather_words = weather.split("_")
    all_words = set(forecast_words) & set(weather_words)
    if len(all_words) > 1 and len(all_words) >= len(forecast_words) - 1:
        return True
    return False

def weather_function(option, duration=1.0, instant=False):
    if not option:
        return
    build_weather(option, duration)
    weather_ini()
    if "weather" in option:
        selected_weather_list = [weather for weather in sc_Vars.weather_values if weather.title == option]
        if selected_weather_list:
            for weather in selected_weather_list:
                set_weather(weather, instant)
                set_forecast_to_weather(weather.title)


def set_weather(weather, instant=False):
    weather_service = services.weather_service()
    trans_info = {}
    now = services.time_service().sim_now
    current_temp = Temperature(int(weather.TEMPERATURE))
    end_time = now + create_time_span(hours=weather.duration)
    trans_info[int(WeatherEffectType.WIND)] = WeatherElementTuple(weather.WIND, now, 0.0, end_time)
    trans_info[int(WeatherEffectType.WATER_FROZEN)] = WeatherElementTuple(weather.WATER_FROZEN, now, 0.0, end_time)
    trans_info[int(WeatherEffectType.WINDOW_FROST)] = WeatherElementTuple(weather.WINDOW_FROST, now, 0.0, end_time)
    trans_info[int(WeatherEffectType.THUNDER)] = WeatherElementTuple(weather.THUNDER, now, 0.0, end_time)
    trans_info[int(WeatherEffectType.LIGHTNING)] = WeatherElementTuple(weather.LIGHTNING, now, 0.0, end_time)
    trans_info[int(PrecipitationType.SNOW)] = WeatherElementTuple(weather.SNOW, now, 0.0, end_time)
    trans_info[int(PrecipitationType.RAIN)] = WeatherElementTuple(weather.RAIN, now, 0.0, end_time)
    trans_info[int(CloudType.LIGHT_SNOWCLOUDS)] = WeatherElementTuple(weather.LIGHT_SNOWCLOUDS, now, 0.0, end_time)
    trans_info[int(CloudType.DARK_SNOWCLOUDS)] = WeatherElementTuple(weather.DARK_SNOWCLOUDS, now, 0.0, end_time)
    trans_info[int(CloudType.LIGHT_RAINCLOUDS)] = WeatherElementTuple(weather.LIGHT_RAINCLOUDS, now, 0.0, end_time)
    trans_info[int(CloudType.DARK_RAINCLOUDS)] = WeatherElementTuple(weather.DARK_RAINCLOUDS, now, 0.0, end_time)
    trans_info[int(CloudType.CLOUDY)] = WeatherElementTuple(weather.CLOUDY, now, 0.0, end_time)
    trans_info[int(CloudType.HEATWAVE)] = WeatherElementTuple(weather.HEATWAVE, now, 0.0, end_time)
    trans_info[int(CloudType.PARTLY_CLOUDY)] = WeatherElementTuple(weather.PARTLY_CLOUDY, now, 0.0, end_time)
    trans_info[int(CloudType.CLEAR)] = WeatherElementTuple(weather.CLEAR, now, 0.0, end_time)
    trans_info[int(GroundCoverType.SNOW_ACCUMULATION)] = WeatherElementTuple(weather.SNOW_ACCUMULATION, now, 0.0, end_time)
    trans_info[int(GroundCoverType.RAIN_ACCUMULATION)] = WeatherElementTuple(weather.RAIN_ACCUMULATION, now, 0.0, end_time)
    trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now, current_temp, end_time)
    trans_info[int(CloudType.SKYBOX_INDUSTRIAL)] = WeatherElementTuple(weather.SKYBOX_INDUSTRIAL, now, 0.0, end_time)
    trans_info[int(WeatherEffectType.SNOW_ICINESS)] = WeatherElementTuple(weather.SNOW_ICINESS, now, 0.0, end_time)
    trans_info[int(WeatherEffectType.SNOW_FRESHNESS)] = WeatherElementTuple(weather.SNOW_FRESHNESS, now, 0.0, end_time)

    if not instant:
        sc_Vars.update_trans_info = trans_info
        sc_Vars.update_trans_duration = weather.duration
    else:
        sc_Vars.update_trans_info = {}
        weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
        weather_service.start_weather_event(weather_event_manager.get(186636), weather.duration)
        weather_service._trans_info = trans_info
        weather_service._send_weather_event_op()


def build_weather(section, duration):
    try:
        datapath = sc_Vars.config_data_location
        filename = datapath + r"\Data\weather.ini"
        if not os.path.exists(filename):
            return
        config = configparser.ConfigParser()
        config.read(filename)
        if not config.has_section(section):
            config.add_section(section)

            config.set(section, "duration", str(duration))
            config.set(section, "WIND", "0.0")
            config.set(section, "WINDOW_FROST", "0.0")
            config.set(section, "WATER_FROZEN", "0.0")
            config.set(section, "THUNDER", "0.0")
            config.set(section, "LIGHTNING", "0.0")
            config.set(section, "TEMPERATURE", "0.0")
            config.set(section, "SNOW", "0.0")
            config.set(section, "SNOW_ACCUMULATION", "0.0")
            config.set(section, "RAIN", "0.0")
            config.set(section, "RAIN_ACCUMULATION", "0.0")
            config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
            config.set(section, "DARK_SNOWCLOUDS", "0.0")
            config.set(section, "LIGHT_RAINCLOUDS", "0.0")
            config.set(section, "DARK_RAINCLOUDS", "0.0")
            config.set(section, "CLOUDY", "0.0")
            config.set(section, "HEATWAVE", "0.0")
            config.set(section, "PARTLY_CLOUDY", "0.0")
            config.set(section, "CLEAR", "0.0")
            config.set(section, "SKYBOX_INDUSTRIAL", "0.0")
            config.set(section, "SNOW_ICINESS", "0.0")
            config.set(section, "SNOW_FRESHNESS", "0.0")

            if "awind" in section or "ahotwind" in section:
                config.set(section, "WIND", "0.5")
            elif "windstorm" in section:
                config.set(section, "WIND", "1.0")
            if "freezing" in section:
                config.set(section, "WINDOW_FROST", "1.0")
                config.set(section, "WATER_FROZEN", "1.0")
                config.set(section, "TEMPERATURE", "-3")
                config.set(section, "SNOW_ICINESS", "0.0")
                config.set(section, "SNOW_FRESHNESS", "0.0")
            elif "cold" in section:
                config.set(section, "TEMPERATURE", "-2")
            elif "cool" in section:
                config.set(section, "TEMPERATURE", "-1")
            elif "warm" in section:
                config.set(section, "TEMPERATURE", "0")
            elif "hot" in section:
                config.set(section, "TEMPERATURE", "1")
            elif "heatwave" in section:
                config.set(section, "TEMPERATURE", "2")
                config.set(section, "HEATWAVE", "1.0")
            if "thunder" in section:
                config.set(section, "WIND", "0.5")
                config.set(section, "THUNDER", "1.0")
                config.set(section, "LIGHTNING", "1.0")
            if "heavy_snow" in section or "snowstorm" in section:
                config.set(section, "SNOW", "1.0")
                config.set(section, "SNOW_ACCUMULATION", "-1.0")
                config.set(section, "LIGHT_SNOWCLOUDS", "1.0")
                config.set(section, "DARK_SNOWCLOUDS", "1.0")
                config.set(section, "LIGHT_RAINCLOUDS", "0.0")
                config.set(section, "DARK_RAINCLOUDS", "0.0")
            elif "light_snow" in section:
                config.set(section, "SNOW", "0.25")
                config.set(section, "SNOW_ACCUMULATION", "-0.25")
                config.set(section, "LIGHT_SNOWCLOUDS", "1.0")
                config.set(section, "DARK_SNOWCLOUDS", "1.0")
                config.set(section, "LIGHT_RAINCLOUDS", "0.0")
                config.set(section, "DARK_RAINCLOUDS", "0.0")
            elif "blizzard" in section:
                config.set(section, "WIND", "1.0")
                config.set(section, "SNOW", "1.0")
                config.set(section, "SNOW_ACCUMULATION", "-1.0")
                config.set(section, "LIGHT_SNOWCLOUDS", "1.0")
                config.set(section, "DARK_SNOWCLOUDS", "1.0")
                config.set(section, "LIGHT_RAINCLOUDS", "0.0")
                config.set(section, "DARK_RAINCLOUDS", "0.0")
            elif "snow" in section:
                config.set(section, "SNOW", "0.5")
                config.set(section, "SNOW_ACCUMULATION", "-0.5")
                config.set(section, "LIGHT_SNOWCLOUDS", "1.0")
                config.set(section, "DARK_SNOWCLOUDS", "1.0")
                config.set(section, "LIGHT_RAINCLOUDS", "0.0")
                config.set(section, "DARK_RAINCLOUDS", "0.0")
            elif "heavy_rain" in section or "thunderstorm" in section:
                config.set(section, "RAIN", "1.0")
                config.set(section, "RAIN_ACCUMULATION", "1.0")
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "0.0")
                config.set(section, "LIGHT_RAINCLOUDS", "1.0")
                config.set(section, "DARK_RAINCLOUDS", "1.0")
            elif "light_rain" in section:
                config.set(section, "RAIN", "0.25")
                config.set(section, "RAIN_ACCUMULATION", "0.25")
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "0.0")
                config.set(section, "LIGHT_RAINCLOUDS", "1.0")
                config.set(section, "DARK_RAINCLOUDS", "1.0")
            elif "drizzle" in section:
                config.set(section, "RAIN", "0.1")
                config.set(section, "RAIN_ACCUMULATION", "0.1")
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "0.0")
                config.set(section, "LIGHT_RAINCLOUDS", "1.0")
                config.set(section, "DARK_RAINCLOUDS", "1.0")
            elif "showers" in section or "monsoon" in section:
                config.set(section, "WIND", "0.5")
                config.set(section, "RAIN", "1.0")
                config.set(section, "RAIN_ACCUMULATION", "1.0")
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "0.0")
                config.set(section, "LIGHT_RAINCLOUDS", "1.0")
                config.set(section, "DARK_RAINCLOUDS", "1.0")
            elif "rain" in section:
                config.set(section, "RAIN", "0.5")
                config.set(section, "RAIN_ACCUMULATION", "0.5")
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "0.0")
                config.set(section, "LIGHT_RAINCLOUDS", "1.0")
                config.set(section, "DARK_RAINCLOUDS", "1.0")
            if "sunny" in section:
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "0.0")
                config.set(section, "LIGHT_RAINCLOUDS", "0.0")
                config.set(section, "DARK_RAINCLOUDS", "0.0")
                config.set(section, "CLOUDY", "0.0")
                config.set(section, "PARTLY_CLOUDY", "0.0")
                config.set(section, "CLEAR", "1.0")
            elif "fog" in section:
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "1.01")
                config.set(section, "LIGHT_RAINCLOUDS", "0.0")
                config.set(section, "DARK_RAINCLOUDS", "0.0")
                config.set(section, "CLOUDY", "0.1")
                config.set(section, "PARTLY_CLOUDY", "0.0")
                config.set(section, "CLEAR", "0.0")
            elif "june_gloom" in section:
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "0.5")
                config.set(section, "LIGHT_RAINCLOUDS", "0.5")
                config.set(section, "DARK_RAINCLOUDS", "0.0")
                config.set(section, "CLOUDY", "0.0")
                config.set(section, "PARTLY_CLOUDY", "0.0")
                config.set(section, "CLEAR", "0.0")
            elif "partly" in section:
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "0.0")
                config.set(section, "LIGHT_RAINCLOUDS", "0.0")
                config.set(section, "DARK_RAINCLOUDS", "0.0")
                config.set(section, "CLOUDY", "0.0")
                config.set(section, "PARTLY_CLOUDY", "1.0")
                config.set(section, "CLEAR", "0.0")
            elif "cloudy" in section:
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "1.0")
                config.set(section, "LIGHT_RAINCLOUDS", "0.0")
                config.set(section, "DARK_RAINCLOUDS", "0.0")
                config.set(section, "CLOUDY", "0.25")
            if "city" in section:
                config.set(section, "SKYBOX_INDUSTRIAL", "0.25")
                config.set(section, "SNOW_ICINESS", "0.0")
                config.set(section, "SNOW_FRESHNESS", "0.25")

            with open(filename, 'w') as configfile:
                config.write(configfile)

    except BaseException as e:
        error_trap(e)


def add_weather(section, duration):
    try:
        trans_type = [info for info in WeatherEffectType]
        trans_type = trans_type + [info for info in CloudType]
        trans_type = trans_type + [info for info in PrecipitationType]
        trans_type = trans_type + [info for info in GroundCoverType]

        weather_service = services.weather_service()
        now = services.time_service().sim_now
        datapath = sc_Vars.config_data_location
        filename = datapath + r"\Data\weather.ini"
        if not os.path.exists(filename):
            return
        config = configparser.ConfigParser()
        config.read(filename)
        if not config.has_section(section):
            config.add_section(section)

        config.set(section, "duration", str(duration))
        config.set(section, "WIND", "0.0")
        config.set(section, "WINDOW_FROST", "0.0")
        config.set(section, "WATER_FROZEN", "0.0")
        config.set(section, "THUNDER", "0.0")
        config.set(section, "LIGHTNING", "0.0")
        config.set(section, "TEMPERATURE", "0.0")
        config.set(section, "SNOW", "0.0")
        config.set(section, "SNOW_ACCUMULATION", "0.0")
        config.set(section, "RAIN", "0.0")
        config.set(section, "RAIN_ACCUMULATION", "0.0")
        config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
        config.set(section, "DARK_SNOWCLOUDS", "0.0")
        config.set(section, "LIGHT_RAINCLOUDS", "0.0")
        config.set(section, "DARK_RAINCLOUDS", "0.0")
        config.set(section, "CLOUDY", "0.0")
        config.set(section, "HEATWAVE", "0.0")
        config.set(section, "PARTLY_CLOUDY", "0.0")
        config.set(section, "CLEAR", "0.0")
        config.set(section, "SKYBOX_INDUSTRIAL", "0.0")
        config.set(section, "SNOW_ICINESS", "0.0")
        config.set(section, "SNOW_FRESHNESS", "0.0")

        for key, value in weather_service._trans_info.items():
            current_value = weather_service.get_weather_element_value(int(key), now)
            data = weather_service._trans_info.get(int(key), None)
            if data:
                names = [info for info in trans_type if int(key) == int(info)]
                if names:
                    for name in names:
                        part = str(name).split(".")
                        if len(part) > 1:
                            start_value = current_value
                            if "temperature" in str(name).lower():
                                start_value = int(current_value)
                            config.set(section, str(part[1]), str(start_value))

        with open(filename, 'w') as configfile:
            config.write(configfile)
    except BaseException as e:
        error_trap(e)

def get_weather():
    try:
        font_color1 = "000000"
        font_text1 = "<font color='#{}'>".format(font_color1)
        end_font_text = "</font>"

        trans_type = [info for info in WeatherEffectType]
        trans_type = trans_type + [info for info in CloudType]
        trans_type = trans_type + [info for info in PrecipitationType]
        trans_type = trans_type + [info for info in GroundCoverType]

        weather_service = services.weather_service()
        now = services.time_service().sim_now
        current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
        weather_info = ""
        weather_info = weather_info + "[TEMPERATURE]: {}\n".format(Temperature(current_temp))
        weather_info = weather_info + "[Icy Conditions]: {}\n".format(weather_service._icy_conditions_option)
        if len(sc_Vars.update_trans_info):
            weather_info = weather_info + "[Weather Transition Running]: True"

        for key, value in weather_service._trans_info.items():
            current_value = weather_service.get_weather_element_value(int(key), now)
            data = weather_service._trans_info.get(int(key), None)
            if data:
                names = [info for info in trans_type if int(key) == int(info)]
                if names:
                    for name in names:
                        part = str(name).split(".")
                        if len(part) > 1:
                            if not "temperature" in part[1].lower():
                                start_value = float(current_value)
                                weather_info = weather_info + "[{}]: {:0.6}\n".format(str(part[1]), start_value)

        weather, forecast = get_weather_names()
        if weather:
            weather_info = weather_info + "\n[Forecast]: {}\n Picked weather for forecast...\n[Weather]: {}\n\n".format(forecast, weather)
        weather, forecast, words, filter = get_weather_names_from_weather(False)
        weather_info = weather_info + "[Forecast]: {}\n Weather from conditions...\n[Weather]: {}\n[Words Used:] {}\n[Filter:] {}".format(forecast, weather, str(words), filter)
        weather_info = weather_info.replace("[", font_text1).replace("]", end_font_text)
        message_box(None, None, "Weather Info", weather_info)

    except BaseException as e:
        error_trap(e)

def get_weather_names():
    street_or_region_id = get_street_or_region_id_with_weather_tuning()
    if len(services.weather_service()._weather_info[street_or_region_id]._forecasts):
        forecast_tuning = services.weather_service()._weather_info[street_or_region_id]._forecasts[0]
    else:
        return None, None
    forecast = str(forecast_tuning.__name__).lower().replace("forecast_", "")
    weather = "weather_" + forecast
    return weather, forecast

def get_weather_names_from_weather(set_weather=True, instant=False):
    datapath = sc_Vars.config_data_location
    filename = datapath + r"\Data\weather.ini"
    if not os.path.exists(filename):
        return
    config = configparser.ConfigParser()
    config.read(filename)

    weather_list = config.sections()

    weather_service = services.weather_service()
    trans_type = [info for info in WeatherEffectType]
    trans_type = trans_type + [info for info in CloudType]
    trans_type = trans_type + [info for info in PrecipitationType]
    trans_type = trans_type + [info for info in GroundCoverType]

    now = services.time_service().sim_now

    words = []
    for key, value in weather_service._trans_info.items():
        current_value = weather_service.get_weather_element_value(int(key), now)
        data = weather_service._trans_info.get(int(key), None)
        if data:
            names = [info for info in trans_type if int(key) == int(info)]
            if names:
                for name in names:
                    part = str(name).split(".")
                    if len(part) > 1:
                        weather_label = str(part[1]).lower()
                        if "skybox_industrial" in weather_label and "city" not in str(words) and current_value > 0:
                            words.append("city")
                        if "wind" in weather_label and "window_frost" not in weather_label and "wind" not in str(words) and current_value > 0:
                            words.append("wind")
                        if "partly" in weather_label and "cloudy" not in str(words) and current_value > 0:
                            words.append("cloudy")
                            words.append("partly")
                        if "dark_snowclouds" in weather_label and "fog" not in str(words) and current_value > 1:
                            words.append("fog")
                        if "cloud" in weather_label and "partly" not in weather_label and "cloudy" not in str(words) and "fog" not in str(words) and current_value > 0:
                            words.append("cloudy")
                        if "clear" in weather_label and "sunny" not in str(words) and current_value > 0:
                            words.append("sunny")
                        if "thunder" in weather_label and "thunder" not in str(words) and "rain" not in str(words) and current_value > 0:
                            words.append("thunder")
                        if "snow" in weather_label and "snow" not in str(words) and current_value > 0.9:
                            words.append("snow")
                            words.append("heavy")
                        if "snow" in weather_label and "snow" not in str(words) and current_value > 0.1:
                            words.append("snow")
                            words.append("light")
                        if "snow" in weather_label and "snow" not in str(words) and current_value > 0:
                            words.append("snow")
                        if "rain" in weather_label and "rain" not in str(words) and "showers" not in str(words) and "drizzle" not in str(words) and current_value > 0.9:
                            words.append("rain")
                            words.append("heavy")
                        if "showers" in weather_label and "rain" not in str(words) and "showers" not in str(words) and "drizzle" not in str(words) and current_value > 0.9:
                            words.append("showers")
                        if "drizzle" in weather_label and "rain" not in str(words) and "showers" not in str(words) and "drizzle" not in str(words) and current_value > 0.1:
                            words.append("drizzle")
                        if "rain" in weather_label and "rain" not in str(words) and "showers" not in str(words) and "drizzle" not in str(words) and current_value > 0.1:
                            words.append("rain")
                            words.append("light")
                        if "rain" in weather_label and "rain" not in str(words) and "showers" not in str(words) and "drizzle" not in str(words) and current_value > 0:
                            words.append("rain")

    if not len(words):
        words.append("cloudy")
        words.append("partly")
    current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
    if "freezing" not in str(words) and current_temp == Temperature.FREEZING:
        words.append("freezing")
    elif "cold" not in str(words) and current_temp == Temperature.COLD:
        words.append("cold")
    elif "cool" not in str(words) and current_temp == Temperature.COOL:
        words.append("cool")
    elif "warm" not in str(words) and current_temp == Temperature.WARM:
        words.append("warm")
    elif "hot" not in str(words) and current_temp == Temperature.HOT:
        words.append("hot")
    elif "heatwave" not in str(words) and current_temp == Temperature.BURNING:
        words.append("heatwave")

    weather, forecast = get_weather_names()
    weathers = [weather for weather in weather_list if filter_by_words(weather, words)]
    if not weathers:
        weathers = [weather for weather in weather_list if filter_by_words(weather, words, 1)]
    if weathers:
        for weather in weathers:
            if set_weather:
                weather_function(weather, 120, instant)
                w, forecast = get_weather_names()
            return weather, forecast, words, True
    if set_weather:
        weather_function(weather, 120, instant)
    return weather, forecast, words, False

def filter_by_words(label, words, precision=0):
    label = label.replace("weather_", "")
    label = label.replace("forecast_", "")
    label_words = label.split("_")
    check = [word for word in words if word in str(label_words)]
    if len(check) and len(check) == len(words)-precision:
        return True
    return False

def weather_ini(weather_choices=()):
    try:
        weather_choices = weather_choices + ("Reset Weather",)
        weather_choices = weather_choices + ("Modify Weather",)
        weather_choices = weather_choices + ("Save Weather",)
        weather_choices = weather_choices + ("Get Forecast",)
        sc_Vars.weather_values = []
        datapath = sc_Vars.config_data_location
        filename = datapath + r"\Data\weather.ini"
        if not os.path.exists(filename):
            return
        config = configparser.ConfigParser()
        config.read(filename)

        for each_section in config.sections():
            duration = config.getfloat(each_section, "duration")
            wind = config.getfloat(each_section, "WIND")
            window_frost = config.getfloat(each_section, "WINDOW_FROST")
            water_frozen = config.getfloat(each_section, "WATER_FROZEN")
            thunder = config.getfloat(each_section, "THUNDER")
            lightning = config.getfloat(each_section, "LIGHTNING")
            temperature = config.getfloat(each_section, "TEMPERATURE")
            snow = config.getfloat(each_section, "SNOW")
            snow_accumulation = config.getfloat(each_section, "SNOW_ACCUMULATION")
            rain = config.getfloat(each_section, "RAIN")
            rain_accumulation = config.getfloat(each_section, "RAIN_ACCUMULATION")
            light_snowclouds = config.getfloat(each_section, "LIGHT_SNOWCLOUDS")
            dark_snowclouds = config.getfloat(each_section, "DARK_SNOWCLOUDS")
            light_rainclouds = config.getfloat(each_section, "LIGHT_RAINCLOUDS")
            dark_rainclouds = config.getfloat(each_section, "DARK_RAINCLOUDS")
            cloudy = config.getfloat(each_section, "CLOUDY")
            heatwave = config.getfloat(each_section, "HEATWAVE")
            partly_cloudy = config.getfloat(each_section, "PARTLY_CLOUDY")
            clear = config.getfloat(each_section, "CLEAR")
            skybox_industrial = config.getfloat(each_section, "SKYBOX_INDUSTRIAL")
            snow_iciness = config.getfloat(each_section, "SNOW_ICINESS")
            snow_freshness = config.getfloat(each_section, "SNOW_FRESHNESS")

            weather_choices = weather_choices + (each_section,)
            sc_Vars.weather_values.append(sc_Weather(each_section,
                                              duration,
                                              wind,
                                              window_frost,
                                              water_frozen,
                                              thunder,
                                              lightning,
                                              temperature,
                                              snow,
                                              snow_accumulation,
                                              rain,
                                              rain_accumulation,
                                              light_snowclouds,
                                              dark_snowclouds,
                                              light_rainclouds,
                                              dark_rainclouds,
                                              cloudy,
                                              heatwave,
                                              partly_cloudy,
                                              clear,
                                              skybox_industrial,
                                              snow_iciness,
                                              snow_freshness))
    except BaseException as e:
        error_trap(e)

def load_weather(zone):
    ScriptCoreMain.config_ini(zone)
    weather_ini()
    set_weather_by_zone(zone, True)

def set_weather_by_zone(zone, instant=False):
    zone_id = zone.id
    datapath = sc_Vars.config_data_location
    filename = datapath + r"\Data\zones.ini"
    if not os.path.exists(filename):
        return
    config = configparser.ConfigParser()
    config.read(filename)
    if config.has_section(str(zone_id)):
        if config.has_option(str(zone_id), "weather"):
            weather = config.get(str(zone_id), "weather")
            weather_function(weather, 120.0, True)
            return
        if config.has_option(str(zone_id), "use_forecast"):
            use_forecast = config.getboolean(str(zone_id), "use_forecast")
            if use_forecast:
                services.weather_service().reset_forecasts(False)
                weather, forecast = get_weather_names()
                if weather:
                    weather_function(weather, 120.0, True)
                return

    if config.has_section("global"):
        if config.has_option("global", "weather"):
            weather = config.get("global", "weather")
            weather_function(weather, 120.0, True)
            return
        if config.has_option("global", "use_forecast"):
            use_forecast = config.getboolean("global", "use_forecast")
            if use_forecast:
                services.weather_service().reset_forecasts(False)
                weather, forecast = get_weather_names()
                if weather:
                    weather_function(weather, 120.0, True)
                return

    if not sc_Vars.disable_forecasts:
        weather, forecast = get_weather_names()
        if weather:
            weather_function(weather, 120, instant)
            return

    get_weather_names_from_weather(True, instant)

def update_weather(weather):
    try:
        now = services.time_service().sim_now
        duration = sc_Vars.update_trans_duration
        if not sc_Vars.update_trans_timestamp:
            sc_Vars.update_trans_timestamp = now + create_time_span(hours=duration)
        if len(sc_Vars.update_trans_info):
            sc_Vars.current_trans_info = weather._trans_info
            end_time = now + create_time_span(minutes=10)
            sc_Vars.update_trans_timestamp = now + create_time_span(hours=duration)
            weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
            weather.start_weather_event(weather_event_manager.get(186636), duration)
            for weather_element in sc_Vars.update_trans_info:
                current_value = weather.get_weather_element_value(weather_element, now)
                new_data = sc_Vars.update_trans_info.get(weather_element, None)
                #debugger("{} {}".format(weather_element, current_value))
                if weather_element == 1007:
                    weather._trans_info[int(weather_element)] = WeatherElementTuple(Temperature(int(new_data.start_value)), now, Temperature(int(new_data.start_value)), end_time)
                elif new_data:
                    weather._trans_info[int(weather_element)] = WeatherElementTuple(current_value, now, new_data.start_value, end_time)
                else:
                    weather._trans_info[int(weather_element)] = WeatherElementTuple(0, now, 0, end_time)

            weather._send_weather_event_op()
            sc_Vars.update_trans_info = {}

    except BaseException as e:
        error_trap(e)
        sc_Vars.update_trans_info = {}
        sc_Vars.current_trans_info = {}
        pass

