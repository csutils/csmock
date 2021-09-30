# Copyright (C) 2021 Red Hat, Inc.
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

import csmock.common.util

import re
import shutil


GITLEAKS_SCAN_DIR = "/builddir/build/BUILD"

GITLEAKS_OUTPUT = "/builddir/gitleaks-capture.js"

GITLEAKS_LOG = "/builddir/gitleaks-capture.log"

FILTER_CMD = "gitleaks-convert-output '%s' '%s' | csgrep --mode=json > '%s'"


class PluginProps:
    def __init__(self):
        self.description = "[TODO] experimental csmock plug-in"


class Plugin:
    def __init__(self):
        self.enabled = False

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        parser.add_argument(
            "--gitleaks-bin-url", default="https://nexus.corp.redhat.com/repository/infosec-raw/gitleaks/releases/linux/gitleaks-v7.5.0",
            help="URL to download gitleaks binary executable from")

        parser.add_argument(
            "--gitleaks-config",
            help="local configuration file to be used for gitleaks")

    def handle_args(self, parser, args, props):
        if args.gitleaks_config is not None:
            self.enable()

        if not self.enabled:
            return

        # fetch gitleaks using the given URL
        def fetch_gitleaks_hook(results):
            gitleaks_bin = "%s/gitleaks" % results.tmpdir
            url = args.gitleaks_bin_url
            ec = results.exec_cmd(['curl', '-o', gitleaks_bin, url])
            if 0 != ec:
                results.error("failed to download gitleask binary executable: %s" % url)
                return ec

            ec = results.exec_cmd(['chmod', '0755', gitleaks_bin])
            if 0 != ec:
                return ec

            (ec, out) = results.get_cmd_output([gitleaks_bin, '--version'], shell=False)
            if 0 != ec:
                return ec

            ver = re.sub("^v", "", out)
            results.ini_writer.append("analyzer-version-gitleaks", ver)

            props.copy_in_files += [gitleaks_bin]
            cmd = "%s --no-git --path=%s --report=%s" % (gitleaks_bin, GITLEAKS_SCAN_DIR, GITLEAKS_OUTPUT)
            props.copy_out_files += [GITLEAKS_OUTPUT, GITLEAKS_LOG]

            if args.gitleaks_config is not None:
                gitleaks_config = "%s/gitleaks-config.js" % results.tmpdir
                shutil.copyfile(args.gitleaks_config, gitleaks_config)
                props.copy_in_files += [gitleaks_config]
                cmd += " --config-path=%s" % gitleaks_config

            cmd += " 2>%s" % GITLEAKS_LOG
            props.post_build_chroot_cmds += [cmd]
            return 0

        props.pre_mock_hooks += [fetch_gitleaks_hook]

        def filter_hook(results):
            src = results.dbgdir_raw + GITLEAKS_OUTPUT
            dst = "%s/gitleaks-capture.js" % results.dbgdir_uni
            cmd = FILTER_CMD % (GITLEAKS_SCAN_DIR, src, dst)
            return results.exec_cmd(cmd, shell=True)

        props.post_process_hooks += [filter_hook]
