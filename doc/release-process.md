# Upstream Release Process

## Prerequisites

* GPG key configured for signing tags and tarballs
* GitHub personal access token with `repo` scope

## Create a Signed Tag

Tag the release commit on `main` with a signed annotated tag:

```bash
git tag -s csmock-X.Y.Z
```

The tag message should contain the version on the first line, followed
by a blank line and a bullet-list changelog.  For example:

```
csmock-3.8.5

- make `--embed-context` use `csgrep-static` in the chroot (#216)
```

Push the tag:

```bash
git push origin csmock-X.Y.Z
```

## Upload Release Artifacts

Run the `upload-release.sh` script from the repository root:

```bash
./upload-release.sh csmock-X.Y.Z "$GITHUB_TOKEN"
```

The script performs the following steps:

1. Creates a source tarball using `git archive`
2. Compresses it into `.tar.gz` and `.tar.xz`
3. Signs both tarballs with GPG (producing `.asc` detached signatures)
4. Creates a GitHub release via the API
5. Uploads the tarballs and signatures as release assets

Upstream releases are published at:
<https://github.com/csutils/csmock/releases>

## Finalize on GitHub

Open the newly created release in the GitHub web UI and review/edit
the release description as needed.

## Downstream Packaging

Packit (configured in `.packit.yaml`) automatically picks up new tags
and triggers COPR builds for Fedora and EPEL.
