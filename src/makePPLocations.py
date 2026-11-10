# A script to turn the polling places XML file into a simple CSV that can be merged with the results CSV

import json
import xmltodict
import pandas as pd
import os
from azure.storage.blob import ContainerClient
from downloadBlob import getAndReadFile
from io import BytesIO

# pp_location_xml_file = "data/sample-vec-data/round 1 samples (election wkend)/TestState2026MediaFilePollingLocationsV2.xml"

VEC_TOKEN = os.environ["VEC_RESULTS_SAS"]

with ContainerClient.from_container_url(VEC_TOKEN) as container:
    pp_location_data = getAndReadFile(container, "State2026MediaFilePollingLocationsV2")

pp_location_data = xmltodict.parse(BytesIO(pp_location_data))

pp_data = []

# Variables we need in the final CSV
# pp_id - polling place ID 
# pp_type - polling place type
# pp_type_2 - ???
# pp_name - polling place name
# pp_new_indicator - is the polling place new or now
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
# formal_informal_indicator,
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
# enrolment_2026,enrolment_2022,
# distirct_turnout_2022,
# district_formal_2022,
# district_informal_2022,
# distirct_turnout_rate_2022,
# district_formal_rate_2022,
# district_informal_rate_2022,
# aec_2025_pp_id,
# alt_2025_pp_site_id


for district in pp_location_data['PollingDistrictList']['PollingDistrict']:
    
    district_id = district['PollingDistrictIdentifier']['@Id']
    district_name = district['PollingDistrictIdentifier']['Name']

    for PollingPlace in district['PollingPlaces']['PollingPlace']:
        pp_id = PollingPlace['PollingPlaceIdentifier']['@Id']
        pp_name = PollingPlace['PollingPlaceIdentifier']['@Name']
        pp_type = PollingPlace['PollingPlaceIdentifier']['@Classification']
        # pp_type_2 = PollingPlace['PollingPlaceIdentifier']['@Type']
        pp_address = PollingPlace['Address']['AddressLine1']
        pp_suburb = PollingPlace['Address']['Suburb']
        pp_postcode = PollingPlace['Address']['Postcode']
        latitude = PollingPlace['Address']['AddressLatitude']
        longitude = PollingPlace['Address']['AddressLongitude']
        pp_data.append(
        {
            'pp_id': pp_id,
            'pp_name': pp_name,
            'pp_type': pp_type,
            'address': pp_address,
            'suburb': pp_suburb,
            'latitude': latitude,
            'longitude': longitude,
            'postcode': pp_postcode,
            'district_id': district_id,
            'district_name': district_name,
  
        })


out_df = pd.DataFrame(pp_data)
out_df.to_csv('data/pp-data.csv', index=False)

# with open('pp-data.json', 'w') as f:
#     json.dump(pp_location_data, f)

# print(pp_location_data)