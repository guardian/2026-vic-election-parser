import json
import xmltodict
import boto3
import os
import pandas as pd

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


def eml_to_JSON(eml_file, local, timestamp, uploadPath, upload):
	if local:
		elect_data = xmltodict.parse(open(eml_file, 'rb'))
	else:
		elect_data = xmltodict.parse(eml_file)	

	
	# with open('elec-data.json', 'w') as f:
	# 	json.dump(elect_data, f)
	# The array to store all the PP results

	candidate_results = []

	contests = elect_data['MediaFeed']['Election']['House']['Contests']['Contest']
	# print(contests)
	for contest in contests:
		# MediaFeed.Election.House.Contests.Contest[0].PollingDistrictIdentifier["@Id"]

		# District-level results stuff

		district_id = contest['PollingDistrictIdentifier']['@Id']
		district_name = contest['PollingDistrictIdentifier']['Name']
		enrolment_2026 = contest['Enrolment']
		print(district_name)
		# PP level stuff 

		for pp in contest['PollingPlaces']['PollingPlace']:
			pp_id = int(pp['PollingPlaceIdentifier']['@Id'])
			pp_name = pp['PollingPlaceIdentifier']['@Name']
			pp_type = pp['PollingPlaceIdentifier']['@Classification']
			pp_last_update = pp['@Updated']
			print(pp_name)
			for candidate in pp['FirstPreferences']['Candidate']:
				candidate_id = int(candidate['eml:CandidateIdentifier']['@Id'])
				votes = candidate['Votes']

				candidate_results.append({
					'candidate_id': candidate_id,
					'votes': votes,
					'pp_id': pp_id,
					'pp_name': pp_name,
					'pp_type': pp_type,
					'pp_last_update': pp_last_update,
					'district_id': district_id,
					'district_name': district_name,
					'enrolment_2026': enrolment_2026,
				})
	
	candidate_df = pd.DataFrame(candidate_results)
	
	candidate_info = pd.read_csv('src/candidate-info.csv')

	pp_info = pd.read_csv('src/pp-data.csv')
	pp_info = pp_info[['pp_id', 'address', 'suburb', 'latitude', 'longitude', 'postcode']]

	merged_df = pd.merge(candidate_df, candidate_info, on='candidate_id', how='left')
	merged_df = pd.merge(merged_df, pp_info, on='pp_id', how='left')
	merged_df.to_csv('src/candidate-results-pp.csv', index=False)

	# out_df = pd.DataFrame(polling_places)

	# out_df.to_csv('src/candidate-results-pp.csv', index=False)

if __name__ == "__main__":
	print("Running parser")
	eml_to_JSON(eml_file='data/sample-vec-data/round 1 samples (election wkend)/TestState2026mediafileverboselhv2_20260926_100901.xml',
			 local=True,
			 timestamp='20260926_100901', 
			 uploadPath="",
			 upload=False)	