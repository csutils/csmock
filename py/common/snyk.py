# standard imports
import json


def snyk_write_analysis_meta(results, results_file):
    try:
        with open(results_file) as snyk_results_file:
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

    except Exception as e:
        results.error(f"snyk-scan: error parsing results from snyk-results.sarif file: {e}")
        return 1
