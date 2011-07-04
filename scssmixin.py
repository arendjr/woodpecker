from scssexceptions import *
from scssfunction import SCSSFunction


class SCSSMixin(SCSSFunction):
    def __init__(self, name, scope, arguments, body):
        SCSSFunction.__init__(self, name, scope, arguments, body)

    def tokenToBody(self, token):
        return token.clone()

    def evaluate(self, callerScope, arguments = None):
        try:
            scope = self.scope.clone()
            if arguments != None:
                self.mapArguments(arguments, callerScope, scope)
    
            body = self.body.clone()
            import scsscompiler
            compiler = scsscompiler.SCSSCompiler()
            compiler.setGlobalScope(scope)
            compiler.compile(body)
            return body.children[1:-1]
        except Exception, exception:
            raise SCSSRunTimeError(str(exception) + "\n  In call to mixin " + self.name)
