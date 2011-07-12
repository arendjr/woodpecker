import copy
import string


class CSSOptions(object):
    def __init__(self, options = None, stripWhiteSpace = False, stripComments = False, minimizeValues = False,
                 stripExtraSemicolons = False, colorize = False, compileScss = False, stripQuotes = False, importCss = True, **keywords):
        if options:
            self.stripWhiteSpace = stripWhiteSpace if "stripWhiteSpace" in keywords.keys() else options.stripWhiteSpace
            self.stripComments = stripComments if "stripComments" in keywords.keys() else options.stripComments
            self.minimizeValues = minimizeValues if "minimizeValues" in keywords.keys() else options.minimizeValues
            self.stripExtraSemicolons = stripExtraSemicolons if "stripExtraSemicolons" in keywords.keys() else options.stripExtraSemicolons
            self.colorize = colorize if "colorize" in keywords.keys() else options.colorize
            self.compileScss = compileScss if "compileScss" in keywords.keys() else options.compileScss
            self.stripQuotes = stripQuotes if "stripQuotes" in keywords.keys() else options.stripQuotes
            self.importCss = importCss if "importCss" in keywords.keys() else options.importCss
        else:
            self.stripWhiteSpace = stripWhiteSpace
            self.stripComments = stripComments
            self.minimizeValues = minimizeValues
            self.stripExtraSemicolons = stripExtraSemicolons
            self.colorize = colorize
            self.compileScss = compileScss
            self.stripQuotes = stripQuotes
            self.importCss = importCss


def colorize(string, color):
    return "\x1B[" + color + "m" + string + "\x1B[00m"

def minimizeColorValue(token):
    import scssvariables
    variable = scssvariables.SCSSColor(token)
    return variable.toString()

def tokenListToString(tokenList, options = CSSOptions()):
    string = ""
    for token in tokenList:
        string += token.toString(options)
    return string


CSS_EOF = "EOF"
CSS_UNKNOWN_VALUE = "UNKNOWN"
CSS_IDENT_VALUE = "IDENT"
CSS_NUMBER_VALUE = "NUMBER"
CSS_PERCENTAGE_VALUE = "PERCENTAGE"
CSS_DIMENSION_VALUE = "DIMENSION"
CSS_STRING_VALUE = "STRING"
CSS_URI_VALUE = "URI"
CSS_HASH_VALUE = "HASJ"
CSS_FUNCTION_VALUE = "FUNCTION"
CSS_SET_VALUE = "SET"
CSS_LIST_VALUE = "LIST"
CSS_DELIM_VALUE = "DELIM"
SCSS_VARIABLE_VALUE = "VARIABLE"


class CSSParseError(Exception):
    def __init__(self, message, stream = None, token = None):
        if stream or token:
            message += " ("
            if stream:
                message += "in fragment: \"%s\", at line %d, column %d" % (stream.peekRange(-10, 20).replace("\n", ""), stream.line, stream.column)
            if token:
                if stream:
                    message += ", "
                if token.parent:
                    message += "while parsing token: \"%s\"" % token.parent.toString(CSSOptions(colorize = True))
                else:
                    message += "while parsing token: \"%s\"" % token.toString(CSSOptions(colorize = True)) 
            message += ")"
            
        Exception.__init__(self, message)


class CSSParser(object):
    def parse(self, css, options = CSSOptions()):
        stream = CSSStream(css, options)
        styleSheet = CSSStyleSheetToken()
        token = styleSheet
        while not stream.isEndOfFile():
            token = token.process(stream, options)
        return styleSheet


