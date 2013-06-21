#!/usr/bin/env python

import sys
import os
import re
import argparse

class C_DependencyFinder:

    def handled_extensions(self):
        return {"c", "cpp", "cxx", "cc", "h", "hpp"}

    # ------ multiple files ------

    def find_dependencies(self, files):
        dep_map = {}
        for f in files:
            self.__find_dependency_for_file(f, dep_map)
        return dep_map

    def __find_dependency_for_file(self, filename, dep_map):
        if filename in dep_map:
            return dep_map[filename]
        deps = set([filename])
        directory = os.path.dirname(filename)
        try:
            with open(filename, "r") as input_file:
                for line in input_file:
                    include_file = self.__extract_include_file(line)
                    if include_file:
                        include_file = os.path.join(directory, include_file)
                        incdeps = self.__find_dependency_for_file(
                                                       include_file, dep_map)
                        deps = deps.union(incdeps)
        except:
            pass
        dep_map[filename] = deps
        return deps

    # ------ single file ------

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
        self.project_name = "my_project"
        self.c_compiler = "gcc"
        self.cpp_compiler = "g++"
        self.sources = []
        self.output = None
        self.link_libraries = []
        self.defines = []
        self.library_paths = []
        self.include_paths = []

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
        link_libraries = options.link_libraries
        compiler_flags = self.__compiler_flags(options)

        for f in options.sources:
            base, ext = self.__split_extension(f)
            if ext in C_RuleGenerator().handled_extensions():
                c_compiler = options.c_compiler
                object_files.append(base + ".o")
            elif ext in CPP_RuleGenerator().handled_extensions():
                cpp_compiler = options.cpp_compiler
                object_files.append(base + ".o")

        with open("Makefile", "w") as output_file:
            # variables
            if c_compiler:
                output_file.write("CC=%s\n" % (c_compiler))
                output_file.write("CFLAGS=-g -Wall -O2 %(FLAGS)s\n"
                                  % {"FLAGS": compiler_flags})
            if cpp_compiler:
                output_file.write("CXX=%s\n" % (cpp_compiler))
                output_file.write("CXXFLAGS=-g -Wall -O2 %(FLAGS)s\n"
                                  % {"FLAGS": compiler_flags})
            if object_files:
                output_file.write("OBJS=%s\n" % (' '.join(object_files)))
                output_file.write("LDFLAGS=%s\n"
                                  % (self.__linker_flags(options)))
            output_file.write("\n")

            # executable
            if object_files:
                output_file.write("%1s: $(OBJS)\n" % (options.output))
                linker = "$(CC)"
                if cpp_compiler:
                    linker = "$(CXX)"
                output_file.write("\t%1s -o %2s $(LDFLAGS) $(OBJS)\n\n"
                                  % (linker, options.output))

            # object files
            for f in options.sources:
                self.__generate_rule(f, output_file)

            # clean
            output_file.write("clean:\n")
            for f in object_files:
                output_file.write("\trm -f %s\n" % (f)) # remove *.o
            if object_files:
                output_file.write("\trm -f %s\n" % (options.output))

    def __linker_flags(self, options):
        flags = []
        for lib in options.link_libraries:
            flags.append("-l%s" % (lib))
        for path in options.library_paths:
            flags.append("-L%s" % (path))
        return ' '.join(flags)

    def __compiler_flags(self, options):
        flags = []
        for d in options.defines:
            flags.append("-D%s" % (d))
        for path in options.include_paths:
            flags.append("-I%s" % (path))
        return ' '.join(flags)

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
        with open("CMakeLists.txt", "w") as output_file:
            output_file.write("project(%1s)\n" % (options.project_name))
            self.__write_defines(output_file, options)
            self.__write_link_libraries(output_file, options)
            self.__write_add_executable(output_file, options)

    def __write_add_executable(self, output_file, options):
        output_file.write("add_executable(%1s\n" % (options.output))
        dep_map = C_DependencyFinder().find_dependencies(options.sources)
        for f in dep_map:
            if os.path.exists(f): # exclude non-existing files
                output_file.write("\t%1s\n" % (f))
        output_file.write(")\n")

    def __write_link_libraries(self, output_file, options):
        if options.link_libraries:
            output_file.write("link_libraries(%1s\n" % (options.output))
            for lib in options.link_libraries:
                output_file.write("\t%1s\n" % (lib))
            output_file.write(")\n")

    def __write_defines(self, output_file, options):
        if options.defines:
            output_file.write("add_definitions(\n")
            for d in options.defines:
                output_file.write("\t-D%1s\n" % (d))
            output_file.write(")\n")

