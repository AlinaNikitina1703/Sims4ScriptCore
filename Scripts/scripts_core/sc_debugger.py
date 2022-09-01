import inspect
import os
import re

import services
import sims4

from scripts_core.sc_message_box import message_box


def debugger(debug_text, frame=1, full_frame=False, write=True, to_console=True, popup=False, file=""):
    # 0 is root function info, 1 is function info from where its running and 2 is parent calling function
    font_color1 = "ffff00"
    font_color2 = "000000"
    font_color3 = "660000"
    font_text1 = "<font color='#{}'>".format(font_color1)
    font_text2 = "<font color='#{}'>".format(font_color2)
    font_text3 = "<font color='#{}'>".format(font_color3)
    end_font_text = "</font>"

    if file:
        file = os.path.basename(file)

    now = services.time_service().sim_now
    total_stack = inspect.stack()  # total complete stack
    func_name = None
    filename = None
    line_number = 0
    if popup:
        debug_text = debug_text.replace("File", font_text3).replace(", in", end_font_text)
        debug_text = debug_text.replace("[", font_text1).replace("]", end_font_text)
        debug_text = debug_text.replace("(", font_text2).replace(")", end_font_text)
    if frame:
        frameinfo = total_stack[int(frame)][0]  # info on rel frame
        func_name = frameinfo.f_code.co_name
        filename = os.path.basename(frameinfo.f_code.co_filename)
        line_number = frameinfo.f_lineno  # of the call

    debug_text = "\n{}\n".format(now) + debug_text
    if full_frame and not frame:
        for stack in total_stack:
            frameinfo = stack[0]
            func_name = frameinfo.f_code.co_name
            filename = os.path.basename(frameinfo.f_code.co_filename)
            line_number = frameinfo.f_lineno
            if popup and file in filename and file:
                debug_text = debug_text + font_text1
            elif popup:
                debug_text = debug_text + font_text2
            debug_text = debug_text + "\n@{} - {} - {}".format(line_number, filename, func_name)
            if popup:
                debug_text = debug_text + end_font_text
    elif full_frame and frame:
        for f in range(1, frame+1, 1):
            frameinfo = total_stack[int(f)][0]  # info on rel frame
            func_name = frameinfo.f_code.co_name
            filename = os.path.basename(frameinfo.f_code.co_filename)
            line_number = frameinfo.f_lineno
            if popup and file in filename and file:
                debug_text = debug_text + font_text1
            elif popup:
                debug_text = debug_text + font_text2
            debug_text = debug_text + "\n@{} - {} - {}".format(line_number, filename, func_name)
            if popup:
                debug_text = debug_text + end_font_text
    elif frame:
        debug_text = debug_text + "\n@{} - {} - {}".format(line_number, filename, func_name)
    if popup:
        message_box(None, None, "Error!", debug_text, "ORANGE")
        clean = re.compile('<.*?>')
        debug_text = re.sub(clean, '', debug_text)
    if write:
        datapath = os.path.abspath(os.path.dirname(__file__))
        filename = datapath + r"\{}.log".format("debugger")
        if os.path.exists(filename):
            append_write = 'a'  # append if already exists
        else:
            append_write = 'w'  # make a new file if not
        file = open(filename, append_write)
        file.write("\n{}".format(debug_text))
        file.close()
    if to_console:
        client = services.client_manager().get_first_client()
        sims4.commands.cheat_output(debug_text, client.id)
