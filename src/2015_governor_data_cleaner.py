import pandas as pd
import numpy as np

#Hinds County totals are conflicting with statewide and need eating to match up with county precinct
#Simpson County totals are conflicting with statewide but match up with county precinct
#Also changes have yet to be applied to individual county files

file_name = '/Users/sammahle/Desktop/election_projects/openelections-data-ms/2015/20151103__ms__general__precinct.csv'
df = pd.read_csv(file_name)

df.district = df.district.fillna('0')
df.votes = df.votes.fillna('0')
df.votes = df.votes.astype(str)
df.votes = df.votes.str.replace(',','')
df.votes = df.votes.str.replace(r'\*','0')
df.votes = df.votes.str.replace('X','0')
df.votes = df.votes.str.replace('x','0')
df.votes = df.votes.apply(pd.to_numeric, errors='coerce')
df.votes = df.votes.astype(float)

df.loc[df.precinct=='600 DE SOTO MS','precinct'] = np.nan
df.loc[df.precinct=='YAZOO MS','precinct'] = np.nan
df.loc[df.precinct=='HOLMES MS','precinct'] = np.nan

df = df.loc[df.precinct!='Total']
df.dropna(subset=['precinct'],inplace=True)

df.loc[(df.county=='Alcorn')&(df.precinct=='College Hill')&(df.candidate=='Phil Bryant'),'votes'] = 303
df.loc[(df.county=='Alcorn')&(df.precinct=='Wenasoga')&(df.candidate=='Phil Bryant'),'votes'] = 466

df.loc[(df.county=='Grenada')&(df.precinct=='Futheyville 1st Pentecost')&(df.candidate=='Robert Gray'),'votes'] = 83
df.loc[(df.county=='Grenada')&(df.precinct=='Geeslin')&(df.candidate=='Robert Gray'),'votes'] = 64
df.loc[(df.county=='Grenada')&(df.precinct=='Gore Springs Comm Center')&(df.candidate=='Robert Gray'),'votes'] = 49
df.loc[(df.county=='Grenada')&(df.precinct=='Holcomb CC')&(df.candidate=='Robert Gray'),'votes'] = 110
df.loc[(df.county=='Grenada')&(df.precinct=='Pleasant Grove Commun Cen')&(df.candidate=='Robert Gray'),'votes'] = 168
df.loc[(df.county=='Grenada')&(df.precinct=='Sweethome Hol #2 Fire Stat')&(df.candidate=='Robert Gray'),'votes'] = 53

df.loc[(df.county=='Grenada')&(df.precinct=='Futheyville 1st Pentecost')&(df.candidate=='Phil Bryant'),'votes'] = 396
df.loc[(df.county=='Grenada')&(df.precinct=='Geeslin')&(df.candidate=='Phil Bryant'),'votes'] = 407
df.loc[(df.county=='Grenada')&(df.precinct=='Gore Springs Comm Center')&(df.candidate=='Phil Bryant'),'votes'] = 276
df.loc[(df.county=='Grenada')&(df.precinct=='Holcomb CC')&(df.candidate=='Phil Bryant'),'votes'] = 397
df.loc[(df.county=='Grenada')&(df.precinct=='Pleasant Grove Commun Cen')&(df.candidate=='Phil Bryant'),'votes'] = 145
df.loc[(df.county=='Grenada')&(df.precinct=='Sweethome Hol #2 Fire Stat')&(df.candidate=='Phil Bryant'),'votes'] = 162

df.loc[(df.county=='Harrison')&(df.precinct=='Long Beach #1')&(df.candidate=='Phil Bryant'),'votes'] = 239
#conflicting vote for below
df.loc[(df.county=='Harrison')&(df.precinct=='Long Beach #1')&(df.candidate=='Robert Gray'),'votes'] = 78

df.loc[(df.county=='Jones')&(df.precinct=='Sand Hill')&(df.candidate=='Phil Bryant'),'votes'] = 428

