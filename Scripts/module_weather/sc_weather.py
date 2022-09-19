import configparser
import os

import services
from date_and_time import create_time_span
from distributor.system import Distributor
from protocolbuffers import WeatherSeasons_pb2
from sims4.resources import Types
from weather.weather_enums import WeatherElementTuple, Temperature, WeatherEffectType, PrecipitationType, CloudType, \
    GroundCoverType
from weather.weather_ops import WeatherEventOp
from weather.weather_service import WeatherService, get_street_or_region_id_with_weather_tuning


from scripts_core.sc_debugger import debugger
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


sc_Vars.weather_function = sc_WeatherFunctions()

def weather_function(option, duration=1.0, instant=False):
    build_weather(option, duration)
    weather_ini()
    if "weather" in option:
        selected_weather_list = [weather for weather in sc_Vars.weather_values if weather.title == option]
        if selected_weather_list:
            for weather in selected_weather_list:
                set_weather(weather, instant)


def set_weather(weather, instant=False):
    weather_service = services.weather_service()
    trans_info = {}
    now = services.time_service().sim_now
    current_temp = Temperature(int(weather.TEMPERATURE))
    end_time = now + create_time_span(hours=weather.duration)
    trans_info[int(WeatherEffectType.WIND)] = WeatherElementTuple(weather.WIND, now, 0.0, end_time)
    trans_info[int(WeatherEffectType.WATER_FROZEN)] = WeatherElementTuple(weather.WATER_FROZEN, now,
                                                                          weather.WATER_FROZEN, end_time)
    trans_info[int(WeatherEffectType.WINDOW_FROST)] = WeatherElementTuple(weather.WINDOW_FROST, now,
                                                                          weather.WINDOW_FROST, end_time)
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
    trans_info[int(GroundCoverType.SNOW_ACCUMULATION)] = WeatherElementTuple(weather.SNOW_ACCUMULATION, now,
                                                                             weather.SNOW_ACCUMULATION, end_time)
    trans_info[int(GroundCoverType.RAIN_ACCUMULATION)] = WeatherElementTuple(weather.RAIN_ACCUMULATION, now,
                                                                             weather.RAIN_ACCUMULATION, end_time)
    trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now, current_temp, end_time)
    trans_info[int(CloudType.SKYBOX_INDUSTRIAL)] = WeatherElementTuple(weather.SKYBOX_INDUSTRIAL, now,
                                                                       weather.SKYBOX_INDUSTRIAL, end_time)
    trans_info[int(WeatherEffectType.SNOW_ICINESS)] = WeatherElementTuple(weather.SNOW_ICINESS, now,
                                                                          weather.SNOW_ICINESS, end_time)
    trans_info[int(WeatherEffectType.SNOW_FRESHNESS)] = WeatherElementTuple(weather.SNOW_FRESHNESS, now,
                                                                            weather.SNOW_FRESHNESS, end_time)
    if not instant:
        sc_Vars.update_trans_info = trans_info
        sc_Vars.update_trans_duration = weather.duration
    else:
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
            config.set(section, "SNOW_ACCUMULATION", "1.0")
            config.set(section, "LIGHT_SNOWCLOUDS", "1.0")
            config.set(section, "DARK_SNOWCLOUDS", "1.0")
            config.set(section, "LIGHT_RAINCLOUDS", "0.0")
            config.set(section, "DARK_RAINCLOUDS", "0.0")
        elif "light_snow" in section:
            config.set(section, "SNOW", "0.25")
            config.set(section, "SNOW_ACCUMULATION", "0.25")
            config.set(section, "LIGHT_SNOWCLOUDS", "1.0")
            config.set(section, "DARK_SNOWCLOUDS", "1.0")
            config.set(section, "LIGHT_RAINCLOUDS", "0.0")
            config.set(section, "DARK_RAINCLOUDS", "0.0")
        elif "blizzard" in section:
            config.set(section, "WIND", "1.0")
            config.set(section, "SNOW", "1.0")
            config.set(section, "SNOW_ACCUMULATION", "1.0")
            config.set(section, "LIGHT_SNOWCLOUDS", "1.0")
            config.set(section, "DARK_SNOWCLOUDS", "1.0")
            config.set(section, "LIGHT_RAINCLOUDS", "0.0")
            config.set(section, "DARK_RAINCLOUDS", "0.0")
        elif "snow" in section:
            config.set(section, "SNOW", "0.5")
            config.set(section, "SNOW_ACCUMULATION", "0.5")
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
            config.set(section, "LIGHT_SNOWCLOUDS", "0.5")
            config.set(section, "DARK_SNOWCLOUDS", "0.5")
            config.set(section, "LIGHT_RAINCLOUDS", "0.5")
            config.set(section, "DARK_RAINCLOUDS", "0.5")
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
        weather_info = ""

        for key, value in weather_service._trans_info.items():
            current_value = weather_service.get_weather_element_value(int(key), now)
            data = weather_service._trans_info.get(int(key), None)
            if data:
                names = [info for info in trans_type if int(key) == int(info)]
                if names:
                    for name in names:
                        part = str(name).split(".")
                        if len(part) > 1:
                            if "temperature" in str(value.start_value).lower():
                                start_value = int(current_value)
                                weather_info = weather_info + "[{}]: {}\n".format(str(part[1]), start_value)
                            else:
                                start_value = float(current_value)
                                weather_info = weather_info + "[{}]: {:0.6}\n".format(str(part[1]), start_value)

        weather_info = weather_info.replace("[", font_text1).replace("]", end_font_text)
        message_box(None, None, "Weather Info", weather_info)

    except BaseException as e:
        error_trap(e)

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

