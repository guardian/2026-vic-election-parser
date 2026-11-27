#%%

from util import format_xml

format_xml("/Users/nick_evershed/Documents/projects/2026/oct/vic-election-stuff/vic-election-results-parser/data/test-2022/State2022mediafileverboselh_20221215_180017.xml")

#%% make party name dict files

import pandas as pd
import json

df = pd.read_csv('../data/party_codes.csv')
print(df.head())

by_code = {}
by_name = {}

for index, row in df.iterrows():
    by_code[row['party_code']] = row.to_dict()
    by_name[row['party_name']] = row.to_dict()

with open('../data/party_codes_by_name.json', 'w') as f:
    json.dump(by_name, f, indent=2)

with open('../data/party_codes_by_code.json', 'w') as f:
    json.dump(by_code, f, indent=2)

#%% Conver Raue files to json

# 2CP
import pandas as pd
import json

df = pd.read_excel("/Users/nick_evershed/Documents/projects/2026/oct/vic-election-stuff/vic-election-results-parser/data/raue/VIC-2022/VIC-2022-LA-2CP-Electorate.xlsx", sheet_name="Sheet1")
print(df.head())

district_votes = df.groupby("district_name")["votes"].transform("sum")
df["vote_pct"] = df["votes"] / district_votes * 100
df["vote_pct"] = df["vote_pct"].round(2)
records = json.loads(df.to_json(orient="records"))
by_district = {}

for row in records:
    district = row.pop("district_name")
    by_district.setdefault(district, []).append(row)

with open("VIC-2022-LA-2CP-Electorate.json", "w") as f:
    json.dump(by_district, f, indent=2)

print(json.dumps({"Albert Park": by_district["Albert Park"]}, indent=2))

#%% Primary vote
import pandas as pd
import json

df = pd.read_excel("/Users/nick_evershed/Documents/projects/2026/oct/vic-election-stuff/vic-election-results-parser/data/raue/VIC-2022/VIC-2022-LA-Primary-Electorate.xlsx", sheet_name="Sheet1")
print(df.head())

df = df[df['candidate_name'] != "Informal"]
district_votes = df.groupby("district_name")["votes"].transform("sum")
df["vote_pct"] = df["votes"] / district_votes * 100
df["vote_pct"] = df["vote_pct"].round(2)

df.to_csv("VIC-2022-LA-Primary-Electorate.csv", index=False)
# print(df[["district_name", "candidate_name", "votes", "vote_pct"]].head())

records = json.loads(df.to_json(orient="records"))
by_district = {}
for row in records:
    district = row.pop("district_name")
    by_district.setdefault(district, []).append(row)


with open("VIC-2022-LA-Primary-Electorate.json", "w") as f:
    json.dump(by_district, f, indent=2)

print(json.dumps({"Albert Park": by_district["Albert Park"]}, indent=2))


#%%

import json

with open("/Users/nick_evershed/Documents/projects/2026/oct/vic-election-stuff/vic-election-results-parser/data/vec/State Election 2022 - Sample Pack/Phase 1 - Election night (12am)/State2022mediafileverboselh_20221127_000008.json", "r") as f:
    data = json.load(f)

#%%

import pandas as pd
import json

with open("../results/20221215_180017.json", "r") as f:
    data = json.load(f)

df = pd.DataFrame(data['partyNationalResults'])

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


# parties_to_name = []
# Fields we need:
# { "party": "Labor party", "votesPercent": 37.03, "votes": 1339496, "swing": 0.38 }

results_df = results_df.rename(columns={'shortName': 'party', 'votesTotal': 'votes'})
results_df = results_df[['party', 'votes', 'votesPercent', 'swing']]
results_df = results_df.sort_values(by='votes', ascending=False)

#%%

import requests
import pandas as pd
from pathlib import Path
import json

SRC_DIR = Path(__file__).resolve().parent
DATA_DIR = SRC_DIR.parent / "data"
print(DATA_DIR)
with open(DATA_DIR / "party_codes_by_code.json") as f:
    party_names_by_code = json.load(f)

googledoc_key = "1k0_d-Og6sWr3BYz1Hw3Sz9eA98IRuvccm3r6xaA7U7s"
googledoc = requests.get(f"https://interactive.guim.co.uk/docsdata/{googledoc_key}.json").json()['sheets']

# Set up constants
key = 'upperhouse'
party_field = 'party'

# Filter out records with an empty party field
has_data = [d for d in googledoc[key] if d[party_field]]

df = pd.DataFrame(has_data)
print(df.head())
df['count'] = 1


parties_df = df[['party','count']].groupby('party').sum().reset_index()
parties_df = parties_df.sort_values(by='count', ascending=False)

parties_df['name'] = parties_df['party'].map(party_names_by_code).apply(lambda party: party['short_name'])

# parties_to_name = ['ALP', 'LIB', 'NAT', 'ON', 'GRN']

# #%%
# def make_others(row):
#     if row['party'] in parties_to_name:
#         return row['name']
#     else:
#         return 'Other'

parties_gp = parties_df[['party', 'name', 'count']].groupby(['party', 'name']).sum().reset_index()
parties_gp = parties_gp.rename(columns={'party':'key', 'count':'seats'})
parties_gp = parties_gp.sort_values(by='seats', ascending=False)
parties_gp['key'] = parties_gp['key'].str.lower()

#%% Do seats by region

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
print(regions_gp.to_dict(orient='records'))