df.loc[(df.county=='Leflore')&(df.precinct=='Rising Sun')&(df.candidate=='Robert Gray'),'votes'] = 228
df.loc[(df.county=='Leflore')&(df.precinct=='Schlater')&(df.candidate=='Robert Gray'),'votes'] = 51
df.loc[(df.county=='Leflore')&(df.precinct=='South Gwd')&(df.candidate=='Robert Gray'),'votes'] = 169
df.loc[(df.county=='Leflore')&(df.precinct=='South Itta Bena')&(df.candidate=='Robert Gray'),'votes'] = 154
df.loc[(df.county=='Leflore')&(df.precinct=='Southeast Gwd')&(df.candidate=='Robert Gray'),'votes'] = 552
df.loc[(df.county=='Leflore')&(df.precinct=='Southwest Gwd')&(df.candidate=='Robert Gray'),'votes'] = 169
df.loc[(df.county=='Leflore')&(df.precinct=='Swiftown')&(df.candidate=='Robert Gray'),'votes'] = 13
df.loc[(df.county=='Leflore')&(df.precinct=='West Gwd')&(df.candidate=='Robert Gray'),'votes'] = 462

df.loc[(df.county=='Leflore')&(df.precinct=='Rising Sun')&(df.candidate=='Phil Bryant'),'votes'] = 58
df.loc[(df.county=='Leflore')&(df.precinct=='Schlater')&(df.candidate=='Phil Bryant'),'votes'] = 89
df.loc[(df.county=='Leflore')&(df.precinct=='South Gwd')&(df.candidate=='Phil Bryant'),'votes'] = 30
df.loc[(df.county=='Leflore')&(df.precinct=='South Itta Bena')&(df.candidate=='Phil Bryant'),'votes'] = 73
df.loc[(df.county=='Leflore')&(df.precinct=='Southeast Gwd')&(df.candidate=='Phil Bryant'),'votes'] = 236
df.loc[(df.county=='Leflore')&(df.precinct=='Southwest Gwd')&(df.candidate=='Phil Bryant'),'votes'] = 41
df.loc[(df.county=='Leflore')&(df.precinct=='Swiftown')&(df.candidate=='Phil Bryant'),'votes'] = 24
df.loc[(df.county=='Leflore')&(df.precinct=='West Gwd')&(df.candidate=='Phil Bryant'),'votes'] = 153

df.loc[(df.county=='Lincoln')&(df.precinct=='Little Bahala')&(df.candidate=='Phil  Bryant'),'votes'] = 101

df.loc[(df.county=='Marion')&(df.precinct=='Morgantown')&(df.candidate=='Phil Bryant'),'votes'] = 257

df.loc[(df.county=='Monroe')&(df.precinct=='3 Lackey')&(df.candidate=='Phil Bryant'),'votes'] = 406
df.loc[(df.county=='Monroe')&(df.precinct=='4 South Aberdeen')&(df.candidate=='Phil Bryant'),'votes'] = 190

df.loc[(df.county=='Oktibbeha')&(df.precinct=='North Starkville District 3')&(df.candidate=='Phil Bryant'),'votes'] = 529

df = df.append({'county':'Panola','precinct':'Pleasant Mount','office':'Governor','district':'0','candidate':'Phil Bryant','party':'Republican','votes':145},ignore_index=True)
df = df.append({'county':'Panola','precinct':'Pleasant Mount','office':'Governor','district':'0','candidate':'Robert Gray','party':'Democrat','votes':127},ignore_index=True)
df = df.append({'county':'Panola','precinct':'Pleasant Mount','office':'Governor','district':'0','candidate':"Shawn O'Hara",'party':'Reform','votes':4},ignore_index=True)

df.loc[(df.county=='Pearl River')&(df.precinct=='Savannah Beat 3')&(df.candidate=='Phil Bryant'),'votes'] = 202
df.loc[(df.county=='Pearl River')&(df.precinct=='Ozona Beat 3')&(df.candidate=='Robert Gray'),'votes'] = 16

