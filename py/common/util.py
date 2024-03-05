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

import os
import re
import shlex


def shell_quote(str_in):
    str_out = ""
    for i in range(0, len(str_in)):
        c = str_in[i]
        if c == "\\":
            str_out += "\\\\"
        elif c == "\"":
            str_out += "\\\""
        elif c == "$":
            str_out += "\\$"
        else:
            str_out += c
    return "\"" + str_out + "\""


def arg_value_by_name(parser, args, arg_name):
    """return value of an argument parsed by argparse.ArgumentParser"""
    for action in parser._actions:
        if arg_name in action.option_strings:
            return getattr(args, action.dest)


def sanitize_opts_arg(parser, args, arg_name):
    """sanitize command-line options passed to an option of argparse.ArgumentParser"""
    opts_str = arg_value_by_name(parser, args, arg_name)
    if opts_str is None:
        return None

    # split, quote, and rejoin the options to avoid shell injection
    try:
        split_opts = shlex.split(args.snyk_code_test_opts)

        # starting with Python 3.8, one can use shlex.join(split_opts)
        return ' '.join(shlex.quote(arg) for arg in split_opts)

    except ValueError as e:
        parser.error(f"failed to parse value given to {arg_name}: {str(e)}")


def strlist_to_shell_cmd(cmd_in, escape_special=False):
    def translate_one(i):
        if escape_special:
            return shell_quote(i)
        return "'%s'" % i

    if type(cmd_in) is str:
        return "sh -c %s" % translate_one(cmd_in)
    cmd_out = ""
    for i in cmd_in:
        cmd_out += " " + translate_one(i)
    return cmd_out.lstrip()


def write_toolver(ini_writer, tool_key, ver):
    ini_writer.append("analyzer-version-%s" % tool_key, ver)


def write_toolver_from_rpmlist(results, mock, tool, tool_key):
    cmd = "grep '^%s-[0-9]' %s/rpm-list-mock.txt" % (tool, results.dbgdir)
    (rc, nvr) = results.get_cmd_output(cmd)
    if rc != 0:
        results.error("tool \"%s\" does not seem to be installed in build root" \
                % tool, ec=0)
        return rc

    ver = re.sub("-[0-9].*$", "", re.sub("^%s-" % tool, "", nvr.strip()))
    write_toolver(results.ini_writer, tool_key, ver)
    return 0


def install_default_toolver_hook(props, tool):
    tool_key = tool.lower()

    def toolver_by_rpmlist_hook(results, mock):
        return write_toolver_from_rpmlist(results, mock, tool, tool_key)

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


def require_file(parser, name):
    """Print an error and exit unsuccessfully if 'name' is not a file"""
    if not os.path.isfile(name):
        parser.error(f"'{name}' is not a file")