class CSSStream(object):
    def __init__(self, buffer, options = CSSOptions()):
        self.buffer = buffer
        self.options = options
        self.pos = 0
        self.line = 1
        self.column = 1

    def current(self):
        return self.peek(0)

    def take(self, num = 1):
        characters = ""
        while num > 0:
            character = self.current()
            if character == CSS_EOF:
                return character
            self.advance()
            if ord(character) == 13 and ord(self.current()) == 10:
                character += self.take()
            elif self.isEscape(-1):
                character += self.take()
            characters += character
            num -= 1
        return characters

    def takeIdentifier(self):
        if not self.isIdentifierStart():
            raise CSSParseError("Current character is not an identifier", self)

        characters = self.take()
        if self.options.compileScss and characters == "#":
            characters = ""
            self.pos -= 1 # this hurts, but the alternative is even less elegant
        while self.isNameChar():
            if (self.options.compileScss and
                self.current() == "#" and self.peek(1) == "{"):
                characters += self.take(2)
                while self.current() != "}" and not self.isEndOfFile():
                    characters += self.take()
                if self.current() != "}":
                    break
            characters += self.take()
        return characters

    def takeName(self):
        if not self.isNameChar():
            raise CSSParseError("Current character is not a name", self)

        characters = self.take()
        while self.isNameChar():
            characters += self.take()
        return characters

    def takeNumber(self):
        if not self.isNumberStart():
            raise CSSParseError("Current character is not a number", self)

        characters = self.take()
        numDots = 0
        while self.isNumberChar():
            character = self.take()
            if character == ".":
                numDots += 1
            characters += character

        if characters[-1] == "." or numDots > 1:
            raise CSSParseError("Error parsing number", self)

        return characters

    def takeAtKeyword(self):
        if self.current() != "@":
            raise CSSParseError("Current character is not an @ keyword", self)

        return self.take() + self.takeIdentifier()

    def takeUri(self):
        if self.isStringStart():
            return self.takeString()

        if not self.isUrlChar():
            raise CSSParseError("Current character is not a URI", self)

        characters = self.take()
        while self.isUrlChar():
            characters += self.take()
        return characters

    def takeString(self):
        if self.current() == "'":
            characters = self.take()
            while self.current() != "'":
                if self.current() == CSS_EOF:
                    raise CSSParseError("Unexpected end-of-file", self)

                characters += self.take()

            characters += self.take()
            return characters

        if self.current() == "\"":
            characters = self.take()
            while self.current() != "\"":
                if self.current() == CSS_EOF:
                    raise CSSParseError("Unexpected end-of-file", self)

                characters += self.take()

            characters += self.take()
            return characters

        raise CSSParseError("Current character is not a string", self)

    def takeWhiteSpace(self):
        characters = ""
        while not self.isEndOfFile() and self.isWhiteSpaceChar():
            characters += self.take()
        return characters

    def advance(self):
        if self.isNewline():
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        self.pos += 1

    def peek(self, offset):
        pos = self.pos + offset
        if pos >= len(self.buffer):
            return CSS_EOF
        if pos < 0:
            return ""
        return self.buffer[pos]

    def peekRange(self, offset = 0, num = 1):
        characters = ""
        for i in range(0, num):
            character = self.peek(offset + i)
            if character != CSS_EOF:
                characters += character
        return characters

    def findFirstDelimiter(self, characterRange, offset = 0):
        character = self.peek(offset)
        while character != CSS_EOF:
            if character in characterRange:
                return (character, offset)

            if self.isIdentifierStart(offset):
                while self.isNameChar(offset):
                    if self.peek(offset) == "#" and self.peek(offset + 1) == "{":
                        offset += 2
                        while self.peek(offset) != "}" and not self.isEndOfFile(offset):
                            offset += 1
                    offset += 1
            else:
                offset += 1
            character = self.peek(offset)
        return (CSS_EOF, offset)

    def isEndOfFile(self, offset = 0):
        return self.peek(offset) == CSS_EOF

    def isVariableStart(self, offset = 0):
        return self.peek(offset) == "$"

    def isIdentifierStart(self, offset = 0):
        return (self.isNameStart(offset) or
                (self.peek(offset) == "-" and self.isNameStart(offset + 1)))

    def isNameStart(self, offset = 0):
        return (self.peek(offset) in string.ascii_letters + "_" or
                self.isNonAscii(offset) or
                self.isEscape(offset) or
                (self.options.compileScss and self.peek(offset) == "#" and self.peek(offset + 1) == "{"))

    def isNameChar(self, offset = 0):
        return (self.peek(offset) in string.ascii_letters + "_-0123456789" or
                self.isNonAscii(offset) or
                self.isEscape(offset) or
                (self.options.compileScss and self.peek(offset) == "#"))

    def isNumberStart(self, offset = 0):
        return (self.isNumberChar(offset) or
                (self.peek(offset) == "-" and self.isNumberChar(offset + 1)))

    def isNumberChar(self, offset = 0):
        character = self.peek(offset)
        return (character in "0123456789" or
                (character == "." and self.peek(offset + 1) in "0123456789"))

    def isStringStart(self, offset = 0):
        return self.peek(offset) in "'\""

    def isStringChar(self, offset = 0):
        character = self.peek(offset)
        if character == CSS_EOF:
            return False
        return (self.isUrlChar(offset) or
                character == " " or
                (character == "\\" and self.isNewline(offset + 1)))

    def isUrlChar(self, offset = 0):
        character = self.peek(offset)
        if character == CSS_EOF:
            return False
        val = ord(character)
        return (val == 9 or val == 33 or (val >= 25 and val <= 126 and val != 41) or
                self.isNonAscii() or
                self.isEscape())

    def isNonAscii(self, offset = 0):
        character = self.peek(offset)
        if character == CSS_EOF:
            return False
        val = ord(character)
        return ((val >= 128 and val <= 55295) or
                (val >= 57344 and val <= 65533) or
                (val >= 65536 and val <= 131071))

    def isEscape(self, offset = 0):
        if self.peek(offset) != "\\":
            return False
        nextCharacter = self.peek(offset + 1)
        if nextCharacter in string.hexdigits:
            return True
        val = ord(nextCharacter)
        return ((val >= 32 and val <= 126) or
                (val >= 128 and val <= 55295) or
                (val >= 57344 and val <= 65533) or
                (val >= 65536 and val <= 131071))

    def isNewline(self, offset = 0):
        return self.peek(offset) in "\x0a\x0c\x0d"

    def isWhiteSpaceChar(self, offset = 0):
        return self.peek(offset) in "\x09\x0a\x0c\x0d\x20"

    def isCommentStart(self, offset = 0):
        if self.peek(offset) != "/":
            return False

        return self.peek(offset + 1) == "*" or (self.options.compileScss and self.peek(offset + 1) == "/")

    def isCommentEnd(self, offset = 0):
        return self.peek(offset) == "*" and self.peek(offset + 1) == "/"


