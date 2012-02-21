import cssparser
import scssvariables

from scssexceptions import *


class SCSSExpression(object):
    def __init__(self, tokens = []):
        self.value = cssparser.CSSValueToken(None)
        self.value.setChildren(tokens)
        self.tokens = self.value.children

    @staticmethod
    def fromString(expression, options = None):
        if options:
            options.compileScss = True
        else:
            options = cssparser.CSSOptions(compileScss = True)
        stream = cssparser.CSSStream(expression, options)
        return SCSSExpression.fromStream(stream)

    @staticmethod
    def fromStream(stream):
        options = cssparser.CSSOptions(compileScss = True)
        value = cssparser.CSSValueToken(None)
        token = value
        while token and not stream.isEndOfFile():
            token = token.process(stream, options)
        return SCSSExpression(value.getStrippedChildren())

    @staticmethod
    def fromToken(token):
        if not isinstance(token, cssparser.CSSValueToken):
            raise SCSSRunTimeException("Cannot create an SCSS expression from \"%s\"" % token.toString())

        return SCSSExpression(token.getStrippedChildren())

    @staticmethod
    def processInterpolation(token, scope = None):
        result = ""
        stream = cssparser.CSSStream(token.data[1:-1] if token.isString() else token.data)
        character = stream.take()
        while character != cssparser.CSS_EOF:
            if character == "#" and stream.current() == "{":
                stream.take() # skip the {
                expression = SCSSExpression.fromStream(stream)
                expression.evaluate(scope)
                result += expression.toString(cssparser.CSSOptions(stripQuotes = True))
                stream.take() # skip the }
            else:
                if character == "\"":
                    result += "\\"
                result += character
            character = stream.take()
        if token.isString():
            return cssparser.CSSStringToken(None, "\"" + result + "\"")
        else:
            return cssparser.CSSIdentifierToken(None, result)

    @staticmethod
    def processAssignment(token, scope):
        name = token.getVariable().getName()
        expression = SCSSExpression.fromToken(token.getValue())

        if (len(expression.tokens) > 0 and
            expression.value.getLastChild(True).isKeyword("!default")):
            if scope.has(name):
                return
            expression.value.getLastChild(True).remove()
            while (len(expression.tokens) > 0 and
                   expression.value.getLastChild().isWhiteSpace()):
                expression.value.getLastChild().remove()

        expression.evaluate(scope)
        if len(expression.tokens) == 1:
            value = scssvariables.SCSSVariable.fromToken(expression.tokens[0], scope)
        else:
            value = scssvariables.SCSSList.fromTokens(expression.tokens, scope)
        scope.set(name, value)

    @staticmethod
    def evaluateSet(token, scope):
        expression = SCSSExpression(token.getStrippedChildren())
        expression.evaluate(scope, processSlash = True)
        if len(expression.tokens) == 0:
            raise SCSSCompileError("Cannot evaluate an empty set", token)
        elif len(expression.tokens) == 1:
            return scssvariables.SCSSVariable.fromToken(expression.tokens[0], scope)
        else:
            return scssvariables.SCSSList.fromTokens(expression.tokens, scope)

    @staticmethod
    def evaluateVariable(token, scope):
        expression = SCSSExpression(token.getStrippedChildren())
        expression.evaluate(scope, processSlash = True)
        if len(expression.tokens) == 0:
            raise SCSSCompileError("Cannot evaluate an empty set", token)
        elif len(expression.tokens) == 1:
            return scssvariables.SCSSVariable.fromToken(expression.tokens[0], scope)
        else:
            return scssvariables.SCSSList.fromTokens(expression.tokens, scope)

    def evaluate(self, scope = None, parentPriority = 0, startIndex = 0, processSlash = False):
        i = startIndex
        returnTokens = []
        while i < len(self.tokens) and len(returnTokens) == 0:
            token = self.tokens[i]
            if token.isWhiteSpace() or token.isComment():
                i += 1
                continue

            if token.isSet():
                value = SCSSExpression.evaluateSet(token, scope)
                self.value.replaceAt(i, 1, value.toToken())
            elif token.isVariable():
                value = scssvariables.SCSSVariable.fromToken(token, scope)
                self.value.replaceAt(i, 1, value.toToken())
            elif token.isFunction():
                name = token.getName()
                if scope.hasFunction(name):
                    function = scope.getFunction(name)
                    arguments = token.getArguments(includeCommas = True)
                    value = function.evaluate(scope, arguments)
                    self.value.replaceAt(i, 1, value.toToken())
            else:
                priority = self.priorityFromToken(token)

                if priority == 0 and parentPriority > 0:
                    j = i
                    while j > startIndex:
                        if (not self.tokens[j].isWhiteSpace() and
                            not self.tokens[j].isComment()):
                            returnTokens = self.tokens[startIndex:j - 1]
                            break
                        j -= 1
                    if len(returnTokens) > 0:
                        break

                while i < len(self.tokens) - 1 and priority > 0:
                    if priority and parentPriority and priority <= parentPriority:
                        returnTokens = self.tokens[startIndex:i]
                        break

                    nextToken = token.getNextSibling(True)
                    if nextToken == None:
                        break

                    nextIndex = nextToken.ownIndex()
                    if token.isKeyword("not"): # unary operator
                        i += 1
                        previousToken = token

                        operator = "not"
                        operand1 = self.evaluate(scope, priority, nextIndex, processSlash = True)
                        operand2 = None
                        if operand1 == None:
                            break
                    else:
                        previousToken = token.getPreviousSibling(True)
                        if previousToken:
                            # little special treatment for the / operator
                            if (token.isOperator("/") and not processSlash and
                                not previousToken.isVariable() and not nextToken.isVariable()):
                                break

                            operator = token.data
                            operand1 = scssvariables.SCSSVariable.fromToken(previousToken, scope)
                            operand2 = self.evaluate(scope, priority, nextIndex, processSlash = True)
                            if operand2 == None:
                                break
                        else:
                            i += 1
                            if token.isOperator("-"): # unary operator
                                previousToken = token
                                operator = "-"
                                operand1 = scssvariables.SCSSNumber(0)
                                operand2 = self.evaluate(scope, priority, nextIndex, processSlash = True)
                            else:
                                continue

                    for j in range(0, nextIndex - i):
                        self.value.removeChildAt(i)
                    if (i > 0 and self.tokens[i - 1].isWhiteSpace() and
                        (i == len(self.tokens) or self.tokens[i].isWhiteSpace())):
                        self.value.removeChildAt(i - 1)

                    result = operand1.apply(operator, operand2).toToken()
                    previousToken.replaceWith(result)
                    i = result.ownIndex() + 1

                    if i < len(self.tokens) - 1:
                        token = self.tokens[i]
                        priority = self.priorityFromToken(token)

            i += 1

        if parentPriority:
            if len(returnTokens) == 0:
                returnTokens = self.tokens[startIndex:i]

            for i in range(0, len(returnTokens)):
                self.value.removeChildAt(startIndex)
            while (len(returnTokens) > 0 and
                   (returnTokens[-1].isWhiteSpace() or returnTokens[-1].isComment())):
                returnTokens = returnTokens[0:-1]

            if len(returnTokens) > 1:
                raise SCSSRunTimeError("A sub-expression should never return more than one token", token = self.tokens[0])

            return scssvariables.SCSSVariable.fromToken(returnTokens[0], scope)
        else:
            return self.tokens

    def priorityFromToken(self, token):
        if token.isKeyword("not"):
            return 5
        if token.isDelimiter("*/%"):
            return 4
        if token.isDelimiter("+-"):
            return 3
        if (token.isOperator("==") or token.isOperator("!=") or
            token.isOperator("<=") or token.isOperator(">=") or
            token.isOperator("<") or token.isOperator(">")):
            return 2
        if token.isKeyword("and") or token.isKeyword("or"):
            return 1
        return 0    

    def toString(self, options = cssparser.CSSOptions()):
        string = ""
        for token in self.tokens:
            string += token.toString(options)
        return string
