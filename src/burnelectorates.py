from src.util import get_json, get_local_json, get_latest_feed, upload_to_s3, save_to_file
import requests
from datetime import datetime
from typing import Dict, List
import json
from pathlib import Path
import schedule
import time

googledoc_key = "1k0_d-Og6sWr3BYz1Hw3Sz9eA98IRuvccm3r6xaA7U7s"
startTime = datetime.now()

SRC_DIR = Path(__file__).resolve().parent
DATA_DIR = SRC_DIR.parent / "data"
RESULTS_DIR = SRC_DIR.parent / "results"

# print("RESULTS_DIR: ", RESULTS_DIR)
uploadPath = "2026/11/aus-vic-election/results-data"


with open(DATA_DIR / "party_codes_by_name.json") as f:
    party_codes_by_name = json.load(f)

def select_electorate(id: str, electorate: str, results: Dict, divisions: Dict, parties: Dict) -> Dict:
    
    swing_time = True
    
    def party_names(party):
        return party_codes_by_name.get(party, party)

    # print(f"Selected electorate: {electorate}")
    result = results.get(electorate)
    aec_result = divisions.get(electorate)

    if not aec_result:
        return {}

    candidates = sorted(aec_result['candidates'], key=lambda x: x['votesTotal'], reverse=True)
    
    # "swigInfo": {"status": true, "text": "6.53% swing to Australian Labor Party (Northern Territory) Branch", "label": 15, "swingLeft": 6.53, "swingRight": -6.53, "swingPartyLeft": "Australian Labor Party (Northern Territory) Branch", "swingPartyRight": "NT CLP", "swingLeftBar": 21.764490000000002, "swingRightBar": -6.53, "swingLeftShort": "alp", "swingRightShort": "clp"}

    # "twoCandidatePreferred": [
    #             {
    #                 "candidate_id": "18552",
    #                 "candidate_name": "TAYLOR, Nina",
    #                 "votesTotal": 23824,
    #                 "votesPercent": 60.91536691383278,
    #                 "party_short": "ALP",
    #                 "party_long": "Australian Labor Party - Victorian Branch",
    #                 "votesPercentHistoric": 61.15,
    #                 "swing": -0.23463308616722145
    #             },
    #             {
    #                 "candidate_id": "19061",
    #                 "candidate_name": "SHERSON, Lauren",
    #                 "votesTotal": 15310,
    #                 "votesPercent": 39.1459984658655,
    #                 "party_short": "LIB",
    #                 "party_long": "Liberal Party of Australia - Victorian Division",
    #                 "votesPercentHistoric": 38.85,
    #                 "swing": 0.2959984658655017
    #             }
    #         ]

    swing_info = {'status': False}

    if "twoCandidatePreferred" in aec_result:
        candidate_swing_data = aec_result['twoCandidatePreferred']

        if candidate_swing_data and len(candidate_swing_data) == 2 and swing_time and candidate_swing_data[0]['swing'] is not None:

            # Find which one is positive
           
            if candidate_swing_data[0]['swing'] > candidate_swing_data[1]['swing']:
                positive_swinger = 0
                negative_swinger = 1
            else:
                positive_swinger = 1
                negative_swinger = 0

            multiplier = 3.333 if candidate_swing_data[positive_swinger]['swing'] < 15 else 2 if candidate_swing_data[positive_swinger]['swing'] < 25 else 1

            if positive_swinger == 0:            
                label = 15 if candidate_swing_data[positive_swinger]['swing'] < 15 else 25 if candidate_swing_data[positive_swinger]['swing'] < 25 else 50
            else:
                # Swing goes to the left side, so lets try inverting it and see what happens idk
                label = 15 if candidate_swing_data[positive_swinger]['swing'] < 15 else 25 if candidate_swing_data[positive_swinger]['swing'] < 25 else 50
                label = -label

            swing_info = {
                'status': True,
                'text': f"{candidate_swing_data[positive_swinger]['swing']}% swing to {party_names(candidate_swing_data[positive_swinger]['party_short'])}",
                'label': label,
                'swingLeft': candidate_swing_data[positive_swinger]['swing'],
                'swingRight': candidate_swing_data[negative_swinger]['swing'],
                'swingPartyLeft': party_names(candidate_swing_data[positive_swinger]['party_long']),
                'swingPartyRight': party_names(candidate_swing_data[negative_swinger]['party_long']),
                'swingLeftBar': candidate_swing_data[positive_swinger]['swing'] * multiplier,
                'swingRightBar': candidate_swing_data[negative_swinger]['swing'],
                'swingLeftShort': candidate_swing_data[positive_swinger]['party_short'].lower(),
                'swingRightShort': candidate_swing_data[negative_swinger]['party_short'].lower()
            }

    hide_two_party = True
    two_party = None
    name_field = None

    if isinstance(aec_result.get('twoCandidatePreferred'), list):
        two_party = sorted(aec_result['twoCandidatePreferred'], key=lambda x: x['votesTotal'], reverse=True)
        name_field = 'party_long'
        hide_two_party = False

    prediction = result['prediction'].lower() if result['prediction'] else ''
    prediction_name = parties[prediction]['partyName'] if prediction else ''

    # print(aec_result['votesCounted'], aec_result['enrolment'])
    
    tcpCountProgress = None 

    if "tcpCountProgress" in aec_result:
        tcpCountProgress = aec_result["tcpCountProgress"]

    info = {
        'display': True,
        'id': id,
        'electorate': electorate,
        'candidates': candidates,
        'hideTwoParty': hide_two_party,
        'twoParty': two_party,
        'nameField': name_field,
        'prediction': prediction,
        'status': bool(prediction),
        'predictionName': prediction_name,
        'heldBy': result['incumbent'].lower(),
        'heldByName': parties[result['incumbent'].lower()]['partyName'],
        'percentageCounted': round((aec_result['votesCounted'] / aec_result['enrolment']) * 100, 1),
        'swigInfo': swing_info,
        "tcpCountProgress": tcpCountProgress
    }

    return info