class CSSToken(object):
    def __init__(self, allowedChildren, parent):
        self.allowedChildren = allowedChildren
        self.parent = parent
        self.children = []
        self.data = ""

    # adds a child token to the token
    def add(self, token):
        if len(self.data) > 0:
            raise CSSParseError("Cannot consume data and add children to the same token", token = self)

        if not isinstance(token, tuple(self.allowedChildren)):
            raise CSSParseError("Cannot add %s to %s" % (token.__class__, self.__class__), token = self)

        self.children.append(token)
        self.adopt(token)

    # adds this token as a child right after token
    def insertAfter(self, token):
        if token.parent == None:
            raise CSSParseError("Cannot insert a token after the root token", token = self)

        token.parent.insertAt(token.ownIndex() + 1, self)

    # adds a clone (copy) of itself as a child right after token
    def copyAfter(self, token):
        self.clone().insertAfter(token)

    # adds a space token right after token
    def insertSpaceAfter(self, token):
        CSSWhiteSpaceToken(self, " ").insertAfter(token)

    # adds a token as a child at the given index
    def insertAt(self, index, token):
        if len(self.data) > 0:
            raise CSSParseError("Cannot consume data and add children to the same token", token = self)

        if not isinstance(token, tuple(self.allowedChildren)):
            raise CSSParseError("Cannot add %s to %s" % (token.__class__, self.__class__), token = self)

        self.children.insert(index, token)
        self.adopt(token)

    # adds a clone (copy) of token as a child at the given index
    def copyAt(self, index, token):
        self.insertAt(index, token.clone())

    # adds a token as a child as a replacement for one or more existing children
    def replaceAt(self, index, howMany, token):
        if not isinstance(token, tuple(self.allowedChildren)):
            raise CSSParseError("Cannot add %s to %s" % (token.__class__, self.__class__), token = self)

        while howMany > 1:
            self.children.remove(index)
            howMany -= 1
        self.children[index] = token
        self.adopt(token)

    # replaces this token with another token
    def replaceWith(self, token):
        if self.parent == None:
            raise CSSParseError("Cannot replace the root token", token = self)

        self.parent.children[self.ownIndex()] = token
        self.parent.adopt(token)

    # creates and adds a child token
    def createChild(self, TokenClass):
        token = TokenClass(self)
        self.add(token)
        return token

    # adopts token as a child (without explicitly adding it to the children)
    def adopt(self, token):
        token.parent = self

    # rejects token as a child (without explicitly removing it from the children)
    def reject(self, token):
        token.parent = None

    # creates and adds a child delimiter token which consumes the first stream
    # character
    def createDelimiterChild(self, stream):
        token = CSSDelimiterToken(self)
        token.consume(stream.take() if isinstance(stream, CSSStream) else stream)
        self.add(token)
        return token

    # I just love the name of this one :)
    def createSpaceChild(self):
        token = CSSWhiteSpaceToken(self)
        token.consume(" ")
        self.add(token)
        return token

    # removes the child token at a given index from the children list
    def removeChildAt(self, index):
        self.reject(self.children[index])
        self.children.pop(index)

    # removes a child token from the children list
    def removeChild(self, token):
        self.children.remove(token)
        self.reject(token)

    # removes the token from its parent's children list
    def remove(self):
        if self.parent == None:
            raise CSSParseError("Cannot remove parents from an orphan", token = self)

        self.parent.removeChild(self)

    # replaces all children from a given array of tokens
    def setChildren(self, tokens):
        self.children = tokens
        for child in self.children:
            self.adopt(child)

    # processes a single character from the input stream and returns the token
    # that should process the next character
    def process(self, stream, options = CSSOptions()):
        if stream.isCommentStart():
            parent = self if CSSCommentToken in self.allowedChildren else self.parent
            token = CSSCommentToken(parent)
            token.consume(stream.take(2))
            parent.add(token)
            return token
        if stream.isWhiteSpaceChar():
            if CSSWhiteSpaceToken in self.allowedChildren:
                return self.createChild(CSSWhiteSpaceToken)
        if options.compileScss and stream.isVariableStart():
            if SCSSAssignmentToken in self.allowedChildren:
                return self.createChild(SCSSAssignmentToken)
            if SCSSVariableToken in self.allowedChildren:
                return self.createChild(SCSSVariableToken)
        return self

    # consumes input characters and adds them to the token data
    def consume(self, characters):
        if len(self.children) > 0:
            raise CSSParseError("Cannot consume data and add children to the same token", token = self)

        self.data += characters

    def isStyleSheet(self):
        return isinstance(self, CSSStyleSheetToken)

    def isAtRule(self):
        return isinstance(self, CSSAtRuleToken)

    def isAtKeyword(self):
        return isinstance(self, CSSAtKeywordToken)

    def isBlock(self):
        return isinstance(self, CSSBlockToken)
    
    def isRuleSet(self):
        return isinstance(self, CSSRuleSetToken)
    
    def isSelector(self):
        return isinstance(self, CSSSelectorToken)
    
    def isDeclaration(self):
        return isinstance(self, CSSDeclarationToken)
    
    def isProperty(self):
        return isinstance(self, CSSPropertyToken)
    
    def isValue(self):
        return isinstance(self, CSSValueToken)
    
    def isDelimiter(self, characters = None):
        return (isinstance(self, CSSAnyToken) and self.type == CSS_DELIM_VALUE and
                (characters == None or (len(self.data) == 1 and self.data in characters)))

    def isOperator(self, operator):
        return (isinstance(self, CSSAnyToken) and self.type == CSS_DELIM_VALUE and
                self.data == operator)

    def isAnyToken(self):
        return isinstance(self, CSSAnyToken)

    def isIdentifier(self):
        return isinstance(self, CSSAnyToken) and self.type == CSS_IDENT_VALUE

    def isKeyword(self, keyword):
        return (isinstance(self, CSSAnyToken) and self.type == CSS_IDENT_VALUE and
                self.data == keyword)

    def isNumber(self):
        return isinstance(self, CSSAnyToken) and self.type == CSS_NUMBER_VALUE

    def isPercentage(self):
        return isinstance(self, CSSAnyToken) and self.type == CSS_PERCENTAGE_VALUE

    def isDimension(self):
        return isinstance(self, CSSAnyToken) and self.type == CSS_DIMENSION_VALUE

    def isString(self):
        return isinstance(self, CSSAnyToken) and self.type == CSS_STRING_VALUE

    def isHash(self):
        return isinstance(self, CSSAnyToken) and self.type == CSS_HASH_VALUE

    def isSet(self):
        return isinstance(self, CSSAnyToken) and self.type == CSS_SET_VALUE

    def isList(self):
        return isinstance(self, CSSAnyToken) and self.type == CSS_LIST_VALUE

    def isFunction(self):
        return isinstance(self, CSSAnyToken) and self.type == CSS_FUNCTION_VALUE

    def isComment(self):
        return isinstance(self, CSSCommentToken)
    
    def isWhiteSpace(self):
        return isinstance(self, CSSWhiteSpaceToken)
    
    def isBoundary(self):
        return (isinstance(self, CSSBlockToken) or
                (isinstance(self, CSSAnyToken) and self.type in [CSS_LIST_VALUE, CSS_DELIM_VALUE]))

    def isVariable(self):
        return isinstance(self, SCSSVariableToken)

    def isAssignment(self):
        return isinstance(self, SCSSAssignmentToken)

    def isFirstChild(self, ignoreWhiteSpace = False):
        if self.parent == None:
            return False

        siblings = self.parent.children
        index = siblings.index(self)
        while (index > 0 and
               ignoreWhiteSpace and (siblings[index - 1].isWhiteSpace() or siblings[index - 1].isComment())):
            index -= 1

        return index == 0

    def isLastChild(self, ignoreWhiteSpace = False):
        if self.parent == None:
            return False

        siblings = self.parent.children
        index = siblings.index(self)
        while (index < len(siblings) - 1 and
               ignoreWhiteSpace and (siblings[index + 1].isWhiteSpace() or siblings[index + 1].isComment())):
            index += 1

        return index == len(siblings) - 1

    def getFirstChild(self, ignoreWhiteSpace = False):
        i = 0
        while i < len(self.children):
            if not ignoreWhiteSpace or not (self.children[i].isWhiteSpace() or self.children[i].isComment()):
                return self.children[i]
            i += 1

        return None

    def getLastChild(self, ignoreWhiteSpace = False):
        i = len(self.children) - 1
        while i >= 0:
            if not ignoreWhiteSpace or not (self.children[i].isWhiteSpace() or self.children[i].isComment()):
                return self.children[i]
            i -= 1

        return None

    def getNextSibling(self, ignoreWhiteSpace = False):
        if self.parent == None:
            return None

        siblings = self.parent.children
        i = siblings.index(self) + 1
        while i < len(siblings):
            if not ignoreWhiteSpace or not (siblings[i].isWhiteSpace() or siblings[i].isComment()):
                return siblings[i]
            i += 1

        return None

    def getPreviousSibling(self, ignoreWhiteSpace = False):
        if self.parent == None:
            return None

        siblings = self.parent.children
        i = siblings.index(self) - 1
        while i >= 0:
            if not ignoreWhiteSpace or not (siblings[i].isWhiteSpace() or siblings[i].isComment()):
                return siblings[i]
            i -= 1

        return None

    def getStyleSheet(self):
        token = self
        while token and not token.isStyleSheet():
            token = token.parent
        return token

    def getParentRuleSet(self):
        token = self
        while token and not token.isRuleSet():
            token = token.parent
        return token

    def ownIndex(self):
        if self.parent == None:
            raise CSSParseError("Cannot determine own index of token without parent", self)

        return self.parent.children.index(self)

    # return a clone (copy) of itself
    def clone(self):
        clone = copy.copy(self)
        drones = []
        for child in clone.children:
            if child.isComment():
                continue
            drone = child.clone()
            clone.adopt(drone)
            drones.append(drone)
        clone.children = drones
        return clone

    def performRuleSetVersusDeclarationLookAhead(self, stream):
        # perform some look-ahead processing to distinguish between
        # SCSS nested rules and regular declarations
        (character, offset) = stream.findFirstDelimiter("{:}")
        if character != "}" and character != CSS_EOF:
            if character == "{":
                return self.createChild(CSSRuleSetToken)
            if not stream.isIdentifierStart(offset + 1):
                return self.createChild(CSSDeclarationToken)

            while character != CSS_EOF:
                # the character was a colon, and an identifier followed, but
                # the first identifier could still mean anything...
                (character, offset) = stream.findFirstDelimiter("{};:", offset + 1)
                if character == "{":
                    return self.createChild(CSSRuleSetToken)
                if character in "};" or not stream.isIdentifierStart(offset + 1):
                    return self.createChild(CSSDeclarationToken)

        return None

    # writes all tokens back to a string
    def toString(self, options = CSSOptions()):
        string = ""
        if len(self.children) > 0:
            for token in self.children:
                string += token.toString(options)
        else:
            string += self.data
        return string


