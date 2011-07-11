import colorsys
import operator
import string
import types

import cssparser

from scssexceptions import *


COLOR_MAP = {
    "black": [0, 0, 0],
    "silver": [192, 192, 192],
    "gray": [128, 128, 128],
    "white": [255, 255, 255],
    "maroon": [128, 0, 0],
    "red": [255, 0, 0],
    "purple": [128, 0, 128],
    "fuchsia": [255, 0, 255],
    "green": [0, 128, 0],
    "lime": [0, 255, 0],
    "olive": [128, 128, 0],
    "yellow": [255, 255, 0],
    "navy": [0, 0, 128],
    "blue": [0, 0, 255],
    "teal": [0, 128, 128],
    "aqua": [0, 255, 255],

    # extended colors:
    "aqua": [0, 255, 255],
    "azure": [240, 255, 255],
    "brown": [165, 42, 42],
    "coral": [255, 127, 80],
    "cyan": [0, 255, 255],
    "gold": [255, 215, 0],
    "grey": [128, 128, 128],
    "linen": [250, 240, 230],
    "orange": [255, 165, 0],
    "peru": [205, 133, 63],
    "pink": [255, 192, 203],
    "plum": [221, 160, 221],
    "snow": [255, 250, 250],
    "tan": [210, 180, 140],
    "teal": [0, 128, 128],
    "wheat": [245, 222, 179]
}

CONVERSIONS = {
    "cm": { "cm": 1,     "in": 0.39,  "mm": 10,    "pc":  0.033,  "pt":  0.0055  },
    "in": { "cm": 2.54,  "in": 1,     "mm": 25.4,  "pc": 12,      "pt": 72       },
    "mm": { "cm": 0.1,   "in": 0.039, "mm":  1,    "pc":  0.0033, "pt":  0.00055 },
    "pc": { "cm": 0.21,  "in": 0.083, "mm":  2.1,  "pc":  1,      "pt":  6       },
    "pt": { "cm": 0.035, "in": 0.014, "mm":  0.35, "pc":  0.17,   "pt":  1       }
}


def clamp(number, minValue, maxValue):
    if number < minValue:
        return minValue
    if number > maxValue:
        return maxValue
    return number


class SCSSVariable(object):
    def setValue(self, value):
        raise SCSSRunTimeError("Cannot assign a value to an untyped variable")

    def toString(self):
        return ""

    def toToken(self, parent = None):
        return cssparser.SCSSVariableToken(parent, self)

    def isNumber(self):
        return isinstance(self, SCSSNumber)

    def isString(self):
        return isinstance(self, SCSSString)

    def isColor(self):
        return isinstance(self, SCSSColor)

    def isBoolean(self):
        return isinstance(self, SCSSBoolean)

    def isList(self):
        return isinstance(self, SCSSList)

    def isToken(self):
        return isinstance(self, SCSSToken)

    def apply(self, operator, operand):
        try:
            if operator == "+":
                return self + operand
            elif operator == "-":
                return self - operand
            elif operator == "*":
                return self * operand
            elif operator == "/":
                return self / operand
            elif operator == "%":
                return self % operand
            elif operator == "==":
                return SCSSBoolean(self == operand)
            elif operator == "<=":
                return SCSSBoolean(self <= operand)
            elif operator == ">=":
                return SCSSBoolean(self >= operand)
            elif operator == "<":
                return SCSSBoolean(self < operand)
            elif operator == ">":
                return SCSSBoolean(self > operand)
            elif operator == "or":
                return SCSSBoolean(self or operand)
            elif operator == "and":
                return SCSSBoolean(self and operand)
            elif operator == "not":
                return SCSSBoolean(not self)
            raise SCSSRunTimeError("Unknown operator \"%s\" applied" % operator)

        except Exception, exception:
            raise SCSSRunTimeError("Variable \"%s\" does not support the %s operator in combination with variable \"%s\" (led to exception: %s)" % (self.toString(), operator, operand.toString(), exception))

    @staticmethod
    def fromToken(token, scope = None):
        if token.isVariable():
            if token.variable != None:
                return token.variable
            if scope:
                token.variable = scope.get(token.getName(), token.parent)
                return token.variable
        if token.isNumber() or token.isPercentage() or token.isDimension():
            return SCSSNumber(token)
        elif token.isKeyword("true") or token.isKeyword("false"):
            return SCSSBoolean(token)
        elif token.isString():
            return SCSSString(token)
        elif token.isIdentifier() or token.isHash() or token.isFunction():
            try: # just try and see whether it's a color
                return SCSSColor(token)
            except SCSSRunTimeError, error:
                pass
        return SCSSToken(token, scope)


