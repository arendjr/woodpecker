import types

import scssvariables

from scssexceptions import *
from scssexpression import SCSSExpression
from scssscope import SCSSScope


class SCSSFunction(object):
    def __init__(self, name, scope, arguments, body):
        self.name = name
        self.scope = SCSSScope(scope)
        self.arguments = self.tokensToArguments(arguments, scope)
        self.numArgs = len(self.arguments)
        self.body = self.tokenToBody(body)

    @staticmethod
    def registerBuiltinFunctions(scope):
        import scssbuiltinfunctions
        for function in scssbuiltinfunctions.FUNCTIONS:
            scope.setFunction(function.name, function)

    def typeName(self):
        import scssmixin
        return "mixin" if isinstance(self, scssmixin.SCSSMixin) else "function"

    def tokensToArguments(self, argumentTokens, scope):
        arguments = []
        variable = None
        hasColon = False
        defaultValue = []
        for token in argumentTokens:
            if token.isDelimiter(":"):
                if variable:
                    hasColon = True
                    continue
            elif token.isDelimiter(","):
                if variable:
                    defaultValue = self.tokensToValue(defaultValue, scope)
                    arguments.append((variable, defaultValue))
                    variable = None
                    hasColon = False
                    defaultValue = []
                    continue
            else:
                if hasColon:
                    defaultValue.append(token)
                    continue
                elif token.isVariable() and not variable:
                    variable = token.getName()
                    continue

            raise SCSSCompileError("Invalid token in argument definition", token)

        if variable:
            defaultValue = self.tokensToValue(defaultValue, scope)
            arguments.append((variable, defaultValue))

        return arguments

    def tokenToBody(self, token):
        if not isinstance(token, cssparser.CSSBlockToken):
            raise SCSSRunTimeError("Body of function %s must be a block token (but isn't)" % self.name)
        body = []
        for i in range(1, len(token.children) - 1):
            child = token.children[i]
            if (not child.isComment()) and (not child.isWhiteSpace()):
                body.append(child)
        return body

    def tokensToValue(self, tokens, scope):
        if not tokens or len(tokens) == 0:
            return None
        expression = SCSSExpression(tokens)
        expression.evaluate(scope)
        if not expression.tokens or len(expression.tokens) == 0:
            raise SCSSCompileError("Expression, expression, why did you eat my tokens?", tokens[0])
        elif len(expression.tokens) == 1:
            return scssvariables.SCSSVariable.fromToken(expression.tokens[0])
        else:
            return scssvariables.SCSSList.fromTokens(expression.tokens)

    def mapArguments(self, argumentTokens, callerScope, targetScope):
        if self.numArgs == -1:
            targetScope.set("list", scssvariables.SCSSList.fromTokens(argumentTokens, callerScope))
            return

        if len(argumentTokens) == 1 and argumentTokens[0].isVariable():
            variable = scssvariables.SCSSVariable.fromToken(argumentTokens[0], callerScope)
            if variable.isList():
                # arguments given as list
                self.mapArgumentsList(variable, callerScope, targetScope)
                self.setDefaultArguments(targetScope)
                return

        variable = None
        value = []
        position = 0
        for token in argumentTokens:
            if token.isDelimiter(":"):
                if len(value) == 1 and value[0].isVariable():
                    variable = value.pop().getName()
                    continue
            elif token.isDelimiter(",") or (variable == None and len(value) == 1):
                try:
                    if variable == None:
                        if position >= self.numArgs:
                            break
                        variable = self.arguments[position][0]
                    if targetScope.has(variable):
                        raise SCSSCompileError("Argument $%s is set more than once" % variable, token)
                    value = self.tokensToValue(value, callerScope)
                    if value == None:
                        raise SCSSRunTimeError("Argument $%s has no value (%s)" % (variable, value.toString()), token)
                except Exception, exception:
                    raise SCSSRunTimeError(str(exception) + " in call to %s %s" % (self.typeName(), self.name))

                targetScope.set(variable, value)
                position += 1

                variable = None
                value = []
                if not token.isDelimiter(","):
                    value.append(token)
                continue
            else:
                value.append(token)
                continue

            raise SCSSCompileError("Invalid token in argument list", token)

        if len(value) > 0 and position < len(self.arguments):
            if variable == None:
                variable = self.arguments[position][0]
            if targetScope.has(variable):
                raise SCSSCompileError("Argument $%s is set more than once" % variable)
            value = self.tokensToValue(value, callerScope)
            if value == None:
                raise SCSSRunTimeError("Argument $%s has no value" % variable)

            targetScope.set(variable, value)

        self.setDefaultArguments(targetScope)

    def mapArgumentsList(self, list, callerScope, targetScope):
        position = 0
        for value in list.items:
            if position >= self.numArgs:
                break
            variable = self.arguments[position][0]
            targetScope.set(variable, value)
            position += 1

    def setDefaultArguments(self, targetScope):
        for argument in self.arguments:
            (name, defaultValue) = argument
            if not targetScope.has(name):
                if defaultValue != None:
                    targetScope.set(name, defaultValue)
                else:
                    raise SCSSCompileError("Missing argument $%s in call to %s %s" % (name, self.typeName(), self.name), token.parent)

    def evaluate(self, callerScope, arguments = None):
        try:
            scope = self.scope.clone()
            if arguments:
                self.mapArguments(arguments, callerScope, scope)
    
            for token in self.body:
                if token.isAssignment():
                    SCSSExpression.processAssignment(token, scope)
                elif token.isAtRule() and token.getKeyWord() == "return":
                    expression = SCSSExpression(token.getSignature())
                    expression.evaluate(scope)
                    if len(expression.tokens) == 0:
                        raise SCSSRunTimeError("Could not evaluate return statement of function %s" % self.name)
                    elif len(expression.tokens) == 1:
                        return scssvariables.SCSSVariable.fromToken(expression.tokens[0])
                    else:
                        return scssvariables.SCSSList.fromTokens(expression.tokens)
                else:
                    raise SCSSRunTimeError("Unexpected token in function %s" % self.name, token)
    
            raise SCSSRunTimeError("Function %s does not return a value" % self.name)
        except Exception, exception:
            raise SCSSRunTimeError(str(exception) + "\n  In call to function " + self.name)