class CSSStyleSheetToken(CSSToken):
    def __init__(self):
        CSSToken.__init__(self, [CSSAtRuleToken, CSSRuleSetToken, CSSWhiteSpaceToken, CSSCommentToken, SCSSAssignmentToken], None)
        self.path = "."
        self.ruleSets = []

    def setPath(self, path):
        self.path = path

    def process(self, stream, options = CSSOptions()):
        token = CSSToken.process(self, stream, options)
        if token != self:
            return token

        if stream.current() == "@":
            return self.createChild(CSSAtRuleToken)

        return self.createChild(CSSRuleSetToken)

    def adopt(self, token):
        CSSToken.adopt(self, token)
        if isinstance(token, CSSRuleSetToken):
            self.ruleSets.append(token)

    def reject(self, token):
        CSSToken.reject(self, token)
        if isinstance(token, CSSRuleSetToken):
            self.ruleSets.remove(token)

    def getRuleSets(self):
        return self.ruleSets

    def toString(self, options = CSSOptions()):
        string = ""
        for token in self.children:
            if options.stripWhiteSpace and token.isWhiteSpace():
                continue
            string += token.toString(options)
        return string


class CSSAtRuleToken(CSSToken):
    def __init__(self, parent):
        CSSToken.__init__(self, [CSSAtKeywordToken, CSSWhiteSpaceToken, CSSAnyToken, CSSBlockToken, CSSRuleSetToken, CSSCommentToken, SCSSVariableToken], parent)
        self.block = None

    def process(self, stream, options = CSSOptions()):
        if self.block != None:
            return self.parent

        token = CSSToken.process(self, stream, options)
        if token != self:
            return token

        if len(self.children) == 0:
            return self.createChild(CSSAtKeywordToken)

        if stream.current() == ";":
            self.createDelimiterChild(stream)
            return self.parent

        if stream.current() == "{":
            return self.createChild(CSSBlockToken)

        if stream.current() == "}":
            raise CSSParseError("Invalid character '%s' in stream" % stream.current(), stream, self)

        return self.createChild(CSSAnyToken)

    def adopt(self, token):
        CSSToken.adopt(self, token)
        if isinstance(token, CSSBlockToken):
            self.block = token

    def reject(self, token):
        CSSToken.reject(self, token)
        if self.block == token:
            self.block = None

    def getKeyWord(self):
        if len(self.children) == 0:
            raise CSSParseError("At rule does not have a keyword", token = self)

        return self.children[0].data[1:]

    def getSignature(self):
        tokens = []
        i = 1
        while i < len(self.children):
            token = self.children[i]
            if token.isDelimiter(";") or token.isBlock():
                if len(tokens) > 0 and tokens[-1].isWhiteSpace():
                    tokens.pop()
                return tokens

            i += 1
            if token.isWhiteSpace() or token.isComment():
                continue

            tokens.append(token)

        raise CSSParseError("Malformed at-rule token", token = self)

    def getBlock(self):
        return self.block

    def toString(self, options = CSSOptions()):
        string = ""
        for token in self.children:
            if options.stripWhiteSpace and token.isWhiteSpace():
               if (token.isFirstChild(True) or token.isLastChild(True) or
                   token.getNextSibling(True).isBoundary() or
                   token.getPreviousSibling(True).isBoundary()):
                    continue
            string += token.toString(options)
        return string