class AutoMakeGen:

    def generate(self, options):
        with open("Makefile.am", "w") as output_file:
            bin_filename = re.sub(r"[ \t-+.]", "_", options.output)
            output_file.write("AUTOMAKE_OPTIONS = foreign\n\n")
            output_file.write("bin_PROGRAMS = %s\n" % (bin_filename))
            self.__write_sources(output_file, options, bin_filename)
            if self.__contains_c(options):
                self.__write_cflags(output_file, options, bin_filename)
            if self.__contains_cpp(options):
                self.__write_cxxflags(output_file, options, bin_filename)
            if options.link_libraries:
                self.__write_ldadd(output_file, options, bin_filename)

    def __contains_cpp(self, options):
        for source in options.sources:
            if source.endswith(".cpp"):
                return True
        return False

    def __contains_c(self, options):
        for source in options.sources:
            if source.endswith(".c"):
                return True
        return False

    def __write_flags(self, output_file, options, bin_filename, flag):
        output_file.write("%1s_%2s = " % (bin_filename, flag))
        output_file.write("-g -O2 -Wall")
        for define in options.defines:
            output_file.write(" -D%s" % (define))
        output_file.write("\n")

    def __write_cflags(self, output_file, options, bin_filename):
        self.__write_flags(output_file, options, bin_filename, "CFLAGS")

    def __write_cxxflags(self, output_file, options, bin_filename):
        self.__write_flags(output_file, options, bin_filename, "CXXFLAGS")

    def __write_sources(self, output_file, options, bin_filename):
        output_file.write("%s_SOURCES = \\\n" % (bin_filename))
        files = list(C_DependencyFinder().find_dependencies(options.sources))
        last_index = len(files) - 1
        for i in range(0, last_index):
            source = files[i]
            if os.path.exists(source):
                output_file.write("\t%s \\\n" % (source))
        if last_index >= 0:
            source = files[last_index]
            if os.path.exists(source):
                output_file.write("\t%s\n" % (source))

    def __write_ldadd(self, output_file, options, bin_filename):
        output_file.write("%s_LDADD =" % (bin_filename))
        for lib in options.link_libraries:
            output_file.write(" -l%s" % (lib))
        output_file.write("\n")

GENERATORS = {
    "make": MakeGen(),
    "cmake": CMakeGen(),
    "automake": AutoMakeGen()
}

def list_generators():
    generators = []
    for gen in GENERATORS:
        generators.append(gen)
    return ', '.join(generators)

def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Generate makefile from source files.")
    parser.add_argument("file", type=str, nargs="+",
                        help="source files")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="the name of the output executable or library")
    parser.add_argument("-f", "--format", default="make",
                        help="format of the output makefile.")
    parser.add_argument("-l", action="append", dest="link_libraries",
                        help="link to a library")
    parser.add_argument("-D", action="append", dest="defines",
                        help="add a preprocessor definition")
    parser.add_argument("-L", action="append", dest="library_paths",
                        help="add a library path")
    parser.add_argument("-I", action="append", dest="include_paths",
                        help="add a include path")
    parser.add_argument("-n", "--name", type=str, default="my_project",
                        help="name of the project")
    return parser

def build_make_options(arg):
    options = MakeOptions()
    options.project_name = arg.name
    options.sources = arg.file
    options.output = "a.out"
    if arg.output:
        options.output = arg.output
    if arg.link_libraries:
        options.link_libraries = arg.link_libraries
    if arg.defines:
        options.defines = arg.defines
    if arg.library_paths:
        options.library_paths = arg.library_paths
    if arg.include_paths:
        options.include_paths = arg.include_paths
    return options

if __name__ == "__main__":
    parser = build_argument_parser()
    arg = parser.parse_args()
    options = build_make_options(arg)

    if arg.format in GENERATORS:
        generator = GENERATORS[arg.format]
        generator.generate(options)
    else:
        print("error: unknown format %1s" % arg.format)
        print("supported formats are: %1s" % list_generators())
