# turn on verbose mode
set -v

# prevent our build host from being shot down by a build of a broken package
ulimit -u 256 -v 10485760
ulimit -a