class CSSAtKeywordToken(CSSToken):
    def __init__(self, parent):
        CSSToken.__init__(self, [], parent)

    def process(self, stream, options = CSSOptions()):
        self.consume(stream.takeAtKeyword())
        return self.parent

    def toString(self, options = CSSOptions()):
        return colorize(self.data, "00;32") if options.colorize else self.data


class CSSBlockToken(CSSToken):
    def __init__(self, parent):
        CSSToken.__init__(self, [CSSAnyToken, CSSBlockToken, CSSAtRuleToken, CSSRuleSetToken, CSSDeclarationToken, CSSWhiteSpaceToken, CSSCommentToken, SCSSAssignmentToken], parent)

    def process(self, stream, options = CSSOptions()):
        token = CSSToken.process(self, stream, options)
        if token != self:
            return token

        if stream.current() == "{":
            if len(self.children) == 0:
                self.createDelimiterChild(stream)
                return self
            else:
                return self.createChild(CSSBlockToken)

        if stream.current() == "}":
            self.createDelimiterChild(stream)
            return self.parent

        if stream.current() == ";":
            self.createDelimiterChild(stream)
            return self

        if stream.current() == "@":
            return self.createChild(CSSAtRuleToken)

        if options.compileScss:
            if stream.isIdentifierStart():
                token = self.performRuleSetVersusDeclarationLookAhead(stream)
                if token != None:
                    return token
            elif stream.current() in "&*.#":
                 return self.createChild(CSSRuleSetToken)

        return self.createChild(CSSAnyToken)

    def toString(self, options = CSSOptions()):
        string = ""
        for token in self.children:
            if options.stripWhiteSpace and token.isWhiteSpace():
                if (token.isFirstChild() or token.isLastChild() or
                    token.getNextSibling().isBoundary() or
                    token.getPreviousSibling().isBoundary()):
                    continue
            if options.stripExtraSemicolons and token.isDelimiter(";"):
                if token.getNextSibling(ignoreWhiteSpace = True).isDelimiter():
                    continue
            string += token.toString(options)
        return string


class CSSRuleSetToken(CSSToken):
    def __init__(self, parent):
        CSSToken.__init__(self, [CSSAtRuleToken, CSSRuleSetToken, CSSSelectorToken, CSSDeclarationToken, CSSDelimiterToken, SCSSAssignmentToken, CSSWhiteSpaceToken, CSSCommentToken], parent)
        self.selector = None
        self.isOpened = False

    def process(self, stream, options = CSSOptions()):
        token = CSSToken.process(self, stream, options)
        if token != self:
            return token

        if self.isOpened:
            if stream.current() == "}":
                self.createDelimiterChild(stream)
                return self.parent

            if stream.current() == ";":
                self.createDelimiterChild(stream)
                return self

            if stream.isIdentifierStart():
                if options.compileScss:
                    token = self.performRuleSetVersusDeclarationLookAhead(stream)
                    if token != None:
                        return token

                return self.createChild(CSSDeclarationToken)

            if stream.current() == "*": # IE <= 7 hack
                return self.createChild(CSSDeclarationToken)

            if options.compileScss:
                if stream.current() == "@":
                    return self.createChild(CSSAtRuleToken)

                if stream.current() in "&.:#":
                    return self.createChild(CSSRuleSetToken)
        else:
            if stream.current() == "{":
                self.isOpened = True
                self.createDelimiterChild(stream)
                return self

            if self.selector == None:
                return self.createChild(CSSSelectorToken)

        raise CSSParseError("Invalid character '%s' in stream" % stream.current(), stream, self)

    def adopt(self, token):
        CSSToken.adopt(self, token)
        if isinstance(token, CSSSelectorToken):
            self.selector = token

    def reject(self, token):
        CSSToken.reject(self, token)
        if self.selector == token:
            self.selector = None

    def getSelector(self):
        if self.selector == None:
            raise CSSParseError("Rule set does not have selector", token = self)
        return self.selector

    def getDeclarations(self):
        declarations = []
        for token in self.children:
            if token.isDeclaration():
                declarations.append(token)
        return declarations

    def toString(self, options = CSSOptions()):
        if options.minimizeValues and len(self.getDeclarations()) == 0:
            return ""

        string = ""
        for token in self.children:
            if options.stripWhiteSpace and token.isWhiteSpace():
                continue
            if options.stripExtraSemicolons and token.isDelimiter(";"):
                if token.getNextSibling(ignoreWhiteSpace = True).isDelimiter():
                    continue
            string += token.toString(options)
        return string


