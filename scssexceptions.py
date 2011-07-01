import cssparser


class SCSSException(Exception):
    def __init__(self, message, token = None):
        if token:
            message += " ("
            if token.parent:
                message += "while processing %s in \"%s\"" % (token.__class__.__name__, token.parent.toString(cssparser.CSSOptions(colorize = True)))
            else:
                message += "while processing %s: \"%s\"" % (token.__class__.__name__, token.toString(cssparser.CSSOptions(colorize = True)))
            message += ")"
            
        Exception.__init__(self, message)


class SCSSCompileError(SCSSException):
    pass


class SCSSRunTimeError(SCSSException):
    pass
