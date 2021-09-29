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

if(ENABLE_CSBUILD)
    install(FILES
        ${CMAKE_CURRENT_SOURCE_DIR}/run-scan.sh
        DESTINATION ${SHARE_INSTALL_PREFIX}/csbuild/scripts
        PERMISSIONS ${PERM_EXECUTABLE})
endif()

if(ENABLE_CSMOCK)
    install(DIRECTORY chroot-fixups
        FILE_PERMISSIONS ${PERM_EXECUTABLE}
        DESTINATION ${SHARE_INSTALL_PREFIX}/csmock/scripts)

    install(FILES
        ${CMAKE_CURRENT_SOURCE_DIR}/enable-keep-going.sh
        ${CMAKE_CURRENT_SOURCE_DIR}/find-unicode-control.py
        ${CMAKE_CURRENT_SOURCE_DIR}/patch-rawbuild.sh
        ${CMAKE_CURRENT_SOURCE_DIR}/run-bandit.sh
        ${CMAKE_CURRENT_SOURCE_DIR}/run-pylint.sh
        ${CMAKE_CURRENT_SOURCE_DIR}/run-shellcheck.sh
        DESTINATION ${SHARE_INSTALL_PREFIX}/csmock/scripts
        PERMISSIONS ${PERM_EXECUTABLE})
endif()