class SCSSNumber(SCSSVariable):
    def __init__(self, value = None, intVal = 0, unit = ""):
        SCSSVariable.__init__(self)

        if value:
            self.setValue(value)
        else:
            self.value = intVal
            self.unit = unit

    def parseNumber(self, number):
        if "." in number:
            return float(number)
        else:
            return int(number)

    def setValue(self, value):
        if isinstance(value, int):
            self.value = value
            self.unit = ""
            return

        if isinstance(value, SCSSNumber):
            self.value = value.value
            self.unit = value.unit
            return

        if isinstance(value, cssparser.CSSAnyToken):
            if value.type == cssparser.CSS_NUMBER_VALUE:
                self.value = self.parseNumber(value.data)
                self.unit = ""
                return

            if value.type == cssparser.CSS_PERCENTAGE_VALUE:
                self.value = self.parseNumber(value.data[0:-1])
                self.unit = "%"
                return

            if value.type == cssparser.CSS_DIMENSION_VALUE:
                for unit in ["cm", "deg", "em", "ex", "in", "mm", "pc", "pt", "px", "s"]:
                    if value.data[-len(unit):] == unit:
                        self.value = self.parseNumber(value.data[0:-len(unit)])
                        self.unit = unit
                        return

        raise SCSSRunTimeError("Unrecognized value \"%s\" assigned to number" % value)

    def toString(self, options = cssparser.CSSOptions()):
        return str(self.value) + self.unit

    def convertToUnit(self, unit):
        if unit == "" or unit == self.unit:
            return (self.value, self.unit)
        if self.unit == "":
            return (self.value, unit)

        if not self.unit in CONVERSIONS or not unit in CONVERSIONS[self.unit]:
            raise SCSSRunTimeError("Cannot convert number from %s units to %s units" % (self.unit, unit))

        value = self.value * CONVERSIONS[self.unit][unit]
        return (value, unit)

    def __add__(self, operand):
        if isinstance(operand, SCSSColor):
            return operand + self

        if isinstance(operand, SCSSList):
            return SCSSList.fromOperands(self, operand)

        if not isinstance(operand, SCSSNumber):
            raise SCSSRunTimeError("Cannot sum number \"%s\" with \"%s\"" % (self.toString(), operand.toString()))

        (value, unit) = operand.convertToUnit(self.unit)
        return SCSSNumber(intVal = self.value + value, unit = unit)

    def __sub__(self, operand):
        if isinstance(operand, SCSSColor):
            return operand - self

        if not isinstance(operand, SCSSNumber):
            raise SCSSRunTimeError("Cannot subtract number \"%s\" with \"%s\"" % (self.toString(), operand.toString()))

        (value, unit) = operand.convertToUnit(self.unit)
        return SCSSNumber(intVal = self.value - value, unit = unit)

    def __mul__(self, operand):
        if isinstance(operand, SCSSColor):
            return operand * self

        if not isinstance(operand, SCSSNumber):
            raise SCSSRunTimeError("Cannot multiply number \"%s\" with \"%s\"" % (self.toString(), operand.toString()))

        (value, unit) = operand.convertToUnit(self.unit)
        return SCSSNumber(intVal = self.value * value, unit = unit)

    def __div__(self, operand):
        if not isinstance(operand, SCSSNumber):
            raise SCSSRunTimeError("Cannot divide number \"%s\" with \"%s\"" % (self.toString(), operand.toString()))

        (value, unit) = operand.convertToUnit(self.unit)
        return SCSSNumber(intVal = self.value / value, unit = unit)

    def __mod__(self, operand):
        if not isinstance(operand, SCSSNumber):
            raise SCSSRunTimeError("Cannot get modulo of number \"%s\" with \"%s\"" % (self.toString(), operand.toString()))

        (value, unit) = operand.convertToUnit(self.unit)
        return SCSSNumber(intVal = self.value % value, unit = unit)

    def __cmp__(self, operand):
        if operand == None:
            return 1
        elif isinstance(operand, types.BooleanType):
            return 0 if self and operand else 1 if self else -1
        elif ((isinstance(operand, cssparser.CSSToken) and
               (operand.isIdentifier() or operand.isString())) or
              (isinstance(operand, SCSSVariable) and
               (operand.isString() or operand.isToken()))):
            return -1

        operand = SCSSNumber(operand)
        (value, unit) = operand.convertToUnit(self.unit)

        if self.value == value:
            return 0
        else:
            return 1 if self.value > value else -1

    def __nonzero__(self):
        if self.value > 0 or self.value < 0:
            return True
        else:
            return False


