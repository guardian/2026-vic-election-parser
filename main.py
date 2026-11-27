import json
import schedule
import time
import os
from azure.storage.blob import ContainerClient
from contextlib import nullcontext
from datetime import datetime
from zipfile import ZipFile
import src.logResults as logresults
from src.downloadBlob import getAndReadFile
from src.feedburner import burnfeeds
from pathlib import Path
from src.makeStateAndDivisionResults import eml_to_JSON
from datetime import datetime
from src.burnelectorates import burnElectorates
from src.candidateResultsByPP import getPollingPlaceResults

SRC_DIR = Path(__file__).resolve().parent
DATA_DIR = SRC_DIR / "data"
TEST_DATA_DIR = DATA_DIR / "test-2022"

print(SRC_DIR)
print(TEST_DATA_DIR)

# Uses the local data in data/test-2022

testing = False

# True if we want to upload results to s3 on election night, false for local testing

upload = True

# Ignores recentResults.json if True

ignore_results = False

# Election idenfier string. TestState2026 is the test election, State026 is the real election.

election_id = "State2026"

if election_id == "TestState2026":
    print("YOU HAVE THE TEST ID SET CHANGE THIS IF IT IS ELECTION NIGHT")

# Filetypes to filter by

filetype = "mediafileverboselhv2"

if testing:
    filetype = "mediafileverboselh"

# The first part of the s3 upload path

uploadPath = "2026/11/aus-vic-election/results-data"

# Make results directory if it doesn't exist

RESULTS_DIR = SRC_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Make electorates directory if it doesn't exist

ELECTORATES_DIR = RESULTS_DIR / "electorates"
ELECTORATES_DIR.mkdir(parents=True, exist_ok=True)

# Extract timestamp from blob name eg TestState2026mediafileverboselhv2_20260926_100901.xml

def getTimestamp(file_str):
    # Timestamps are in the format YYYYMMDD_HHMMSS
    # print(file_str)
    timestamp = file_str.split(filetype + "_")[1].split(".zip")[0]

    timestamp_parsed = datetime.strptime(timestamp,"%Y%m%d_%H%M%S")

    return timestamp_parsed

def results_source(test):
    # Local zips do not need the VEC SAS URL.
    if test:
        return nullcontext(None)
    return ContainerClient.from_container_url(os.environ["VEC_RESULTS_SAS"])

def list_result_names(container=None):
    if container is None:
        names = [path.name for path in TEST_DATA_DIR.glob("*.zip")]
        # print("files in test data directory: ", names)
        return [name for name in names if filetype in name]

    prefix = f"{election_id}{filetype}"
    return [blob.name for blob in container.list_blobs() if prefix in blob.name]

def read_results_xml(filename, container=None):
    stem = filename.removesuffix(".zip")
    
    if container is None:
        local_name = Path(stem).name
        with ZipFile(TEST_DATA_DIR / f"{local_name}.zip") as archive:
            return archive.read(f"{local_name}.xml")

    return getAndReadFile(container, stem)

def process_latest(names, container=None):
    
    if not names:
        print("No results files found")
        return
    print("names: ", names)
    latest_name = max(names, key=getTimestamp)
    latest_timestamp = datetime.strftime(getTimestamp(latest_name), "%Y%m%d_%H%M%S")
    print("latest timestamp is ", latest_timestamp)

    # Get the latest timestamp from the local results file
    recent_path = Path("recentResults.json")
    already_saved = False


    if recent_path.exists() and not ignore_results:
        recent_results = json.loads(recent_path.read_text())
        already_saved = latest_timestamp in recent_results

    # We already have these results, so do nothing

    if already_saved:

        print(f"{latest_timestamp} has already been saved")

    else:

        if recent_path.exists() and not ignore_results:
            print(f"{latest_timestamp} hasn't been saved, saving now")
        else:
            print(f"Results file not found or ignored, saving {latest_timestamp} as first entry")

        print("Getting", latest_name)
        content = read_results_xml(latest_name, container)
        print("Parsing results...")

        # eml_to_JSON(eml_file=VEC_2022_XML_FILE_DECLARED,
		# 	 local=True,
		# 	 timestamp='20260926_100901', 
		# 	 uploadPath="2026/11/aus-vic-election/results-data",
		# 	 upload=True)	

        eml_to_JSON(content, local=False, timestamp=latest_timestamp, uploadPath=uploadPath, upload=upload)
        getPollingPlaceResults(content, testing=testing, local=False, timestamp=latest_timestamp, uploadPath=uploadPath, upload=upload)

        logresults.saveRecentResults(
            timestamp=latest_timestamp,
            uploadPath=uploadPath,
            upload=upload,
        )

    burnfeeds(uploadPath, latest_timestamp, upload)
    
    # burnElectorates(uploadPath, uploadElectorates=True)

def get_results_files(test):
    with results_source(test) as container:
        process_latest(list_result_names(container), container)

def parse_results(test):
    startTime = datetime.now()
    # Get a list of the latest files in the VEC's azure storage thing
    print("Parsing VEC results...")
    print("test:", test)
    get_results_files(test)
    endTime = datetime.now()
    print(f"Time taken: {endTime - startTime}")


# if __name__ == "__main__":
parse_results(testing)

schedule.every(1).minutes.do(parse_results,testing)
# schedule.every(3).minutes.do(burnElectorates, uploadPath, upload)

while True:
    schedule.run_pending()
    time.sleep(1)
    print(datetime.now())