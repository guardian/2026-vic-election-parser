# Splits the big results JSON data into smaller files for different parts of the results dashboard

import requests
import json
from datetime import datetime
from typing import Dict, List, Optional, Union
import math
try:
    from src.util import get_json, get_local_json, get_latest_feed, upload_to_s3, save_to_file
except ImportError:
    from util import get_json, get_local_json, get_latest_feed, upload_to_s3, save_to_file

import pytz
from pathlib import Path
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent
DATA_DIR = SRC_DIR.parent / "data"
RESULTS_DIR = SRC_DIR.parent / "results"

aest = pytz.timezone("Australia/Sydney") 

startTime = datetime.now()

# Total seats in the lower house

totalSeats = 88
majoritySeats = 45

# Total seats in the senate
totalSeatsSenate = 40

senateMajority = 21


with open(DATA_DIR / "party_codes_by_name.json") as f:
    party_codes_by_name = json.load(f)


with open(DATA_DIR / "party_codes_by_code.json") as f:
    party_codes_by_code = json.load(f)


# uploadElectorates = False
# if not uploadElectorates:
#     print("WARNING: NOT UPLOADING ELECTORATES")

# config = {
#     "title": "",
#     "docData": "",
#     "path": "embed/aus/2025/02/aus-election/results-data"
# }

# https://interactive.guim.co.uk/docsdata/1k0_d-Og6sWr3BYz1Hw3Sz9eA98IRuvccm3r6xaA7U7s.json
googledoc_key = "1k0_d-Og6sWr3BYz1Hw3Sz9eA98IRuvccm3r6xaA7U7s"

# url = "https://interactive.guim.co.uk/2022/05/aus-election/results-data"

COALITION = ['lib', 'lnp', 'nat', 'clp']
SENATE = ['lib', 'nat', 'on', 'other', 'alp', 'grn']

# def get_alignment(key: str) -> str:
#     left_aligned = ["alp", "grn", "ajp"]
#     right_aligned = ["lib", "lnp", "nat", "ind", "sff"]
    
#     key = key.lower()
#     if key in left_aligned:
#         return "left"
#     elif key in right_aligned or key not in left_aligned:
#         return "right"

def compile(electorates: List[Dict], options: List[Dict], parties: Dict, summary_results: Dict) -> Dict:
    # Calculate tallies
    tallies = {}
    for electorate in electorates:
        party = electorate['prediction'].lower()
        if party:
            tallies[party] = tallies.get(party, 0) + 1

    party_data = []
    for party, value in tallies.items():
        if party:
            party_info = parties.get(party)
            if party_info:
                party_data.append({
                    'key': party,
                    'value': value,
                    'name': party_info['partyName'],
                    'shortName': party_info['shortName']
                })

    # Sort party data by value
    party_data.sort(key=lambda x: x['value'], reverse=True)
    list_size = math.ceil(len(party_data) / 2)

    # Calculate Labor and Coalition seats
    lab_seats = next((p['value'] for p in party_data if p['key'] == 'alp'), 0)
    coalition_seats = sum(p['value'] for p in party_data if p['key'] in ['lib', 'lnp', 'nat', 'clp'])

    lab_percentage = (lab_seats / totalSeats) * 100
    coalition_percentage = (coalition_seats / totalSeats) * 100

    twoParty = [
        { "name": "Coalition", "party": "coal", "seats": coalition_seats },
        { "name": "Labor", "party": "alp", "seats": lab_seats }
    ]

    # party_data_2pp = [
    #     {'name': 'Coalition', 'seats': coalition_seats, 'percentage': coalition_percentage, 'party': 'coal'},
    #     {'name': 'Labor', 'seats': lab_seats, 'percentage': lab_percentage, 'party': 'alp'}
    # ]

    displaySwing = False if options[0]['swing'] == "FALSE" else True
    showSwingometer = False if options[0]['showSwingometer'] == "FALSE" else True
    # showNationalSwing = False if options[0]['showNationalSwing'] == "FALSE" else True

    render_data = {
        'TOTAL_SEATS': totalSeats,
        'MAJORITY_SEATS': majoritySeats,
        'parties': party_data,
        'twoParty': twoParty,
        'votesCountedPercent': summary_results['votesCountedPercent'],
        'outcome': options[0]['outcome']
    }

    # render_data['twoParty'] = party_data_2pp
    
    print(f"{summary_results['votesCountedPercent']}% of Victoria has voted.")

    
    return render_data