class CSSSelectorToken(CSSToken):
    def __init__(self, parent):
        CSSToken.__init__(self, [CSSAnyToken, CSSWhiteSpaceToken, CSSCommentToken], parent)

    def process(self, stream, options = CSSOptions()):
        token = CSSToken.process(self, stream, options)
        if token != self:
            return token

        if stream.current() == "{":
            return self.parent

        return self.createChild(CSSAnyToken)

    def getAmpersand(self):
        for token in self.children:
            if token.isDelimiter("&"):
                return token
        return None

    # returns all comma-separated sub-selectors (each selector has been stripped
    # of leading and trailing whitespace)
    def getSubSelectors(self):
        subSelectors = []
        subSelector = []
        for token in self.children:
            if len(subSelector) == 0 and token.isWhiteSpace():
                continue
            if token.isDelimiter(","):
                if len(subSelector) > 0:
                    while subSelector[-1].isWhiteSpace():
                        subSelector = subSelector[0:-1]
                    subSelectors.append(subSelector)
                    subSelector = []
            else:
                subSelector.append(token)
        if len(subSelector) > 0:
            while subSelector[-1].isWhiteSpace():
                subSelector = subSelector[0:-1]
            subSelectors.append(subSelector)
        return subSelectors

    # returns all children with the exception of leading and trailing whitespace 
    def getStrippedChildren(self):
        i = 0
        children = []
        while i < len(self.children):
            child = self.children[i]
            i += 1
            if i == 1 or i == len(self.children):
                if child.isWhiteSpace():
                    continue
            children.append(child)
        return children

    def toString(self, options = CSSOptions()):
        string = ""
        for token in self.children:
            if options.stripWhiteSpace and token.isWhiteSpace() and token.isLastChild():
                continue
            string += token.toString(CSSOptions(options, colorize = False))
        return colorize(string, "00;36") if options.colorize else string

class CSSDeclarationToken(CSSToken):
    def __init__(self, parent):
        CSSToken.__init__(self, [CSSPropertyToken, CSSValueToken, CSSDelimiterToken, CSSWhiteSpaceToken, CSSCommentToken], parent)
        self.property = None
        self.hasColon = False
        self.value = None

    def process(self, stream, options = CSSOptions()):
        token = CSSToken.process(self, stream, options)
        if token != self:
            return token

        if self.value != None:
            return self.parent

        if self.hasColon:
            return self.createChild(CSSValueToken)
        elif self.property:
            if stream.current() == ":":
                self.hasColon = True
                self.createDelimiterChild(stream)
                return self
        else:
            if stream.isIdentifierStart():
                return self.createChild(CSSPropertyToken)
            if stream.current() == "*": # IE <= 7 hack
                child = self.createChild(CSSPropertyToken)
                child.consume(stream.take())
                return child

        raise CSSParseError("Invalid character '%s' in stream" % stream.current(), stream, self)

    def adopt(self, token):
        CSSToken.adopt(self, token)
        if isinstance(token, CSSValueToken):
            self.value = token
        elif isinstance(token, CSSIdentifierToken):
            self.property = token

    def getProperty(self):
        if self.property == None:
            raise CSSParseError("Declaration does not have a property", token = self)

        return self.property

    def getValue(self):
        if self.value == None:
            raise CSSParseError("Declaration does not have a value", token = self)

        return self.value

    def toString(self, options = CSSOptions()):
        if options.stripWhiteSpace:
            return self.property.toString(options) + ":" + self.value.toString(options)
        string = ""
        for token in self.children:
            string += token.toString(options)
        return string


class CSSValueToken(CSSToken):
    def __init__(self, parent):
        CSSToken.__init__(self, [CSSAnyToken, CSSBlockToken, CSSAtKeywordToken, CSSWhiteSpaceToken, CSSCommentToken, SCSSVariableToken], parent)
        self.block = None

    def process(self, stream, options = CSSOptions()):
        token = CSSToken.process(self, stream, options)
        if token != self:
            return token

        if self.block != None:
            return self.parent

        if stream.current() == "{":
            return self.createChild(CSSBlockToken)

        if stream.current() == "@":
            return self.createChild(CSSAtKeywordToken)

        if stream.current() in "};":
            return self.parent

        return self.createChild(CSSAnyToken)

    def getStrippedChildren(self):
        children = []
        for i in range(0, len(self.children)):
            child = self.children[i]
            if child.isWhiteSpace() or child.isComment():
                if (child.isFirstChild(True) or child.isLastChild(True) or
                    child.getNextSibling().isBoundary() or
                    child.getPreviousSibling().isBoundary()):
                    continue
            children.append(child)
        return children

    def getBlock(self):
        return self.block

    def adopt(self, token):
        CSSToken.adopt(self, token)
        if isinstance(token, CSSBlockToken):
            self.block = token

    def reject(self, token):
        CSSToken.reject(self, token)
        if self.block == token:
            self.block = None

    def toString(self, options = CSSOptions()):
        string = ""
        children = self.getStrippedChildren() if options.stripWhiteSpace else self.children
        for token in children:
            # these minimizations are only valid in the context of a value token
            if options.minimizeValues and token.isAnyToken():
                if token.type == CSS_IDENT_VALUE or token.type == CSS_HASH_VALUE:
                    try: # try to see whether it's a color and minify if it is
                        color = minimizeColorValue(token)
                        string += colorize(color, "01;34") if options.colorize else color
                        continue
                    except Exception, exception:
                        pass

                if token.type == CSS_IDENT_VALUE and token.data == "none":
                    property = self.parent.getProperty().data
                    if property in ["border", "border-top", "border-right", "border-bottom", "border-left", "outline", "background"]:
                        string += colorize("0", "01;34") if options.colorize else "0";
                        continue;

            string += token.toString(options)
        return string


