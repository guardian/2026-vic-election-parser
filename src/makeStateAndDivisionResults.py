import json
import xmltodict
import boto3
import os
import pandas as pd
from pathlib import Path
import copy

SRC_DIR = Path(__file__).resolve().parent
DATA_DIR = SRC_DIR.parent / "data"

AWS_KEY = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET = os.environ['AWS_SECRET_ACCESS_KEY']

if 'AWS_SESSION_TOKEN' in os.environ:
	AWS_SESSION = os.environ['AWS_SESSION_TOKEN']

with open(SRC_DIR / "VIC-2022-LA-Primary-Electorate.json") as f:
    results_2022_primary = json.load(f)

with open(SRC_DIR / "VIC-2022-LA-2CP-Electorate.json") as f:
    results_2022_2cp = json.load(f)

with open(DATA_DIR / "party_codes_by_name.json") as f:
    party_codes_by_name = json.load(f)

with open(DATA_DIR / "party_codes_by_code.json") as f:
    party_codes_by_code = json.load(f)

# print(results_2022_primary['Albert Park'])

def getOldVotes(candidate, primary_2022):
	result = None
	votes_by_party = {row["party_code"]: row for row in primary_2022}
	votes_by_name = {row["candidate_name"]: row for row in primary_2022}

	# If it's not an independent, use the party code

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

	# If it's an independent, use the name

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

def getOldTwoCPVotes(twoCP, twocp_2022):
	result = None
	votes_by_party = {row["party_code"]: row for row in twocp_2022}
	votes_by_name = {row["candidate_name"]: row for row in twocp_2022}

	# If it's not independent, use the party code

	if twoCP['party_short'] != "IND":
		votes_2cp = None
		pct = None
		old_data = votes_by_party.get(twoCP['party_short'])	

		if old_data is not None:
			votes_2cp = old_data['votes']
			pct = old_data['vote_pct']

		if votes_2cp is not None:
			result = {
				"votes": votes_2cp,
				"vote_pct": pct
			}
			return result
		else:
			return None

	# If it's an indie, use the name

	else:
		votes_2cp = None
		pct = None

		old_data = votes_by_name.get(twoCP['candidate_name'])

		if old_data is not None:
			votes_2cp = old_data['votes']
			pct = old_data['vote_pct']

		if votes_2cp is not None:
			result = {
				"votes": votes_2cp,
				"vote_pct": pct
			}
			return result
		else:
			return None


def getCurrentTwoCandidates(contest, currentCandidateInfo):

	twoPPCandidate1 = contest["TwoCandidatePreferred"]['Candidate'][0]["eml:CandidateIdentifier"]["@Id"]
	twoPPCandidate2 = contest["TwoCandidatePreferred"]['Candidate'][1]["eml:CandidateIdentifier"]["@Id"]
	candidate1 = currentCandidateInfo[twoPPCandidate1]['party_short']
	candidate2 = currentCandidateInfo[twoPPCandidate2]['party_short']

	# If they're independent, use their name instead
	if candidate1 == "IND":
		candidate1 = currentCandidateInfo[twoPPCandidate1]['candidate_name']
	if candidate2 == "IND":
		candidate2 = currentCandidateInfo[twoPPCandidate2]['candidate_name']

	return [candidate1, candidate2]

