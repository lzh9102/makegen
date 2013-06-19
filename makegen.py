#!/usr/bin/env python

import sys
import os
import re
import argparse

class DependencyFinder:

    def handled_extensions(self):
        return []

    def find_dependency(self, filename):
        return []

class C_DependencyFinder(DependencyFinder):

    def handled_extensions(self):
        return {"c", "cpp", "cxx", "cc", "h", "hpp"}

    def find_dependency(self, filename):
        dep_set = set()
        self.__find_dependency(filename, dep_set)
        return [filename] + list(dep_set)

    def __find_dependency(self, filename, dep_set):
        with open(filename, "r") as input_file:
            for line in input_file:
                self.__process_line(os.path.dirname(filename), line, dep_set)

    def __process_line(self, directory, line, dep_set):
        dependent_file = self.__extract_include_file(line)
        if dependent_file:
            dependent_file = os.path.join(directory, dependent_file)
        if dependent_file != None and dependent_file not in dep_set:
            dep_set.add(dependent_file)
            try:
                self.__find_dependency(dependent_file, dep_set)
            except:
                pass

    def __extract_include_file(self, line):
        # match `#include "file"` but not `#include <file>`
        match = re.match(r'^[ \t]*#[ \t]*include[ \t]*"([^"]*)"', line)
        if match:
            return match.group(1) # filename
        else:
            return None

class RuleGenerator:
    def handled_extensions(self):
        return {}
    def generate_rule(self, filename):
        return ""

def generate_source_to_object_rule(filename, compiler, flags):
    dep_finder = C_DependencyFinder()
    dependencies = dep_finder.find_dependency(filename)
    base, ext = os.path.splitext(filename)
    rule = "%1s.o: %2s\n" % (base, ' '.join(dependencies))
    rule += "\t%(CC)s -o %(BASE)s.o -c %(FLAGS)s %(FILE)s\n\n" % {
        "CC": compiler,
        "BASE": base,
        "FLAGS": flags,
        "FILE": filename }
    return rule

class C_RuleGenerator(RuleGenerator):
    def handled_extensions(self):
        return {"c"}
    def generate_rule(self, filename):
        return generate_source_to_object_rule(filename, "$(CC)", "$(CFLAGS)")

class CPP_RuleGenerator(RuleGenerator):
    def handled_extensions(self):
        return {"cpp", "cxx", "cc"}
    def generate_rule(self, filename):
        return generate_source_to_object_rule(filename, "$(CXX)", "$(CXXFLAGS)")

class HEADER_RuleGenerator(RuleGenerator):
    def handled_extensions(self):
        return {"h", "hpp"}
    def generate_rule(self, filename):
        return "" # header files don't need to be compiled

RULE_GENERATORS = [
    C_RuleGenerator(),
    CPP_RuleGenerator(),
    HEADER_RuleGenerator()
]

class MakeOptions:
    def __init__(self):
        self.c_compiler = "gcc"
        self.cpp_compiler = "g++"
        self.output = None
        self.sources = []
        self.executable = None
        self.link_libraries = []
        self.defines = []

class MakeGen:

    def __init__(self):
        self.rule_generator = {}
        for generator in RULE_GENERATORS:
            for ext in generator.handled_extensions():
                self.rule_generator[ext] = generator

    def generate(self, options):
        c_compiler = None
        cpp_compiler = None
        object_files = []

        for f in options.sources:
            base, ext = self.__split_extension(f)
            if ext in C_RuleGenerator().handled_extensions():
                c_compiler = options.c_compiler
                object_files.append(base + ".o")
            elif ext in CPP_RuleGenerator().handled_extensions():
                cpp_compiler = options.cpp_compiler
                object_files.append(base + ".o")

        makefile = options.output
        if not makefile:
            makefile = "Makefile"
        with open(makefile, "w") as output_file:
            # variables
            if c_compiler:
                output_file.write("CC=%s\n" % (c_compiler))
                output_file.write("CFLAGS=-g -Wall -O2\n")
            if cpp_compiler:
                output_file.write("CXX=%s\n" % (cpp_compiler))
                output_file.write("CXXFLAGS=-g -Wall -O2\n")
            if object_files:
                output_file.write("OBJS=%s\n" % (' '.join(object_files)))
                output_file.write("LDFLAGS=\n")
            output_file.write("\n")

            # executable
            if object_files:
                output_file.write("%1s: $(OBJS)\n" % (options.executable))
                linker = "$(CC)"
                if cpp_compiler:
                    linker = "$(CXX)"
                output_file.write("\t%1s -o %2s $(LDFLAGS) $(OBJS)\n\n"
                                  % (linker, options.executable))

            # object files
            for f in options.sources:
                self.__generate_rule(f, output_file)

            # clean
            output_file.write("clean:\n")
            for f in object_files:
                output_file.write("\trm -f %s\n" % (f)) # remove *.o
            if object_files:
                output_file.write("\trm -f %s\n" % (options.executable))

    def __split_extension(self, filename):
        name, ext = os.path.splitext(filename)
        ext = ext[1:] # remove leading '.'
        return (name, ext)

    def __generate_rule(self, filename, output_file):
        name, ext = self.__split_extension(filename)
        if ext not in self.rule_generator:
            print("warning: don't know how to generate rule for \"%s\"" % (filename))
            return
        generator = self.rule_generator[ext]
        rule = generator.generate_rule(filename)
        output_file.write(rule)

class CMakeGen:

    def generate(self, options):
        cmakelists = options.output
        if not cmakelists:
            cmakelists = "CMakeLists.txt"
        with open(cmakelists, "w") as output_file:
            output_file.write("project(project_name)\n")
            output_file.write("add_executable(%1s\n" % (options.executable))
            for f in options.sources:
                output_file.write("\t%1s\n" % (f))
            output_file.write(")\n")

GENERATORS = {
    "make": MakeGen(),
    "cmake": CMakeGen()
}

def list_generators():
    generators = []
    for gen in GENERATORS:
        generators.append(gen)
    return ', '.join(generators)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate makefile from source files.")
    parser.add_argument("file", type=str, nargs="+",
                        help="source files")
    parser.add_argument("--exe", type=str, default="a.out",
                        help="the name of the output executable")
    parser.add_argument("-f", "--format", default="make",
                        help="format of the output makefile.")
    arg = parser.parse_args()

    options = MakeOptions()
    options.sources = arg.file
    options.executable = arg.exe

    if arg.format in GENERATORS:
        generator = GENERATORS[arg.format]
        generator.generate(options)
    else:
        print("error: unknown format %1s" % arg.format)
        print("supported formats are: %1s" % list_generators())