class CSSAnyToken(CSSToken):
    def __init__(self, parent, type = CSS_UNKNOWN_VALUE, data = None):
        CSSToken.__init__(self, [CSSAnyToken, CSSWhiteSpaceToken, CSSCommentToken, SCSSVariableToken], parent)
        self.type = type
        if data:
            self.consume(data)

    def process(self, stream, options = CSSOptions()):
        token = CSSToken.process(self, stream, options)
        if token != self:
            return token

        if self.type == CSS_FUNCTION_VALUE or self.type == CSS_SET_VALUE or self.type == CSS_LIST_VALUE:
            if stream.current() == ("]" if self.type == CSS_LIST_VALUE else ")"):
                self.createDelimiterChild(stream)
                return self.parent

            if stream.current() == ",":
                self.createDelimiterChild(stream)
                return self

            return self.createChild(CSSAnyToken)
        else:
            if stream.isIdentifierStart():
                identifier = stream.takeIdentifier()
                if stream.current() == "(":
                    if identifier == "url":
                        self.type = CSS_URI_VALUE
                        self.consume(identifier)
                        self.consume(stream.take())
                        self.consume(stream.takeWhiteSpace())
                        self.consume(stream.takeUri())
                        self.consume(stream.takeWhiteSpace())
                        if stream.current() == ")":
                            self.consume(stream.take())
                            return self.parent
                        else:
                            raise CSSParseError("Invalid character '%s' in stream" % stream.current(), stream, self)
                    else:
                        self.type = CSS_FUNCTION_VALUE
                        self.add(CSSIdentifierToken(self, identifier))
                        self.createDelimiterChild(stream)
                        return self
                else:
                    self.type = CSS_IDENT_VALUE
                    self.consume(identifier)
                    return self.parent

            if stream.isNumberStart():
                self.consume(stream.takeNumber())
                if stream.current() == "%":
                    self.type = CSS_PERCENTAGE_VALUE
                    self.consume(stream.take())
                elif stream.isIdentifierStart():
                    self.type = CSS_DIMENSION_VALUE
                    self.consume(stream.takeIdentifier())
                else:
                    self.type = CSS_NUMBER_VALUE
                return self.parent

            if stream.isStringStart():
                self.type = CSS_STRING_VALUE
                self.consume(stream.takeString())
                return self.parent

            if stream.current() == "#":
                self.type = CSS_HASH_VALUE
                self.consume(stream.take())
                self.consume(stream.takeName())
                return self.parent

            if stream.current() == "(":
                self.type = CSS_SET_VALUE
                self.createDelimiterChild(stream)
                return self

            if stream.current() == "[":
                self.type = CSS_LIST_VALUE
                self.createDelimiterChild(stream)
                return self

            # these are not officially identifiers, but it makes many things a
            # whole lot easier
            if stream.current() == "!" and stream.isIdentifierStart(1):
                self.type = CSS_IDENT_VALUE
                self.consume(stream.take())
                self.consume(stream.takeIdentifier())
                return self.parent

            self.type = CSS_DELIM_VALUE
            self.consume(stream.take())
            if self.data in "=!<>" and stream.current() == "=":
                self.consume(stream.take())
            return self.parent

    def getName(self):
        if self.type == CSS_IDENT_VALUE:
            return self.data

        if self.type == CSS_FUNCTION_VALUE:
            for token in self.children:
                if token.isIdentifier():
                    return token.getName()
                if token.isDelimiter("("):
                    break
            raise CSSParseError("Could not find an identifier for the function", token = self)

        raise CSSParseError("Cannot get the name for this token type", token = self)

    def getArguments(self, includeCommas = False):
        if self.type != CSS_FUNCTION_VALUE:
            raise CSSParseError("Can only get arguments from a function", token = self)

        arguments = []
        isOpened = False
        for token in self.children:
            if isOpened:
                if (token.isWhiteSpace() or token.isComment() or
                    token.isDelimiter(")" if includeCommas else ",)")):
                    continue
                arguments.append(token)
            else:
                if token.isDelimiter("("):
                    isOpened = True
        return arguments

    def getStrippedChildren(self):
        if self.type != CSS_SET_VALUE and self.type != CSS_LIST_VALUE:
            raise CSSParseError("Can only get children from a set or list", token = self)

        children = []
        for i in range(0, len(self.children)):
            child = self.children[i]
            if (i == 0 or i == len(self.children) - 1 or
                child.isWhiteSpace() or child.isComment()):
                continue
            children.append(child)
        return children

    def getUrl(self, options = CSSOptions()):
        if self.type != CSS_URI_VALUE:
            raise CSSParseError("Can only get a URL from a URI token", token = self)

        url = self.data[4:-1].strip()
        if options.minimizeValues:
            if ((url[0] == "'" and url[-1] == "'") or
                (url[0] == '"' and url[-1] == '"')):
                character = ""
                stream = CSSStream(url[1:-1], options)
                urlCharsOnly = True
                while character != CSS_EOF:
                    if not stream.isUrlChar():
                        urlCharsOnly = False
                        break
                    character = stream.take()
                if urlCharsOnly:
                    url = stream.buffer
        return url

    def toFloat(self):
        if self.type == CSS_NUMBER_VALUE:
            return float(self.data)
        if self.type == CSS_PERCENTAGE_VALUE:
            return float(self.data[0:-1])

        raise CSSParseError("Cannot convert this type of token to a float", token = self)

    def toString(self, options = CSSOptions()):
        if len(self.children) > 0:
            string = ""
            if options.minimizeValues and self.type == CSS_FUNCTION_VALUE:
                name = self.getName()
                if name in ["rgb", "rgba", "hsl", "hsla"]:
                    string = minimizeColorValue(self)

            if string == "":
                for token in self.children:
                    if options.stripWhiteSpace and token.isWhiteSpace():
                        if (token.getNextSibling().isBoundary() or
                            token.getPreviousSibling().isBoundary()):
                            continue
                    string += token.toString(options)
        else:
            data = self.data
            if self.type == CSS_URI_VALUE and options.stripWhiteSpace:
                data = "url(" + self.getUrl(options) + ")"
            elif self.type in [CSS_NUMBER_VALUE, CSS_PERCENTAGE_VALUE, CSS_DIMENSION_VALUE]:
                zeros = ""
                while len(data) > 1 and data[0] == "0":
                    zeros += "0"
                    data = data[1:]
                if len(zeros) > 0:
                    if data[0] in ".0123456789":
                        pass # okay, we just stripped off leading zeros
                    else:
                        data = "0" # a measurement was following, leave it out...
            string = data
        return colorize(string, "01;36") if options.colorize and not self.isDelimiter() else string


