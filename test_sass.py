#!/usr/bin/python

from __future__ import with_statement

import codecs
import optparse
import os

import cssparser
import scsscompiler


def dirEntries(path):
    if not os.path.exists(path):
        return;
    for entry in sorted(os.listdir(path)):
        if entry[0] == ".":
            continue
        yield entry

if __name__ == "__main__":

    usage = "Usage: %prog [options]"
    optionParser = optparse.OptionParser(usage = usage)
    optionParser.add_option("", "--color", action = "store_true",
                      help = "Colorize the output")
    (o, args) = optionParser.parse_args()

    for test in dirEntries("test/sass"):
        parser = cssparser.CSSParser()
        options = cssparser.CSSOptions(stripWhiteSpace = True, compileScss = True)
        colorOptions = cssparser.CSSOptions(stripWhiteSpace = True, compileScss = True, colorize = True)

        with codecs.open("test/sass/%s/in.scss" % test, "r", "utf-8") as f:
            token = parser.parse(f.read(), options)
    
        compiler = scsscompiler.SCSSCompiler()
        compiler.compile(token)
        output = token.toString(options)

        with codecs.open("test/sass/%s/out.css" % test, "r", "utf-8") as f:
            expected = f.read()

        if output == expected.strip():
            print "Test %s passed." % test
        else:
            if o.color:
                expectedToken = parser.parse(expected)
                expected = expectedToken.toString(colorOptions)
                output = token.toString(colorOptions)

            print "Test %s FAILED!" % test
            print "EXPECTED:" + expected
            print "RECEIVED:" + output
            print ""
