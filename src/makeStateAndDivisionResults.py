import json
import xmltodict
import boto3
import os
import pandas as pd
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
DATA_DIR = SRC_DIR.parent / "data"

with open(SRC_DIR / "VIC-2022-LA-Primary-Electorate.json") as f:
    results_2022_primary = json.load(f)

with open(SRC_DIR / "VIC-2022-LA-2CP-Electorate.json") as f:
    results_2022_2cp = json.load(f)

with open(DATA_DIR / "party_codes.json") as f:
    party_codes = json.load(f)

# print(results_2022_primary['Albert Park'])

def getOldVotes(candidate, primary_2022):
	result = None
	votes_by_party = {row["party_code"]: row for row in primary_2022}
	votes_by_name = {row["candidate_name"]: row for row in primary_2022}

	if candidate['party_short'] != "IND":
		primary = None
		pct = None
		old_data = votes_by_party.get(candidate['party_short'])

		if old_data is not None:
			primary = old_data['votes']
			pct = old_data['vote_pct']

		if primary is not None:
			result = {
				"votes": primary,
				"vote_pct": pct
			}
			return result
		else:
			return None

	else:
		primary = None
		pct = None
		old_data = votes_by_name.get(candidate['candidate_name'])

		if old_data is not None:
			primary = old_data['votes']
			pct = old_data['vote_pct']

		if primary is not None:
			result = {
				"votes": primary,
				"vote_pct": pct
			}
			return result
		


def eml_to_JSON(eml_file, local, timestamp, uploadPath, upload):
	if local:
		elect_data = xmltodict.parse(open(eml_file, 'rb'))
	else:
		elect_data = xmltodict.parse(eml_file)	

	
	# with open('elec-data.json', 'w') as f:
	# 	json.dump(elect_data, f)
	# The array to store all the PP results

	results_json = {}
	summary_json = {}
	swing_list = []
	electorates_list = []
	primary_vote_by_candidate = []

	stateEnrolment = 0
	stateVotesCounted = 0
	stateVotesCountedPercent = 0

	alp2pp2022 = 55.0
	coalition2pp2022 = 45.0

	# MediaFeed.Election.House.Contests.Contest
	# Loop through each electoral division

	for contest in elect_data['MediaFeed']['Election']['House']['Contests']['Contest']:
		currentElectorate = contest["eml:ContestIdentifier"]["eml:ContestName"].split(" District")[0]
		print("currentElectorate: ", currentElectorate)
		
		# The object for the individual electorate JSON
		electorates_json = {}

		# The object for the swing JSON
		swing_json = {}
		
		
		electorates_json['id'] = contest["eml:ContestIdentifier"]["@Id"]
		electorates_json['district_name'] = contest["eml:ContestIdentifier"]["eml:ContestName"]
		electorates_json['name'] = electorates_json['district_name'].split(" District")[0]
		electorates_json['enrolment'] = contest["Enrolment"]
		
		# Update the state enrolment
		stateEnrolment += int(electorates_json['enrolment'])
		
		# Variable to count up the total votes counted for the electorate
		
		# List to store the candidate results

		candidate_results = []
		
		# Get the candidate-level results for the electorate
		candidates = contest["FirstPreferences"]["Candidate"]
		
		# Sum the total votes counted for the electorate
		electorateVotesCounted = sum([int(candidate["Votes"]) for candidate in candidates])
		
		# Add the total votes counted for the electorate to the electorate JSON
		electorates_json['votesCounted'] = electorateVotesCounted

		print("electorate votes counted: ", electorateVotesCounted)

		primary_2022 = results_2022_primary[currentElectorate]
		twocp_2022 = results_2022_2cp[currentElectorate]


		for candidate in contest["FirstPreferences"]["Candidate"]:
			candidates_row = {}

			candidates_row['candidate_id'] = candidate["eml:CandidateIdentifier"]["@Id"]
			candidates_row['candidate_name'] = candidate["eml:CandidateIdentifier"]["eml:CandidateName"]
			candidates_row['votesTotal'] = int(candidate["Votes"])
			candidates_row['votesPercent'] = int(candidate["Votes"]) / electorateVotesCounted * 100
			# candidates_row['votesPercent'] = candidate["Votes"]["@Percentage"]
			# candidates_row['votesHistoric'] = candidate["Votes"]["@Historic"]
			
			if candidate["@Independent"] == "yes":
				candidates_row['party_short'] = "IND"
				candidates_row['party_long'] = "Independent"
			else:
				candidates_row['party_long'] = candidate["Affiliation"]["eml:AffiliationIdentifier"]["eml:RegisteredName"]
				candidates_row['party_short'] = party_codes[candidates_row['party_long']]["party_code"]
			
			old_results = getOldVotes(candidates_row, primary_2022)
			
			if old_results is not None:
				candidates_row['votesHistoric'] = old_results['votes']
				candidates_row['votesPercentHistoric'] = old_results['vote_pct']
				candidates_row['swing'] = candidates_row['votesPercent'] - old_results['vote_pct']

			else:
				candidates_row['votesHistoric'] = None
				candidates_row['votesPercentHistoric'] = None
				candidates_row['swing'] = None

			candidates_row['id'] = candidate["eml:CandidateIdentifier"]["@Id"]
			candidate_results.append(candidates_row)
		
		
		electorates_json['candidates'] = candidate_results
		electorates_list.append(electorates_json)
		
	results_json['divisions'] = electorates_list	

	newJson = json.dumps(results_json, indent=4)
	# summaryJson = json.dumps(summary_json, indent=4)
	# swingJson = json.dumps(swing_list, indent=4)

	# Save the file locally

	with open('results/{timestamp}.json'.format(timestamp=timestamp),'w') as fileOut:
		print(f"saving {timestamp}.json locally")
		fileOut.write(newJson)	

	# with open('results/{timestamp}-swing.json'.format(timestamp=timestamp),'w') as fileOut:
	# 	print(f"saving {timestamp}-swing.json locally")
	# 	fileOut.write(swingJson)		

	# with open('summaryResults.json','w') as fileOut:
	# 	print("saving summaryResults.json locally")
	# 	fileOut.write(summaryJson)		
	
	# out_df = pd.DataFrame(polling_places)

	# out_df.to_csv('src/candidate-results-pp.csv', index=False)


# VEC test file data/sample-vec-data/round 1 samples (election wkend)/TestState2026mediafileverboselhv2_20260926_100901.xml'
# VEC 2022 file /Users/nick_evershed/Documents/projects/2026/oct/vic-election-stuff/vic-election-results-parser/data/vec/State Election 2022 - Sample Pack/Phase 1 - Election night (12am)/State2022mediafileverboselh_20221127_000008.xml
if __name__ == "__main__":
	print("Running parser")
	eml_to_JSON(eml_file='/Users/nick_evershed/Documents/projects/2026/oct/vic-election-stuff/vic-election-results-parser/data/vec/State Election 2022 - Sample Pack/Phase 1 - Election night (12am)/State2022mediafileverboselh_20221127_000008.xml',
			 local=True,
			 timestamp='20260926_100901', 
			 uploadPath="",
			 upload=False)	