# Copyright (C) 2019 Red Hat, Inc.
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

# standard imports
import codecs
import datetime
import errno
import os
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile

# local imports
from csmock.common.util         import shell_quote
from csmock.common.util         import strlist_to_shell_cmd

CSGREP_FINAL_FILTER_ARGS = "--invert-match --event \"internal warning\" \
--prune-events=1"

def current_iso_date():
    now = datetime.datetime.now()
    return "%04u-%02u-%02u %02u:%02u:%02u" % \
           (now.year, now.month, now.day, now.hour, now.minute, now.second)


class FatalError(Exception):
    def __init__(self, ec):
        self.ec = ec


class ScanResults:
    def __init__(self, output, tool, tool_version, keep_going=False, create_dbgdir=True,
                 no_clean=False):
        self.output = output
        self.tool = tool
        self.tool_version = tool_version
        self.keep_going = keep_going
        self.create_dbgdir = create_dbgdir
        self.no_clean = no_clean
        self.use_xz = False
        self.use_tar = False
        self.dirname = os.path.basename(output)
        self.codec = codecs.lookup('utf8')
        self.ec = 0
        self.dying = False

        # just to silence pylint, will be initialized in __enter__()
        self.tmpdir = None
        self.resdir = None
        self.dbgdir = None
        self.dbgdir_raw = None
        self.dbgdir_uni = None
        self.log_pid = None
        self.log_fd = None
        self.ini_writer = None
        self.subproc = None

        m = re.match("^(.*)\\.xz$", self.dirname)
        if m is not None:
            self.use_xz = True
            self.dirname = m.group(1)

        m = re.match("^(.*)\\.tar$", self.dirname)
        if m is not None:
            self.use_tar = True
            self.dirname = m.group(1)

    def utf8_wrap(self, fd):
        # the following hack is needed to support both Python 2 and 3
        return codecs.StreamReaderWriter(
            fd, self.codec.streamreader, self.codec.streamwriter)

    def __enter__(self):
        self.tmpdir = tempfile.mkdtemp(prefix=self.tool)
        if self.use_tar:
            self.resdir = "%s/%s" % (self.tmpdir, self.dirname)
        else:
            if os.path.exists(self.output):
                shutil.rmtree(self.output)
            self.resdir = self.output

        try:
            os.mkdir(self.resdir)
        except OSError as e:
            sys.stderr.write(
                "error: failed to create output directory: %s\n" % e)
            raise FatalError(1)

        if self.create_dbgdir:
            self.dbgdir = "%s/debug" % self.resdir
            self.dbgdir_raw = "%s/raw-results" % self.dbgdir
            self.dbgdir_uni = "%s/uni-results" % self.dbgdir
            os.mkdir(self.dbgdir)
            os.mkdir(self.dbgdir_raw)
            os.mkdir(self.dbgdir_uni)
            os.mknod(os.path.join(self.dbgdir_uni, "empty.err"), stat.S_IFREG|0o444)

        tee = ["tee", "%s/scan.log" % self.resdir]
        self.log_pid = subprocess.Popen(
            tee, stdin=subprocess.PIPE, preexec_fn=os.setsid)
        self.log_fd = self.utf8_wrap(self.log_pid.stdin)

        def signal_handler(signum, frame):
            # avoid throwing FatalError out of a signal handler
            self.dying = True
            self.error("caught signal %d" % signum, 128 + signum)
            if self.subproc is not None:
                # forward the signal to the child process being executed
                try:
                    os.kill(self.subproc.pid, signum)
                except Exception as e:
                    self.error("failed to kill child process: %s" % e)
            # this will make the foreground process throw FatalError synchronously
            self.dying = False

        for i in [signal.SIGINT, signal.SIGPIPE, signal.SIGQUIT, signal.SIGTERM]:
            signal.signal(i, signal_handler)

        self.ini_writer = IniWriter(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.ini_writer.close()
        if self.no_clean:
            self.print_with_ts(f"temporary directory preserved: {self.tmpdir}")

        self.print_with_ts("%s exit code: %d\n" % (self.tool, self.ec), prefix="<<< ")
        self.log_fd.close()
        self.log_fd = sys.stderr
        self.log_pid.wait()
        if self.use_tar:
            tar_opts = "-c --remove-files"
            if self.use_xz:
                tar_opts += " -J"
            tar_cmd = "tar %s -f '%s' -C '%s' '%s'" % (
                tar_opts, self.output, self.tmpdir, self.dirname)
            # do not treat 'tar: file changed as we read it' as fatal error
            if os.system(tar_cmd) > 1:
                self.fatal_error(
                    "failed to write '%s', not removing '%s'..." % (
                        self.output, self.tmpdir))

        sys.stderr.write("Wrote: %s\n\n" % self.output)
        if self.no_clean:
            return

        try:
            shutil.rmtree(self.tmpdir)
        except Exception:
            sys.stderr.write("%s: warning: failed to remove tmp dir: %s\n" \
                    % (self.tool, self.tmpdir))


    def print_with_ts(self, msg, prefix=">>> "):
        self.log_fd.write("%s%s\t%s\n" % (prefix, current_iso_date(), msg))
        self.log_fd.flush()
        # eventually handle terminating signals
        self.handle_ec()

    def update_ec(self, ec):
        if self.ec < ec:
            self.ec = ec

    def error(self, msg, ec=1, err_prefix=""):
        self.print_with_ts("%serror: %s\n" % (err_prefix, msg), prefix="!!! ")
        self.update_ec(ec)
        if not self.dying and not self.keep_going and (self.ec != 0):
            raise FatalError(ec)

    def fatal_error(self, msg, ec=1):
        # avoid recursive handling of errors, handle synchronous shutdown
        self.dying = True
        self.error(msg, err_prefix="fatal ", ec=ec)
        raise FatalError(ec)

    def handle_ec(self):
        if not self.dying and (128 < self.ec < (128 + 64)):
            # caught terminating signal, handle synchronous shutdown
            self.fatal_error("caught signal %d" % (self.ec - 128), self.ec)

    def handle_rv(self, rv):
        if 128 < rv:
            # command terminated by signal, handle synchronous shutdown
            self.update_ec(rv)
            self.handle_ec()

    def exec_cmd(self, cmd, shell=False, echo=True):
        self.handle_ec()
        if echo:
            if shell:
                self.print_with_ts(shell_quote(cmd))
            else:
                self.print_with_ts(strlist_to_shell_cmd(cmd, escape_special=True))
        try:
            self.subproc = subprocess.Popen(
                cmd, stdout=self.log_fd, stderr=self.log_fd, shell=shell)
            rv = self.subproc.wait()
            self.subproc = None
            self.log_fd.write("\n")
        except OSError as e:
            self.log_fd.write("%s\n" % str(e))
            if e.errno == errno.ENOENT:
                # command not found
                return 0x7F
            else:
                # command not executable
                return 0x7E
        self.handle_rv(rv)
        return rv

    def get_cmd_output(self, cmd, shell=True):
        self.handle_ec()
        self.subproc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=self.log_fd, shell=shell)
        (out, _) = self.subproc.communicate()
        rv = self.subproc.returncode
        self.subproc = None
        self.handle_rv(rv)
        out = out.decode("utf8")
        return (rv, out)

    def open_res_file(self, rel_path):
        abs_path = "%s/%s" % (self.resdir, rel_path)
        return open(abs_path, "w")


