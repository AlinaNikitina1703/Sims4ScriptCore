import string

import sims4.commands
import services
from scripts_core.sc_util import ld_notice
from sims4.collections import AttributeDict
from sims4.localization import LocalizationHelperTuning
from sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit
from ui.ui_dialog import UiDialog, UiDialogOk, UiDialogOkCancel
from ui.ui_dialog_generic import UiDialogTextInputOkCancel
from ui.ui_text_input import UiTextInput


class JargonKeys(object):
    BANG = '!'
    SHRIEK = '!'
    DOUBLE_QUOTE = '"'
    QUOTE = '"'
    NUMBER_SIGN = '#'
    SHARP = '#'
    OCTOTHORPE = '#'
    BUCK = '$'
    CASH = '$'
    STRING = '$'
    MOD = '%'
    GRAPES = '%'
    AMPERSAND = '&'
    AMP = '&'
    AND_SIGN = '&'
    APOSTROPHE = '\''
    PRIME = '\''
    TICK = '\''
    STAR = '*'
    SPLAT = '*'
    GLOB = '*'
    ADD = '+'


class IntercalKeys(object):
    SPOT = '.'
    TWO_SPOT = ':'
    TAIL = ','
    HYBRID = ';'
    MESH = '#'
    HALF_MESH = '='
    SPARK = '\''
    BACKSPARK = '`'
    WOW = '!'
    WHAT = '?'
    RABBIT_EARS = '"'
    # RABBIT is `"` over `.`
    SPIKE = '|'
    DOUBLE_OH_SEVEN = '%'
    WORM = '-'
    ANGLE = '<'
    RIGHT_ANGLE = '>'
    WAX = '('
    WANE = ')'
    U_TURN = '['
    U_TURN_BACK = ']'
    EMBRACE = '{'
    BRACELET = '}'
    SPLAT = '*'
    AMPERSAND = '&'
    V = 'V'
    BOOK = 'V'
    # BOOKWORM is `-` over `V`
    BIG_MONEY = '$'
    # CHANGE is cent sign
    SQUIGGLE = '~'
    FLAT_WORM = '_'
    # OVERLINE is line on top
    INTERSECTION = '+'
    SLAT = '/'
    BACKSLAT = '\\'
    WHIRLPOOL = '@'
    # HOOKWORK is logical NOT symbol
    SHARK = '^'
    SHARKFIN = '^'
    # BLOTCH is several characters smashed on top of each other