def create_table(data):
    # Build party map lookup
    df = pd.DataFrame(data)

    # Data fields
    #  {
    #             "coalition_short": "ALP",
    #             "votesTotal": 1339496,
    #             "votesPercent": 37.03,
    #             "partygroup_name": "Australian Labor Party - Victorian Branch",
    #             "votesPercentOld": 36.65330142019311,
    #             "swing": 0.38
    #         }

    # Merge the coalition party results into a single row

    coalition_parties = ["Liberal Party of Australia - Victorian Division", "National Party of Australia - Victoria"]

    coalition_only = df[df['partygroup_name'].isin(coalition_parties)]
    coalition_only['coalition'] = 'coalition'
    coalition_only_gp = coalition_only.groupby('coalition').sum().reset_index()
    coalition_only_gp = coalition_only_gp[['coalition_short', 'shortName', 'votesTotal', 'votesPercent', 'partygroup_name', 'votesPercentOld', 'swing']]
    coalition_only_gp = coalition_only_gp.round(2)
    coalition_only_gp['partygroup_name'] = 'Coalition'
    coalition_only_gp['coalition_short'] = 'COAL'
    coalition_only_gp['shortName'] = 'Coalition'

    results_df = df[~df['partygroup_name'].isin(coalition_parties)]
    results_df = pd.concat([results_df, coalition_only_gp])

    # Later, maybe only keep a certain set and truncate the others to "Other"
    # parties_to_name = []
    # Fields we need:
    # { "party": "Labor party", "votesPercent": 37.03, "votes": 1339496, "swing": 0.38 }

    results_df = results_df.rename(columns={'shortName': 'party', 'votesTotal': 'votes'})
    results_df = results_df[['party', 'votes', 'votesPercent', 'swing']]
    results_df = results_df.sort_values(by='votes', ascending=False)

    results_dict = results_df.to_dict(orient='records')
    for row in results_dict:
        for key, value in row.items():
            if isinstance(value, float) and pd.isna(value):
                row[key] = None
                
    return results_dict

def create_ticker_feed(data: Dict) -> List[Dict]:
    predictions = [d for d in data['electorates'] if d['prediction']]
    party_map = {item['partyCode']: item for item in data['partyNames']}
    
    for prediction in predictions:
        prediction['announced'] = "Predicted"
        prediction['status'] = "hold" if prediction['prediction'] == prediction['incumbent'] else "wins"
        prediction['label'] = (party_map.get(prediction['prediction'], {}).get('shortName', '')
                             if prediction['prediction'] != "IND"
                             else prediction['prediction-name'])

    with_timestamp = []
    without_timestamp = []

    for item in predictions:
        if item['timestamp']:
            # '05-31-2022 07:09:33'
            dt_naive = datetime.strptime(item['timestamp'], "%m-%d-%Y %H:%M:%S")
            # Localize to AEST
            dt_aest = aest.localize(dt_naive)
            # print(item['timestamp'], dt_aest.timestamp())
            item['unix'] = int(dt_aest.timestamp())
            # 2007-12-03T10:15:30+01:00[Europe/Paris]
            item['isoTimestamp'] = dt_aest.isoformat()
            with_timestamp.append(item)
        else:
            without_timestamp.append(item)

    with_timestamp.sort(key=lambda x: x['unix'], reverse=True)
    results = (with_timestamp + without_timestamp)[:15]

    fields_to_keep = ['electorate', 'prediction', 'incumbent', 'label', 'announced', 'isoTimestamp']

    results = [{k: v for k, v in item.items() if k in fields_to_keep} for item in results]
    # print("results", results)
    return results

def senate_render(googledoc):
    # Set up constants
    key = 'upperhouse'
    party_field = 'party'

    # Set up constants
    key = 'upperhouse'
    party_field = 'party'

    # Filter out records with an empty party field
    has_data = [d for d in googledoc[key] if d[party_field]]

    if len(has_data) > 0:
        df = pd.DataFrame(has_data)
        print(df.head())
        df['count'] = 1


        parties_df = df[['party','count']].groupby('party').sum().reset_index()
        parties_df = parties_df.sort_values(by='count', ascending=False)

        parties_df['name'] = parties_df['party'].map(party_codes_by_code).apply(lambda party: party['short_name'])

        # parties_to_name = ['ALP', 'LIB', 'NAT', 'ON', 'GRN']

        parties_gp = parties_df[['party', 'name', 'count']].groupby(['party', 'name']).sum().reset_index()
        parties_gp = parties_gp.rename(columns={'party':'key', 'count':'seats'})
        parties_gp = parties_gp.sort_values(by='seats', ascending=False)
        parties_gp['key'] = parties_gp['key'].str.lower()

        regions_df = df.copy()

        regions_df['party'] = regions_df['party'].str.lower()
        regions_df['spot'] = pd.to_numeric(regions_df['spot'], errors='coerce')
        regions_df = regions_df.sort_values(['region', 'spot'])

        regions_gp = (
            regions_df.groupby('region', sort=False)['party']
            .agg(list)
            .reset_index(name='parties')
        )

        regions_gp = regions_gp.rename(columns={'parties':'elected'})
        # print(regions_gp.to_dict(orient='records'))
    
        return {"parties": parties_gp.to_dict(orient='records'), "regions": regions_gp.to_dict(orient='records')}

    else:
        return {"parties": [], "regions": []}

