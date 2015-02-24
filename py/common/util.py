#!/usr/bin/env python

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

import re

def install_default_toolver_hook(props, tool):
    tool_key = tool.lower()

    def toolver_by_rpmlist_hook(results, mock):
        cmd = "grep '^%s-[0-9]' %s/rpm-list-mock.txt" % (tool, results.dbgdir)
        (rc, nvr) = results.get_cmd_output(cmd)
        if 0 != rc:
            return rc

        ver = re.sub("-[0-9].*$", "", re.sub("^%s-" % tool, "", nvr.strip()))
        results.ini_writer.append("analyzer-version-%s" % tool_key, ver)
        return 0

    props.post_depinst_hooks += [toolver_by_rpmlist_hook]
