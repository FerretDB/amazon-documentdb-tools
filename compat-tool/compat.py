#!/usr/bin/python3
import glob
import pathlib
import os
import sys
import re
import argparse

processingFeedbackLines = 10000
issuesDict = {}
detailedIssuesDict = {}
supportedDict = {}
skippedFileList = []
exceptionFileList = []
numProcessedFiles = 0


def double_check(checkOperator, checkLine, checkLineLength):
    foundOperator = False

    for match in re.finditer(re.escape(checkOperator), checkLine):
        if (match.end() == checkLineLength) or (not checkLine[match.end()].isalpha()):
            foundOperator = True
            break

    return foundOperator


def scan_code(args, keywords):
    global numProcessedFiles, issuesDict, detailedIssuesDict, supportedDict, skippedFileList, exceptionFileList

    ver = "6.0"

    usage_map = {}
    cmd_map = {}
    line_ct = 0
    totalLines = 0

    # create the file or list of files
    fileArray = []

    includedExtensions = []
    if args.includedExtensions != "ALL":
        includedExtensions = args.includedExtensions.lower().split(",")
    excludedExtensions = []
    if args.includedExtensions != "NONE":
        excludedExtensions = args.excludedExtensions.lower().split(",")

    if args.scanFile is not None:
        fileArray.append(args.scanFile)
        numProcessedFiles += 1
    else:
        for filename in glob.iglob("{}/**".format(args.scanDir), recursive=True):
            if os.path.isfile(filename):
                if ((pathlib.Path(filename).suffix[1:].lower() not in excludedExtensions) and
                     ((args.includedExtensions == "ALL") or
                      (pathlib.Path(filename).suffix[1:].lower() in includedExtensions))):
                    fileArray.append(filename)
                    numProcessedFiles += 1
                else:
                    skippedFileList.append(filename)

    for thisFile in fileArray:
        print("processing file {}".format(thisFile))
        with open(thisFile, "r") as code_file:
            # line by line technique
            try:
                fileLines = code_file.readlines()
            except:
                print("  exception reading file, skipping")
                exceptionFileList.append(thisFile)
                continue

            fileLineNum = 1

            for lineNum, thisLine in enumerate(fileLines):
                thisLineLength = len(thisLine)

                for checkCompat in keywords:
                    if (keywords[checkCompat][ver] == 'No'):
                        # only check for unsupported operators
                        if (thisLine.find(checkCompat) >= 0):
                            # check for false positives - for each position found see if next character is not a..z|A..Z or if at EOL
                            if double_check(checkCompat, thisLine, thisLineLength):
                                # add it to the counters
                                if checkCompat in issuesDict:
                                    issuesDict[checkCompat] += 1
                                else:
                                    issuesDict[checkCompat] = 1
                                # add it to the filenames/line-numbers
                                if checkCompat in detailedIssuesDict:
                                    if thisFile in detailedIssuesDict[checkCompat]:
                                        detailedIssuesDict[checkCompat][thisFile].append(fileLineNum)
                                    else:
                                        detailedIssuesDict[checkCompat][thisFile] = [fileLineNum]
                                else:
                                    detailedIssuesDict[checkCompat] = {}
                                    detailedIssuesDict[checkCompat][thisFile] = [fileLineNum]

                    elif (keywords[checkCompat][ver] == 'No') and args.showSupported:
                        # check for supported operators
                        if (thisLine.find(checkCompat) >= 0):
                            # check for false positives - for each position found see if next character is not a..z|A..Z or if at EOL
                            if double_check(checkCompat, thisLine, thisLineLength):
                                if checkCompat in supportedDict:
                                    supportedDict[checkCompat] += 1
                                else:
                                    supportedDict[checkCompat] = 1

                if (fileLineNum % processingFeedbackLines) == 0:
                    print("  processing line {}".format(fileLineNum))
                fileLineNum += 1


