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
    
    print(f"{summary_results['votesCountedPercent']}% of Australia has voted.")
    
    return render_data


def create_table(data: List[Dict], party_map: List[Dict], swing: bool, coalition_old_primary: float) -> List[Dict]:
    # Build party map lookup
    p_map = {item['partyCode'].lower(): item for item in party_map}
    
    # Build initial table data
    table_data = []
    for item in data:
        base = {
            'party': item['partygroup_name'],
            'votesPercent': float(item['votesPercent']),
            'votes': float(item['votesTotal']),
            'short': item['coalition_short']
        }
        if swing:
            base['Swing'] = float(item['swing'])
        table_data.append(base)

    # Process coalition items
    coalition = ["Liberal party", "Liberal Party of Australia - Victorian Division", "National Party of Australia - Victoria"]
    coalition_items = [item for item in table_data if item['party'] in coalition]
    
    coalition_summary = {
        'party': 'Coalition',
        'votesPercent': sum(item['votesPercent'] for item in coalition_items),
        'votes': sum(item['votes'] for item in coalition_items),
        'short': 'Coalition'
    }
    
    # Hard coded primary vote for Coalition, needs to be updated for new elections

    if swing:
        if coalition_summary['votesPercent'] > 0:
            coalition_summary['swing'] = coalition_summary['votesPercent'] - coalition_old_primary
        else:
            coalition_summary['swing'] = 0

    others = [
        "Australian Labor Party - Victorian Branch", "Australian Greens Victoria", "The Australian Greens - Victoria", "Independent",
        "Pauline Hanson's One Nation"
        ]
    
    result = [item for item in table_data if item['party'] in others]

    # Update party names
    for item in result:
        party_info = p_map.get(item['short'])
        if party_info:
            item['party'] = party_info['shortName']

    # Keep only desired properties
    result = [{k: v for k, v in item.items() if k in ['party', 'short','votesPercent', 'votes', 'swing']} 
              for item in result]

    result.append(coalition_summary)
    result.sort(key=lambda x: x['votes'], reverse=True)

    # Format numeric values
    for record in result:
        record['votesPercent'] = round(record['votesPercent'], 2)
        if 'swing' in record:
            record['swing'] = round(record['swing'], 2)

    return result

def create_ticker_feed(data: Dict) -> List[Dict]:
    predictions = [d for d in data['electorates'] if d['prediction']]
    party_map = {item['partyCode']: item for item in data['partyNames']}
    
    for prediction in predictions:
        prediction['announced'] = "Predicted"
        prediction['status'] = "hold" if prediction['prediction'] == prediction['incumbent'] else "wins"
        prediction['label'] = (party_map.get(prediction['prediction'], {}).get('partyName', '')
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
    print("results", results)
    return results

def senate_render(data: Dict) -> Dict:
    # Set up constants
    key = 'upperhouse'
    party_field = 'party'

    # Filter out records with an empty party field
    has_data = [d for d in data[key] if d[party_field]]

    # Tally each party's count (using a case-insensitive party key)
    party_data = []
    party_counts = {}
    others_count = 0

    for curr in has_data:
        party_key = curr[party_field].lower()
        if party_key not in party_counts:
            party_counts[party_key] = {'key': party_key, 'value': 0}
            party_data.append(party_counts[party_key])
        party_counts[party_key]['value'] += 1
        if party_key not in SENATE:
            others_count += 1

    print("party_counts", party_counts)

    # Enhance partyData with additional properties
    for d in party_data:
        current_items = [item for item in has_data 
                        if item[party_field].lower() == d['key'] 
                        and item.get('current') == 'yes']
        
        party_info = data['parties'].get(d['key'])
        d['name'] = party_info['partyName'] if party_info else d['key']
        d['shortName'] = party_info['shortName'] if party_info else d['key']
        # d['current'] = len(current_items)
        # d['elected'] = d['value'] - d['current']

    # Create a lookup map for party data
    party_map = {item['key']: item for item in party_data}

    print("party_data", party_data)

    # Build senateData based on the global SENATE array
    senate_data = []
    for d in SENATE:
        party = party_map.get(d)
        seats = party['value'] if party else 0

        senate_data.append({
            'key': d,
            'name': party['shortName'] if party else d,
            'seats': seats
        })

    # Create a Map from senateData for quick lookup
    senate_map = {item['key']: item for item in senate_data}

    # # Define breakdown fields
    # breakdowns = [
    #     {'value': 'value', 'seats': 'seats', 'percentage': 'percentage'},
    #     {'value': 'current', 'seats': 'currentSeats', 'percentage': 'currentPercentage'},
    #     {'value': 'elected', 'seats': 'electedSeats', 'percentage': 'electedPercentage'}
    # ]

    # # Calculate aggregate values for 'other' and adjust the 'lib' totals
    # for field in breakdowns:
    #     other = senate_map['other']
    #     # Sum values for parties not in senateMap and not LNP/CLP
    #     other_sum = sum(d[field['value']] for d in party_data 
    #                    if d['key'] not in senate_map and d['key'] not in ['lnp', 'clp'])
        
    #     other[field['value']] = other_sum
    #     other[field['seats']] = other_sum > 0
    #     other[field['percentage']] = (
    #         (other_sum / totalSeatsSenate * 100) if field['value'] == 'value'
    #         else (other_sum / other['value'] * 100) if other['value']
    #         else 0
    #     )

    #     # Add LNP and CLP numbers into the Liberal totals
    #     lib = senate_map['lib']
    #     lnp_value = party_map.get('lnp', {}).get(field['value'], 0)
    #     clp_value = party_map.get('clp', {}).get(field['value'], 0)

    #     lib[field['value']] += lnp_value + clp_value
    #     lib[field['seats']] = lib[field['value']] > 0
    #     lib[field['percentage']] = (
    #         (lib[field['value']] / totalSeatsSenate * 100) if field['value'] == 'value'
    #         else (lib[field['value']] / lib['value'] * 100) if lib['value']
    #         else 0
    #     )

    # # Calculate pending seats
    # senate_map['pending']['value'] = totalSeatsSenate - len(has_data)

    # Sort party_data
    party_data.sort(key=lambda x: x['value'], reverse=True)

    list_size = math.ceil(len(party_map) / 2)

    # Build final render data

    render_data = list(senate_map.values()),

    return render_data

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
    print(f"Latest googledoc: https://interactive.guim.co.uk/docsdata/{googledoc_key}.json")

    latest_data = get_local_json(RESULTS_DIR / f"{latestTimestampStr}.json")
    
    # Get summary results
    summary_results = get_local_json("summaryResults.json")
    
    # Get swing data
    # swing = get_local_json(RESULTS_DIR / f"{latest_feed}-swing.json")
    
    # Create data maps
    electorates_map = {item['electorate']: item for item in googledoc['electorates']}
    places = [item['electorate'] for item in googledoc['electorates']]
    divisions = {item['name']: item for item in latest_data['divisions']}

    # What happens if there are parties not in the party list?
    parties = {item['partyCode'].lower(): item for item in googledoc['partyNames']}
    
    # Process data
    parties_table_data = create_table(latest_data['partyNationalResults'], googledoc['partyNames'], True, coalition_old_primary)
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
        'partiesTableData': parties_table_data,
        'council': { 
            'TOTAL_SEATS': totalSeatsSenate,
            'MAJORITY_SEATS': senateMajority,
            'display': True, 
            'parties': senate_data
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
        latestTimestampStr="20260926_100901", 
        upload=False) 