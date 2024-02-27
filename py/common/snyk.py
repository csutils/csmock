# Copyright (C) 2024 Red Hat, Inc.
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

import json


def snyk_write_analysis_meta(results, raw_results_file):
    """write snyk stats on metadata file. At the time, we write the total number of files,
    the number of supported files and the coverage ratio."""

    try:
        with open(raw_results_file) as snyk_results_file:
            data = json.load(snyk_results_file)
            coverage_stats = data["runs"][0]["properties"]["coverage"]
            total_files = 0
            supported_files = 0
            for lang in coverage_stats:
                total_files += lang["files"]
                if lang["type"] == "SUPPORTED":
                    supported_files += lang["files"]

            coverage_ratio = 0
            if total_files > 0:
                coverage_ratio = int(supported_files * 100 / total_files)

            results.ini_writer.append("snyk-scanned-files-coverage", coverage_ratio)
            results.ini_writer.append("snyk-scanned-files-success", supported_files)
            results.ini_writer.append("snyk-scanned-files-total", total_files)

            return 0

    except OSError as e:
        results.error(f"snyk-scan: failed to read {raw_results_file}: {e}")
        return 1

    except KeyError as e:
        results.error(f"snyk-scan: error parsing results from snyk-results.sarif file: {e}")
        return 1
