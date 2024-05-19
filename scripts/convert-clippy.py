#!/usr/bin/env python3

import json
import sys
import re

MESSAGE_PATTERN     = r"^(.*?): (.*?)\s+-->\s+(.*?):(\d+):(\d+)(.*)"
# we extract package path from the package_id
# eg -- "package_id":"stratisd 3.6.5 (path+file:///builddir/build/BUILD/stratisd-3.6.5)
PACKAGE_ID_PATTERN  = r"path\+file://(.*)\)"
# eg -- "package_id":"path+file:///builddir/build/BUILD/stratisd-3.6.5#stratisd@3.6.5"
PACKAGE_ID_PATTERN2 = r"^path\+file:\/\/([^#]+)(?:#([^@]*))?(?:@(.+))?$"
PACKAGE_ID_PATTERNS = [PACKAGE_ID_PATTERN, PACKAGE_ID_PATTERN2]

def main():
    for line in sys.stdin:
        try:
            item = json.loads(line)
        except Exception as e:
            print("rust-clippy: Error while converting results:", e, file=sys.stderr)
            sys.exit(1)

        if item["reason"] != "compiler-message":
            continue

        for pattern in PACKAGE_ID_PATTERNS:
            match = re.search(pattern, item["package_id"])
            if match:
                break
        if not match:
            continue

        package_path = match.group(1)
        package = package_path[len("/builddir/build/BUILD/"):]
        package = package.split("/")[0]
        # we just need the builddir and package name, the relative file path is in the message
        package_path = "/builddir/build/BUILD/" + package

        match = re.search(MESSAGE_PATTERN, item["message"]["rendered"].strip(), re.DOTALL)
        if not match:
            continue

        message_type, message_content, file_path, line_number, column, rest = match.groups()

        print("Error: CLIPPY_WARNING:")
        print(f"{package_path}/{file_path}:{line_number}:{column}: {message_type}: {message_content}")
        for x, line in enumerate(rest.split("\n")):
            if x == 0 and line.strip() == "":
                continue
            print(f"#  {line}")

        print()


if __name__ == "__main__":
    main()