class IniWriter:
    def __init__(self, results):
        self.results = results
        self.ini = self.results.open_res_file("scan.ini")
        self.write("[scan]\n")
        self.append("tool", self.results.tool)
        self.append("tool-version", self.results.tool_version)
        self.append("tool-args", strlist_to_shell_cmd(sys.argv))
        self.append("host", socket.gethostname())
        self.append("store-results-to", self.results.output)
        self.append("time-created", current_iso_date())

    def close(self):
        if self.ini is None:
            return
        self.append("time-finished", current_iso_date())
        self.append("exit-code", self.results.ec)
        self.ini.close()
        self.ini = None

    def write(self, text):
        self.ini.write(text)
        self.results.log_fd.write("scan.ini: " + text)

    def append(self, key, value):
        val_str = str(value).strip()
        self.write("%s = %s\n" % (key, val_str))


def re_from_checker_set(checker_set):
    """return operand for the --checker option of csgrep based on checker_set"""
    chk_re = "^("
    first = True
    for chk in sorted(checker_set):
        if first:
            first = False
        else:
            chk_re += "|"
        chk_re += chk
    chk_re += ")$"
    return chk_re


def transform_results(js_file, results):
    err_file  = re.sub("\\.js", ".err",  js_file)
    html_file = re.sub("\\.js", ".html", js_file)
    stat_file = re.sub("\\.js", "-summary.txt", js_file)
    results.exec_cmd("csgrep --mode=grep %s '%s' > '%s'" %
                     (CSGREP_FINAL_FILTER_ARGS, js_file,  err_file), shell=True)
    results.exec_cmd("csgrep --mode=json %s '%s' | cshtml - > '%s'" %
                     (CSGREP_FINAL_FILTER_ARGS, js_file, html_file), shell=True)
    results.exec_cmd("csgrep --mode=evtstat %s '%s' | tee '%s'" % \
                     (CSGREP_FINAL_FILTER_ARGS, js_file, stat_file), shell=True)
    return err_file, html_file


