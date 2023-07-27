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

import os
import re
import shutil


# default URL to download gitleaks binary executable (in a .tar.gz) from
GITLEAKS_BIN_URL = "https://github.com/zricethezav/gitleaks/releases/download/v8.15.1/gitleaks_8.15.1_linux_x64.tar.gz"

# default directory where downloaded Gitleaks tarballs are cached across runs
GITLEAKS_CACHE_DIR = "/var/tmp/csmock/gitleaks"

GITLEAKS_SCAN_DIR = "/builddir/build/BUILD"

GITLEAKS_OUTPUT = "/builddir/gitleaks-capture.sarif"

GITLEAKS_LOG = "/builddir/gitleaks-capture.log"

FILTER_CMD = "csgrep '%s' --mode=json --warning-rate-limit=%i --limit-msg-len=%i > '%s'"


class PluginProps:
    def __init__(self):
        self.description = "Tool for finding secrets in source code."

        # include this plug-in in `csmock --all-tools`
        self.stable = True


class Plugin:
    def __init__(self):
        self.enabled = False

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        parser.add_argument(
            "--gitleaks-bin-url", default=GITLEAKS_BIN_URL,
            help="URL to download gitleaks binary executable (in a .tar.gz) from")

        parser.add_argument(
            "--gitleaks-cache-dir", default=GITLEAKS_CACHE_DIR,
            help="directory where downloaded Gitleaks tarballs are cached across runs")

        parser.add_argument(
            "--gitleaks-config",
            help="local configuration file to be used for gitleaks")

        parser.add_argument(
            "--gitleaks-rate-limit", type=int, default=1024,
            help="drop warnings if their count exceeds the specified limit")

        parser.add_argument(
            "--gitleaks-limit-msg-len", type=int, default=512,
            help="trim message if it exceeds max message length")

        parser.add_argument(
            "--gitleaks-refresh", action="store_true",
            help="force download of gitleaks binary executable (in a .tar.gz) from")

    def handle_args(self, parser, args, props):
        if args.gitleaks_config is not None:
            self.enable()

        if not self.enabled:
            return

        # fetch gitleaks using the given URL
        def fetch_gitleaks_hook(results, props):
            cache_dir = args.gitleaks_cache_dir
            try:
                # make sure the cache directory exists
                os.makedirs(cache_dir, mode=0o755, exist_ok=True)
            except OSError:
                results.error("failed to create gitleaks cache directory: %s" % cache_dir)
                return 1

            url = args.gitleaks_bin_url
            gitleaks_tgz_name = url.split("/")[-1]
            gitleaks_tgz = os.path.join(cache_dir, gitleaks_tgz_name)

            if not args.gitleaks_refresh and os.path.exists(gitleaks_tgz):
                results.print_with_ts("reusing previously downloaded gitleaks tarball: %s" % gitleaks_tgz)
            else:
                # fetch .tar.gz
                ec = results.exec_cmd(['curl', '-Lfso', gitleaks_tgz, url])
                if 0 != ec:
                    results.error("failed to download gitleaks binary executable: %s" % url)
                    return ec

            # extract the binary executable
            ec = results.exec_cmd(['tar', '-C', results.tmpdir, '-xvzf', gitleaks_tgz, 'gitleaks'])
            if 0 != ec:
                results.error("failed to extract gitleaks binary executable from .tar.gz: %s" % url)
                return ec

            # check whether we have eXecute access
            gitleaks_bin = os.path.join(results.tmpdir, "gitleaks")
            if not os.access(gitleaks_bin, os.X_OK):
                results.error("gitleaks binary is not executable: %s" % gitleaks_bin)
                return 2

            # query version of gitleaks
            (ec, out) = results.get_cmd_output([gitleaks_bin, 'version'], shell=False)
            if 0 != ec:
                return ec

            ver = re.sub("^v", "", out)
            results.ini_writer.append("analyzer-version-gitleaks", ver)

            props.copy_in_files += [gitleaks_bin]
            cmd = "%s detect --no-git --source=%s --report-path=%s --report-format=sarif" % (gitleaks_bin, GITLEAKS_SCAN_DIR, GITLEAKS_OUTPUT)
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
            cmd = FILTER_CMD % (src, args.gitleaks_rate_limit, args.gitleaks_limit_msg_len, dst)
            return results.exec_cmd(cmd, shell=True)

        props.post_process_hooks += [filter_hook]
