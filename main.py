import json
import requests
import schedule
import time
import xmltodict
import os
from azure.storage.blob import ContainerClient
from datetime import datetime
from zipfile import ZipFile
import src.logResults as logresults
from src.downloadBlob import getAndReadFile
from src.feedburner import burnfeeds
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
DATA_DIR = SRC_DIR / "data"
TEST_DATA_DIR = DATA_DIR / "test-2022"

print(SRC_DIR)
print(TEST_DATA_DIR)
# Credentials URL from the VEC

VEC_TOKEN = os.environ["VEC_RESULTS_SAS"]

# Uses the local data in data/test-2022

testing = True

# True if we want to upload results to s3 on election night, false for local testing

upload = True

# Ignores recentResults.json if True

ignore_results = True

# Election idenfier string. TestState2026 is the test election, State026 is the real election.

election_id = "TestState2026"

if election_id == "TestState2026":
    print("YOU HAVE THE TEST ID SET CHANGE THIS IF IT IS ELECTION NIGHT")

# Filetypes to filter by

filetype = "mediafileverboselhv2"

if testing:
    filetype = "mediafileverboselh"

# The first part of the s3 upload path

uploadPath = "2026/11/aus-vic-election/results-data"

def returnFilename(timestamp):
    return f"{election_id}{filetype}_{timestamp}"

# Extract timestamp from blob name eg TestState2026mediafileverboselhv2_20260926_100901.xml

def getTimestamp(file_str):
    # Timestamps are in the format YYYYMMDD_HHMMSS
    print(file_str)
    timestamp = file_str.split(filetype + "_")[1].split(".zip")[0]

    timestamp_parsed = datetime.strptime(timestamp,"%Y%m%d_%H%M%S")

    return timestamp_parsed

# Authenticate and download file list

def get_results_files(test):
    if test:
        files = [f.name for f in TEST_DATA_DIR.glob("*.zip")]
        # print(files)
        timestamps = [getTimestamp(fileName) for fileName in files]
            # print(timestamps)

        latestTimestamp = max(timestamps)
        latestTimestampStr = datetime.strftime(latestTimestamp, '%Y%m%d_%H%M%S')

        print("latest timestamp is", latestTimestampStr)

    else:
        with ContainerClient.from_container_url(VEC_TOKEN) as container:
            blobs = list(container.list_blobs())
            filtered_blobs = [blob.name for blob in blobs if f"{election_id}{filetype}" in blob.name]
            # print(filtered_blobs)

            timestamps = [getTimestamp(fileName) for fileName in filtered_blobs]
            # print(timestamps)

            latestTimestamp = max(timestamps)
            latestTimestampStr = datetime.strftime(latestTimestamp, '%Y%m%d_%H%M%S')

            print("latest timestamp is", latestTimestampStr)

            if os.path.exists('recentResults.json') and not ignore_results:

                # Get recent timestamps of results

                with open('recentResults.json','r') as recentResultsFile:
                    recentResults = json.load(recentResultsFile)
                
                # print(recentResults)

                # Check if we have it or not

                if latestTimestampStr not in recentResults:
                    print(f"{latestTimestampStr} hasn't been saved, saving now")
                    
                    # Get latest file

                    latestFilename = returnFilename(latestTimestampStr)
                    print("Getting", f"{latestFilename}.zip")
                    content = getAndReadFile(container, latestFilename)

                    # Parse results functions here

                    print("Parsing results...")
                else:
                    print(f"{latestTimestampStr} has already been saved")
                    
            else:
                print(f"Results file not found or ignored, saving {latestTimestampStr} as first entry")
                latestFilename = returnFilename(latestTimestampStr)
                print("Getting", f"{latestFilename}.zip")

                content = getAndReadFile(container, latestFilename)
                
                # Parse results functions here
                print("Parsing results...")
                # results = xmltodict.parse(content)
            
                logresults.saveRecentResults(timestamp=latestTimestampStr, 
                                    uploadPath=uploadPath,
                                    upload=upload)

            # Outputs a json version for testing
            # with open("demo-results.json", "w") as f:
            #     json.dump(filtered_blobs, f, indent=2, default=lambda o: dict(o) if hasattr(o, "keys") else str(o))

            # latest = max(blobs, key=lambda blob: blob.last_modified)
            # print(f"Latest results file is {latest.name} ({latest.last_modified:%Y-%m-%d %H:%M:%S})")
            # print(f"Latest results file is {blob.name} ({timestamp:%Y-%m-%d %H:%M:%S})")
            # xml_bytes = read_blob_xml(container, blob.name)
            burnfeeds(uploadPath, latestTimestampStr)

        # results = xmltodict.parse(xml_bytes)
        # return results

def parse_results(test):

    # Get a list of the latest files in the VEC's azure storage thing
    print("Parsing VEC results...")
    print("test:", test)
    get_results_files(test)


if __name__ == "__main__":
    parse_results(testing)