class UnicodeAsciiKeys(object):
    NULL = '\x00'
    START_OF_HEADING = '\x01'
    START_OF_TEXT = '\x02'
    END_OF_TEXT = '\x03'
    END_OF_TRANSMISSION = '\x04'
    ENQUIRY = '\x05'
    ACKNOWLEDGE = '\x06'
    BELL = '\x07'
    BACKSPACE = '\x08'
    CHARACTER_TABULATION = '\t'
    HORIZONTAL_TABULATION = '\t'
    TAB = '\t'
    LINE_FEED = '\n'
    NEW_LINE = '\n'
    END_OF_LINE = '\n'
    LINE_TABULATION = '\x0b'
    VERTICAL_TABULATION = '\x0b'
    FORM_FEED = '\x0c'
    CARRIAGE_RETURN = '\r'
    SHIFT_OUT = '\x0e'
    SHIFT_IN = '\x0f'
    DATA_LINK_ESCAPE = '\x10'
    DEVICE_CONTROL_ONE = '\x11'
    DEVICE_CONTROL_TWO = '\x12'
    DEVICE_CONTROL_THREE = '\x13'
    DEVICE_CONTROL_FOUR = '\x14'
    NEGATIVE_ACKNOWLEDGE = '\x15'
    SYNCHRONOUS_IDLE = '\x16'
    END_OF_TRANSMISSION_BLOCK = '\x17'
    CANCEL = '\x18'
    END_OF_MEDIUM = '\x19'
    SUBSTITUTE = '\x1a'
    ESCAPE = '\x1b'
    INFORMATION_SEPARATOR_FOUR = '\x1c'
    FILE_SEPARATOR = '\x1c'
    INFORMATION_SEPARATOR_THREE = '\x1d'
    GROUP_SEPARATOR = '\x1d'
    INFORMATION_SEPARATOR_TWO = '\x1e'
    RECORD_SEPARATOR = '\x1e'
    INFORMATION_SEPARATOR_ONE = '\x1f'
    UNIT_SEPARATOR = '\x1f'
    SPACE = ' '
    EXCLAMATION_MARK = '!'
    FACTORIAL = '!'
    BANG = '!'
    QUOTATION_MARK = '"'
    NUMBER_SIGN = '#'
    POUND_SIGN = '#'
    HASH = '#'
    CROSSHATCH = '#'
    OCTOTHORPE = '#'
    DOLLAR_SIGN = '$'
    ESCUDO = '$'
    PERCENT_SIGN = '%'
    AMPERSAND = '&'
    APOSTROPHE = "'"
    APOSTROPHE_QUOTE = "'"
    APL_QUOTE = "'"
    LEFT_PARENTHESIS = '('
    OPENING_PARENTHESIS = '('
    RIGHT_PARENTHESIS = ')'
    CLOSING_PARENTHESIS = ')'
    ASTERISK = '*'
    STAR = '*'
    PLUS_SIGN = '+'
    COMMA = ','
    DECIMAL_SEPARATOR = ','
    HYPHEN_MINUS = '-'
    HYPHEN_OR_MINUS_SIGN = '-'
    FULL_STOP = '.'
    PERIOD = '.'
    DOT = '.'
    DECIMAL_POINT = '.'
    SOLIDUS = '/'
    SLASH = '/'
    VIRGULE = '/'
    DIGIT_ZERO = '0'
    DIGIT_ONE = '1'
    DIGIT_TWO = '2'
    DIGIT_THREE = '3'
    DIGIT_FOUR = '4'
    DIGIT_FIVE = '5'
    DIGIT_SIX = '6'
    DIGIT_SEVEN = '7'
    DIGIT_EIGHT = '8'
    DIGIT_NINE = '9'
    COLON = ':'
    SEMICOLON = ';'
    LESS_THAN_SIGN = '<'
    EQUALS_SIGN = '='
    GREATER_THAN_SIGN = '>'
    QUESTION_MARK = '?'
    COMMERCIAL_AT = '@'
    AT_SIGN = '@'
    LATIN_CAPITAL_LETTER_A = 'A'
    LATIN_CAPITAL_LETTER_B = 'B'
    LATIN_CAPITAL_LETTER_C = 'C'
    LATIN_CAPITAL_LETTER_D = 'D'
    LATIN_CAPITAL_LETTER_E = 'E'
    LATIN_CAPITAL_LETTER_F = 'F'
    LATIN_CAPITAL_LETTER_G = 'G'
    LATIN_CAPITAL_LETTER_H = 'H'
    LATIN_CAPITAL_LETTER_I = 'I'
    LATIN_CAPITAL_LETTER_J = 'J'
    LATIN_CAPITAL_LETTER_K = 'K'
    LATIN_CAPITAL_LETTER_L = 'L'
    LATIN_CAPITAL_LETTER_M = 'M'
    LATIN_CAPITAL_LETTER_N = 'N'
    LATIN_CAPITAL_LETTER_O = 'O'
    LATIN_CAPITAL_LETTER_P = 'P'
    LATIN_CAPITAL_LETTER_Q = 'Q'
    LATIN_CAPITAL_LETTER_R = 'R'
    LATIN_CAPITAL_LETTER_S = 'S'
    LATIN_CAPITAL_LETTER_T = 'T'
    LATIN_CAPITAL_LETTER_U = 'U'
    LATIN_CAPITAL_LETTER_V = 'V'
    LATIN_CAPITAL_LETTER_W = 'W'
    LATIN_CAPITAL_LETTER_X = 'X'
    LATIN_CAPITAL_LETTER_Y = 'Y'
    LATIN_CAPITAL_LETTER_Z = 'Z'
    LEFT_SQUARE_BRACKET = '['
    OPENING_SQUARE_BRACKET = '['
    REVERSE_SOLIDUS = '\\'
    BACKSLASH = '\\'
    RIGHT_SQUARE_BRACKET = ']'
    CLOSING_SQUARE_BRACKET = ']'
    CIRCUMFLEX_ACCENT = '^'
    LOW_LINE = '_'
    SPACING_UNDERSCORE = '_'
    GRAVE_ACCENT = '`'
    LATIN_SMALL_LETTER_A = 'a'
    LATIN_SMALL_LETTER_B = 'b'
    LATIN_SMALL_LETTER_C = 'c'
    LATIN_SMALL_LETTER_D = 'd'
    LATIN_SMALL_LETTER_E = 'e'
    LATIN_SMALL_LETTER_F = 'f'
    LATIN_SMALL_LETTER_G = 'g'
    LATIN_SMALL_LETTER_H = 'h'
    LATIN_SMALL_LETTER_I = 'i'
    LATIN_SMALL_LETTER_J = 'j'
    LATIN_SMALL_LETTER_K = 'k'
    LATIN_SMALL_LETTER_L = 'l'
    LATIN_SMALL_LETTER_M = 'm'
    LATIN_SMALL_LETTER_N = 'n'
    LATIN_SMALL_LETTER_O = 'o'
    LATIN_SMALL_LETTER_P = 'p'
    LATIN_SMALL_LETTER_Q = 'q'
    LATIN_SMALL_LETTER_R = 'r'
    LATIN_SMALL_LETTER_S = 's'
    LATIN_SMALL_LETTER_T = 't'
    LATIN_SMALL_LETTER_U = 'u'
    LATIN_SMALL_LETTER_V = 'v'
    LATIN_SMALL_LETTER_W = 'w'
    LATIN_SMALL_LETTER_X = 'x'
    LATIN_SMALL_LETTER_Y = 'y'
    LATIN_SMALL_LETTER_Z = 'z'
    LEFT_CURLY_BRACKET = '{'
    OPENING_CURLY_BRACKET = '{'
    LEFT_BRACE = '{'
    VERTICAL_LINE = '|'
    VERTICAL_BAR = '|'
    RIGHT_CURLY_BRACKET = '}'
    CLOSING_CURLY_BRACKET = '}'
    RIGHT_BRACE = '}'
    TILDE = '~'
    DELETE = '\x7f'


