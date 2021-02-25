#!/bin/sh

for bin in make ninja; do
    # check whether ${bin} is installed
    bin_fp=/usr/bin/${bin}
    test -x ${bin_fp}                   || continue

    # move original ${bin} if not already moved
    bin_fp_orig=${bin_fp}.orig
    mv -nv ${bin_fp} ${bin_fp_orig}     || continue

    # create a wrapper script named ${bin}
    case ${bin} in
        make)
            opt="-k"
            ;;
        ninja)
            opt="-k0"
            ;;
    esac
    printf "#!/bin/sh\nexec ${bin_fp_orig} ${opt} \"\$@\"\n" \
        > ${bin_fp}                     || continue
    chmod 0755 ${bin_fp}                || continue

    # print verbose output on success
    (set -x && ls -l ${bin_fp} && cat ${bin_fp})
done
