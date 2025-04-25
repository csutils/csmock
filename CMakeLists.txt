# Copyright (C) 2014-2022 Red Hat, Inc.
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

cmake_minimum_required(VERSION 3.12)
project(csmock NONE)

set(PERM_EXECUTABLE
    OWNER_READ OWNER_WRITE OWNER_EXECUTE
    GROUP_READ             GROUP_EXECUTE
    WORLD_READ             WORLD_EXECUTE)

if(NOT DEFINED SHARE_INSTALL_PREFIX)
    set(SHARE_INSTALL_PREFIX /usr/share)
endif()

option(ENABLE_CSBUILD "if enabled, install the csbuild tool" ON)
option(ENABLE_CSMOCK  "if enabled, install the csmock tool"  ON)

if(ENABLE_CSMOCK)
    install(FILES
        ${CMAKE_CURRENT_SOURCE_DIR}/cwe-map.csv
        DESTINATION ${SHARE_INSTALL_PREFIX}/csmock)
endif()

add_subdirectory(csmock)
add_subdirectory(doc)
add_subdirectory(scripts)