class SCSSString(SCSSVariable):
    def __init__(self, value = None):
        SCSSVariable.__init__(self)

        if value:
            self.setValue(value)
        else:
            self.value = ""

    def setValue(self, value):
        if isinstance(value, str) or isinstance(value, unicode):
            self.value = value
            return

        if isinstance(value, SCSSString):
            self.value = value.value
            return

        if isinstance(value, SCSSToken):
            value = value.token

        if isinstance(value, cssparser.CSSAnyToken):
            if value.type == cssparser.CSS_STRING_VALUE:
                self.value = value.data[1:-1]
                return

            if value.type == cssparser.CSS_IDENT_VALUE:
                self.value = value.data
                return

        raise SCSSRunTimeError("Unrecognized value \"%s\" (%s) assigned to string" % (value, value.__class__))

    def toString(self, options = cssparser.CSSOptions()):
        result = ""
        stream = cssparser.CSSStream(self.value)
        character = stream.take()
        while character != cssparser.CSS_EOF:
            if character == "\"":
                result += "\\"
            result += character
            character = stream.take()
        if options.stripQuotes:
            return result
        else:
            return "\"" + result + "\""

    def __add__(self, operand):
        if isinstance(operand, SCSSList):
            return SCSSList.fromOperands(self, operand)

        if (not isinstance(operand, SCSSString) and
            not (isinstance(operand, SCSSToken) and operand.token.isIdentifier())):
            raise SCSSRunTimeError("Cannot concatenate string \"%s\" with \"%s\"" % (self.toString(), operand.toString()))

        if isinstance(operand, SCSSString):
            return SCSSString(self.value + operand.value)
        else:
            return SCSSString(self.value + operand.token.data)

    def __cmp__(self, operand):
        if operand == None:
            return 1
        elif isinstance(operand, types.BooleanType):
            return 0 if self and operand else 1 if self else -1

        operand = SCSSString(operand)
        return cmp(self.value, operand.value)

    def __len__(self):
        return len(self.value)


