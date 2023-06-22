#!/usr/bin/python3
import glob
import pathlib
import os
import sys
import re
import argparse

versions = ['3.6','4.0','5.0','EC5.0','FerretDB']
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
    
    ver = args.version

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

                    elif (keywords[checkCompat][ver] == 'Yes') and args.showSupported:
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
    parser.add_argument("--version", dest="version", action="store", default="5.0", help="Check for DocumentDB version compatibility (default is 5.0) and FerretDB compatibility", choices=versions, required=False)
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
    # to avoid false positives and or negatives for FerretDB we set all keywords to "No".
    # only set to "Yes" if we support them in all commands and CRUD operations.
    thisKeywords = {
        "$$CURRENT":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$$DESCEND":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"No","FerretDB":"No"},
        "$$KEEP":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"No","FerretDB":"No"},
        "$$PRUNE":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"No","FerretDB":"No"},
        "$$REMOVE":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$$ROOT":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"No","FerretDB":"No"},
        "$abs":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$accumulator":{"mongodbversion":"4.4","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$acos":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$acosh":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$add":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$addFields":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$addToSet":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$all":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$allElementsTrue":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$and":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$anyElementTrue":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$arrayElemAt":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$arrayToObject":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$asin":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$asinh":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$atan":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$atan2":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$atanh":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$avg":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$binarySize":{"mongodbversion":"4.4","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$bit":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$bitsAllClear":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$bitsAllSet":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$bitsAnyClear":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$bitsAnySet":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$bottom":{"mongodbversion":"5.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$bottomN":{"mongodbversion":"5.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$box":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$bsonSize":{"mongodbversion":"4.4","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$bucket":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$bucketAuto":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$ceil":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$center":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$centerSphere":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$cmp":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$collStats":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$comment":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$concat":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$concatArrays":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$cond":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$convert":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$cos":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$cosh":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$count":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"Yes"},
        "$currentDate":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"Yes"},
        "$currentOp":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"No","FerretDB":"No"},
        "$dateAdd":{"mongodbversion":"5.0","3.6":"No","4.0":"No","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$dateDiff":{"mongodbversion":"5.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$dateFromParts":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$dateFromString":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$dateSubtract":{"mongodbversion":"5.0","3.6":"No","4.0":"No","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$dateToParts":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$dateToString":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$dateTrunc":{"mongodbversion":"5.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$dayOfMonth":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$dayOfWeek":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$dayOfYear":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$degreesToRadians":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$densify":{"mongodbversion":"5.1","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$divide":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$documents":{"mongodbversion":"5.1","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$each":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$elemMatch":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$eq":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$exists":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"Yes"},
        "$exp":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$expr":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$facet":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$fill":{"mongodbversion":"5.3","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$filter":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$first":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$firstN":{"mongodbversion":"5.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$floor":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$function":{"mongodbversion":"4.4","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$geoIntersects":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"No","FerretDB":"No"},
        "$geometry":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"No","FerretDB":"No"},
        "$geoNear":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$geoWithin":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"No","FerretDB":"No"},
        "$getField":{"mongodbversion":"5.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$graphLookup":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$group":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"Yes"},
        "$gt":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$gte":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$hour":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$ifNull":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$in":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$inc":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$indexOfArray":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$indexOfBytes":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$indexOfCP":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$indexStats":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$isArray":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$isNumber":{"mongodbversion":"4.4","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$isoDayOfWeek":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$isoWeek":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$isoWeekYear":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$jsonSchema":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$last":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$lastN":{"mongodbversion":"5.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$let":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$limit":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"Yes"},
        "$linearFill":{"mongodbversion":"5.3","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$listLocalSessions":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$listSessions":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$literal":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$ln":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$locf":{"mongodbversion":"5.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$log":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$log10":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$lookup":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$lt":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$lte":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$ltrim":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$map":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$match":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"Yes"},
        "$max":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$maxDistance":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"No","FerretDB":"No"},
        "$maxN":{"mongodbversion":"5.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$merge":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$mergeObjects":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$meta":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$millisecond":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$min":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$minDistance":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"No","FerretDB":"No"},
        "$minN":{"mongodbversion":"5.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$minute":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$mod":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$month":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$mul":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$multiply":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$natural":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$ne":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$near":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$nearSphere":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"No","FerretDB":"No"},
        "$nin":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$nor":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$not":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$objectToArray":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$or":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$out":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"No","FerretDB":"No"},
        "$planCacheStats":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$polygon":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$pop":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$position":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$pow":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$project":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"Yes"},
        "$pull":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$pullAll":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$push":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$radiansToDegrees":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$rand":{"mongodbversion":"5.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$range":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$redact":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$reduce":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$regex":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$regexFind":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$regexFindAll":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$regexMatch":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$rename":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"Yes"},
        "$replaceAll":{"mongodbversion":"4.4","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$replaceOne":{"mongodbversion":"4.4","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$replaceRoot":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$replaceWith":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$reverseArray":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$round":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$rtrim":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$sample":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"No","FerretDB":"No"},
        "$sampleRate":{"mongodbversion":"5.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$second":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$set":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$setDifference":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$setEquals":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$setField":{"mongodbversion":"5.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$setIntersection":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$setIsSubset":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$setOnInsert":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$setUnion":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$setWindowFields":{"mongodbversion":"5.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$sin":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$sinh":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$size":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$skip":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"Yes"},
        "$slice":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$sort":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"Yes"},
        "$sortArray":{"mongodbversion":"5.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$sortByCount":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$split":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$sqrt":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$stdDevPop":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$stdDevSamp":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$strcasecmp":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$strLenBytes":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$strLenCP":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$substr":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$substrBytes":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$substrCP":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$subtract":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$sum":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$switch":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$tan":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$tanh":{"mongodbversion":"4.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$text":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$toBool":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$toDate":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$toDecimal":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$toDouble":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$toInt":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$toLong":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$toLower":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$toObjectId":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$top":{"mongodbversion":"5.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$topN":{"mongodbversion":"5.2","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$toString":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$toUpper":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$trim":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$trunc":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$tsIncrement":{"mongodbversion":"5.1","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$tsSecond":{"mongodbversion":"5.1","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$type":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"Yes"},
        "$unionWith":{"mongodbversion":"4.4","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$uniqueDocs":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$unset":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"Yes"},
        "$unsetField":{"mongodbversion":"5.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$unwind":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$week":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$where":{"mongodbversion":"4.0","3.6":"No","4.0":"No","5.0":"No","EC5.0":"No","FerretDB":"No"},
        "$year":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes","FerretDB":"No"},
        "$zip":{"mongodbversion":"4.0","3.6":"Yes","4.0":"Yes","5.0":"Yes","EC5.0":"Yes"},"FerretDB":"No"}
        
    return thisKeywords

    
if __name__ == '__main__':
    main(sys.argv[1:])