def burnfeeds(uploadPath="", latestTimestampStr="", upload=False):
    
    if not upload:
        print("WARNING: NOT UPLOADING TO SERVER")    

    if uploadPath == "":
        raise ValueError("uploadPath is required")

    # Set some variables
    # Primary % for Liberal and National at the 2022 election

    coalition_old_primary = (29.60 + 4.77)
    
    # Fetch Google doc data
    
    googledoc = requests.get(f"https://interactive.guim.co.uk/docsdata/{googledoc_key}.json").json()['sheets']
    # print(f"Latest googledoc: https://interactive.guim.co.uk/docsdata/{googledoc_key}.json")

    latest_data = get_local_json(RESULTS_DIR / f"{latestTimestampStr}.json")
    
    # Get summary results
    summary_results = get_local_json(RESULTS_DIR / "summaryResults.json")
    
    # Get swing data
    # swing = get_local_json(RESULTS_DIR / f"{latest_feed}-swing.json")
    
    # Create data maps
    electorates_map = {item['electorate']: item for item in googledoc['electorates']}
    places = [item['electorate'] for item in googledoc['electorates']]
    divisions = {item['name']: item for item in latest_data['divisions']}

    # What happens if there are parties not in the party list?
    parties = {item['partyCode'].lower(): item for item in googledoc['partyNames']}
    
    # Process data
    parties_table_data = create_table(latest_data['partyNationalResults'])
    ticker = create_ticker_feed(googledoc)
    googledoc['parties'] = parties
    
    # Process electorates

    electorates_data = googledoc['electorates']

    electorate_fields_to_keep = ['id', 'electorate', 'prediction', 'incumbent', 'margin', 'against']

    electorates_data = [{k: v for k, v in item.items() if k in electorate_fields_to_keep} for item in electorates_data]

    # Upload electorates data
    electorates_data_buffer = json.dumps(electorates_data).encode()
    if upload:
        upload_to_s3(f"{uploadPath}/electorates.json", electorates_data_buffer)
    save_to_file("results/electorates.json", electorates_data_buffer)
    
    # Process and upload firewire data
    firewire = compile(googledoc['electorates'], googledoc['options'], parties, summary_results)
    firewire_data_buffer = json.dumps(firewire).encode()
    if upload:
        upload_to_s3(f"{uploadPath}/firewire.json", firewire_data_buffer)
    save_to_file("results/firewire.json", firewire_data_buffer)    

    # Process senate data
    senate_data = senate_render(googledoc)
    
    # Create and upload feed data
    updated = datetime.now(aest).isoformat()
    print(f"Updating feed with {updated}")
    # dt_aest = aest.localize(dt_naive)
    feed = {
        'updated': updated,
        'ticker': ticker,
        'partiesTable': parties_table_data,
        'council': { 
            'TOTAL_SEATS': totalSeatsSenate,
            'MAJORITY_SEATS': senateMajority,
            'display': True, 
            'parties': senate_data['parties'],
            'regions': senate_data['regions']
            }
    }
    
    feed_data_buffer = json.dumps(feed).encode()
    if upload:
        upload_to_s3(f"{uploadPath}/feed.json", feed_data_buffer)
    save_to_file("results/feed.json", feed_data_buffer)    

    # Upload last updated timestamp
    last_updated_buffer = json.dumps({'updated': updated}).encode()
    if upload:
        upload_to_s3(f"{uploadPath}/lastUpdated.json", last_updated_buffer)
    save_to_file("results/lastUpdated.json", last_updated_buffer)    

    # Upload swing data
    # swing_feed_buffer = json.dumps(swing).encode()
    # if upload:
    #     upload_to_s3(f"{uploadPath}/swing.json", swing_feed_buffer)
    # save_to_file("results/swing.json", swing_feed_buffer)    
    
    timeRun = datetime.now() - startTime
    print(f"Finished in {timeRun}")

if __name__ == "__main__":
    burnfeeds(
        uploadPath="2026/11/aus-vic-election/results-data", 
        latestTimestampStr="20221215_180017", 
        upload=False) 