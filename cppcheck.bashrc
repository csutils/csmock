# turn on verbose mode
set -v

# prevent our build host from being shot down by a cppcheck looping forever
ulimit -u 256 -v 10485760 -t 16384
ulimit -a