ASCII_NAMES = {
    '\t': 'tab',

    ' ': 'space',  # 0x20
    '!': 'exclamation',  # 0x21
    '"': 'double quote',  # 0x22
    '#': 'hash',  # 0x23
    '$': 'dollar',  # 0x24
    '%': 'percent',  # 0x25
    '&': 'ampersand',  # 0x26
    '\'': 'single quote',  # 0x27
    '(': 'open paren',  # 0x28
    ')': 'close paren',  # 0x29
    '*': 'asterisk',  # 0x2a
    '+': 'plus',  # 0x2b
    ',': 'comma',  # 0x2c
    '-': 'minus',  # 0x2d
    '.': 'period',  # 0x2e
    '/': 'slash',  # 0x2f

    ':': 'colon',  # 0x3a
    ';': 'semicolon',  # 0x3b
    '<': 'less than',  # 0x3c
    '=': 'equals',  # 0x3d
    '>': 'greater than',  # 0x3e
    '?': 'question',  # 0x3f
    '@': 'at',  # 0x40

    '[': 'left bracket',  # 0x5b
    '\\': 'backslash',  # 0x5c
    ']': 'right bracket',  # 0x5d
    '^': 'caret',  # 0x5e
    '_': 'underscore',  # 0x5f
    '`': 'backtick',  # 0x60

    '{': 'left brace',  # 0x7b
    '|': 'pipe',  # 0x7c
    '}': 'right brace',  # 0x7d
    '~': 'tilde',  # 0x7e
}


class AlternativeUnixFunctionKeys(object):
    # Unsure origin: alternate V220 mode?
    F1 = '\x1bO11~'
    F2 = '\x1bO12~'
    F3 = '\x1bO13~'
    F4 = '\x1bO14~'
    F5 = '\x1bO15~'
    F6 = '\x1bO17~'
    F7 = '\x1bO18~'
    F8 = '\x1bO19~'
    F9 = '\x1bO20~'
    F10 = '\x1bO21~'
    F11 = '\x1bO23~'
    F12 = '\x1bO24~'


