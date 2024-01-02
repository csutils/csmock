# Copyright (C) 2024 Red Hat, Inc.
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

"""
Semgrep client plugin
"""
import os

from csmock.common.util import sanitize_opts_arg  # pylint: disable=import-error


# disable metrics to be sent to semgrep cloud
DEFAULT_SEMGREP_SEND_METRICS = "off"

# This plug-in is pinned to a specific version of Semgrep because newer Semgrep
# versions break compatibility with externally maintained Semgrep rules.  See
# https://github.com/semgrep/semgrep/releases for available releases.
SEMGREP_CLI_VERSION = "1.56.0"

SEMGREP_SCAN_DIR = "/builddir/build/BUILD"

SEMGREP_SCAN_OUTPUT = "/builddir/semgrep-scan-results.sarif"

SEMGREP_SCAN_CHROOT_ROOT_PATH = "/builddir/semgrep-chroot-root"

SEMGREP_SCAN_LOG = "/builddir/semgrep-scan.log"


class PluginProps:  # pylint: disable=too-few-public-methods
    """
    Props of the plugin
    """
    def __init__(self):
        self.description = (
            "A fast, open-source, static analysis engine for finding bugs, "
            "detecting dependency vulnerabilities, and enforcing code standards."
        )

        self.stable = False


