import json
import xmltodict
import pandas as pd
from azure.storage.blob import ContainerClient
from downloadBlob import getAndReadFile
import os
from io import BytesIO

# candidate_xml_file = "data/sample-vec-data/round 1 samples (election wkend)/TestState2026MediaFileCandidatesV2.xml"

VEC_TOKEN = os.environ["VEC_RESULTS_SAS"]

with ContainerClient.from_container_url(VEC_TOKEN) as container:
    candidate_data = getAndReadFile(container, "State2026MediaFileCandidatesV2")

candidate_data = xmltodict.parse(BytesIO(candidate_data))

# with open('src/candidate-data.json', 'w') as f:
#     json.dump(candidate_data, f)


# Variables we need in the final CSV
# pp_id - polling place ID 
# pp_type - polling place type
# pp_type_2 - ???
# pp_name - polling place name
# pp_new_indicator - is the polling place new or now
# pp_last_update - timestamp of last update
# district_id - PollingDistrictIdentifie district id (the electorate)
# district_name - electorate name
# district_byelection - ???
# district_byelection_alp_contest - ???
# region_id 
# region_name,
# premises,
# address,
# suburb
# postcode,
# latitude,
# longitude,
# formal_informal_indicator - ????
# candidate,
# candidate_id,
# party_name,
# party_code,
# incumbent,
# retirement,
# vote,
# ballot_order_2022,
# ballot_order_2026,
# number_of_candidates_la_2022,
# number_of_candidates_la_2026,
# enrolment_2026,
# enrolment_2022,
# distirct_turnout_2022,
# district_formal_2022,
# district_informal_2022,
# distirct_turnout_rate_2022,
# district_formal_rate_2022,
# district_informal_rate_2022,
# aec_2025_pp_id,
# alt_2025_pp_site_id

party_abbrev = {
  "Independent": "IND",
  "Liberal Party of Australia - Victorian Division": "LIB",
  "Pauline Hanson's One Nation": "ON",
  "Australian Labor Party - Victorian Branch": "ALP",
  "The Australian Greens - Victoria": "GRN",
  "Family First Victoria": "FFV",
  "Victorian Socialists": "",
  "Shooters, Fishers and Farmers Party Victoria": "SFF",
  "Transport Matters Party": "",
  "Health Australia Party": "HAP",
  "Freedom Party of Victoria": "FPV",
  "The Nationals": "NAT"
}

candidate_results = []

for contest in candidate_data['EML']['CandidateList']['Election'][0]['Contest']:
    contest_id = contest['ContestIdentifier']['@Id']
    contest_name = contest['ContestIdentifier']['ContestName']
    for candidate in contest['Candidate']:
        print(candidate)
        candidate_id = candidate['CandidateIdentifier']['@Id']
        candidate_name = candidate['CandidateIdentifier']['CandidateName']
        
        # Check if independent

        if candidate['@Independent'] == 'yes':
            party_name = 'Independent'
            party_code = None

        else:
            # Raue has this as the party abbreviation - here it is a numeric identifier - suggest we do both
            party_code = candidate['Affiliation']['AffiliationIdentifier']['@Id']
            # party_abbreviation = candidate['Affiliation']['AffiliationIdentifier']['@Abbreviation']
            
            party_name = candidate['Affiliation']['AffiliationIdentifier']['RegisteredName']

        incumbent = candidate['Elected']['@Historic']
        ballot_order_2026 = candidate['BallotPosition']

        candidate_results.append({
            'candidate_id': candidate_id,
            'candidate_name': candidate_name,
            'party_name': party_name,
            'party_code': party_code,
            'incumbent': incumbent,
            'ballot_order_2026': ballot_order_2026,
        })

out_df = pd.DataFrame(candidate_results)

out_df.to_csv('data/candidate-info.csv', index=False, encoding='utf-8')