class WindowsKeys(object):
    ESC = '\x1b'

    LEFT = '\xe0K'
    RIGHT = '\xe0M'
    UP = '\xe0H'
    DOWN = '\xe0P'

    ENTER = '\r'
    BACKSPACE = '\x08'
    SPACE = ' '

    F1 = '\x00;'
    F2 = '\x00<'
    F3 = '\x00='
    F4 = '\x00>'
    F5 = '\x00?'
    F6 = '\x00@'
    F7 = '\x00A'
    F8 = '\x00B'
    F9 = '\x00C'
    F10 = '\x00D'
    F11 = '\xe0\x85'
    F12 = '\xe0\x86'

    INSERT = '\xe0R'
    DELETE = '\xe0S'
    PAGE_UP = '\xe0I'
    PAGE_DOWN = '\xe0Q'
    HOME = '\xe0G'
    END = '\xe0O'

    CTRL_F1 = '\x00^'
    CTRL_F2 = '\x00_'
    CTRL_F3 = '\x00`'
    CTRL_F4 = '\x00a'
    CTRL_F5 = '\x00b'
    CTRL_F6 = '\x00c'
    CTRL_F7 = '\x00d'  # Captured by something?
    CTRL_F8 = '\x00e'
    CTRL_F9 = '\x00f'
    CTRL_F10 = '\x00g'
    CTRL_F11 = '\xe0\x89'
    CTRL_F12 = '\xe0\x8a'

    CTRL_HOME = '\xe0w'
    CTRL_END = '\xe0u'
    CTRL_INSERT = '\xe0\x92'
    CTRL_DELETE = '\xe0\x93'
    CTRL_PAGE_DOWN = '\xe0v'

    CTRL_2 = '\x00\x03'
    CTRL_UP = '\xe0\x8d'
    CTRL_DOWN = '\xe0\x91'
    CTRL_LEFT = '\xe0s'
    CTRL_RIGHT = '\xe0t'

    CTRL_ALT_A = '\x00\x1e'
    CTRL_ALT_B = '\x000'
    CTRL_ALT_C = '\x00.'
    CTRL_ALT_D = '\x00 '
    CTRL_ALT_E = '\x00\x12'
    CTRL_ALT_F = '\x00!'
    CTRL_ALT_G = '\x00"'
    CTRL_ALT_H = '\x00#'
    CTRL_ALT_I = '\x00\x17'
    CTRL_ALT_J = '\x00$'
    CTRL_ALT_K = '\x00%'
    CTRL_ALT_L = '\x00&'
    CTRL_ALT_M = '\x002'
    CTRL_ALT_N = '\x001'
    CTRL_ALT_O = '\x00\x18'
    CTRL_ALT_P = '\x00\x19'
    CTRL_ALT_Q = '\x00\x10'
    CTRL_ALT_R = '\x00\x13'
    CTRL_ALT_S = '\x00\x1f'
    CTRL_ALT_T = '\x00\x14'
    CTRL_ALT_U = '\x00\x16'
    CTRL_ALT_V = '\x00/'
    CTRL_ALT_W = '\x00\x11'
    CTRL_ALT_X = '\x00-'
    CTRL_ALT_Y = '\x00\x15'
    CTRL_ALT_Z = '\x00,'
    CTRL_ALT_1 = '\x00x'
    CTRL_ALT_2 = '\x00y'
    CTRL_ALT_3 = '\x00z'
    CTRL_ALT_4 = '\x00{'
    CTRL_ALT_5 = '\x00|'
    CTRL_ALT_6 = '\x00}'
    CTRL_ALT_7 = '\x00~'
    CTRL_ALT_8 = '\x00\x7f'
    CTRL_ALT_9 = '\x00\x80'
    CTRL_ALT_0 = '\x00\x81'
    CTRL_ALT_MINUS = '\x00\x82'
    CTRL_ALT_EQUALS = '\x00x83'
    CTRL_ALT_BACKSPACE = '\x00\x0e'

    ALT_F1 = '\x00h'
    ALT_F2 = '\x00i'
    ALT_F3 = '\x00j'
    ALT_F4 = '\x00k'
    ALT_F5 = '\x00l'
    ALT_F6 = '\x00m'
    ALT_F7 = '\x00n'
    ALT_F8 = '\x00o'
    ALT_F9 = '\x00p'
    ALT_F10 = '\x00q'
    ALT_F11 = '\xe0\x8b'
    ALT_F12 = '\xe0\x8c'
    ALT_HOME = '\x00\x97'
    ALT_END = '\x00\x9f'
    ALT_INSERT = '\x00\xa2'
    ALT_DELETE = '\x00\xa3'
    ALT_PAGE_UP = '\x00\x99'
    ALT_PAGE_DOWN = '\x00\xa1'
    ALT_LEFT = '\x00\x9b'
    ALT_RIGHT = '\x00\x9d'
    ALT_UP = '\x00\x98'
    ALT_DOWN = '\x00\xa0'

    CTRL_ALT_LEFT_BRACKET = '\x00\x1a'
    CTRL_ALT_RIGHT_BRACKET = '\x00\x1b'
    CTRL_ALT_SEMICOLON = '\x00\''
    CTRL_ALT_SINGLE_QUOTE = '\x00('
    CTRL_ALT_ENTER = '\x00\x1c'
    CTRL_ALT_SLASH = '\x005'
    CTRL_ALT_PERIOD = '\x004'
    CTRL_ALT_COMMA = '\x003'


