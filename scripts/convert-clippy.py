#!/usr/bin/env python3

import json
import sys
import re


def main():
    pattern = r"^(.*?): (.*?)\s+-->\s+(.*?):(\d+):\d+(.*)"
    pattern = re.compile(pattern, re.DOTALL)

    for line in sys.stdin:
        item = json.loads(line)

        if item["reason"] != "compiler-message":
            continue

        match = re.search(r"path\+file://(.*)\)", item["package_id"])
        if not match:
            continue
        package_path = match.group(1)
        package = package_path[len("/builddir/build/BUILD/") :]
        package = package.split("/")[0]

        match = pattern.search(item["message"]["rendered"].strip())
        if not match:
            continue

        message_type, message_content, file_path, line_number, rest = match.groups()

        print("Error: RUST_CLIPPY_WARNING:")
        print(f"{package}/{file_path}:{line_number}: {message_type}: {message_content}")
        for x, line in enumerate(rest.split("\n")):
            if x == 0 and line.strip() == "":
                continue
            print(f"#  {line}")

        print()


if __name__ == "__main__":
    main()
