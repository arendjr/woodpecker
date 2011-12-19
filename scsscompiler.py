import string
import sys

import cssparser
import scssexpression
import scssfunction
import scssimporter
import scssmixin
import scssvariables

from scssexceptions import *
from scssexpression import SCSSExpression
from scssscope import SCSSScope


class SCSSCompiler(object):
    def __init__(self):
        scope = SCSSScope()
        scssfunction.SCSSFunction.registerBuiltinFunctions(scope)
        self.setGlobalScope(scope)

    def setGlobalScope(self, scope):
        self.scopes = [scope]

    def getGlobalScope(self):
        return self.scopes[0]

    def pushScope(self):
        self.scopes.append(SCSSScope(self.scopes[-1]))

    def pushScope(self):
        self.scopes.append(SCSSScope(self.scopes[-1]))

    def popScope(self):
        if len(self.scopes) == 1:
            raise SCSSRunTimeError("Dude, are you trying to kill me? Don't touch my global scope, please.")
        self.scopes.pop()

    def getCurrentScope(self):
        return self.scopes[-1]

    def compile(self, token, options = cssparser.CSSOptions()):
        if token.isRuleSet():
            self.pushScope()

        if token.isAtRule():
            self.compileAtRule(token, options)
            if token.parent == None: # the token could have been removed
                return

        i = 0
        while i < len(token.children):
            child = token.children[i]
            if child.parent == None:
                raise SCSSCompileError("Child is looking for its parents, please report at the tent next to the main stage", child)
            self.compile(child, options)
            if child.parent: # the token could have been removed
                i += 1

        if token.isAnyToken():
            self.compileAny(token)
        elif token.isValue():
            self.compileValue(token)
        elif token.isDeclaration():
            self.compileDeclaration(token)
        elif token.isAssignment():
            SCSSExpression.processAssignment(token, self.getCurrentScope())
        elif token.isRuleSet():
            self.compileRuleSet(token)
            self.popScope()
        elif token.isAtRule() and token.getKeyWord() == "extend":
            self.processExtend(token)

    def compileAtRule(self, token, options):
        keyword = token.getKeyWord()
        if keyword == "include":
            self.processInclude(token)
        elif keyword == "mixin":
            self.defineMixin(token)
        elif keyword == "function":
            self.defineFunction(token)
        elif keyword == "import":
            self.processImport(token, options)
        elif keyword == "warn":
            self.processWarn(token)
        elif keyword == "if":
            self.processIf(token)

    def processInclude(self, token):
        nameToken = token.getFirstChild(True).getNextSibling(True)
        if nameToken:
            if nameToken.isIdentifier():
                name = nameToken.data
                arguments = []
            elif nameToken.isFunction():
                name = nameToken.getName()
                arguments = nameToken.getArguments(includeCommas = True)
            else:
                raise SCSSCompileError("Unexpected token in mixin definition", nameToken)
        else:
            raise SCSSCompileError("Mixin is missing a name", token)

        scope = self.getCurrentScope()
        if not scope.hasMixin(name):
            raise SCSSCompileError("No mixin defined with the name %s" % name, token)

        tokens = scope.getMixin(name).evaluate(scope, arguments)
        index = token.ownIndex() + 1
        for newToken in tokens:
            token.parent.insertAt(index, newToken)
            index += 1
        token.remove()

    def defineMixin(self, token):
        nameToken = token.getFirstChild(True).getNextSibling(True)
        if nameToken:
            if nameToken.isIdentifier():
                name = nameToken.data
                arguments = []
            elif nameToken.isFunction():
                name = nameToken.getName()
                arguments = nameToken.getArguments(includeCommas = True)
            else:
                raise SCSSCompileError("Unexpected token in mixin definition", nameToken)
        else:
            raise SCSSCompileError("Mixin is missing a name", token)

        blockToken = nameToken.getNextSibling(True)
        if blockToken == None or not blockToken.isBlock():
            raise SCSSCompileError("Mixin is missing a body", blockToken or token)

        mixin = scssmixin.SCSSMixin(name, self.getCurrentScope(), arguments, blockToken)
        self.getCurrentScope().setMixin(name, mixin)
        token.remove()

    def defineFunction(self, token):
        nameToken = token.getFirstChild(True).getNextSibling(True)
        if nameToken:
            if nameToken.isIdentifier():
                name = nameToken.data
                arguments = []
            elif nameToken.isFunction():
                name = nameToken.getName()
                arguments = nameToken.getArguments(includeCommas = True)
            else:
                raise SCSSCompileError("Unexpected token in function definition", nameToken)
        else:
            raise SCSSCompileError("Function is missing a name", token)

        blockToken = nameToken.getNextSibling(True)
        if not blockToken or not blockToken.isBlock():
            raise SCSSCompileError("Function is missing a body", blockToken or token)

        function = scssfunction.SCSSFunction(name, self.getCurrentScope(), arguments, blockToken)
        self.getCurrentScope().setFunction(name, function)
        token.remove()

    def processImport(self, token, options):
        nameToken = token.getFirstChild(True).getNextSibling(True)
        nextToken = nameToken.getNextSibling(True)
        foundImport = False
        while (nameToken and nameToken.isString() and
               (len(nameToken.data) < 9 or nameToken.data[1:8] != "http://") and
               (len(nameToken.data) < 6 or nameToken.data[-5:-1] != ".css") and
               (not nextToken or nextToken.isDelimiter(",;"))):

            try:
                foundImport = True
                resource = nameToken.data[1:-1]
                import scssimporter
                scssimporter.Importer.importScss(self.getCurrentScope(), token, resource, options)
            except Exception, exception:
                raise SCSSCompileError(str(exception) + " while importing resource " + resource)

            if nextToken:
                nameToken = nextToken.getNextSibling(True)
                if nameToken:
                    nextToken = nameToken.getNextSibling(True)

        if foundImport:
            token.remove()

    def processWarn(self, token):
        for child in token.children:
            self.compile(child)
        sys.stderr.write(token.toString() + "\n")
        token.remove()

    def processIf(self, token, elseIf = False, alreadyTrue = False):
        if alreadyTrue:
            value = False
        else:
            tokens = token.getSignature()
            if elseIf and len(tokens) > 0 and tokens[0].isKeyword("if"):
                tokens = tokens[1:]
            if len(tokens) == 0:
                value = not alreadyTrue
            else:
                expression = scssexpression.SCSSExpression(tokens)
                expression.evaluate(self.getCurrentScope())
                if len(expression.tokens) == 0:
                    value = False
                elif len(expression.tokens) == 1:
                    value = bool(scssvariables.SCSSVariable.fromToken(expression.tokens[0]))
                else:
                    value = True

        if value:
            block = token.getBlock()
            insertToken = token
            for child in block.children[1:-1]:
                child.insertAfter(insertToken)
                insertToken = child
            nextToken = insertToken.getNextSibling(True)
        else:
            nextToken = token.getNextSibling(True)
        
        if nextToken and nextToken.isAtRule() and nextToken.getKeyWord() == "else":
            self.processIf(nextToken, elseIf = True, alreadyTrue = value or alreadyTrue)
        token.remove()

    def compileDeclaration(self, token):
        self.processNestedProperties(token)

    def processNestedProperties(self, token):
        value = token.getValue()
        block = value.getBlock()
        if not block:
            return

        prefix = token.getProperty().toString() + "-"
        parent = token.parent
        insertIndex = token.ownIndex() + 1
        for child in block.children:
            if child.isDeclaration():
                child.replaceAt(0, 1, cssparser.CSSPropertyToken(child, prefix + child.getProperty().toString()))
                parent.insertAt(insertIndex, child)
                parent.insertAt(insertIndex + 1, cssparser.CSSDelimiterToken(token.parent, ";"))
                insertIndex += 2

        if block.getPreviousSibling(True):
            token.createDelimiterChild(";").insertAfter(token)
            value.removeChild(block)
        else:
            token.remove()

    def compileRuleSet(self, token):
        nestedRules = []
        for child in token.children:
            if child.isRuleSet():
                nestedRules.append(child)

        self.processNestedRules(token, nestedRules)

    def processNestedRules(self, token, nestedRules):
        if len(nestedRules) == 0:
            return

        parentSelector = token.getSelector()
        parentSubSelectors = parentSelector.getSubSelectors()
        for ruleSet in reversed(nestedRules):
            selector = ruleSet.getSelector()

            ampersand = selector.getAmpersand()
            if ampersand:
                while ampersand:
                    elderly = []
                    sibling = ampersand.getPreviousSibling()
                    while sibling:
                        elderly.insert(0, sibling)
                        sibling = sibling.getPreviousSibling()
                    youngsters = []
                    sibling = ampersand.getNextSibling()
                    while sibling:
                        youngsters.append(sibling)
                        sibling = sibling.getNextSibling()

                    ampersand = None
                    selector.children = []
                    for sub1 in parentSubSelectors:
                        for child in elderly:
                            selector.add(child.clone())
                        for child in sub1:
                            selector.add(child.clone())
                        for child in youngsters:
                            clone = child.clone()
                            selector.add(clone)
                            if not ampersand and child.isDelimiter("&"):
                                ampersand = clone
                        selector.createDelimiterChild(",")
                    selector.getLastChild().remove() # remove last comma
            else:
                subSelectors = selector.getSubSelectors()
                selector.children = []
                for sub1 in parentSubSelectors:
                    for sub2 in subSelectors:
                        for child in sub1:
                            selector.add(child.clone())
                        selector.createSpaceChild()
                        for child in sub2:
                            selector.add(child.clone())
                        selector.createDelimiterChild(",")
                selector.getLastChild().remove() # remove last comma

            token.removeChild(ruleSet)
            ruleSet.insertAfter(token)

    def compileValue(self, token):
        expression = SCSSExpression.fromToken(token)
        tokens = expression.evaluate(self.getCurrentScope())
        if tokens:
            token.setChildren(tokens)

    def compileAny(self, token):
        if ((token.isString() or token.isIdentifier()) and
            token.data.find("#{") > -1):
            token.replaceWith(SCSSExpression.processInterpolation(token, self.getCurrentScope()))

    def processExtend(self, token):
        ruleSets = token.getStyleSheet().getRuleSets()
        mySelector = token.getParentRuleSet().getSelector()
        options = cssparser.CSSOptions(stripWhiteSpace = True)
        signatureString = cssparser.tokenListToString(token.getSignature(), options)
        for ruleSet in ruleSets:
            selector = ruleSet.getSelector()
            for sub1 in selector.getSubSelectors():
                if cssparser.tokenListToString(sub1, options) == signatureString:
                    for sub2 in mySelector.getSubSelectors():
                        if selector.getLastChild().isWhiteSpace():
                            selector.getLastChild().remove()
                        selector.createDelimiterChild(",")
                        for child in sub2:
                            selector.add(child.clone())
                    break
        token.remove()