class ControlKeys(object):
    def __init__(self, format='CTRL_{}'):
        for i in range(0x20):
            low_char = chr(i)
            high_char = chr(i + 0x40)
            name = ASCII_NAMES.get(high_char, high_char).upper()
            ctrl_name = format.format(name)
            setattr(self, ctrl_name, low_char)


class AsciiKeys(object):
    def __init__(
            self,
            lower_format='{}', upper_format='SHIFT_{}', digit_format='N{}',
            ascii_names=ASCII_NAMES,
    ):
        for letter in string.ascii_lowercase:
            name = lower_format.format(letter.upper())
            setattr(self, name, letter)
        for letter in string.ascii_uppercase:
            name = upper_format.format(letter.upper())
            setattr(self, name, letter)
        for digit in string.digits:
            name = digit_format.format(digit)
            setattr(self, name, digit)
        for char, name in ascii_names.items():
            name = name.upper().replace(' ', '_')
            setattr(self, name, char)


class Keys(object):
    def __init__(self, keyclasses):
        self.__names = dict()  # Map of codes -> names
        self.__codes = dict()  # Map of names -> codes

        self.__escapes = set()

        for keyclass in keyclasses:
            for name in dir(keyclass):
                if self._is_key_name(name):
                    code = getattr(keyclass, name)
                    self.register(name, code)

    def register(self, name, code):
        if name not in self.__codes:
            self.__codes[name] = code
        if code not in self.__names:
            self.__names[code] = name
        for i in range(len(code)):
            self.__escapes.add(code[:i])

        # Update towards canonicity
        while True:
            canon_code = self.canon(code)
            canon_canon_code = self.canon(canon_code)
            if canon_code != canon_canon_code:
                self.__codes[self.name(code)] = canon_canon_code
            else:
                break
        while True:
            canon_name = self.name(self.code(name))
            canon_canon_name = self.name(self.code(canon_name))
            if canon_name != canon_canon_name:
                self.__names[self.code(name)] = canon_canon_name
            else:
                break

    @property
    def escapes(self):
        return self.__escapes

    @property
    def names(self):
        return self.__codes.keys()

    def name(self, code):
        return self.__names.get(code)

    def code(self, name):
        return self.__codes.get(name)

    def canon(self, code):
        name = self.name(code)
        return self.code(name) if name else code

    def __getattr__(self, name):
        code = self.code(name)
        if code is not None:
            return code
        else:
            return self.__getattribute__(name)

    def _is_key_name(self, name):
        return name == name.upper() and not name.startswith('_')


windows_keys = Keys([
    WindowsKeys(),
    AsciiKeys(),
    ControlKeys(),
    UnicodeAsciiKeys(),
    JargonKeys(),
    IntercalKeys()
])

PLATFORM_KEYS = {
    'windows': windows_keys,
}