class Plugin:
    """
    Semgrep static analysis engine plugin
    """
    def __init__(self):
        self.enabled = False
        self.semgrep_scan_opts = None

    def get_props(self):  # pylint: disable=missing-function-docstring
        return PluginProps()

    def enable(self):  # pylint: disable=missing-function-docstring
        self.enabled = True

    def init_parser(self, parser):
        """
        Initialize the argument parser for the Semgrep plugin.
        """
        parser.add_argument(
            "--semgrep-metrics",
            default=DEFAULT_SEMGREP_SEND_METRICS,
            help=f"configure whether usage metrics are sent to the Semgrep server (defaults to {DEFAULT_SEMGREP_SEND_METRICS})",
        )

        parser.add_argument(
            "--semgrep-rules-repo",
            help="semgrep rules repo, assuming rules are located under the 'rules' sub-directory",
        )

        parser.add_argument(
            "--semgrep-verbose",
            action="store_true",
            help="show more details about what rules are running, which files failed to parse, etc.",
        )

        parser.add_argument(
            "--semgrep-scan-opts",
            help="space-separated list of additional options passed to the 'semgrep scan' command",
        )

    def handle_args(self, parser, args, props):  # pylint: disable=too-many-statements,missing-function-docstring
        if not self.enabled:
            return

        if not args.semgrep_rules_repo:
            parser.error("'--semgrep-rules-repo' is required to run semgrep scan")

        # sanitize options passed to --semgrep-scan-opts to avoid shell injection
        self.semgrep_scan_opts = sanitize_opts_arg(parser, args, "--semgrep-scan-opts")

        # install semgrep cli and download semgrep rules
        def prepare_semgrep_runtime_hook(results, props):
            # target dir where semgrep cli and its dependencies are installed
            semgrep_lib_dir = os.path.join(results.tmpdir, "semgrep_lib")
            try:
                # make sure the lib directory exists
                os.makedirs(semgrep_lib_dir, mode=0o755, exist_ok=True)
            except OSError:
                results.error("failed to create semgrep lib directory")
                return 1

            # install semgrep cli using pip
            cmd = f"python3 -m pip install --target={semgrep_lib_dir} semgrep=={SEMGREP_CLI_VERSION}"
            ec = results.exec_cmd(cmd, shell=True)
            if 0 != ec:
                results.error("failed to install semgrep cli using pip")
                return 1

            semgrep_prefix = f"env PATH={semgrep_lib_dir}/bin:$PATH, PYTHONPATH={semgrep_lib_dir}"

            semgrep_rules_repo_dir = os.path.join(results.tmpdir, "semgrep_rules")
            repo_clone_cmd = [
                "git", "clone", "--depth", "1",
                args.semgrep_rules_repo,
                semgrep_rules_repo_dir
            ]
            ec = results.exec_cmd(repo_clone_cmd)
            if 0 != ec:
                results.error("failed to download semgrep rules")
                return ec
            # query version of semgrep
            cmd = semgrep_prefix + " semgrep --version"
            ec, output = results.get_cmd_output(cmd)
            if 0 != ec:
                results.error("failed to query semgrep cli version", ec=ec)
                return ec

            # parse and record the version of semgrep cli
            version = output.rstrip("\n")
            results.ini_writer.append("analyzer-version-semgrep-cli", version)

            # get the results out of the chroot
            props.copy_out_files += [
                SEMGREP_SCAN_OUTPUT,
                SEMGREP_SCAN_LOG,
                SEMGREP_SCAN_CHROOT_ROOT_PATH,
            ]
            return 0

        props.pre_mock_hooks += [prepare_semgrep_runtime_hook]

        def scan_hook(results, mock, props):  # pylint: disable=unused-argument
            semgrep_lib_dir = os.path.join(results.tmpdir, "semgrep_lib")
            semgrep_prefix = f"env PATH={semgrep_lib_dir}/bin:$PATH PYTHONPATH={semgrep_lib_dir}"
            # assuming semgrep rules are located under the 'rules' directory
            semgrep_rules_dir = os.path.join(results.tmpdir, "semgrep_rules/rules")
            # write the chroot root path to the SEMGREP_SCAN_CHROOT_ROOT_PATH
            with open(f"{mock.mock_root}{SEMGREP_SCAN_CHROOT_ROOT_PATH}", "w", encoding="utf-8") as f:
                f.write(mock.mock_root)

            # command to run semgrep scan
            semgrep_scan_cmd = semgrep_prefix + (
                f" semgrep scan --metrics={args.semgrep_metrics} --sarif"
                f" --config={semgrep_rules_dir}"
            )
            if args.semgrep_verbose:
                semgrep_scan_cmd += " --verbose"

            # append additional options passed to the 'semgrep scan' command
            if self.semgrep_scan_opts:
                semgrep_scan_cmd += f" {self.semgrep_scan_opts}"

            # eventually append the target directory to be scanned
            semgrep_scan_cmd += (
                f" --output={mock.mock_root}{SEMGREP_SCAN_OUTPUT} {mock.mock_root}{SEMGREP_SCAN_DIR}"
                f" 2>{mock.mock_root}{SEMGREP_SCAN_LOG}"
            )
            # run semgrep scan
            ec = results.exec_cmd(semgrep_scan_cmd, shell=True)

            # according to semgrep cli scan doc, below are the known error codes
            error_messages = {
                123: "Indiscriminate errors reported on standard error.",
                124: "Command line parsing errors.",
                125: "Unexpected internal errors (bugs)."
            }

            if ec in error_messages:
                results.error(f"semgrep: {error_messages[ec]} Command: {semgrep_scan_cmd}")
            elif ec != 0:
                results.error(f"semgrep: Scan failed with exit code {ec}. Command: {semgrep_scan_cmd}")

            return 0

        # run semgrep scan after successful build
        props.post_install_hooks += [scan_hook]

        # convert the results into the csdiff's JSON format
        def filter_hook(results):
            src = results.dbgdir_raw + SEMGREP_SCAN_OUTPUT
            if not os.path.exists(src):
                return 0
            dst = f"{results.dbgdir_uni}/semgrep-scan-results.json"

            # read from SEMGREP_SCAN_CHROOT_ROOT_PATH to get the chroot root path
            chroot_root_path = ""
            with open(f"{results.dbgdir_raw}{SEMGREP_SCAN_CHROOT_ROOT_PATH}", "r", encoding="utf-8") as f:
                chroot_root_path = f.read().rstrip("\n")

            # remove the `SEMGREP_SCAN_CHROOT_ROOT_PATH` file
            os.remove(f"{results.dbgdir_raw}{SEMGREP_SCAN_CHROOT_ROOT_PATH}")

            tmp_dir_basename = results.tmpdir.split("/")[-1]
            semgrep_rules_path_prefix = f"{tmp_dir_basename}/semgrep_rules/"
            # semgrep report has dot-separated rules path
            tmp_path = semgrep_rules_path_prefix.lstrip("/").replace("/", r"\.")
            # strip suspicious path prefix from the semgrep rules directory
            # depending on where the semgrep scan process is run, the raw report may or may not contain "/tmp"
            # in its rules path. The following sed command strips suspicious path prefixes by removing
            # any sequence of non left-square-bracket characters preceding '{tmp_path}'
            cmd = (
                fr"csgrep {src} --mode=json --strip-path-prefix {chroot_root_path}{SEMGREP_SCAN_DIR}/ "
                fr"| sed 's|[^\[]*{tmp_path}||' > {dst}"  # pylint: disable=W1401
            )

            return results.exec_cmd(cmd, shell=True)

        props.post_process_hooks += [filter_hook]
