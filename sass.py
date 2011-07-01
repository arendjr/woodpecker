#!/usr/bin/python

import optparse
import sys

import cssparser
import scsscompiler
import scssconsole


if __name__ == "__main__":

    usage = "Usage: stdin | %prog [options] | stdout"
    optionParser = optparse.OptionParser(usage = usage)
    optionParser.add_option("", "--color", action = "store_true",
                      help = "Colorize the output")
    optionParser.add_option("-i", "--interactive", action = "store_true",
                      help = "Run an interactive SassScript shell.")
    optionParser.add_option("-I", "--load-path",
                      help = "Add a sass import path.")
    optionParser.add_option("", "--minimize", action = "store_true",
                      help = "Minimize the output (--style compact in sass).")
    (o, args) = optionParser.parse_args()

    options = cssparser.CSSOptions(stripWhiteSpace = o.minimize, stripComments = o.minimize,
                                   minimizeValues = o.minimize, stripExtraSemicolons = o.minimize,
                                   colorize = o.color, compileScss = True)

    if o.load_path:
        import scssimporter
        scssimporter.Importer.addPath(load_path)

    if o.interactive:
        console = scssconsole.SCSSConsole()
        console.start(options)
    else:
        parser = cssparser.CSSParser()
        token = parser.parse(sys.stdin.read(), options)
    
        compiler = scsscompiler.SCSSCompiler()
        compiler.compile(token, options)
    
        print token.toString(options)
