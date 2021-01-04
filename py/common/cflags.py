# Copyright (C) 2014 Red Hat, Inc.
#
# This file is part of csmock.
#
# csmock is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# csmock is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with csmock.  If not, see <http://www.gnu.org/licenses/>.

DEL_FLAGS_BY_LEVEL_COMMON = {
    0: ["-Werror*", "-fdiagnostics-color*", "-no-canonical-prefixes",
        "-Wno-error=deprecated-register"]}

ADD_FLAGS_BY_LEVEL_COMMON = {
    1: ["-Wall", "-Wextra"],
    2: ["-Wunreachable-code", "-Wundef", "-Wcast-align",
            "-Wpointer-arith", "-Wfloat-equal", "-Wshadow",
            "-Wwrite-strings", "-Wformat=2"]}

ADD_FLAGS_BY_LEVEL_C_ONLY = {
    0: ["-Wno-unknown-pragmas"],
    2: ["-Wstrict-prototypes"]}

ADD_FLAGS_BY_LEVEL_CXX_ONLY = {
    2: ["-Wctor-dtor-privacy", "-Woverloaded-virtual"]}


def add_custom_flag_opts(parser):
    parser.add_argument(
        "--gcc-add-flag", action="append", default=[],
        help="append the given compiler flag when invoking gcc \
(can be used multiple times)")

    parser.add_argument(
        "--gcc-add-c-only-flag", action="append", default=[],
        help="append the given compiler flag when invoking gcc for C \
(can be used multiple times)")

    parser.add_argument(
        "--gcc-add-cxx-only-flag", action="append", default=[],
        help="append the given compiler flag when invoking gcc for C++ \
(can be used multiple times)")

    parser.add_argument(
        "--gcc-del-flag", action="append", default=[],
        help="drop the given compiler flag when invoking gcc \
(can be used multiple times)")


def encode_custom_flag_opts(args):
    cmd = ""
    for flag in args.gcc_add_flag:
        cmd += " --gcc-add-flag='%s'" % flag
    for flag in args.gcc_add_c_only_flag:
        cmd += " --gcc-add-c-only-flag='%s'" % flag
    for flag in args.gcc_add_cxx_only_flag:
        cmd += " --gcc-add-cxx-only-flag='%s'" % flag
    for flag in args.gcc_del_flag:
        cmd += " --gcc-del-flag='%s'" % flag
    return cmd


def serialize_flags(flags, separator=":"):
    out = ""
    for f in flags:
        if out:
            out += separator
        out += f
    return out


class FlagsMatrix:
    def __init__(self):
        self.add_cflags = []
        self.del_cflags = []
        self.add_cxxflags = []
        self.del_cxxflags = []

    def append_flags(self, flags):
        self.add_cflags += flags
        self.add_cxxflags += flags

    def remove_flags(self, flags):
        self.del_cflags += flags
        self.del_cxxflags += flags

    def append_custom_flags(self, args):
        self.add_cflags += args.gcc_add_flag
        self.add_cflags += args.gcc_add_c_only_flag

        self.add_cxxflags += args.gcc_add_flag
        self.add_cxxflags += args.gcc_add_cxx_only_flag

        self.del_cflags   += args.gcc_del_flag
        self.del_cxxflags += args.gcc_del_flag

        return (0 < len(args.gcc_add_flag)) or \
                (0 < len(args.gcc_add_c_only_flag)) or \
                (0 < len(args.gcc_add_cxx_only_flag)) or \
                (0 < len(args.gcc_del_flag))

    def write_to_env(self, env):
        env["CSWRAP_ADD_CFLAGS"]   = serialize_flags(self.add_cflags)
        env["CSWRAP_DEL_CFLAGS"]   = serialize_flags(self.del_cflags)
        env["CSWRAP_ADD_CXXFLAGS"] = serialize_flags(self.add_cxxflags)
        env["CSWRAP_DEL_CXXFLAGS"] = serialize_flags(self.del_cxxflags)


def flags_by_warning_level(level):
    flags = FlagsMatrix()
    for l in range(0, level + 1):
        if l in DEL_FLAGS_BY_LEVEL_COMMON:
            flags.del_cflags += DEL_FLAGS_BY_LEVEL_COMMON[l]
            flags.del_cxxflags += DEL_FLAGS_BY_LEVEL_COMMON[l]

        if l in ADD_FLAGS_BY_LEVEL_COMMON:
            flags.add_cflags += ADD_FLAGS_BY_LEVEL_COMMON[l]
            flags.add_cxxflags += ADD_FLAGS_BY_LEVEL_COMMON[l]

        if l in ADD_FLAGS_BY_LEVEL_C_ONLY:
            flags.add_cflags += ADD_FLAGS_BY_LEVEL_C_ONLY[l]

        if l in ADD_FLAGS_BY_LEVEL_CXX_ONLY:
            flags.add_cxxflags += ADD_FLAGS_BY_LEVEL_CXX_ONLY[l]
    return flags
