import scssvariables

from scssexceptions import *
from scssfunction import SCSSFunction
from scssscope import SCSSScope


class SCSSBuiltinFunction(SCSSFunction):
    def __init__(self, function, name = None, numArgs = None):
        name = name or function.__name__
        self.name = name.replace("_", "-")
        self.function = function

        self.arguments = []
        if numArgs == None:
            self.numArgs = function.func_code.co_argcount
            dd = self.numArgs - len(function.func_defaults) if function.func_defaults else self.numArgs
            for i in range(0, self.numArgs):
                name = function.func_code.co_varnames[i]
                default = function.func_defaults[i - dd] if i >= dd else []
                self.arguments.append((name, default))
        else:
            self.numArgs = numArgs

    def evaluate(self, callerScope, arguments = None):
        scope = SCSSScope()
        if arguments:
            self.mapArguments(arguments, callerScope, scope)

        args = {}
        for name in scope.variables:
            args[name] = scope.get(name)

        return self.function(**args)


def compact(list):
    compactList = []
    for item in list.items:
        if item:
            compactList.append(item)
    return scssvariables.SCSSList.fromVariables(compactList)


def darken(color, amount):
    if not color.isColor():
        raise SCSSRunTimeError("Can only darken colors, not \"%s\"" % color.toString())
    if not amount.isNumber():
        raise SCSSRunTimeError("Cannot darken color \"%s\" by \"%s\"" % (color.toString(), amount.toString()))

    result = scssvariables.SCSSColor(color)
    result.darken(amount.value / 100.0 if amount.unit == "%" else amount.value)
    return result


def first_value_of(value):
    if isinstance(value, scssvariables.SCSSList):
        if len(value.items) > 0:
            return value.items[0]
        else:
            return None
    else:
        return value


def function_if(condition, value1, value2):
    if condition:
        return value1
    else:
        return value2


def lighten(color, amount):
    if not color.isColor():
        raise SCSSRunTimeError("Can only lighten colors, not \"%s\"" % color.toString())
    if not amount.isNumber():
        raise SCSSRunTimeError("Cannot lighten color \"%s\" by \"%s\"" % (color.toString(), amount.toString()))

    result = scssvariables.SCSSColor(color)
    result.lighten(amount.value / 100.0 if amount.unit == "%" else amount.value)
    return result


def opacify(color, opacity):
    if not isinstance(color, scssvariables.SCSSColor):
        raise SCSSRunTimeError("Color argument to opacify() should be a color, but is \"%s\"" % color.toString())

    if not isinstance(opacity, scssvariables.SCSSNumber):
        raise SCSSRunTimeError("Opacity argument to opacify() should be a number, but is \"%s\"" % opacity.toString())

    if opacity.unit == "":
        opacity = scssvariables.clamp(float(opacity.value), 0.0, 1.0)
    elif opacity.unit == "%":
        opacity = scssvariables.clamp(float(opacity.value) / 100.0, 0.0, 1.0)
    else:
        raise SCSSRunTimeError("Opacity argument to opacify() should be a number or percentage, not a dimension in %s units" % opacity.unit)

    return scssvariables.SCSSColor([color.r, color.g, color.b, (1.0 - color.a) * opacity + color.a])


def quote(token):
    if not isinstance(token, scssvariables.SCSSToken):
        raise SCSSRunTimeError("quote() only works on tokens, not on \"%s\"" % token.toString())

    return scssvariables.SCSSString(token.token.toString())


def transparentize(color, opacity):
    if not isinstance(color, scssvariables.SCSSColor):
        raise SCSSRunTimeError("Color argument to transparentize() should be a color, but is \"%s\"" % color.toString())

    if not isinstance(opacity, scssvariables.SCSSNumber):
        raise SCSSRunTimeError("Opacity argument to transparentize() should be a number, but is \"%s\"" % opacity.toString())

    if opacity.unit == "":
        opacity = scssvariables.clamp(float(opacity.value), 0.0, 1.0)
    elif opacity.unit == "%":
        opacity = scssvariables.clamp(float(opacity.value) / 100.0, 0.0, 1.0)
    else:
        raise SCSSRunTimeError("Opacity argument to transparentize() should be a number or percentage, not a dimension in %s units" % opacity.unit)

    return scssvariables.SCSSColor([color.r, color.g, color.b, color.a * opacity])


def type_of(value):
    if isinstance(value, scssvariables.SCSSNumber):
        return scssvariables.SCSSString("number")
    elif isinstance(value, scssvariables.SCSSToken):
        if value.token.isIdentifier():
            return scssvariables.SCSSString("string")
        else:
            variable = scssvariables.SCSSVariable.fromToken(value.token)
            return type_of(variable)
    elif isinstance(value, scssvariables.SCSSString):
        return scssvariables.SCSSString("string")
    elif isinstance(value, scssvariables.SCSSBoolean):
        return scssvariables.SCSSString("bool")
    elif isinstance(value, scssvariables.SCSSColor):
        return scssvariables.SCSSString("color")
    raise SCSSRunTimeError("Unknown type of \"%s\"" % value.toString)


def unquote(string):
    if not isinstance(string, scssvariables.SCSSString):
        raise SCSSRunTimeError("unquote() only works on strings, not on \"%s\"" % string.toString())

    return scssvariables.SCSSToken(cssparser.CSSIdentifier(None, string.value))


FUNCTIONS = [
    SCSSBuiltinFunction(compact, numArgs = -1),
    SCSSBuiltinFunction(darken),
    SCSSBuiltinFunction(first_value_of),
    SCSSBuiltinFunction(function_if, name = "if"),
    SCSSBuiltinFunction(lighten),
    SCSSBuiltinFunction(opacify),
    SCSSBuiltinFunction(quote),
    SCSSBuiltinFunction(transparentize),
    SCSSBuiltinFunction(type_of),
    SCSSBuiltinFunction(unquote)
]
