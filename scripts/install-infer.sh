#!/bin/bash

# $1 -- Infer archive path
# $2 -- infer-out path

create_wrapper()
{
  # $1 -- name of a compiler
  # $2 -- type of a compiler for Infer's --force-integration option
  #       -- 'cc' for C-like languages
  #       -- 'javac' for Java
  # $3 -- infer-out path

  echo '#!/bin/bash

trap unlock_on_exit EXIT INT TERM

compiler="'"$1"'"
compiler_original="${compiler}-original"
all_options=("$@")
infer_dir="'"$3"'"
skip_capture=false
lock_dir="/tmp/infer.lockdir"
pid_file="${lock_dir}/PID"

function lock {
  mkdir "${lock_dir}" > /dev/null 2>&1 && echo $$ > ${pid_file}
}

# unlocks the lock even if this process isnt the owner
function unlock {
  PID=$(cat ${pid_file} 2>&1)
  rm -rf ${lock_dir}
}

# checks if the lock owner still exists -- if not, the lock is removed
function lock_failed {
  PID=$(cat ${pid_file} 2>&1)  # 2>&1 -- do not print anything if cat fails

  # an error while reading PID file, e.g. PID file wasnt created yet
  if [ $? != 0 ]; then
    return
  fi

  # lock owner doesnt exist anymore -- remove the lock
  if ! kill -0 ${PID} &>/dev/null; then
    unlock
  fi
}

# checks if the lock owner is this script -- if so, the lock is removed
function unlock_on_exit {
  PID=$(cat ${pid_file} 2>&1)  # 2>&1 -- do not print anything if cat fails

  # if PID file was loaded correctly
  if [ $? == 0 ]; then
    # if this script still owns the lock then remove it
    if [ $$ == ${PID} ]; then
      unlock
    fi
  fi

  # restore all passed options
  set -- "${all_options[@]}"

  # return code is carried back to a caller
  ${compiler_original} "$@"
  exit $?
}

if [[ $# -eq 1 && "$1" == *"@/tmp/"* ]] ;
then
  skip_capture=true
  set -- "/usr/bin/${compiler_original}"
fi

for var in "$@"
do
    if [[ "$var" =~ conftest[0-9]*\.c$ ]] ;
    then
      skip_capture=true
    fi
done

if [ "${skip_capture}" = false ]
then
  # delete incompatible options of Infers clang
  for arg do
    shift
    [ "$arg" = "-fstack-clash-protection" ] && continue
    [ "$arg" = "-flto=auto" ] && continue
    [ "$arg" = "-flto=jobserver" ] && continue
    [ "$arg" = "-ffat-lto-objects" ] && continue
    [[ "$arg" =~ "-flto-jobs=[0-9]*" ]] && continue
    [ "$arg" = "-flto=thin" ] && continue
    [ "$arg" = "-flto=full" ] && continue
    [ "$arg" = "-fsplit-lto-unit" ] && continue
    [ "$arg" = "-fvirtual-function-elimination" ] && continue
    [ "$arg" = "-flto=full" ] && continue
    [ "$arg" = "-fwhole-program-vtables" ] && continue
    [ "$arg" = "-fno-leading-underscore" ] && continue
    [ "$arg" = "-mno-avx256-split-unaligned-load" ] && continue
    [ "$arg" = "-mno-avx256-split-unaligned-store" ] && continue
    set -- "$@" "$arg"
  done

  # critical section
  while :
  do
    if lock
    then
      # lock acquired
      # logging
      >&2 echo ""
      >&2 echo "NOTE: INFER: ${compiler}-wrapper: running capture phase"
      if infer capture --reactive -o ${infer_dir} --force-integration' "$2" '-- ${compiler} "$@" 1>&2
      then
        >&2 echo "NOTE: INFER: ${compiler}-wrapper: successfully captured: \"${compiler} $@\""
      else
        >&2 echo "WARNING: INFER: ${compiler}-wrapper: unsuccessfully captured: \"${compiler} $@\""
      fi
      >&2 echo ""

      # the script terminates in the unlock function
      unlock
      break
    #else
      # lock_failed
    fi
  done
fi' > "/usr/bin/$1"

  if ! chmod +x "/usr/bin/$1"
  then
    echo "ERROR: INFER: install-infer.sh: Failed to add +x permission to /usr/bin/$1"
    exit 1
  fi
}


# install Infer
if ! cd /opt
then
  echo "ERROR: INFER: install-infer.sh: Failed to open /opt directory"
  exit 1
fi

if ! tar -xf "$1" -C /opt
then
  echo "ERROR: INFER: install-infer.sh: Failed to extract an Infer archive $1"
  exit 1
else
  echo "NOTE: INFER: install-infer.sh: Infer archive extracted successfully"
fi

INFER_DIR=$(ls /opt | grep infer-linux | head -n 1)

if ! rm "$1"
then
  echo "ERROR: INFER: install-infer.sh: Failed to delete an Infer archive $1"
  exit 1
fi

if [ -f /usr/bin/infer ] || ln -sf "/opt/${INFER_DIR}/bin/infer" /usr/bin/infer
then
  echo "NOTE: INFER: install-infer.sh: Infer symlink created successfully"
else
  echo "ERROR: INFER: install-infer.sh: Failed to create a symlink to /opt/${INFER_DIR}/bin/infer"
  exit 1
fi

# test if the symlink works
if ! infer --version > /dev/null 2>&1
then
  echo "ERROR: INFER: install-infer.sh: Failed to run 'infer --version' to test a symlink to /opt/${INFER_DIR}/bin/infer"
  exit 1
else
  echo "NOTE: INFER: install-infer.sh: Infer installed successfully"
fi

# remove possible leftovers from previous run
rm -rf /tmp/infer.lockdir "$2" > /dev/null 2>&1

# create wrappers for compilers, this script is executed after all the dependencies are installed,
# so all the necessary compilers should be already installed
declare -a ccompilers=( "8cc"
                        "9cc"
                        "ack"
                        "c++"
                        "ccomp"
                        "chibicc"
                        "clang"
                        "cproc"
                        "g++"
                        "gcc"
                        "icc"
                        "icpc"
                        "lacc"
                        "lcc"
                        "openCC"
                        "opencc"
                        "pcc"
                        "scc"
                        "sdcc"
                        "tcc"
                        "vc"
                        "x86_64-redhat-linux-c++"
                        "x86_64-redhat-linux-g++"
                        "x86_64-redhat-linux-gcc"
                        "x86_64-redhat-linux-gcc-10")

for c in "${ccompilers[@]}"
do
  if [ -f "/usr/bin/${c}-original" ] || mv "/usr/bin/${c}" "/usr/bin/${c}-original" > /dev/null 2>&1
  then
    create_wrapper "${c}" cc "$2"
    echo "NOTE: INFER: install-infer.sh: /usr/bin/${c} wrapper created successfully"
  fi
done
