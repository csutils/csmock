#!/usr/bin/env python

import json
import sys
import re


def uninitFilter(bug):
    if bug["bug_type"] == "UNINITIALIZED_VALUE":
        if re.match("The value read from .*\[_\] was never initialized.", bug["qualifier"]):
            return True


def biabductionFilter(bug):
    if bug["bug_type"] == "NULL_DEREFERENCE" or bug["bug_type"] == "RESOURCE_LEAK":
        for bugTrace in bug["bug_trace"]:
            if re.match("Skipping .*\(\):", bugTrace["description"]):
                return True
            if re.match("Switch condition is false. Skipping switch case", bugTrace["description"]):
                return True


def inferboFilter(bug):
    if bug["bug_type"] == "BUFFER_OVERRUN_U5" or bug["bug_type"] == "INTEGER_OVERFLOW_U5":
        return True

    bufferOverRunTypes = [
        "BUFFER_OVERRUN_L2",
        "BUFFER_OVERRUN_L3",
        "BUFFER_OVERRUN_L4",
        "BUFFER_OVERRUN_L5",
        "BUFFER_OVERRUN_S2",
        "INFERBO_ALLOC_MAY_BE_NEGATIVE",
        "INFERBO_ALLOC_MAY_BE_BIG"]

    integerOverFlowTypes = [
        "INTEGER_OVERFLOW_L2",
        "INTEGER_OVERFLOW_L5",
        "INTEGER_OVERFLOW_U5"]

    if bug["bug_type"] in bufferOverRunTypes or bug["bug_type"] in integerOverFlowTypes:
        if ("+oo" in bug["qualifier"]) or ("-oo" in bug["qualifier"]):
            return True


def lowerSeverityForDEADSTORE(bug):
    if bug["bug_type"] == "DEAD_STORE":
        bug["severity"] = "WARNING"


def applyFilters(bugList, filterList):
    modifiedBugList = []

    while bugList:
        bug = bugList.pop(0)
        bugIsFalseAlarm = False
        for filter in filterList:
            try:
                # if a filter returns true, then this bug is considered a
                # false alarm and will not be included in the final report
                # NOTE: a bug marked as a false alarm may not actually be
                #       a false alarm
                if filter(bug):
                    bugIsFalseAlarm = True
                    break
            except:
                # if a filter fails on a bug, then the filter behaves as if
                # the bug was real
                bugIsFalseAlarm = False
        if not bugIsFalseAlarm:
            modifiedBugList.append(bug)

    return modifiedBugList


def main():
    bugList = json.load(sys.stdin)

    if "--only-transform" not in sys.argv:
        filterList = []

        if "--no-biadbuction" not in sys.argv:
            filterList += [biabductionFilter]

        if "--no-inferbo" not in sys.argv:
            filterList += [inferboFilter]

        if "--no-uninit" not in sys.argv:
            filterList += [uninitFilter]

        if "--no-dead-store" not in sys.argv:
            filterList += [lowerSeverityForDEADSTORE]

        bugList = applyFilters(bugList, filterList)


    firstBug = True

    for bug in bugList:
        if not firstBug:
            print()
        print("Error: INFER_WARNING:")
        for bugTrace in bug["bug_trace"]:
            print("%s:%s:%s: note: %s" % (bugTrace["filename"], bugTrace["line_number"], bugTrace["column_number"], bugTrace["description"]))
        print("%s:%s:%s: %s[%s]: %s" % (bug["file"], bug["line"], bug["column"], bug["severity"].lower(), bug["bug_type"], bug["qualifier"]))
        firstBug=False

if __name__ == "__main__":
    main()
