# intentionally no shebang so that rpmbuild does not break this script
# shellcheck shell=sh

# exit successfully if this is a post-UsrMove chroot
test -L /bin && exit 0

# if rpmbuild from the host env translated /bin/bash to /usr/bin/bash in the
# shebangs of our scripts, create reverse symlinks to make the scripts work
# in the chroot env again
for sh in bash sh; do
    dst=/usr/bin/${sh}
    test -e ${dst} && continue
    test -x /bin/${sh} && ln -sv ../../bin/${sh} $dst
done