def finalize_results(js_file, results, props):
    """transform scan-results.js to scan-results.{err,html} and write stats"""
    if props.imp_checker_set:
        # filter out "important" defects, first based on checkers only
        cmd = "csgrep '%s' --mode=json --checker '%s'" % \
                (js_file, re_from_checker_set(props.imp_checker_set))

        # then apply custom per-checker filters
        for (chk, csgrep_args) in props.imp_csgrep_filters:
            chk_re = re_from_checker_set(props.imp_checker_set - set([chk]))
            cmd += " | csdiff <(csgrep '%s' --mode=json --drop-scan-props --invert-regex --checker '%s' %s) -" \
                    % (js_file, chk_re, csgrep_args)

        # finally take all defects that were tagged important by the scanner already
        cmd += " | csgrep --mode=json --set-imp-level=0"
        cmd += f" <(csgrep --mode=json --imp-level=1 '{js_file}') -"

        # write the result into *-imp.js
        imp_js_file = re.sub("\\.js", "-imp.js", js_file)
        cmd += " > '%s'" % imp_js_file

        # bash is needed to process <(...)
        cmd = strlist_to_shell_cmd(["bash", "-c", cmd], escape_special=True)
        results.exec_cmd(cmd, shell=True)

        # initialize the "imp" flag in the resulting `-all.js` output file
        # and replace the original .js file by `-imp.js`
        all_js_file = re.sub("\\.js", "-all.js", js_file)
        cmd = "cslinker --implist '%s' '%s' > '%s' && mv -v '%s' '%s'" \
                % (imp_js_file, js_file, all_js_file, imp_js_file, js_file)
        if 0 != results.exec_cmd(cmd, shell=True):
            results.error("failed to tag important findings in the full results", ec=0)

        # generate *-all{.err,.html,-summary.txt}
        transform_results(all_js_file, results)

    (err_file, _) = transform_results(js_file, results)

    if props.print_defects:
        os.system("csgrep '%s'" % err_file)


def apply_result_filters(props, results, supp_filters=[]):
    """apply filters, sort the list and record suppressed results"""
    js_file = os.path.join(results.resdir, "scan-results.js")
    all_file = os.path.join(results.dbgdir, "scan-results-all.js")

    # apply filters, sort the list and store the result as scan-results.js
    cmd = f"cat '{all_file}'"
    for filt in props.result_filters:
        cmd += f" | {filt}"
    cmd += f" | cssort --key=path > '{js_file}'"
    results.exec_cmd(cmd, shell=True)

    # record suppressed results
    js_supp = os.path.join(results.dbgdir, "suppressed-results.js")
    cmd = f"cat '{all_file}'"
    for filt in supp_filters:
        cmd += f" | {filt}"
    cmd += f" | csdiff --show-internal '{js_file}' -"
    cmd += f" | cssort > '{js_supp}'"
    results.exec_cmd(cmd, shell=True)
    finalize_results(js_supp, results, props)
    finalize_results(js_file, results, props)

    # create `-imp` symlinks for compatibility (if important defects were filtered)
    if props.imp_checker_set:
        for suffix in [".err", ".html", ".js", "-summary.txt"]:
            src = f"scan-results{suffix}"
            dst = os.path.join(results.resdir, f"scan-results-imp{suffix}")
            results.exec_cmd(["ln", "-s", src, dst])


def handle_known_fp_list(props, results):
    """Update props.result_filters based on props.known_false_positives"""
    if not props.known_false_positives:
        return

    # update scan metadata
    results.ini_writer.append("known-false-positives", props.known_false_positives)

    # install global filter of known false positives
    filter_cmd = f'csdiff --json-output --show-internal "{props.known_false_positives}" -'
    props.result_filters += [filter_cmd]

    if props.pkg is None:
        # no package name available
        return

    kfp_dir = re.sub("\\.js", ".d", props.known_false_positives)
    if not os.path.isdir(kfp_dir):
        # no per-pkg known false positives available
        return

    ep_file = os.path.join(kfp_dir, props.pkg, "exclude-paths.txt")
    if not os.path.exists(ep_file):
        # no list of path regexes to exclude for this pkg
        return

    # install path exclusion filters for this pkg
    with open(ep_file) as file_handle:
        lines = file_handle.readlines()
        for line in lines:
            path_re = line.strip()
            filter_cmd = f'csgrep --mode=json --invert-match --path="{shell_quote(path_re)}"'
            props.result_filters += [filter_cmd]
