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

find_package(Python3 REQUIRED)

set(PLUGIN_DIR "${Python3_SITELIB}/csmock/plugins")
message(STATUS "PLUGIN_DIR: ${PLUGIN_DIR}")

# install common python modules to the csmock/common subdirectory
set(src_dir "${CMAKE_CURRENT_SOURCE_DIR}")
set(dst_dir "${Python3_SITELIB}/csmock")
install(FILES ${src_dir}/__init__.py        DESTINATION ${dst_dir})
install(FILES ${src_dir}/common/__init__.py DESTINATION ${dst_dir}/common)
install(FILES ${src_dir}/common/cflags.py   DESTINATION ${dst_dir}/common)
install(FILES ${src_dir}/common/results.py  DESTINATION ${dst_dir}/common)
install(FILES ${src_dir}/common/snyk.py     DESTINATION ${dst_dir}/common)
install(FILES ${src_dir}/common/util.py     DESTINATION ${dst_dir}/common)

macro(install_executable FILE_NAME)
    configure_file(
        ${CMAKE_CURRENT_SOURCE_DIR}/${FILE_NAME}
        ${PROJECT_BINARY_DIR}/${FILE_NAME}
        @ONLY)

    install(FILES ${PROJECT_BINARY_DIR}/${FILE_NAME}
        DESTINATION bin
        PERMISSIONS ${PERM_EXECUTABLE})
endmacro()

if(ENABLE_CSBUILD)
    install_executable(csbuild)
endif()

if(ENABLE_CSMOCK)
    install_executable(csmock)
    install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/plugins/__init__.py
        DESTINATION ${PLUGIN_DIR})

    macro(install_plugin PLUGIN_NAME)
        install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/plugins/${PLUGIN_NAME}.py
            DESTINATION ${PLUGIN_DIR})
    endmacro()

    install_plugin(bandit)
    install_plugin(cbmc)
    install_plugin(clang)
    install_plugin(cppcheck)
    install_plugin(divine)
    install_plugin(gcc)
    install_plugin(gitleaks)
    install_plugin(infer)
    install_plugin(pylint)
    install_plugin(shellcheck)
    install_plugin(smatch)
    install_plugin(snyk)
    install_plugin(strace)
    install_plugin(symbiotic)
    install_plugin(valgrind)
    install_plugin(unicontrol)
endif()
