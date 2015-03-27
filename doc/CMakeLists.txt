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

set(MAN_PAGES "")

# rules to create symlinks to local python packages
add_custom_command(OUTPUT ${PROJECT_BINARY_DIR}/py/csmock
    COMMAND mkdir -pv ${PROJECT_BINARY_DIR}/py/csmock VERBATIM)
add_custom_command(OUTPUT ${PROJECT_BINARY_DIR}/py/csmock/common
    COMMAND ln -fsv ${PROJECT_SOURCE_DIR}/py/common
                    ${PROJECT_SOURCE_DIR}/py/common/__init__.py
                    ${PROJECT_BINARY_DIR}/py/csmock/
    DEPENDS ${PROJECT_BINARY_DIR}/py/csmock VERBATIM)

# macro to generate a man page from the corresponding binary
macro(create_manpage BINARY)
    add_custom_command(OUTPUT ${PROJECT_BINARY_DIR}/${BINARY}.1
        COMMAND PYTHONPATH=${PROJECT_BINARY_DIR}/py ${HELP2MAN} --no-info
        --section 1 --include ${CMAKE_CURRENT_SOURCE_DIR}/${BINARY}.h2m
          ${PROJECT_BINARY_DIR}/${BINARY}
        > ${PROJECT_BINARY_DIR}/${BINARY}.1
        || rm -f ${PROJECT_BINARY_DIR}/${BINARY}.1
        COMMENT "Generating ${BINARY} man page"
        DEPENDS ${PROJECT_BINARY_DIR}/${BINARY}
                ${PROJECT_BINARY_DIR}/py/csmock/common
        VERBATIM)
    install(FILES ${PROJECT_BINARY_DIR}/${BINARY}.1
        DESTINATION ${SHARE_INSTALL_PREFIX}/man/man1)
    set(MAN_PAGES ${MAN_PAGES} ${PROJECT_BINARY_DIR}/${BINARY}.1)
endmacro(create_manpage)

# generate man pages using help2man if available
find_program(HELP2MAN help2man)
if(HELP2MAN)
    if(ENABLE_CSBUILD)
        create_manpage(csbuild)
    endif()

    if(ENABLE_CSMOCK)
        create_manpage(csmock)
    endif()

    if(NOT "${MAN_PAGES}" STREQUAL "")
        add_custom_target(doc ALL DEPENDS ${MAN_PAGES})
    endif()
endif()