def burnElectorates(uploadPath="", uploadElectorates=True):

    print("Burning electorate files...")
    # Fetch Google doc data
    
    googledoc = requests.get(f"https://interactive.guim.co.uk/docsdata/{googledoc_key}.json").json()['sheets']
    print(f"Latest googledoc: https://interactive.guim.co.uk/docsdata/{googledoc_key}.json")

    # Get latest feed data from the local file
    latest = get_local_json("recentResults.json")
    
    print("Latest results file: ", latest[0])
    # Most recent results file
    latest_data = get_local_json(f"results/{latest[0]}.json")
    
    # Get summary results
    summary_results = get_local_json("results/summaryResults.json")
    
    # Get swing data
    # swing = get_local_json(f"results/{latest_feed}-swing.json")
    
    # Create data maps
    electorates_map = {item['electorate']: item for item in googledoc['electorates']}
    places = [item['electorate'] for item in googledoc['electorates']]
    divisions = {item['name']: item for item in latest_data['divisions']}

    # Custom party names from the Google Doc
    
    parties = {item['partyCode'].lower(): item for item in googledoc['partyNames']}
    
    googledoc['parties'] = parties
    
    # print(latest_data['nationalSwing'])
    
    # Process electorates

    electorates_data = googledoc['electorates']

    
    for item in electorates_data:
        info = select_electorate(item['id'], item['electorate'], electorates_map, divisions, parties)
        if info.get('twoParty'):
            item['byMargin'] = info['twoParty'][0]['swing']
        
        electorate_info = json.dumps(info).encode()
        save_to_file(f"{RESULTS_DIR}/electorates/{item['id']}.json", electorate_info)
        # print(f"Saved {item['id']}.json")
        
        if uploadElectorates:
            upload_to_s3(f"{uploadPath}/electorates/{item['id']}.json", electorate_info)
            # print(f"Uploaded {item['id']}.json")

    timeRun = datetime.now() - startTime
    print(f"Finished in {timeRun}")

if __name__ == "__main__":
    burnElectorates(uploadPath, uploadElectorates=True)
    schedule.every(3).minutes.do(burnElectorates, uploadPath, uploadElectorates=True)
    while True:
        schedule.run_pending()
        time.sleep(1)
        print(datetime.now())