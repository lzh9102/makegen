===========================================================
MakeGen - Quickly generate makefile for C/C++ source files.
===========================================================

Usage
=====

.. code::
   
   makegen.py [options] <source files>

Options
-------

-h
   help

-o output
   name of the output executable or library

-n name
   name of the project

-f format
   format of the output makefile. For a list of available output formats, see
   Formats_.

-l library
   Link against *library*, same as gcc. example: ``-lpthread``.

-D definition
   Add *definition* to c preprocessor definitions, same as gcc.
   example: ``-DNULL=0``

--cflags=flags
   Pass *flags* to c compiler. This option only works in *make* and *automake*
   formats. example: ``--cflags='-g -O2 -Wall'``

--cxxflags=flags
   Pass *flags* to c++ compiler. This option only works in *make* and
   *automake* formats. example: ``--cxxflags='-g -O2 -Wall'``

--ldflags=flags
   Pass *flags* to linker. This option only works in *make* and *automake*
   formats. example: ``--ldflags='-pg'``

-L path
   Add *path* to library path. This option only works in *make* format.

-I path
   Add *path* to include path. This option only works in *make* format.

Formats
-------

Makegen currently supports generating makefile in the following formats:

make
   Generate *Makefile* for GNU Make using GCC toolchain.

cmake
   Generate a CMake project file (*CMakeLists.txt*).
   
automake
   Generate *Makefile.am*.

Examples
========

.. code::

   # create Makefile to compile main.c and library.c into a.out
   makegen.py -o a.out main.c library.c library.h

   # link libpthread and #define THREAD_COUNT 4
   makegen.py -DTHREAD_COUNT=4 -lpthread main.c

   # create CMakeLists.txt
   makegen.py -f cmake main.c foo.c bar.c foo.h bar.h

Description
===========

Writing makefile for C/C++ projects can be a repetitive and cumbersome work. If
an included header is omitted in the dependency list, the source file may not
be rebuilt when the header is modified. This may cause runtime failure because
of inconsistencies between object files. On the other hand, superfluous
dependency list will significantly slow down the build process.

The problem can be addressed by using building systems like CMake_ or
Autotools_. These tools are invaluable in C/C++ project development, but they
can be too complex or may introduce additional dependency for very simple
projects.  For example, autotools requires at least 2 configuration files (one
for autoconf and the other for automake) and has a rather complex workflow.
Using CMake is easier but requires cmake to be installed on the user's system.

.. _CMake: http://www.cmake.org/
.. _Autotools: http://en.wikipedia.org/wiki/GNU_build_system

To balance between hand-written makefiles and full-fledged build systems, I
wrote this tool to ease the process of writing simple makefiles. It
automatically generates makefiles that are as simple and readable as those
hand-written ones. The generated makefile does not depend on this script.

Makegen doesn't support custom targets (e.g. generating source files by perl
scripts). If you need such flexibility, please use a real build system instead.
If you decide to convert to cmake or autotools, you can generate CMakeLists.txt
and Makefile.am by ``makegen -f cmake <srcfiles>`` and ``makegen -f automake
<srcfiles>`` respectively.

Copyright
=========

Copyright 2013 Che-Huai Lin

This work is licensed under `CC BY 3.0`_.

.. _`CC BY 3.0`: http://creativecommons.org/licenses/by/3.0/

.. image:: http://i.creativecommons.org/l/by/3.0/88x31.png
