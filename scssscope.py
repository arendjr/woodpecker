import copy

from scssexceptions import *


class SCSSScope(object):
    def __init__(self, parent = None):
        self.parent = parent
        self.variables = {}
        self.mixins = {}
        self.functions = {}

    def set(self, name, value):
        self.variables[name] = value

    def has(self, name):
        return name in self.variables or (self.parent and self.parent.has(name))

    def get(self, name, token = None):
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.get(name, token)
        raise SCSSRunTimeError("No variable named $%s found" % name, token)

    def setMixin(self, name, value):
        self.mixins[name] = value

    def hasMixin(self, name):
        return name in self.mixins or (self.parent and self.parent.hasMixin(name))

    def getMixin(self, name, token = None):
        if name in self.mixins:
            return self.mixins[name]
        if self.parent:
            return self.parent.getMixin(name, token)
        raise SCSSRunTimeError("No mixin named %s found" % name, token)

    def setFunction(self, name, value):
        self.functions[name] = value

    def hasFunction(self, name):
        return name in self.functions or (self.parent and self.parent.hasFunction(name))

    def getFunction(self, name, token = None):
        if name in self.functions:
            return self.functions[name]
        if self.parent:
            return self.parent.getFunction(name, token)
        raise SCSSRunTimeError("No function named %s found" % name, token)

    def clone(self):
        scope = SCSSScope(self.parent)
        for name in self.variables:
            scope.variables[name] = copy.copy(self.variables[name])
        for name in self.mixins:
            scope.mixins[name] = copy.copy(self.mixins[name])
        for name in self.functions:
            scope.functions[name] = copy.copy(self.functions[name])
        return scope

    def merge(self, scope):
        for name in scope.variables:
            self.variables[name] = copy.copy(scope.variables[name])
        for name in scope.mixins:
            self.mixins[name] = copy.copy(scope.mixins[name])
        for name in scope.functions:
            self.functions[name] = copy.copy(scope.functions[name])

    def toString(self):
        strings = []
        for name in self.variables:
            if self.variables[name]:
                strings.append("$%s: %s" % (name, self.variables[name].toString()))
            else:
                strings.append("WARNING: $%s has None value" % name)
        return "\n".join(strings)
