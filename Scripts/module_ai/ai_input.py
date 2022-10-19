import services
import sims4.commands
from module_ai.ai_util import ld_notice
from sims4.collections import AttributeDict
from sims4.localization import LocalizationHelperTuning
from sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit
from ui.ui_dialog import UiDialog, UiDialogOkCancel
from ui.ui_dialog_generic import UiDialogTextInputOkCancel
from ui.ui_text_input import UiTextInput


class Input_TextInputLength(HasTunableSingletonFactory, AutoFactoryInit):
    __qualname__ = 'Input_TextInputLength'

    def build_msg(self, dialog, msg, *additional_tokens):
        msg.max_length = 9999
        msg.min_length = 0
        msg.input_too_short_tooltip = LocalizationHelperTuning.get_raw_text("")

class DialogTestUiDialogTextInput(UiDialog):
    __qualname__ = 'DialogTestUiDialogTextInput'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text_input_responses = {}

    def on_text_input(self, text_input_name='', text_input=''):
        self.text_input_responses[text_input_name] = text_input
        return False

    def build_msg(self, text_input_overrides=None, additional_tokens=(), **kwargs):
        msg = super().build_msg(additional_tokens=additional_tokens, **kwargs)
        text_input_msg1 = msg.text_input.add()
        text_input_msg1.text_input_name = "userinput"
        text_input_msg1.initial_value = LocalizationHelperTuning.get_raw_text("")
        return msg

class DialogTestUiDialogTextInputOkCancel(UiDialogOkCancel, DialogTestUiDialogTextInput):
    __qualname__ = 'DialogTestUiDialogTextInputOkCancel'

##
## Get input from user dialog test
##
def inputbox(title: str, text: str, callback, initial_value: str = ""):
    input_text = ""
    def inputbox_callback(dialog):
        if dialog.accepted:
            input_text = dialog.text_input_responses.get("search_terms")
            callback(input_text)
        else:
            return
    client = services.client_manager().get_first_client()

    text_input = UiTextInput(sort_order=0, restricted_characters=None)
    text_input.default_text = None
    text_input.title = None
    text_input.max_length = 9999
    text_input.initial_value = lambda **_: LocalizationHelperTuning.get_raw_text(initial_value)
    text_input.check_profanity = False
    text_input.length_restriction = Input_TextInputLength()
    text_input.height = None

    inputs = AttributeDict({'search_terms': text_input})

    dialog = UiDialogTextInputOkCancel.TunableFactory().default(client.active_sim,
        text=lambda **_: LocalizationHelperTuning.get_raw_text(text),
        title=lambda **_: LocalizationHelperTuning.get_raw_text(title),
        text_inputs=inputs)

    dialog.add_listener(inputbox_callback)
    dialog.show_dialog()

def get_input_callback(input_str):
    client = services.client_manager().get_first_client()
    sim_info = client.active_sim.sim_info
    ld_notice(sim_info,"get_input_callback", input_str)
##
## Ok/Cancel dialog test
##
@sims4.commands.Command('dialogtest.okcancel',  command_type=sims4.commands.CommandType.Live)
def okcancelbox(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    def okcancelbox_callback(dialog):
        if dialog.accepted:
            output("User pressed OK")
        else:
            output("User pressed CANCEL")
    title = "Dialog Test 1"
    text = "Please press OK to continue, or Cancel."
    client = services.client_manager().get_first_client()
    dialog = UiDialogOkCancel.TunableFactory().default(client.active_sim, text=lambda **_: LocalizationHelperTuning.get_raw_text(text), title=lambda **_: LocalizationHelperTuning.get_raw_text(title))
    dialog.add_listener(okcancelbox_callback)
    dialog.show_dialog()