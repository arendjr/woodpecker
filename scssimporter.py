from __future__ import with_statement

import codecs
import copy
import os

import cssparser
import scsscompiler

from scssexceptions import *


class SCSSImporter(object):
    def __init__(self):
        self.imports = {}
        self.paths = ["stylesheets"]

    def addPath(self, path):
        self.paths.append(path)

    def importScss(self, scope, token, fileName, options):
        myStyleSheet = token
        while not myStyleSheet.isStyleSheet():
            myStyleSheet = myStyleSheet.parent

        css = None
        extension = ".scss" if len(fileName) < 5 or fileName[-5] != ".scss" else ""
        paths = copy.copy(self.paths)
        paths.append(myStyleSheet.path)
        importPath = ""
        for prefix in paths:
            path = prefix + "/" + fileName + extension
            (dir, file) = os.path.split(path)
            hiddenPath = dir + "/_" + file

            if os.path.exists(hiddenPath):
                options.importCss = False
                importPath = hiddenPath
                break
            if os.path.exists(path):
                importPath = path
                break

        if not importPath:
            raise SCSSRunTimeError("Could not find import \"%s\" in search path: %s" % (fileName, paths))

        if importPath in self.imports:
            (importScope, styleSheet) = self.imports[importPath]
            if importScope:
                if styleSheet:
                    self.importStyleSheet(token, styleSheet)
                self.importScope(scope, importScope)
            else:
                pass # recursive inclusion
        else:
            self.imports[importPath] = (None, None)

            with codecs.open(importPath, "r") as f:
                css = f.read()

            parser = cssparser.CSSParser()
            styleSheet = parser.parse(css, options)
            (directory, fileName) = os.path.split(path)
            styleSheet.setPath(directory)

            compiler = scsscompiler.SCSSCompiler()
            compiler.setGlobalScope(scope)
            compiler.compile(styleSheet, options)

            if options.importCss:
                self.importStyleSheet(token, styleSheet)
                self.imports[importPath] = (scope, styleSheet)
            else:
                self.imports[importPath] = (scope, None)

    def importStyleSheet(self, token, styleSheet):
        insertToken = token
        styleSheet = styleSheet.clone()
        for child in styleSheet.children:
            child.insertAfter(insertToken)
            insertToken = child

    def importScope(self, scope, importScope):
        scope.merge(importScope)

Importer = SCSSImporter()
