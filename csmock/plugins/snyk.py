# Copyright (C) 2023 Red Hat, Inc.
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

from csmock.common.snyk import snyk_write_analysis_meta
from csmock.common.util import sanitize_opts_arg


# default URL to download snyk binary executable
SNYK_BIN_URL = "https://static.snyk.io/cli/latest/snyk-linux"

# default directory where downloaded snyk executable is cached across runs
SNYK_CACHE_DIR = "/var/tmp/csmock/snyk"

SNYK_SCAN_DIR = "/builddir/build/BUILD"

SNYK_OUTPUT = "/builddir/snyk-results.sarif"

SNYK_LOG = "/builddir/snyk-scan.log"

FILTER_CMD = f"csgrep '%s' --mode=json --prepend-path-prefix={SNYK_SCAN_DIR}/ --remove-duplicates > '%s'"

# default value for the maximum amount of time taken by invocation of Snyk (5 hours)
DEFAULT_SNYK_TIMEOUT = 18000


class PluginProps:
    def __init__(self):
        self.description = "Tool to find vulnerabilities in source code."


class Plugin:
    def __init__(self):
        self.enabled = False
        self.auth_token_src = None
        self.snyk_bin = None

    def get_props(self):
        return PluginProps()

    def enable(self):
        self.enabled = True

    def init_parser(self, parser):
        # Create mutually exclusive group for snyk binary source
        snyk_source_group = parser.add_mutually_exclusive_group()

        snyk_source_group.add_argument(
            "--snyk-bin-url",
            help="URL to download snyk binary executable")

        snyk_source_group.add_argument(
            "--snyk-bin",
            help="path to local snyk binary executable (skips download)")

        parser.add_argument(
            "--snyk-auth", default="~/.config/configstore/snyk.json",
            help="file containing snyk authentication token")

        parser.add_argument(
            "--snyk-cache-dir", default=SNYK_CACHE_DIR,
            help="directory where downloaded snyk tarballs are cached across runs")

        parser.add_argument(
            "--snyk-refresh", action="store_true",
            help="force download of snyk binary executable")

        parser.add_argument(
            "--snyk-timeout", type=int, default=DEFAULT_SNYK_TIMEOUT,
            help="maximum amount of time taken by invocation of Snyk [s]")

        parser.add_argument(
            "--snyk-code-test-opts",
            help="space-separated list of additional options passed to the 'snyk code test' command")

    def handle_args(self, parser, args, props):
        if not self.enabled:
            return

        # sanitize options passed to --snyk-code-test-opts to avoid shell injection
        self.snyk_code_test_opts = sanitize_opts_arg(parser, args, "--snyk-code-test-opts")

        # apply default URL if neither snyk source option is specified
        if not args.snyk_bin_url and not args.snyk_bin:
            args.snyk_bin_url = SNYK_BIN_URL

        # check whether we have access to snyk authentication token
        self.auth_token_src = os.path.expanduser(args.snyk_auth)
        if not os.access(self.auth_token_src, os.R_OK):
            parser.error("unable to read snyk authentication token: %s" % self.auth_token_src)

        # define all Snyk's findings with level `error` as important
        props.imp_checker_set.add("SNYK_CODE_WARNING")
        props.imp_csgrep_filters.append(("SNYK_CODE_WARNING", "--event=^error"))

        def fetch_snyk(results):
            # download snyk binary
            cache_dir = args.snyk_cache_dir
            try:
                # make sure the cache directory exists
                os.makedirs(cache_dir, mode=0o755, exist_ok=True)
            except OSError:
                results.error("failed to create snyk cache directory: %s" % cache_dir)
                return 1

            url = args.snyk_bin_url
            snyk_bin_name = url.split("/")[-1]
            snyk_bin = os.path.join(cache_dir, snyk_bin_name)

            if not args.snyk_refresh and os.path.exists(snyk_bin):
                results.print_with_ts(f"reusing previously downloaded snyk executable: {self.snyk_bin}")
            else:
                # fetch the binary executable
                ec = results.exec_cmd(["curl", "-Lfso", snyk_bin, url])
                if 0 != ec:
                    results.error("failed to download snyk binary executable: %s" % url)
                    return ec

                # add eXecute permission on the downloaded file
                os.chmod(snyk_bin, 0o755)

            return snyk_bin

        # fetch snyk using the given URL or use local binary
        def fetch_snyk_hook(results, props):
            if args.snyk_bin:
                # use local snyk binary
                self.snyk_bin = os.path.expanduser(args.snyk_bin)
                results.print_with_ts("using local snyk executable: " + self.snyk_bin)
            else:
                self.snyk_bin = fetch_snyk(results)

            # validate snyk binary (common path for both local and downloaded)
            if not os.path.exists(self.snyk_bin):
                results.error("snyk binary does not exist: %s" % self.snyk_bin)
                return 2

            if not os.access(self.snyk_bin, os.X_OK):
                results.error("snyk binary is not executable: %s" % self.snyk_bin)
                return 2

            # query version of snyk
            (ec, out) = results.get_cmd_output([self.snyk_bin, 'version'], shell=False)
            if 0 != ec:
                results.error("failed to query snyk version", ec=ec)
                return ec

            # parse and record the version of snyk
            ver = out.split(" ")[0]
            results.ini_writer.append("analyzer-version-snyk-code", ver)

            # copy snyk binary into the chroot
            props.copy_in_files += [self.snyk_bin]

            # get the results out of the chroot
            props.copy_out_files += [SNYK_OUTPUT, SNYK_LOG]
            return 0

        # fetch snyk binary executable before initializing the buildroot
        props.pre_mock_hooks += [fetch_snyk_hook]

        def scan_hook(results, mock, props):
            # copy snyk authentication token into the chroot
            dst_dir = "/builddir/.config/configstore"
            mock.exec_chroot_cmd("mkdir -p %s" % dst_dir)
            auth_token_dst = os.path.join(dst_dir, "snyk.json")
            ec = mock.exec_mock_cmd(["--copyin", self.auth_token_src, auth_token_dst])
            if 0 != ec:
                results.error("failed to copy snyk authentication token", ec=ec)
                return ec

            # command to run snyk code
            cmd = f"{self.snyk_bin} code test -d {SNYK_SCAN_DIR}"

            if self.snyk_code_test_opts:
                # propagate options given to --snyk-code-test-opts
                cmd += f" {self.snyk_code_test_opts}"

            cmd += f" --sarif-file-output={SNYK_OUTPUT} >/dev/null 2>{SNYK_LOG}"

            if args.snyk_timeout:
                # wrap snyk invocation by timeout(1)
                cmd = f"/usr/bin/timeout {args.snyk_timeout} {cmd}"

            # snyk requires network connection in the chroot
            mock_cmd = ["--enable-network", "--chroot", cmd]

            # run snyk code
            ec = mock.exec_mock_cmd(mock_cmd)

            # remove authentication token from the chroot
            mock.exec_chroot_cmd("/bin/rm -fv %s" % auth_token_dst)

            # check exit code of snyk code itself
            if ec == 3:
                # If there are no supported project, we return no results but no crash.
                results.print_with_ts("snyk-code: no supported project for Snyk")
                # If no supported project, no results file is generated and no stats are generated
                props.copy_out_files.remove(SNYK_OUTPUT)
                props.post_process_hooks.remove(write_snyk_stats_metadata)
                return 0
            if ec not in [0, 1]:
                results.error("snyk code returned unexpected exit status: %d" % ec, ec=ec)

            # returning non-zero would prevent csmock from archiving SNYK_LOG
            return 0

        # run snyk after successful build
        props.post_install_hooks += [scan_hook]

        # convert the results into the csdiff's JSON format
        def filter_hook(results):
            src = results.dbgdir_raw + SNYK_OUTPUT
            if not os.path.exists(src):
                # do not convert SARIF results if they were not provided by Snyk
                return 0
            dst = "%s/snyk-results.json" % results.dbgdir_uni
            cmd = FILTER_CMD % (src, dst)
            return results.exec_cmd(cmd, shell=True)

        def write_snyk_stats_metadata(results):
            raw_results_file = results.dbgdir_raw + SNYK_OUTPUT
            return snyk_write_analysis_meta(results, raw_results_file)

        props.post_process_hooks += [write_snyk_stats_metadata, filter_hook]