df.loc[(df.county=='Stone')&(df.precinct=='Perkinston')&(df.candidate=='Phil Bryant'),'votes'] = 203

df.loc[(df.county=='Tate')&(df.precinct=='Tyro')&(df.candidate=='Phil Bryant'),'votes'] = 69
df.loc[(df.county=='Tate')&(df.precinct=='Senatobia 1')&(df.candidate=='Phil Bryant'),'votes'] = 796
df.loc[(df.county=='Tate')&(df.precinct=='Senatobia 1')&(df.candidate=='Robert Gray'),'votes'] = 187

df.loc[(df.county=='Walthall')&(df.precinct=='Dexter')&(df.candidate=='Robert Gray'),'votes'] = 62
df.loc[(df.county=='Walthall')&(df.precinct=='West Tylertown')&(df.candidate=='Phil Bryant'),'votes'] = 169

df.loc[(df.county=='Washington')&(df.precinct=='Washington County Convention Center')&(df.candidate=='Phil Bryant'),'votes'] = 186

#Jackson County irregularity addressed below
df.party = df.party.str.replace('Democratic','Democrat',regex=False)

#Rankin County irregularities addressed below
df.party = df.party.str.replace('DEM','Democrat',regex=False)
df.party = df.party.str.replace('REP','Republican',regex=False)
df.loc[(df.candidate=="Shawn O'Hara"),'party'] = 'Reform'
df = df.append({'county':'Rankin','precinct':'Highlands','office':'Governor','district':'0','candidate':'Phil Bryant','party':'Republican','votes':464},ignore_index=True)
df = df.append({'county':'Rankin','precinct':'Highlands','office':'Governor','district':'0','candidate':'Robert Gray','party':'Democrat','votes':182},ignore_index=True)
df = df.append({'county':'Rankin','precinct':'Highlands','office':'Governor','district':'0','candidate':"Shawn O'Hara",'party':'Reform','votes':12},ignore_index=True)

df = df.append({'county':'Rankin','precinct':'Oakdale','office':'Governor','district':'0','candidate':'Phil Bryant','party':'Republican','votes':993},ignore_index=True)
df = df.append({'county':'Rankin','precinct':'Oakdale','office':'Governor','district':'0','candidate':'Robert Gray','party':'Democrat','votes':226},ignore_index=True)
df = df.append({'county':'Rankin','precinct':'Oakdale','office':'Governor','district':'0','candidate':"Shawn O'Hara",'party':'Reform','votes':16},ignore_index=True)

#These counties flipped Bryants and Grays votes
for county in ['Clay','Covington','Lafayette']:
	df.loc[(df.county==county)&(df.candidate=='Phil Bryant'),'party'] = 'Democrat'
	df.loc[(df.county==county)&(df.candidate=='Robert Gray'),'party'] = 'Republican'
	df.loc[(df.county==county)&(df.candidate=='Phil Bryant')&(df.party=='Democrat'),'candidate'] = 'Robert Gray'
	df.loc[(df.county==county)&(df.candidate=='Robert Gray')&(df.party=='Republican'),'candidate'] = 'Phil Bryant'

#Simpson County irregularities addressed below
df.candidate = df.candidate.str.replace('Time Johnson','Tim Johnson',regex=False)
df.candidate = df.candidate.str.replace('Rober Gray','Robert Gray',regex=False)
df.candidate = df.candidate.str.replace('Phill Bryant','Phil Bryant',regex=False)
df.loc[(df.candidate=='Tate Reeves'),'office'] = 'Lieutenant Governor'
df.loc[(df.candidate=='Tim Johnson'),'office'] = 'Lieutenant Governor'

df.district = df.district.replace(r'0',np.nan)

df = df.sort_values(by=['county','office','candidate','district'])
df = df.set_index('county')

df.to_csv('/Users/sammahle/Desktop/election_projects/openelections-data-ms/2015/20151103__ms__general__precinct.csv')


