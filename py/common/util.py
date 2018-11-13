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
        if rc != 0:
            results.error("tool \"%s\" does not seem to be installed in build root" \
                    % tool, ec=0)
            return rc

        ver = re.sub("-[0-9].*$", "", re.sub("^%s-" % tool, "", nvr.strip()))
        results.ini_writer.append("analyzer-version-%s" % tool_key, ver)
        return 0

    props.post_depinst_hooks += [toolver_by_rpmlist_hook]


def add_paired_flag(parser, name, help):
    help_no = "disables --" + name
    arg = parser.add_argument(
        "--" + name, action="store_const", const=True, help=help)
    parser.add_argument(
        "--no-" + name, action="store_const", const=False, help=help_no,
        dest=arg.dest)


def install_script_scan_opts(parser, tool):
    # render help text
    help_tpl = "make %s scan files in the %s directory (%s by default) "
    help_build   = help_tpl % (tool, "build",  "disabled")
    help_install = help_tpl % (tool, "install", "enabled")

    # add 2x2 options
    add_paired_flag(parser, tool + "-scan-build", help=help_build)
    add_paired_flag(parser, tool + "-scan-install", help=help_install)


def dirs_to_scan_by_args(parser, args, props, tool):
    scan_build = getattr(args, tool + "_scan_build")
    if scan_build is None:
        scan_build = (props.shell_cmd_to_build is not None)

    scan_install = getattr(args, tool + "_scan_install")
    if scan_install is None:
        scan_install = (props.shell_cmd_to_build is None)

    if not scan_build and not scan_install:
        parser.error("either --%s-scan-build or --%s-scan-install must be enabled" %
                     (tool, tool))

    if scan_install and (props.shell_cmd_to_build is not None):
        parser.error("--shell-cmd and --%s-scan-install cannot be used together" %
                     tool)

    dirs_to_scan = ""
    if scan_build:
        dirs_to_scan += "/builddir/build/BUILD"
        if scan_install:
            dirs_to_scan += " "

    if scan_install:
        dirs_to_scan += "/builddir/build/BUILDROOT"
        props.need_rpm_bi = True

    return dirs_to_scan
