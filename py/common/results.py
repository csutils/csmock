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
import os
import re
import shutil
import signal
import socket
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
    def __init__(self, output, keep_going=False, create_dbgdir=True):
        self.output = output
        self.keep_going = keep_going
        self.create_dbgdir = create_dbgdir
        self.use_xz = False
        self.use_tar = False
        self.dirname = os.path.basename(output)
        self.codec = codecs.lookup('utf8')
        self.ec = 0

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
        self.tmpdir = tempfile.mkdtemp(prefix="csmock")
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

        tee = ["tee", "%s/scan.log" % self.resdir]
        self.log_pid = subprocess.Popen(
            tee, stdin=subprocess.PIPE, preexec_fn=os.setsid)
        self.log_fd = self.utf8_wrap(self.log_pid.stdin)

        def signal_handler(signum, frame):
            # FIXME: we should use Async-signal-safe functions only
            self.fatal_error("caught signal %d" % signum, ec=(0x80 + signum))
        for i in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(i, signal_handler)

        self.ini_writer = IniWriter(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.ini_writer.close()
        if self.subproc is not None and self.subproc.returncode is None:
            # FIXME: TOCTOU race
            try:
                os.kill(self.subproc.pid, signal.SIGTERM)
                self.subproc.wait()
            except Exception:
                pass
        self.print_with_ts("csmock exit code: %d\n" % self.ec, prefix="<<< ")
        self.log_fd.close()
        self.log_fd = sys.stderr
        self.log_pid.wait()
        if self.use_tar:
            tar_opts = "-c"
            if self.use_xz:
                tar_opts += "J"
            tar_cmd = "tar %s -f '%s' -C '%s' '%s'" % (
                tar_opts, self.output, self.tmpdir, self.dirname)
            # do not treat 'tar: file changed as we read it' as fatal error
            if os.system(tar_cmd) > 1:
                self.fatal_error(
                    "failed to write '%s', not removing '%s'..." % (
                        self.output, self.tmpdir))

        sys.stderr.write("Wrote: %s\n\n" % self.output)
        shutil.rmtree(self.tmpdir)

    def print_with_ts(self, msg, prefix=">>> "):
        self.log_fd.write("%s%s\t%s\n" % (prefix, current_iso_date(), msg))
        self.log_fd.flush()

    def error(self, msg, ec=1, err_prefix=""):
        self.print_with_ts("%serror: %s\n" % (err_prefix, msg), prefix="!!! ")
        if self.ec < ec:
            self.ec = ec
        if not self.keep_going and (self.ec != 0):
            raise FatalError(ec)

    def fatal_error(self, msg, ec=1):
        self.error(msg, err_prefix="fatal ", ec=ec)
        raise FatalError(ec)

    def exec_cmd(self, cmd, shell=False, echo=True):
        if echo:
            if shell:
                self.print_with_ts(shell_quote(cmd))
            else:
                self.print_with_ts(strlist_to_shell_cmd(cmd, escape_special=True))
        self.subproc = subprocess.Popen(
            cmd, stdout=self.log_fd, stderr=self.log_fd, shell=shell)
        rv = self.subproc.wait()
        self.log_fd.write("\n")
        if rv >= 128:
            # if the child has been signalled, signal self with the same signal
            os.kill(os.getpid(), rv - 128)
        return rv

    def get_cmd_output(self, cmd, shell=True):
        self.subproc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=self.log_fd, shell=shell)
        (out, _) = self.subproc.communicate()
        out = out.decode("utf8")
        return self.subproc.returncode, out

    def open_res_file(self, rel_path):
        abs_path = "%s/%s" % (self.resdir, rel_path)
        return open(abs_path, "w")


class IniWriter:
    def __init__(self, results):
        self.results = results
        self.ini = self.results.open_res_file("scan.ini")
        self.write("[scan]\n")
        self.append("tool", "csmock")
        self.append("tool-version", "@VERSION@")
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
        self.write("%s = %s\n" % (key, value))


def transform_results(js_file, results):
    err_file  = re.sub("\\.js", ".err",  js_file)
    html_file = re.sub("\\.js", ".html", js_file)
    stat_file = re.sub("\\.js", "-summary.txt", js_file)
    results.exec_cmd("csgrep --mode=grep %s '%s' > '%s'" %
                     (CSGREP_FINAL_FILTER_ARGS, js_file,  err_file), shell=True)
    results.exec_cmd("csgrep --mode=json %s '%s' | cshtml - > '%s'" %
                     (CSGREP_FINAL_FILTER_ARGS, js_file, html_file), shell=True)
    results.exec_cmd("csgrep --mode=stat %s '%s' | tee '%s'" % \
                     (CSGREP_FINAL_FILTER_ARGS, err_file, stat_file), shell=True)
    return err_file, html_file
