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
    0: set(["-Werror*", "-fdiagnostics-color*"])}

ADD_FLAGS_BY_LEVEL_COMMON = {
    1: set(["-Wall", "-Wextra"]),
    2: set(["-Wunreachable-code", "-Wundef", "-Wcast-align",
            "-Wpointer-arith", "-Wfloat-equal", "-Wshadow",
            "-Wwrite-strings", "-Wformat=2"])}

ADD_FLAGS_BY_LEVEL_C_ONLY = {
    0: set(["-Wno-unknown-pragmas"]),
    2: set(["-Wstrict-prototypes"])}

ADD_FLAGS_BY_LEVEL_CXX_ONLY = {
    2: set(["-Wctor-dtor-privacy", "-Woverloaded-virtual"])}


def serialize_flags(flags):
    out = ""
    for f in flags:
        if out:
            out += ":"
        out += f
    return out


class FlagsMatrix:
    def __init__(self):
        self.add_cflags = set()
        self.del_cflags = set()
        self.add_cxxflags = set()
        self.del_cxxflags = set()

    def __ior__(self, b):
        r = FlagsMatrix()
        r.add_cflags = self.add_cflags | b.add_cflags
        r.del_cflags = self.del_cflags | b.del_cflags
        r.add_cxxflags = self.add_cxxflags | b.add_cxxflags
        r.del_cxxflags = self.del_cxxflags | b.del_cxxflags
        return r

    def write_to_env(self, env):
        env["CSWRAP_ADD_CFLAGS"]   = serialize_flags(self.add_cflags)
        env["CSWRAP_DEL_CFLAGS"]   = serialize_flags(self.del_cflags)
        env["CSWRAP_ADD_CXXFLAGS"] = serialize_flags(self.add_cxxflags)
        env["CSWRAP_DEL_CXXFLAGS"] = serialize_flags(self.del_cxxflags)


def flags_by_warning_level(level):
    flags = FlagsMatrix()
    for l in range(0, level + 1):
        if l in DEL_FLAGS_BY_LEVEL_COMMON:
            flags.del_cflags |= DEL_FLAGS_BY_LEVEL_COMMON[l]
            flags.del_cxxflags |= DEL_FLAGS_BY_LEVEL_COMMON[l]

        if l in ADD_FLAGS_BY_LEVEL_COMMON:
            flags.add_cflags |= ADD_FLAGS_BY_LEVEL_COMMON[l]
            flags.add_cxxflags |= ADD_FLAGS_BY_LEVEL_COMMON[l]

        if l in ADD_FLAGS_BY_LEVEL_C_ONLY:
            flags.add_cflags |= ADD_FLAGS_BY_LEVEL_C_ONLY[l]

        if l in ADD_FLAGS_BY_LEVEL_CXX_ONLY:
            flags.add_cxxflags |= ADD_FLAGS_BY_LEVEL_CXX_ONLY[l]
    return flags