def main(args):
    parser = argparse.ArgumentParser(description="Parse the command line.")
    parser.add_argument("--directory", dest="scanDir", action="store", help="Directory containing files to scan for compatibility", required=False)
    parser.add_argument("--file", dest="scanFile", action="store", help="Specific file to scan for compatibility", required=False)
    parser.add_argument("--excluded-extensions", dest="excludedExtensions", action="store", default="NONE", help="Filename extensions to exclude from scanning, comma separated", required=False)
    parser.add_argument("--included-extensions", dest="includedExtensions", action="store", default="ALL", help="Filename extensions to include in scanning, comma separated", required=False)
    parser.add_argument("--show-supported", dest="showSupported", action="store_true", default=False, help="Include supported operators in the report", required=False)
    args = parser.parse_args()

    if args.scanDir is None and args.scanFile is None:
        parser.error("at least one of --directory and --file required")

    elif args.scanDir is not None and args.scanFile is not None:
        parser.error("must provide exactly one of --directory or --file required, not both")

    elif args.scanFile is not None and not os.path.isfile(args.scanFile):
        parser.error("unable to locate file {}".format(args.scanFile))

    elif args.scanDir is not None and not os.path.isdir(args.scanDir):
        parser.error("unable to locate directory {}".format(args.scanDir))

    keywords = load_keywords()
    scan_code(args, keywords)

    print("")
    print("Processed {} files, skipped {} files".format(numProcessedFiles,len(skippedFileList)+len(exceptionFileList)))

    if len(issuesDict) > 0:
        print("")
        print("The following {} unsupported operators were found:".format(len(issuesDict)))
        for thisKeyPair in sorted(issuesDict.items(), key=lambda x: (-x[1],x[0])):
            print("  {} | found {} time(s)".format(thisKeyPair[0],thisKeyPair[1]))

        # output detailed unsupported operator findings
        print("")
        print("Unsupported operators by filename and line number:")
        for thisKeyPair in sorted(issuesDict.items(), key=lambda x: (-x[1],x[0])):
            print("  {} | lines = found {} time(s)".format(thisKeyPair[0],thisKeyPair[1]))
            for thisFile in detailedIssuesDict[thisKeyPair[0]]:
                print("    {} | lines = {}".format(thisFile,detailedIssuesDict[thisKeyPair[0]][thisFile]))

    else:
        print("")
        print("No unsupported operators found.")

    if len(supportedDict) > 0 and args.showSupported:
        print("")
        print("The following {} supported operators were found:".format(len(supportedDict)))
        for thisKeyPair in sorted(supportedDict.items(), key=lambda x: (-x[1],x[0])):
            print("  - {} | found {} time(s)".format(thisKeyPair[0],thisKeyPair[1]))

    if len(skippedFileList) > 0:
        print("")
        print("List of skipped files - excluded extensions")
        for skippedFile in skippedFileList:
            print("  {}".format(skippedFile))

    if len(exceptionFileList) > 0:
        print("")
        print("List of skipped files - unsupported file type/content")
        for exceptionFile in exceptionFileList:
            print("  {}".format(exceptionFile))

    print("")

    if len(issuesDict) > 0:
        sys.exit(1)
    else:
        sys.exit(0)


