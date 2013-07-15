# turn on verbose mode
set -v

# initialize environment variables
export CC=gcc
export CXX=g++

# prevent our build host from being shot down by a build of a broken package
ulimit -u 1024 -v 10485760
ulimit -a
