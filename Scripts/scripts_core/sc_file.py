import ast
import configparser
import os

from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import error_trap


def get_config(filename, section, option):
    try:
        datapath = sc_Vars.config_data_location
        filename = datapath + r"\Data\{}".format(filename)
        if not os.path.exists(filename):
            return None
        config = configparser.ConfigParser()
        config.read(filename)
        if config.has_section(section):
            if config.has_option(section, option):
                value = ast.literal_eval(config.get(section, option))
                if type(value) is bool:
                    return config.getboolean(section, option)
                elif type(value) is int:
                    return config.getint(section, option)
                elif type(value) is float:
                    return config.getfloat(section, option)
                elif type(value) is list:
                    return value
                elif type(value) is dir:
                    return list(value)
                elif type(value) is tuple:
                    return value
                else:
                    return config.get(section, option)
        return None

    except BaseException as e:
        error_trap(e)

def set_config(filename, section, option, value):
    try:
        datapath = sc_Vars.config_data_location
        filename = datapath + r"\Data\{}".format(filename)
        config = configparser.ConfigParser()
        if not os.path.exists(filename):
            with open(filename, 'w') as configfile:
                config.write(configfile)
        config.read(filename)
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, option, str(value))
        with open(filename, 'w') as configfile:
            config.write(configfile)
    except BaseException as e:
        error_trap(e)