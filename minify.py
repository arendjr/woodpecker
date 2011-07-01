#!/usr/bin/python

import optparse
import sys

import cssparser


if __name__ == "__main__":

    usage = "Usage: stdin | %prog [options] | stdout"
    optionParser = optparse.OptionParser(usage = usage)
    optionParser.add_option("", "--color", action = "store_true",
                      help = "Colorize the output")
    (options, args) = optionParser.parse_args()

    parser = cssparser.CSSParser()
    options = cssparser.CSSOptions(stripWhiteSpace = True, stripComments = True, minimizeValues = True,
                                   stripExtraSemicolons = True, colorize = options.color, compileScss = True)
    token = parser.parse(sys.stdin.read(), options)
    print token.toString(options)