def getOldTwoCandidates(contest, twocp_2022):
	twoPPCandidate1 = contest["TwoCandidatePreferred"]['Candidate'][0]["eml:CandidateIdentifier"]["@Id"]
	twoPPCandidate2 = contest["TwoCandidatePreferred"]['Candidate'][1]["eml:CandidateIdentifier"]["@Id"]
	candidate1 = twocp_2022[0]['party_code']
	candidate2 = twocp_2022[1]['party_code']

	# If they're independent, use their name instead
	if candidate1 == "IND":
		candidate1 = twocp_2022[0]['candidate_name']
	if candidate2 == "IND":
		candidate2 = twocp_2022[1]['candidate_name']
	return [candidate1, candidate2]


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
	stateVotesCountedFormal = 0
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
		
		
		electorates_json['id'] = contest["PollingDistrictIdentifier"]["@Id"]
		electorates_json['district_name'] = contest["PollingDistrictIdentifier"]["Name"]
		electorates_json['name'] = electorates_json['district_name'].split(" District")[0]
		electorates_json['enrolment'] = int(contest["Enrolment"])
		
		# Update the state enrolment
		stateEnrolment += int(electorates_json['enrolment'])
		
		# Variable to count up the total votes counted for the electorate
		
		# List to store the candidate results

		candidate_results = []
		
		# Get the candidate-level results for the electorate

		candidates = contest["FirstPreferences"]["Candidate"]
		
		# Sum the total votes counted for the electorate

		# electorateVotesCounted = sum([int(candidate["Votes"]) for candidate in candidates])
		
		electorateVotesCountedFormal = int(contest["FirstPreferences"]['Formal']['Votes'])

		electorateVotesCountedTotal = int(contest["FirstPreferences"]['Total']['Votes'])


		# Update the state votes counted
		stateVotesCounted += electorateVotesCountedTotal
		stateVotesCountedFormal += electorateVotesCountedFormal

		# Add the total votes counted for the electorate to the electorate JSON
		electorates_json['votesCounted'] = electorateVotesCountedTotal 

		print("electorate votes counted: ", electorateVotesCountedTotal )

		primary_2022 = results_2022_primary[currentElectorate]
		twocp_2022 = results_2022_2cp[currentElectorate]

		currentCandidateInfo = {}

		for candidate in contest["FirstPreferences"]["Candidate"]:
			candidates_row = {}

			candidates_row['candidate_id'] = candidate["eml:CandidateIdentifier"]["@Id"]
			candidates_row['candidate_name'] = candidate["eml:CandidateIdentifier"]["eml:CandidateName"]
			candidates_row['votesTotal'] = int(candidate["Votes"])
			if electorateVotesCountedFormal > 0:
				candidates_row['votesPercent'] = int(candidate["Votes"]) / electorateVotesCountedFormal * 100
			else:
				candidates_row['votesPercent'] = 0
			# candidates_row['votesPercent'] = candidate["Votes"]["@Percentage"]
			# candidates_row['votesHistoric'] = candidate["Votes"]["@Historic"]
			
			if candidate["@Independent"] == "yes":
				candidates_row['party_short'] = "IND"
				candidates_row['party_long'] = "Independent"
			else:
				candidates_row['party_long'] = candidate["Affiliation"]["eml:AffiliationIdentifier"]["eml:RegisteredName"]
				party_names = party_codes_by_name.get(candidates_row['party_long']) or {}
				candidates_row['party_short'] = party_names.get("party_code", candidates_row['party_long'])
			
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
			currentCandidateInfo[candidates_row['id']] = candidates_row
			candidate_results.append(candidates_row)
			flat_candidate_results_row = copy.deepcopy(candidates_row)
			flat_candidate_results_row['id'] = electorates_json['id']
			flat_candidate_results_row['district_name'] = electorates_json['district_name']
			flat_candidate_results_row['name'] = electorates_json['name']
			flat_candidate_results_row['enrolment'] = electorates_json['enrolment']
			primary_vote_by_candidate.append(flat_candidate_results_row)
		
		
		electorates_json['candidates'] = candidate_results
		electorates_list.append(electorates_json)

		# Check if 2cp count exists

		if "TwoCandidatePreferred" in contest:

			# Check if maverick

			maverick_status = False
			
			if "@Maverick" in contest["TwoCandidatePreferred"]:
				if contest["TwoCandidatePreferred"]["@Maverick"] == "true":
					maverick_status = True

			electorates_json["tcpCountProgress"] = f"{contest["TwoCandidatePreferred"]["@PollingPlacesReturned"]} / {contest["TwoCandidatePreferred"]["@PollingPlacesExpected"]}"
			electorates_json["maverick"] = maverick_status

			currentPartyPair = getCurrentTwoCandidates(contest, currentCandidateInfo)
			oldPartyPair = getOldTwoCandidates(contest, twocp_2022)

			pairingsMatch = False

			if set(currentPartyPair) == set(oldPartyPair):
				pairingsMatch = True

			# print("currentPartyPair: ", currentPartyPair)
			# print("oldPartyPair: ", oldPartyPair)
			# print("pairingsMatch: ", pairingsMatch)

			twoCPResults = []

			for twoCP in contest["TwoCandidatePreferred"]['Candidate']:

				twoCPResultsRow = {}

				twoCPResultsRow['candidate_id'] = twoCP["eml:CandidateIdentifier"]["@Id"]
				twoCPResultsRow['candidate_name'] = twoCP["eml:CandidateIdentifier"]["eml:CandidateName"]
				twoCPResultsRow['votesTotal'] = int(twoCP["Votes"])
				twoCPResultsRow['votesPercent'] = int(twoCP["Votes"]) / electorateVotesCountedFormal * 100
				twoCPResultsRow['party_short'] = currentCandidateInfo[twoCPResultsRow['candidate_id']]['party_short']
				twoCPResultsRow['party_long'] = currentCandidateInfo[twoCPResultsRow['candidate_id']]["party_long"]
				

				if pairingsMatch:
					old_results = getOldTwoCPVotes(twoCPResultsRow, twocp_2022)
					if old_results is not None:
						twoCPResultsRow['votesPercentHistoric'] = old_results['vote_pct']
						twoCPResultsRow['swing'] = twoCPResultsRow['votesPercent'] - old_results['vote_pct']
					else:
						twoCPResultsRow['votesPercentHistoric'] = None
						twoCPResultsRow['swing'] = None
				else:
					twoCPResultsRow['votesPercentHistoric'] = None
					twoCPResultsRow['swing'] = None

				twoCPResults.append(twoCPResultsRow)
			
			electorates_json["twoCandidatePreferred"] = twoCPResults
		
		# Otherwise set it all to none
		
		else:
			electorates_json["twoCandidatePreferred"] = None


	# Statewid summary of primary votes by party

	primary_vote_by_candidate_df = pd.DataFrame(primary_vote_by_candidate)
	
	# Output for testing purposes only, remove later

	primary_vote_by_candidate_df.to_csv('src/primary-vote-by-candidate.csv', index=False)

	# candidate_id,candidate_name,votesTotal,votesPercent,party_short,party_long,votesHistoric,votesPercentHistoric,swing,id,district_name,name,enrolment

	# {
    #         "partygroup_id": 4,
    #         "partygroup_name": "Liberal",
    #         "coalition_short": "LP",
    #         "votesTotal": 3502713,
    #         "votesPercent": 23.89,
    #         "swing": -4.28
    #     },

	vote_by_party = primary_vote_by_candidate_df[['party_short','votesTotal']].groupby('party_short').sum()
	vote_by_party['votesPercent'] = vote_by_party['votesTotal'] / primary_vote_by_candidate_df['votesTotal'].sum() * 100
	vote_by_party = vote_by_party.reset_index()
	vote_by_party['partygroup_name'] = vote_by_party['party_short'].map(party_codes_by_code).apply(lambda x: x['party_name'])
	vote_by_party['shortName'] = vote_by_party['party_short'].map(party_codes_by_code).apply(lambda x: x['short_name'])

	vote_by_party = vote_by_party.rename(columns={'party_short': 'coalition_short'})

	old_vote_by_candidate_df = pd.read_csv('src/VIC-2022-LA-Primary-Electorate.csv')

	old_vote_by_party = old_vote_by_candidate_df[['party_code','votes']].groupby('party_code').sum()
	old_vote_by_party['votesPercentOld'] = old_vote_by_party['votes'] / old_vote_by_candidate_df['votes'].sum() * 100
	old_vote_by_party = old_vote_by_party.reset_index()
	old_vote_by_party = old_vote_by_party.rename(columns={'party_code': 'coalition_short'})
	
	# Merge with current vote by party df so we can calculate the swing

	merged_vote_by_party = pd.merge(vote_by_party, old_vote_by_party[['coalition_short', 'votesPercentOld']], on='coalition_short', how='left')
	merged_vote_by_party['swing'] = merged_vote_by_party['votesPercent'] - merged_vote_by_party['votesPercentOld']
	merged_vote_by_party['swing'] = merged_vote_by_party['swing'].round(2)
	merged_vote_by_party['votesPercent'] = merged_vote_by_party['votesPercent'].round(2)

	# CSV output for testing

	# merged_vote_by_party.to_csv('src/merged-vote-by-party.csv', index=False)
	# vote_by_party.to_csv('src/vote-by-party.csv', index=False)

	summary_json['enrollment'] = stateEnrolment
	summary_json['votesCountedPercent'] = round(stateVotesCounted / stateEnrolment * 100, 2)
	summary_json['votesCounted'] = stateVotesCounted

	results_json["enrollment"] = stateEnrolment
	results_json["votesCounted"] = stateVotesCounted
	results_json["votesCountedFormal"] = stateVotesCountedFormal
	results_json["votesCountedPercent"] = round(stateVotesCounted / stateEnrolment * 100, 2)
	results_json["partyNationalResults"] = merged_vote_by_party.to_dict(orient='records')
	results_json['divisions'] = electorates_list	

	print("TOTAL VOTES", stateVotesCounted)

	newJson = json.dumps(results_json, indent=4)

	summaryJson = json.dumps(summary_json, indent=4)
	# swingJson = json.dumps(swing_list, indent=4)

	# Save the file locally

	with open('results/{timestamp}.json'.format(timestamp=timestamp),'w') as fileOut:
		print(f"saving {timestamp}.json locally")
		fileOut.write(newJson)	

	# with open('results/{timestamp}-swing.json'.format(timestamp=timestamp),'w') as fileOut:
	# 	print(f"saving {timestamp}-swing.json locally")
	# 	fileOut.write(swingJson)		

	with open('results/summaryResults.json','w') as fileOut:
		print("saving summaryResults.json locally")
		fileOut.write(summaryJson)		
	
	# out_df = pd.DataFrame(polling_places)

	# out_df.to_csv('src/candidate-results-pp.csv', index=False)

	# Upload the results to S3		

	if upload:
		print("Connecting to S3")

		bucket = 'gdn-cdn'

		if 'AWS_SESSION_TOKEN' in os.environ:
			session = boto3.Session(
			aws_access_key_id=AWS_KEY,
			aws_secret_access_key=AWS_SECRET,
			aws_session_token = AWS_SESSION
			)
		else:
			session = boto3.Session(
			aws_access_key_id=AWS_KEY,
			aws_secret_access_key=AWS_SECRET,
			)
		
		s3 = session.resource('s3')	
		
		key = f"{uploadPath}/{timestamp}.json"
		object = s3.Object(bucket, key)
		object.put(Body=newJson, CacheControl="max-age=60", ACL='public-read', ContentType="application/json")
		print("Uploaded:", f"https://interactive.guim.co.uk/{key}")

		key2 = f"{uploadPath}/summaryResults.json"	
		object = s3.Object(bucket, key2)
		object.put(Body=summaryJson, CacheControl="max-age=60", ACL='public-read', ContentType="application/json")
		print("Uploaded:", f"https://interactive.guim.co.uk/{key2}")

		# key3 = f"{uploadPath}/{timestamp}-swing.json"
		# object = s3.Object(bucket, key3)
		# object.put(Body=swingJson, CacheControl="max-age=60", ACL='public-read', ContentType="application/json")
		# print("Uploaded:", f"https://interactive.guim.co.uk/{key3}")

		print("Done, JSON is uploaded")

	else:
		print("Results not uploaded, uploading switched off")


VEC_2026_TEST_FILE = "data/sample-vec-data/round 1 samples (election wkend)/TestState2026mediafileverboselhv2_20260926_100901.xml"
VEC_2022_XML_FILE_ELEC_NIGHT = "/Users/nick_evershed/Documents/projects/2026/oct/vic-election-stuff/vic-election-results-parser/data/vec/State Election 2022 - Sample Pack/Phase 1 - Election night (12am)/State2022mediafileverboselh_20221127_000008.xml"
VEC_2022_XML_FILE_DECLARED = "/Users/nick_evershed/Documents/projects/2026/oct/vic-election-stuff/vic-election-results-parser/data/vec/State Election 2022 - Sample Pack/Phase 4 - Week following (declarations done)/State2022mediafileverboselh_20221215_180017.xml"


if __name__ == "__main__":
	print("Running parser")
	eml_to_JSON(eml_file=VEC_2022_XML_FILE_DECLARED,
			 local=True,
			 timestamp='20221215_180017', 
			 uploadPath="2026/11/aus-vic-election/results-data",
			 upload=True)	