class Platform(object):
    def __init__(self, keys=None, interrupts=None):
        keys = keys or self.KEYS

        if isinstance(keys, str):
            keys = PLATFORM_KEYS[keys]
        self.key = self.keys = keys
        if interrupts is None:
            interrupts = self.INTERRUPTS
        self.interrupts = {
            self.keys.code(name): action
            for name, action in interrupts.items()
        }

        assert (
                self.__class__.getchar != Platform.getchar or
                self.__class__.getchars != Platform.getchars
        )

    def getkey(self, blocking=True):
        buffer = ''
        for c in self.getchars(blocking):
            buffer += str(c)
            if buffer not in self.keys.escapes:
                break

        keycode = self.keys.canon(buffer)
        if keycode in self.interrupts:
            interrupt = self.interrupts[keycode]
            if isinstance(interrupt, BaseException) or \
                    issubclass(interrupt, BaseException):
                raise interrupt
            else:
                raise NotImplementedError('Unimplemented interrupt: {!r}'
                                          .format(interrupt))
        return keycode

    def bang(self):
        while True:
            code = self.getkey(True)
            name = self.keys.name(code) or '???'
            print('{} = {!r}'.format(name, code))

    # You MUST override at least one of the following
    def getchars(self, blocking=True):
        char = self.getchar(blocking)
        while char:
            yield char
            char = self.getchar(False)

    def getchar(self, blocking=True):
        for char in self.getchars(blocking):
            return char
        else:
            return None


class PlatformWindows(Platform):
    KEYS = 'windows'
    INTERRUPTS = {'CTRL_C': KeyboardInterrupt}

    def __init__(self, keys=None, interrupts=None, msvcrt=None):
        super(PlatformWindows, self).__init__(keys, interrupts)
        if msvcrt is None:
            import msvcrt
        self.msvcrt = msvcrt

    def getchars(self, blocking=True):
        """Get characters on Windows."""

        if blocking:
            yield self.msvcrt.getch()
        while self.msvcrt.kbhit():
            yield self.msvcrt.getch()


class Input_TextInputLength(HasTunableSingletonFactory, AutoFactoryInit):
    __qualname__ = 'Input_TextInputLength'

    def build_msg(self, dialog, msg, *additional_tokens):
        msg.max_length = 255
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
        # text_input_msg1.max_length = nn
        # text_input_msg1.min_length = nn
        return msg


class DialogTestUiDialogTextInputOkCancel(UiDialogOkCancel, DialogTestUiDialogTextInput):
    __qualname__ = 'DialogTestUiDialogTextInputOkCancel'


TEXT_INPUT_NAME = 'name'

class input_text:
    DIALOG = UiDialogTextInputOkCancel.TunableFactory(text_inputs=(TEXT_INPUT_NAME,))

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
    text_input.max_length = 255
    text_input.initial_value = lambda **_: LocalizationHelperTuning.get_raw_text(initial_value)
    text_input.check_profanity = False
    text_input.length_restriction = Input_TextInputLength()
    text_input.height = None

    inputs = AttributeDict({'search_terms': text_input})

    dialog = UiDialogTextInputOkCancel.TunableFactory().default(client.active_sim,
                                                                text=lambda **_: LocalizationHelperTuning.get_raw_text(
                                                                    text),
                                                                title=lambda **_: LocalizationHelperTuning.get_raw_text(
                                                                    title),
                                                                text_inputs=inputs)

    dialog.add_listener(inputbox_callback)
    dialog.show_dialog()


def get_input_callback(input_str):
    client = services.client_manager().get_first_client()
    sim_info = client.active_sim.sim_info
    ld_notice(sim_info, "get_input_callback", input_str)


##
## Ok/Cancel dialog test
##
@sims4.commands.Command('dialogtest.okcancel', command_type=sims4.commands.CommandType.Live)
def dialogtest_okcancel(_connection=None):
    output = sims4.commands.CheatOutput(_connection)

    def dialogtest_okcancel_callback(dialog):
        if dialog.accepted:
            output("User pressed OK")
        else:
            output("User pressed CANCEL")

    title = "Dialog Test 1"
    text = "Please press OK to continue, or Cancel."
    client = services.client_manager().get_first_client()
    dialog = UiDialogOkCancel.TunableFactory().default(client.active_sim,
                                                       text=lambda **_: LocalizationHelperTuning.get_raw_text(text),
                                                       title=lambda **_: LocalizationHelperTuning.get_raw_text(title))
    dialog.add_listener(dialogtest_okcancel_callback)
    dialog.show_dialog()