# just a convenience for creating new identifiers
class CSSIdentifierToken(CSSAnyToken):
    def __init__(self, parent, identifier = ""):
        CSSAnyToken.__init__(self, parent, CSS_IDENT_VALUE, identifier)


class CSSPropertyToken(CSSIdentifierToken):
    def __init__(self, parent, property = ""):
        CSSIdentifierToken.__init__(self, parent, property)

    def process(self, stream, options = CSSOptions()):
        self.consume(stream.takeIdentifier())
        return self.parent

    def toString(self, options = CSSOptions()):
        return colorize(self.data, "00;35") if options.colorize else self.data


# just a convenience for creating new strings
class CSSStringToken(CSSAnyToken):
    def __init__(self, parent, string):
        CSSAnyToken.__init__(self, parent, CSS_STRING_VALUE, string)


class CSSDelimiterToken(CSSAnyToken):
    def __init__(self, parent, delimiter = ""):
        CSSAnyToken.__init__(self, parent, CSS_DELIM_VALUE, delimiter)

    def process(self, stream, options = CSSOptions()):
        raise CSSParseError("CSSDelimiterToken.process() cannot be called directly.", stream)


class SCSSVariableToken(CSSAnyToken):
    def __init__(self, parent, variable = None):
        CSSToken.__init__(self, [], parent)
        self.type = SCSS_VARIABLE_VALUE
        self.variable = variable

    def process(self, stream, options = CSSOptions()):
        if not stream.isVariableStart():
            raise CSSParseError("SCSS variables must start with a $", stream, self)

        self.consume(stream.take())
        self.consume(stream.takeIdentifier())
        return self.parent

    def getName(self):
        return self.data[1:]

    def setVariable(self, variable):
        if not isinstance(variable, scssvariables.SCSSVariable):
            raise CSSParseError("Can only assign SCSS variables to variable tokens", token = self)
        self.variable = variable

    def toString(self, options = CSSOptions()):
        if self.variable != None:
            string = self.variable.toString(options)
        else:
            string = self.data
        return colorize(string, "01;34") if options.colorize else string

    def clone(self):
        clone = copy.copy(self)
        clone.variable = None
        return clone


class SCSSAssignmentToken(CSSToken):
    def __init__(self, parent):
        CSSToken.__init__(self, [SCSSVariableToken, CSSValueToken, CSSDelimiterToken, CSSWhiteSpaceToken, CSSCommentToken], parent)
        self.variable = None
        self.hasColon = False
        self.value = None

    def process(self, stream, options = CSSOptions()):
        token = CSSToken.process(self, stream, options)
        if token != self:
            if isinstance(token, SCSSVariableToken):
                if self.variable == None:
                    self.variable = token
                    return token
            else:
                return token

        if self.value != None:
            if stream.current() == ";":
                stream.advance() # skip the ; or it'll scare the shit out of the rule set
            return self.parent

        if self.hasColon:
            return self.createChild(CSSValueToken)
        elif self.variable:
            if stream.current() == ":":
                self.hasColon = True
                self.createDelimiterChild(stream)
                return self

        raise CSSParseError("Invalid character '%s' in stream" % stream.current(), stream, self)

    def getVariable(self):
        if self.variable == None:
            raise CSSParseError("Assignment does not have a variable to assign", token = self)

        return self.variable

    def getValue(self):
        if self.value == None:
            raise CSSParseError("Assignment does not have a value", token = self)

        return self.value

    def toString(self, options = CSSOptions()):
        return "" # SCSS assignments should never end up in the CSS output

    def adopt(self, token):
        CSSToken.adopt(self, token)
        if isinstance(token, CSSValueToken):
            self.value = token


class CSSCommentToken(CSSToken):
    def __init__(self, parent):
        CSSToken.__init__(self, [], parent)
        self.singleLineComment = False

    def process(self, stream, options = CSSOptions()):
        if len(self.data) == 2 and self.data[1] == "/":
            self.singleLineComment = True

        if self.singleLineComment:
            while not (stream.isEndOfFile() or stream.isNewline()):
                self.consume(stream.take())
        else:
            while not (stream.isEndOfFile() or stream.isCommentEnd()):
                self.consume(stream.take())
            if stream.isCommentEnd():
                self.consume(stream.take(2))

        return self.parent

    def toString(self, options = CSSOptions()):
        stripComment = options.stripComments
        if self.singleLineComment:
            stripComment = True
        if len(self.data) > 2 and self.data[2] == "!":
            stripComment = False

        if stripComment:
            return ""

        if self.singleLineComment:
            comment = "/*" + self.data[2:] + "*/"
        else:
            comment = self.data
        return colorize(comment, "00;32") if options.colorize else comment


class CSSWhiteSpaceToken(CSSToken):
    def __init__(self, parent, data = ""):
        CSSToken.__init__(self, [], parent)
        self.data = data

    def process(self, stream, options = CSSOptions()):
        self.consume(stream.takeWhiteSpace())
        return self.parent

    def toString(self, options = CSSOptions()):
        return " " if options.stripWhiteSpace else self.data 

    def clone(self):
        return CSSWhiteSpaceToken(self.parent, " ")