def load_keywords():
    # to avoid false positives and or negatives we set all keywords to "No".
    # only set to "Yes" if we support them in all commands and CRUD operations.
    thisKeywords = {
        "$$CURRENT":{"mongodbversion":"4.0","6.0":"No"},
        "$$DESCEND":{"mongodbversion":"4.0","6.0":"No"},
        "$$KEEP":{"mongodbversion":"4.0","6.0":"No"},
        "$$PRUNE":{"mongodbversion":"4.0","6.0":"No"},
        "$$REMOVE":{"mongodbversion":"4.0","6.0":"No"},
        "$$ROOT":{"mongodbversion":"4.0","6.0":"No"},
        "$abs":{"mongodbversion":"4.0","6.0":"No"},
        "$accumulator":{"mongodbversion":"4.4","6.0":"No"},
        "$acos":{"mongodbversion":"4.2","6.0":"No"},
        "$acosh":{"mongodbversion":"4.2","6.0":"No"},
        "$add":{"mongodbversion":"4.0","6.0":"No"},
        "$addFields":{"mongodbversion":"4.0","6.0":"No"},
        "$addToSet":{"mongodbversion":"4.0","6.0":"No"},
        "$all":{"mongodbversion":"4.0","6.0":"No"},
        "$allElementsTrue":{"mongodbversion":"4.0","6.0":"No"},
        "$and":{"mongodbversion":"4.0","6.0":"No"},
        "$anyElementTrue":{"mongodbversion":"4.0","6.0":"No"},
        "$arrayElemAt":{"mongodbversion":"4.0","6.0":"No"},
        "$arrayToObject":{"mongodbversion":"4.0","6.0":"No"},
        "$asin":{"mongodbversion":"4.2","6.0":"No"},
        "$asinh":{"mongodbversion":"4.2","6.0":"No"},
        "$atan":{"mongodbversion":"4.2","6.0":"No"},
        "$atan2":{"mongodbversion":"4.2","6.0":"No"},
        "$atanh":{"mongodbversion":"4.2","6.0":"No"},
        "$avg":{"mongodbversion":"4.0","6.0":"No"},
        "$binarySize":{"mongodbversion":"4.4","6.0":"No"},
        "$bit":{"mongodbversion":"4.0","6.0":"No"},
        "$bitsAllClear":{"mongodbversion":"4.0","6.0":"No"},
        "$bitsAllSet":{"mongodbversion":"4.0","6.0":"No"},
        "$bitsAnyClear":{"mongodbversion":"4.0","6.0":"No"},
        "$bitsAnySet":{"mongodbversion":"4.0","6.0":"No"},
        "$bottom":{"mongodbversion":"5.2","6.0":"No"},
        "$bottomN":{"mongodbversion":"5.2","6.0":"No"},
        "$box":{"mongodbversion":"4.0","6.0":"No"},
        "$bsonSize":{"mongodbversion":"4.4","6.0":"No"},
        "$bucket":{"mongodbversion":"4.0","6.0":"No"},
        "$bucketAuto":{"mongodbversion":"4.0","6.0":"No"},
        "$ceil":{"mongodbversion":"4.0","6.0":"No"},
        "$center":{"mongodbversion":"4.0","6.0":"No"},
        "$centerSphere":{"mongodbversion":"4.0","6.0":"No"},
        "$cmp":{"mongodbversion":"4.0","6.0":"No"},
        "$collStats":{"mongodbversion":"4.0","6.0":"No"},
        "$comment":{"mongodbversion":"4.0","6.0":"No"},
        "$concat":{"mongodbversion":"4.0","6.0":"No"},
        "$concatArrays":{"mongodbversion":"4.0","6.0":"No"},
        "$cond":{"mongodbversion":"4.0","6.0":"No"},
        "$convert":{"mongodbversion":"4.0","6.0":"No"},
        "$cos":{"mongodbversion":"4.2","6.0":"No"},
        "$cosh":{"mongodbversion":"4.2","6.0":"No"},
        "$count":{"mongodbversion":"4.0","6.0":"No"},
        "$currentDate":{"mongodbversion":"4.0","6.0":"No"},
        "$currentOp":{"mongodbversion":"4.0","6.0":"No"},
        "$dateAdd":{"mongodbversion":"6.0","6.0":"No"},
        "$dateDiff":{"mongodbversion":"6.0","6.0":"No"},
        "$dateFromParts":{"mongodbversion":"4.0","6.0":"No"},
        "$dateFromString":{"mongodbversion":"4.0","6.0":"No"},
        "$dateSubtract":{"mongodbversion":"6.0","6.0":"No"},
        "$dateToParts":{"mongodbversion":"4.0","6.0":"No"},
        "$dateToString":{"mongodbversion":"4.0","6.0":"No"},
        "$dateTrunc":{"mongodbversion":"6.0","6.0":"No"},
        "$dayOfMonth":{"mongodbversion":"4.0","6.0":"No"},
        "$dayOfWeek":{"mongodbversion":"4.0","6.0":"No"},
        "$dayOfYear":{"mongodbversion":"4.0","6.0":"No"},
        "$degreesToRadians":{"mongodbversion":"4.2","6.0":"No"},
        "$densify":{"mongodbversion":"5.1","6.0":"No"},
        "$divide":{"mongodbversion":"4.0","6.0":"No"},
        "$documents":{"mongodbversion":"5.1","6.0":"No"},
        "$each":{"mongodbversion":"4.0","6.0":"No"},
        "$elemMatch":{"mongodbversion":"4.0","6.0":"No"},
        "$eq":{"mongodbversion":"4.0","6.0":"No"},
        "$exists":{"mongodbversion":"4.0","6.0":"No"},
        "$exp":{"mongodbversion":"4.0","6.0":"No"},
        "$expr":{"mongodbversion":"4.0","6.0":"No"},
        "$facet":{"mongodbversion":"4.0","6.0":"No"},
        "$fill":{"mongodbversion":"5.3","6.0":"No"},
        "$filter":{"mongodbversion":"4.0","6.0":"No"},
        "$first":{"mongodbversion":"4.0","6.0":"No"},
        "$firstN":{"mongodbversion":"5.2","6.0":"No"},
        "$floor":{"mongodbversion":"4.0","6.0":"No"},
        "$function":{"mongodbversion":"4.4","6.0":"No"},
        "$geoIntersects":{"mongodbversion":"4.0","6.0":"No"},
        "$geometry":{"mongodbversion":"4.0","6.0":"No"},
        "$geoNear":{"mongodbversion":"4.0","6.0":"No"},
        "$geoWithin":{"mongodbversion":"4.0","6.0":"No"},
        "$getField":{"mongodbversion":"6.0","6.0":"No"},
        "$graphLookup":{"mongodbversion":"4.0","6.0":"No"},
        "$group":{"mongodbversion":"4.0","6.0":"No"},
        "$gt":{"mongodbversion":"4.0","6.0":"No"},
        "$gte":{"mongodbversion":"4.0","6.0":"No"},
        "$hour":{"mongodbversion":"4.0","6.0":"No"},
        "$ifNull":{"mongodbversion":"4.0","6.0":"No"},
        "$in":{"mongodbversion":"4.0","6.0":"No"},
        "$inc":{"mongodbversion":"4.0","6.0":"No"},
        "$indexOfArray":{"mongodbversion":"4.0","6.0":"No"},
        "$indexOfBytes":{"mongodbversion":"4.0","6.0":"No"},
        "$indexOfCP":{"mongodbversion":"4.0","6.0":"No"},
        "$indexStats":{"mongodbversion":"4.0","6.0":"No"},
        "$isArray":{"mongodbversion":"4.0","6.0":"No"},
        "$isNumber":{"mongodbversion":"4.4","6.0":"No"},
        "$isoDayOfWeek":{"mongodbversion":"4.0","6.0":"No"},
        "$isoWeek":{"mongodbversion":"4.0","6.0":"No"},
        "$isoWeekYear":{"mongodbversion":"4.0","6.0":"No"},
        "$jsonSchema":{"mongodbversion":"4.0","6.0":"No"},
        "$last":{"mongodbversion":"4.0","6.0":"No"},
        "$lastN":{"mongodbversion":"5.2","6.0":"No"},
        "$let":{"mongodbversion":"4.0","6.0":"No"},
        "$limit":{"mongodbversion":"4.0","6.0":"No"},
        "$linearFill":{"mongodbversion":"5.3","6.0":"No"},
        "$listLocalSessions":{"mongodbversion":"4.0","6.0":"No"},
        "$listSessions":{"mongodbversion":"4.0","6.0":"No"},
        "$literal":{"mongodbversion":"4.0","6.0":"No"},
        "$ln":{"mongodbversion":"4.0","6.0":"No"},
        "$locf":{"mongodbversion":"5.2","6.0":"No"},
        "$log":{"mongodbversion":"4.0","6.0":"No"},
        "$log10":{"mongodbversion":"4.0","6.0":"No"},
        "$lookup":{"mongodbversion":"4.0","6.0":"No"},
        "$lt":{"mongodbversion":"4.0","6.0":"No"},
        "$lte":{"mongodbversion":"4.0","6.0":"No"},
        "$ltrim":{"mongodbversion":"4.0","6.0":"No"},
        "$map":{"mongodbversion":"4.0","6.0":"No"},
        "$match":{"mongodbversion":"4.0","6.0":"No"},
        "$max":{"mongodbversion":"4.0","6.0":"No"},
        "$maxDistance":{"mongodbversion":"4.0","6.0":"No"},
        "$maxN":{"mongodbversion":"5.2","6.0":"No"},
        "$merge":{"mongodbversion":"4.0","6.0":"No"},
        "$mergeObjects":{"mongodbversion":"4.0","6.0":"No"},
        "$meta":{"mongodbversion":"4.0","6.0":"No"},
        "$millisecond":{"mongodbversion":"4.0","6.0":"No"},
        "$min":{"mongodbversion":"4.0","6.0":"No"},
        "$minDistance":{"mongodbversion":"4.0","6.0":"No"},
        "$minN":{"mongodbversion":"5.2","6.0":"No"},
        "$minute":{"mongodbversion":"4.0","6.0":"No"},
        "$mod":{"mongodbversion":"4.0","6.0":"No"},
        "$month":{"mongodbversion":"4.0","6.0":"No"},
        "$mul":{"mongodbversion":"4.0","6.0":"No"},
        "$multiply":{"mongodbversion":"4.0","6.0":"No"},
        "$natural":{"mongodbversion":"4.0","6.0":"No"},
        "$ne":{"mongodbversion":"4.0","6.0":"No"},
        "$near":{"mongodbversion":"4.0","6.0":"No"},
        "$nearSphere":{"mongodbversion":"4.0","6.0":"No"},
        "$nin":{"mongodbversion":"4.0","6.0":"No"},
        "$nor":{"mongodbversion":"4.0","6.0":"No"},
        "$not":{"mongodbversion":"4.0","6.0":"No"},
        "$objectToArray":{"mongodbversion":"4.0","6.0":"No"},
        "$or":{"mongodbversion":"4.0","6.0":"No"},
        "$out":{"mongodbversion":"4.0","6.0":"No"},
        "$planCacheStats":{"mongodbversion":"4.2","6.0":"No"},
        "$polygon":{"mongodbversion":"4.0","6.0":"No"},
        "$pop":{"mongodbversion":"4.0","6.0":"No"},
        "$position":{"mongodbversion":"4.0","6.0":"No"},
        "$pow":{"mongodbversion":"4.0","6.0":"No"},
        "$project":{"mongodbversion":"4.0","6.0":"No"},
        "$pull":{"mongodbversion":"4.0","6.0":"No"},
        "$pullAll":{"mongodbversion":"4.0","6.0":"No"},
        "$push":{"mongodbversion":"4.0","6.0":"No"},
        "$radiansToDegrees":{"mongodbversion":"4.2","6.0":"No"},
        "$rand":{"mongodbversion":"6.0","6.0":"No"},
        "$range":{"mongodbversion":"4.0","6.0":"No"},
        "$redact":{"mongodbversion":"4.0","6.0":"No"},
        "$reduce":{"mongodbversion":"4.0","6.0":"No"},
        "$regex":{"mongodbversion":"4.0","6.0":"No"},
        "$regexFind":{"mongodbversion":"4.2","6.0":"No"},
        "$regexFindAll":{"mongodbversion":"4.2","6.0":"No"},
        "$regexMatch":{"mongodbversion":"4.2","6.0":"No"},
        "$rename":{"mongodbversion":"4.0","6.0":"No"},
        "$replaceAll":{"mongodbversion":"4.4","6.0":"No"},
        "$replaceOne":{"mongodbversion":"4.4","6.0":"No"},
        "$replaceRoot":{"mongodbversion":"4.0","6.0":"No"},
        "$replaceWith":{"mongodbversion":"4.2","6.0":"No"},
        "$reverseArray":{"mongodbversion":"4.0","6.0":"No"},
        "$round":{"mongodbversion":"4.2","6.0":"No"},
        "$rtrim":{"mongodbversion":"4.0","6.0":"No"},
        "$sample":{"mongodbversion":"4.0","6.0":"No"},
        "$sampleRate":{"mongodbversion":"6.0","6.0":"No"},
        "$second":{"mongodbversion":"4.0","6.0":"No"},
        "$set":{"mongodbversion":"4.0","6.0":"No"},
        "$setDifference":{"mongodbversion":"4.0","6.0":"No"},
        "$setEquals":{"mongodbversion":"4.0","6.0":"No"},
        "$setField":{"mongodbversion":"6.0","6.0":"No"},
        "$setIntersection":{"mongodbversion":"4.0","6.0":"No"},
        "$setIsSubset":{"mongodbversion":"4.0","6.0":"No"},
        "$setOnInsert":{"mongodbversion":"4.0","6.0":"No"},
        "$setUnion":{"mongodbversion":"4.0","6.0":"No"},
        "$setWindowFields":{"mongodbversion":"6.0","6.0":"No"},
        "$sin":{"mongodbversion":"4.2","6.0":"No"},
        "$sinh":{"mongodbversion":"4.2","6.0":"No"},
        "$size":{"mongodbversion":"4.0","6.0":"No"},
        "$skip":{"mongodbversion":"4.0","6.0":"No"},
        "$slice":{"mongodbversion":"4.0","6.0":"No"},
        "$sort":{"mongodbversion":"4.0","6.0":"No"},
        "$sortArray":{"mongodbversion":"5.2","6.0":"No"},
        "$sortByCount":{"mongodbversion":"4.0","6.0":"No"},
        "$split":{"mongodbversion":"4.0","6.0":"No"},
        "$sqrt":{"mongodbversion":"4.0","6.0":"No"},
        "$stdDevPop":{"mongodbversion":"4.0","6.0":"No"},
        "$stdDevSamp":{"mongodbversion":"4.0","6.0":"No"},
        "$strcasecmp":{"mongodbversion":"4.0","6.0":"No"},
        "$strLenBytes":{"mongodbversion":"4.0","6.0":"No"},
        "$strLenCP":{"mongodbversion":"4.0","6.0":"No"},
        "$substr":{"mongodbversion":"4.0","6.0":"No"},
        "$substrBytes":{"mongodbversion":"4.0","6.0":"No"},
        "$substrCP":{"mongodbversion":"4.0","6.0":"No"},
        "$subtract":{"mongodbversion":"4.0","6.0":"No"},
        "$sum":{"mongodbversion":"4.0","6.0":"No"},
        "$switch":{"mongodbversion":"4.0","6.0":"No"},
        "$tan":{"mongodbversion":"4.2","6.0":"No"},
        "$tanh":{"mongodbversion":"4.2","6.0":"No"},
        "$text":{"mongodbversion":"4.0","6.0":"No"},
        "$toBool":{"mongodbversion":"4.0","6.0":"No"},
        "$toDate":{"mongodbversion":"4.0","6.0":"No"},
        "$toDecimal":{"mongodbversion":"4.0","6.0":"No"},
        "$toDouble":{"mongodbversion":"4.0","6.0":"No"},
        "$toInt":{"mongodbversion":"4.0","6.0":"No"},
        "$toLong":{"mongodbversion":"4.0","6.0":"No"},
        "$toLower":{"mongodbversion":"4.0","6.0":"No"},
        "$toObjectId":{"mongodbversion":"4.0","6.0":"No"},
        "$top":{"mongodbversion":"5.2","6.0":"No"},
        "$topN":{"mongodbversion":"5.2","6.0":"No"},
        "$toString":{"mongodbversion":"4.0","6.0":"No"},
        "$toUpper":{"mongodbversion":"4.0","6.0":"No"},
        "$trim":{"mongodbversion":"4.0","6.0":"No"},
        "$trunc":{"mongodbversion":"4.0","6.0":"No"},
        "$tsIncrement":{"mongodbversion":"5.1","6.0":"No"},
        "$tsSecond":{"mongodbversion":"5.1","6.0":"No"},
        "$type":{"mongodbversion":"4.0","6.0":"No"},
        "$unionWith":{"mongodbversion":"4.4","6.0":"No"},
        "$uniqueDocs":{"mongodbversion":"4.0","6.0":"No"},
        "$unset":{"mongodbversion":"4.0","6.0":"No"},
        "$unsetField":{"mongodbversion":"6.0","6.0":"No"},
        "$unwind":{"mongodbversion":"4.0","6.0":"No"},
        "$week":{"mongodbversion":"4.0","6.0":"No"},
        "$where":{"mongodbversion":"4.0","6.0":"No"},
        "$year":{"mongodbversion":"4.0","6.0":"No"},
        "$zip":{"mongodbversion":"4.0","6.0":"No"}}

    return thisKeywords


if __name__ == '__main__':
    main(sys.argv[1:])
