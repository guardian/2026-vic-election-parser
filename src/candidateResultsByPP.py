import json
import xmltodict
import boto3
import os
import pandas as pd
try:
	from util import upload_to_s3
except ImportError:
	from src.util import upload_to_s3

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


def getPollingPlaceResults(eml_file, testing, local, timestamp, uploadPath, upload):
	if testing:
		print("Testing mode enabled")
	else:
		print("Testing mode disabled")

	print("Getting polling place results...")
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
		# Check if polling places have started reporting yet
		# print(contest['PollingPlaces'])

		if contest['PollingPlaces'] is not None:
			for pp in contest['PollingPlaces']['PollingPlace']:
				pp_id = int(pp['PollingPlaceIdentifier']['@Id'])
				pp_name = pp['PollingPlaceIdentifier']['@Name']
				if '@Classification' in pp['PollingPlaceIdentifier']:
					pp_type = pp['PollingPlaceIdentifier']['@Classification']
				else:
					pp_type = None
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
		else:
			print(f"No polling places found for contest {contest['eml:ContestIdentifier']['eml:ContestName']}")
			continue

	if len(candidate_results) == 0:
		print("No results yet")
	else:	
		candidate_df = pd.DataFrame(candidate_results)

		if testing:
			candidate_info = pd.read_csv('data/candidate-info-2022.csv')
		else:
			candidate_info = pd.read_csv('data/candidate-info.csv')

		if testing:
			pp_info = pd.read_csv('data/pp-data-2022.csv')
		else:
			pp_info = pd.read_csv('data/pp-data.csv')

		pp_info = pp_info[['pp_id', 'address', 'suburb', 'latitude', 'longitude', 'postcode']]

		merged_df = pd.merge(candidate_df, candidate_info, on='candidate_id', how='left')
		merged_df = pd.merge(merged_df, pp_info, on='pp_id', how='left')
		
		merged_df.to_csv('results/candidate-results-pp.csv', index=False)

		if upload:
			if uploadPath != "":
				upload_to_s3(
					dest=f"{uploadPath}/candidate-results-pp.csv", 
					buffer=merged_df.to_csv(index=False).encode('utf-8'),
					content_type='text/csv'
					)
	# out_df = pd.DataFrame(polling_places)

	# out_df.to_csv('src/candidate-results-pp.csv', index=False)

if __name__ == "__main__":
	print("Running parser")
	getPollingPlaceResults(eml_file='data/sample-vec-data/round 1 samples (election wkend)/TestState2026mediafileverboselhv2_20260926_100901.xml',
			 local=True,
			 timestamp='20260926_100901', 
			 uploadPath="2026/11/aus-vic-election/results-data",
			 upload=True)	