def load_weather(self):
    ScriptCoreMain.config_ini(self)
    weather_ini()
    if not sc_Vars.disable_forecasts:
        street_or_region_id = get_street_or_region_id_with_weather_tuning()
        forecasts = services.weather_service()._weather_info[street_or_region_id]._forecasts
        forecast_name = "weather_" + str(forecasts[0]).lower().replace("<class 'sims4.tuning.instances.forecast_", "").replace("'>", "")
        debugger("Region: {} Forecast: {}".format(street_or_region_id, forecast_name))
        weather_function(forecast_name)

def update_weather(self):
    try:
        now = services.time_service().sim_now
        duration = sc_Vars.update_trans_duration
        if not sc_Vars.update_trans_timestamp:
            sc_Vars.update_trans_timestamp = now + create_time_span(hours=duration)
        if len(sc_Vars.update_trans_info):
            sc_Vars.current_trans_info = self._trans_info
            end_time = now + create_time_span(minutes=10)
            sc_Vars.update_trans_timestamp = now + create_time_span(hours=duration)
            weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
            self.start_weather_event(weather_event_manager.get(186636), duration)
            for weather_element in sc_Vars.update_trans_info:
                current_data = self._trans_info.get(int(weather_element), None)
                new_data = sc_Vars.update_trans_info.get(int(weather_element), None)
                if weather_element == 1007:
                    self._trans_info[int(weather_element)] = WeatherElementTuple(Temperature(int(new_data.start_value)), now, Temperature(int(new_data.start_value)), end_time)
                elif current_data:
                    self._trans_info[int(weather_element)] = WeatherElementTuple(current_data.start_value, now, new_data.start_value, end_time)
                else:
                    self._trans_info[int(weather_element)] = WeatherElementTuple(0, now, new_data.start_value, end_time)
            self._send_weather_event_op()
            sc_Vars.update_trans_info = {}

    except BaseException as e:
        error_trap(e)
        sc_Vars.update_trans_info = {}
        sc_Vars.current_trans_info = {}
        pass

def send_weather_event_op(self, update_keytimes=True):
    if self._trans_info:
        messages_to_remove = []
        self._last_op = WeatherSeasons_pb2.SeasonWeatherInterpolations()
        op = WeatherEventOp(self._last_op)
        for message_type, data in self._trans_info.items():
            op.populate_op(message_type, data.start_value, data.start_time, data.end_value, data.end_time)
            if data.start_value == data.end_value == 0.0 and message_type != 1007:
                messages_to_remove.append(message_type)

        Distributor.instance().add_op_with_no_owner(op)
        for message_type in messages_to_remove:
            del self._trans_info[message_type]

    if update_keytimes:
        self._update_keytimes()


WeatherService._send_weather_event_op = send_weather_event_op
