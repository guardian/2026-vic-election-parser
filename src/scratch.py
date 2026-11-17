#%%

from util import format_xml

format_xml("/Users/nick_evershed/Documents/projects/2026/oct/vic-election-stuff/vic-election-results-parser/data/vec/State Election 2022 - Sample Pack/Phase 1 - Election night (12am)/State2022mediafileverboselh_20221127_000008.xml")


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