class SCSSColor(SCSSVariable):
    def __init__(self, value = None):
        SCSSVariable.__init__(self)

        self.a = 1.0
        if value:
            self.setValue(value)
        else:
            self.setRgbValue(0.0, 0.0, 0.0)

    def setValue(self, value):
        if isinstance(value, list):
            self.setRgbValue(value[0], value[1], value[2])
            if len(value) == 4:
                self.a = value[3]
            return

        if isinstance(value, SCSSColor):
            self.r = value.r
            self.g = value.g
            self.b = value.b
            self.h = value.h
            self.s = value.s
            self.l = value.l
            self.a = value.a
            return

        if isinstance(value, str) or isinstance(value, unicode):
            if value[0] == "#":
                hex = value[1:]
                if len(hex) == 6:
                    r = string.hexdigits.find(hex[0].lower()) * 16 + string.hexdigits.find(hex[1].lower())
                    g = string.hexdigits.find(hex[2].lower()) * 16 + string.hexdigits.find(hex[3].lower())
                    b = string.hexdigits.find(hex[4].lower()) * 16 + string.hexdigits.find(hex[5].lower())
                    self.setRgbValue(r / 255.0, g / 255.0, b / 255.0)
                    return
                elif len(hex) == 3:
                    r = string.hexdigits.find(hex[0].lower()) * 16 + string.hexdigits.find(hex[0].lower())
                    g = string.hexdigits.find(hex[1].lower()) * 16 + string.hexdigits.find(hex[1].lower())
                    b = string.hexdigits.find(hex[2].lower()) * 16 + string.hexdigits.find(hex[2].lower())
                    self.setRgbValue(r / 255.0, g / 255.0, b / 255.0)
                    return
            else:
                rgb = self.keywordToColor(value)
                if rgb:
                    self.setRgbValue(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
                    return

        if isinstance(value, cssparser.CSSAnyToken):
            if value.type == cssparser.CSS_IDENT_VALUE:
                return self.setValue(value.data)
            elif value.type == cssparser.CSS_HASH_VALUE:
                return self.setValue(value.data)
            elif value.type == cssparser.CSS_FUNCTION_VALUE:
                name = value.getName()
                if name == "rgb":
                    rgb = value.getArguments()
                    if len(rgb) != 3:
                        raise cssparser.CSSParseError("RGB colors must have 3 arguments, has %d" % len(rgb), token = value)
                    self.setRgbValue(self.tokenToValue(rgb[0]), self.tokenToValue(rgb[1]), self.tokenToValue(rgb[2]))
                    return
                elif name == "rgba":
                    rgba = value.getArguments()
                    if len(rgba) != 4:
                        raise cssparser.CSSParseError("RGBA colors must have 4 arguments, has %d" % len(rgba), token = value)
                    self.setRgbValue(self.tokenToValue(rgba[0]), self.tokenToValue(rgba[1]), self.tokenToValue(rgba[2]))
                    self.setAlpha(self.tokenToValue(rgba[3], numberFormat = "float"))
                    return
                elif name == "hsl":
                    hsl = value.getArguments()
                    if len(hsl) != 3:
                        raise cssparser.CSSParseError("HSL colors must have 3 arguments, has %d" % len(hsl), token = value)
                    self.setHslValue(self.tokenToValue(hsl[0], numberFormat = "degree"),
                                     self.tokenToValue(hsl[1], numberFormat = "float"),
                                     self.tokenToValue(hsl[2], numberFormat = "float"))
                    return
                elif name == "hsla":
                    hsla = value.getArguments()
                    if len(hsla) != 4:
                        raise cssparser.CSSParseError("HSLA colors must have 4 arguments, has %d" % len(hsla), token = value)
                    self.setHslValue(self.tokenToValue(hsla[0], numberFormat = "degree"),
                                     self.tokenToValue(hsla[1], numberFormat = "float"),
                                     self.tokenToValue(hsla[2], numberFormat = "float"))
                    self.setAlpha(self.tokenToValue(hsla[3], numberFormat = "float"))
                    return

        raise SCSSRunTimeError("Unrecognized value \"%s\" (%s) assigned to color" % (str(value), value))

    def toString(self, options = cssparser.CSSOptions()):
        if self.a == 0.0:
            return "transparent"

        # just use some long strings so they are not used by accident
        hex = "012345678901234567890123456789" 
        hsl = "012345678901234567890123456789"
        key = "012345678901234567890123456789"
        rgb = "012345678901234567890123456789"

        if not self.isRgbValue():
            if self.a == 1.0:
                hsl = "hsl(%s,%s%%,%s%%)" % (int(self.h * 360), int(self.s * 100), int(self.l * 100))
            else:
                hsl = "hsla(%s,%s,%s,%s)" % (int(self.h * 360), int(self.s * 100), int(self.l * 100), str(self.a)[1:])
            self.convertToRgb()

        if self.a == 1.0:
            keyword = self.colorToKeyword([self.r * 255, self.g * 255, self.b * 255])
            if keyword:
                key = keyword

            hex = ""
            for c in [self.r, self.g, self.b]:
                hex += string.hexdigits[15 if c * 16 > 15 else int(c * 16)] + string.hexdigits[int((c * 255) % 16)]
            if hex[0] == hex[1] and hex[2] == hex[3] and hex[4] == hex[5]:
                hex = hex[0] + hex[2] + hex[4]
            hex = "#" + hex
        else:
            rgb = "rgba(%s,%s,%s,%s)" % (int(self.r * 255), int(self.g * 255), int(self.b * 255), str(self.a)[1:])

        # always pick the shortest representation
        if len(key) < len(hsl) and len(key) < len(hex) and len(key) < len(rgb):
            return key
        elif len(hsl) < len(hex) and len(hsl) < len(rgb):
            return hsl
        elif len(hex) < len(rgb):
            return hex
        else:
            return rgb

    def __str__(self):
        return self.toString() 

    def tokenToValue(self, token, numberFormat = "int", allowPercentage = True):
        if token.isNumber():
            if numberFormat == "int":
                return clamp(int(token.data) / 255.0, 0.0, 1.0)
            elif numberFormat == "float":
                return clamp(float(token.data), 0.0, 1.0)
            elif numberFormat == "degree":
                return clamp((float(token.data) % 360) / 360.0, 0.0, 1.0)
        elif allowPercentage and token.isPercentage():
            return clamp(int(token.data[0:-1]) / 100.0, 0.0, 1.0)
        elif numberFormat == "degree" and token.isDimension() and token.data[-3:].lower() == "deg":
            return clamp((float(token.data[0:-3]) % 360) / 360.0, 0.0, 1.0)
        raise cssparser.CSSParseError("Color argument is not a valid number or percentage", token = token)

    def isRgbValue(self):
        return self.h == 0.0 and self.s == 0.0 and self.l == 0.0

    def setRgbValue(self, r, g, b):
        self.r = clamp(r, 0.0, 1.0)
        self.g = clamp(g, 0.0, 1.0)
        self.b = clamp(b, 0.0, 1.0)
        self.h = 0.0
        self.s = 0.0
        self.l = 0.0

    def setHslValue(self, h, s, l):
        self.r = 0.0
        self.g = 0.0
        self.b = 0.0
        self.h = clamp(h, 0.0, 1.0)
        self.s = clamp(s, 0.0, 1.0)
        self.l = clamp(l, 0.0, 1.0)

    def setAlpha(self, a):
        self.a = a

    def convertToRgb(self):
        if self.isRgbValue():
            return

        (self.r, self.g, self.b) = colorsys.hls_to_rgb(self.h, self.l, self.s)
        self.h = 0.0
        self.s = 0.0
        self.l = 0.0

    def convertToHsl(self):
        if not self.isRgbValue():
            return

        (self.h, self.l, self.s) = colorsys.rgb_to_hls(self.r, self.g, self.b)
        self.r = 0.0
        self.g = 0.0
        self.b = 0.0

    def keywordToColor(self, keyword):
        if keyword in COLOR_MAP:
            return COLOR_MAP[keyword]

        return None

    def colorToKeyword(self, rgb):
        for keyword in COLOR_MAP:
            if (COLOR_MAP[keyword][0] == rgb[0] and
                COLOR_MAP[keyword][1] == rgb[1] and
                COLOR_MAP[keyword][2] == rgb[2]):
                return keyword

        return None

    def darken(self, amount):
        self.convertToHsl()
        self.l = clamp(self.l - amount, 0.0, 1.0)

    def lighten(self, amount):
        self.convertToHsl()
        self.l = clamp(self.l + amount, 0.0, 1.0)

    def __add__(self, operand):
        if isinstance(operand, SCSSList):
            return SCSSList.fromOperands(operand, self)

        if (not isinstance(operand, SCSSColor) and
            not isinstance(operand, SCSSNumber)):
            raise SCSSRunTimeError("Cannot sum color \"%s\" with \"%s\"" % (self.toString(), operand.toString()))

        if self.a != operand.a:
            raise SCSSRunTimeError("Colors must have equal opacity when applying arithmatic (mismatch between \"%s\" and \"%s\")" % (self.toString(), operand.toString()))

        self.convertToRgb()
        if isinstance(operand, SCSSColor):
            operand.convertToRgb()
            return SCSSColor([self.r + operand.r, self.g + operand.g, self.b + operand.b, self.a])
        else:
            val = operand.value / 255.0
            return SCSSColor([self.r + val, self.g + val, self.b + val, self.a])

    def __sub__(self, operand):
        if (not isinstance(operand, SCSSColor) and
            not isinstance(operand, SCSSNumber)):
            raise SCSSRunTimeError("Cannot subtract color \"%s\" with \"%s\"" % (self.toString(), operand.toString()))

        if self.a != operand.a:
            raise SCSSRunTimeError("Colors must have equal opacity when applying arithmatic (mismatch between \"%s\" and \"%s\")" % (self.toString(), operand.toString()))

        self.convertToRgb()
        if isinstance(operand, SCSSColor):
            operand.convertToRgb()
            return SCSSColor([self.r - operand.r, self.g - operand.g, self.b - operand.b, self.a])
        else:
            val = operand.value / 255.0
            return SCSSColor([self.r - val, self.g - val, self.b - val, self.a])

    def __mul__(self, operand):
        if (not isinstance(operand, SCSSColor) and
            not isinstance(operand, SCSSNumber)):
            raise SCSSRunTimeError("Cannot multiply color \"%s\" with \"%s\"" % (self.toString(), operand.toString()))

        self.convertToRgb()

        if isinstance(operand, SCSSColor):
            if self.a != operand.a:
                raise SCSSRunTimeError("Colors must have equal opacity when applying arithmatic (mismatch between \"%s\" and \"%s\")" % (self.toString(), operand.toString()))
            operand.convertToRgb()
            r = (255 * self.r) * (255 * operand.r) / 255.0
            g = (255 * self.g) * (255 * operand.g) / 255.0
            b = (255 * self.b) * (255 * operand.b) / 255.0
        else:
            r = (255 * self.r * operand.value) / 255.0
            g = (255 * self.g * operand.value) / 255.0
            b = (255 * self.b * operand.value) / 255.0
        return SCSSColor([r, g, b, self.a])

    def __cmp__(self, operand):
        if operand == None:
            return 1
        elif isinstance(operand, types.BooleanType):
            return 0 if self and operand else 1 if self else -1

        if isinstance(operand, SCSSVariable) and operand.isToken() and operand.token.isKeyword("none"):
            operand = SCSSColor()
        else:
            operand = SCSSColor(operand)

        self.convertToRgb()
        operand.convertToRgb()

        return 0 if (self.r == operand.r and
                     self.g == operand.g and
                     self.b == operand.b and
                     self.a == operand.a) else 1

    def __nonzero__(self):
        self.convertToRgb()
        return ((self.r > 0.0 or self.g > 0.0 or self.b > 0.0) and
                self.a > 0.0)


class SCSSBoolean(SCSSVariable):
    def __init__(self, value = None):
        SCSSVariable.__init__(self)

        if value:
            self.setValue(value)
        else:
            self.value = False

    def setValue(self, value):
        if isinstance(value, bool):
            self.value = value
            return
        elif isinstance(value, str) or isinstance(value, unicode):
            self.value = (value == "true")
            return
        elif isinstance(value, cssparser.CSSAnyToken):
            if value.isIdentifier():
                self.value = value.isKeyword("true")
                return
            elif value.isString():
                self.value = value.data[1:-1] == "true"
                return
        elif isinstance(value, SCSSVariable):
            self.value = bool(value)
            return

        raise SCSSRunTimeError("Unrecognized value \"%s\" (%s) assigned to boolean" % (value.toString(), value))

    def toString(self, options = cssparser.CSSOptions()):
        return "true" if self.value else "false"

    def __str__(self):
        return self.toString()

    def __cmp__(self, operand):
        if operand == None:
            return 1
        elif isinstance(operand, types.BooleanType): 
            return 0 if self and operand else 1 if self else -1

        operand = SCSSBoolean(operand)
        if self.value == operand.value:
            return 0
        else:
            return 1 if self.value else -1

    def __nonzero__(self):
        return self.value


class SCSSList(SCSSVariable):
    def __init__(self, value = None, separator = " "):
        SCSSVariable.__init__(self)

        self.items = []
        self.separator = separator
        if value:
            self.append(value)

    @staticmethod
    def fromTokens(tokens, scope = None):
        list = SCSSList()
        for token in tokens:
            if token.isDelimiter(","):
                list.separator = ","
            if (token.isWhiteSpace() or token.isComment() or
                token.isDelimiter(list.separator)):
                continue
            list.append(SCSSVariable.fromToken(token, scope))
        return list

    @staticmethod
    def fromVariables(variables):
        list = SCSSList()
        for variable in variables:
            list.append(variable)
        return list

    @staticmethod
    def fromOperands(operand1, operand2):
        result = SCSSList()
        if operand1.isList():
            result.items = operand1.items
            result.separator = operand1.separator
            result.append(operand2)
        elif operand2.isList():
            result.items = operand2.items
            result.separator = operand2.separator
            result.prepend(operand1)
        else:
            result.items = [operand1, operand2]
        return result

    def append(self, value):
        if isinstance(value, cssparser.CSSToken):
            if not value.isWhiteSpace():
                self.items.append(SCSSVariable.fromToken(value))
        elif isinstance(value, SCSSVariable):
            if value.isList():
                for item in value.items:
                    self.append(item)
            else:
                self.items.append(value)
        elif isinstance(value, str) or isinstance(value, unicode):
            self.items.append(SCSSString(value))
        elif isinstance(value, int):
            self.items.append(SCSSNumber(value))
        else:
            raise SCSSRunTimeError("Unrecognized value \"%s\" appended to list" % value)

    def prepend(self, value):
        if isinstance(value, cssparser.CSSToken):
            if not value.isWhiteSpace():
                self.items.insert(0, SCSSVariable.fromToken(value))
        elif isinstance(value, SCSSVariable):
            if value.isList():
                for item in value.items:
                    self.items.insert(0, item)
            else:
                self.items.insert(0, value)
        elif isinstance(value, str) or isinstance(value, unicode):
            self.items.insert(0, SCSSString(value))
        elif isinstance(value, int):
            self.items.insert(0, SCSSNumber(value))
        else:
            raise SCSSRunTimeError("Unrecognized value \"%s\" prepended to list" % value)

    def at(self, index):
        if index < 0:
            index = len(self.items) + index
        if index < 0 or index >= len(self.items):
            raise SCSSRunTimeError("Index %s is out-of-range for list \"%s\"" % (index, self.toString()))
        return self.items[index]

    def replaceAt(self, index, howMany, value):
        if index < 0:
            index = len(self.items) + index
        if index < 0 or index + howMany > len(self.items):
            raise SCSSRunTimeError("Range (%s, %s) is out-of-range for list \"%s\"" % (index, howMany, self.toString()))
        while howMany > 1:
            self.items.pop(index)
            howMany -= 1
        self.items[index] = value

    def toString(self, options = cssparser.CSSOptions()):
        strings = []
        for item in self.items:
            if isinstance(item, SCSSList) and len(item.items) == 0:
                continue
            strings.append(item.toString(options))
        return self.separator.join(strings)

    def __str__(self):
        return self.toString()

    def __add__(self, operand):
        return SCSSList.fromOperands(self, operand)

    def __cmp__(self, operand):
        if operand == None:
            return 1
        elif isinstance(operand, types.BooleanType):
            return 0 if self and operand else 1 if self else -1

        for i in range(0, len(self.items)):
            if len(operand.items) <= i:
                return -1
            value = cmp(str(self.items[i]), str(operand.items[i]))
            if value != 0:
                return value
        if len(operand.items) > len(self.items):
            return 1
        return 0

    def __len__(self):
        return len(self.items) > 0


# placeholder variable that holds a token not recognized to be of any of the
# other variable types
class SCSSToken(SCSSVariable):
    def __init__(self, token = None, scope = None):
        SCSSVariable.__init__(self)
        self.scope = scope

        if token:
            self.setValue(token)
        else:
            self.token = None

    def setValue(self, token):
        if not isinstance(token, cssparser.CSSToken):
            raise SCSSRunTimeError("Unrecognized value \"%s\" assigned to token variable" % value)

        self.token = token

    def toString(self, options = cssparser.CSSOptions()):
        return self.token.toString(options)

    def __str__(self):
        if not self.token:
            return "None"

        return self.token.toString()

    def __add__(self, operand):
        if isinstance(operand, SCSSList):
            return SCSSList.fromOperands(self, operand)

        if not self.token.isIdentifier():
            raise SCSSRunTimeError("Cannot concatenate token \"%s\"" % self.toString())

        if (not isinstance(operand, SCSSString) and
            not (isinstance(operand, SCSSToken) and operand.token.isIdentifier())):
            raise SCSSRunTimeError("Cannot concatenate identifier \"%s\" with \"%s\"" % (self.toString(), operand.toString()))

        if isinstance(operand, SCSSString):
            return SCSSToken(cssparser.CSSAnyToken(None, cssparser.CSS_IDENT_VALUE, self.token.data + operand.value))
        else:
            return SCSSToken(cssparser.CSSAnyToken(None, cssparser.CSS_IDENT_VALUE, self.token.data + operand.token.data))

    def __cmp__(self, operand):
        if operand == None:
            return 1
        elif isinstance(operand, types.BooleanType):
            return 0 if self and operand else 1 if self else -1

        if isinstance(operand, SCSSColor):
            return cmp(operand, value)

        operand = operand.toToken()
        return cmp(self.token.toString(), operand.toString())

    def __nonzero__(self):
        variable = SCSSVariable.fromToken(self.token)
        if isinstance(variable, SCSSToken):
            return True
        else:
            return bool(variable)
