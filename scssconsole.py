import readline
import string

import cssparser
import scsscompiler
import scssexpression


class SCSSConsole(object):
    def start(self, options = cssparser.CSSOptions()):
        compiler = scsscompiler.SCSSCompiler()
        scope = compiler.getGlobalScope()
        while True:
            statement = raw_input(">> ")
            if statement == "\\q" or statement == "exit()":
                print "Bye."
                return

            try:
                expression = scssexpression.SCSSExpression.fromString(statement, options)
                expression.evaluate(scope)
                for token in expression.tokens:
                    print token.toString(options)
            except Exception, exception:
                print exception
