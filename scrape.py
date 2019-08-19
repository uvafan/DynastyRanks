from bs4 import BeautifulSoup
from urllib.request import urlopen
import pandas as pd
import numpy as np
from selenium import webdriver

'''
TODO:
- Per-36 value
- Age for players not ranked in HT
'''

def main():
    df = pd.DataFrame(columns=['Name', 
                               'Score',
                               'Age', 
                               'Last_Season_Value', 
                               'Proj_Value',
                               'Hashtag_Rank',
                               'CARMELO_5_YR_Value',
                               'Per_36_Value',
                               'Pos', 
                     ])
    df = load_last_season_ranks(df)
    df = load_proj_ranks(df)
    df = load_hashtag_ranks(df)
    df = load_carmelo_values(df)
    df = get_player_values(df)
    df.to_csv('ranks.csv', index=False)

def load_last_season_ranks(df):
    bbm_df = pd.read_csv('BBM_PlayerRankings.csv', index_col = None)
    df['Name'] = bbm_df['Name']
    df['Last_Season_Value'] = bbm_df['Value']
    bbm_per_36_df = pd.read_csv('BBM_Per36Rankings.csv', index_col = None)
    values = dict()
    for index, row in bbm_per_36_df.iterrows():
        values[row['Name']] = row['Value']
    for index, row in df.iterrows():
        df.loc[index, 'Per_36_Value'] = values[row['Name']]
    df.loc[df.Name == 'Mohamed Bamba', 'Name'] = 'Mo Bamba'
    return df

def clean_name(name, name_set):
    name = name.rstrip()
    if name[:12] == 'Jusuf Nurkic':
        name = name[:12]
    if name == 'DeAndre Ayton':
        name = 'Deandre Ayton'
    name = name.replace('Maurice', 'Moe')
    if not (name in name_set) and name[-2:] == 'Jr':
        name += '.'
    if str.isupper(name[1]):
        name = name[0] + '.' + name[1] + '.' + name[2:]
    if name[-3:] == 'III' and not (name in name_set):
        name = name[:-4]
    if not (name in name_set) and name[-3:] == 'Jr.' and name[:-4] in name_set:
        name = name[:-4]
    return name

def load_proj_ranks(df):
    url = 'https://hashtagbasketball.com/fantasy-basketball-projections'
    soup = BeautifulSoup(urlopen(url),features='lxml')
    name_set = set(df['Name'])
    for tr in soup.findAll('tr')[5:]:
        data = [td.getText() for td in tr.findAll('td')]
        if data[0] == 'R#':
            continue
        name = clean_name(data[1].split('\n')[1], name_set)
        value = float(data[-1].split('\n')[1])
        df.loc[df.Name == name, 'Proj_Value'] = value
        if name not in name_set:
            df = df.append({'Name': name, 'Proj_Value': value}, ignore_index=True)
    return df

def load_hashtag_ranks(df):
    url = 'https://hashtagbasketball.com/fantasy-basketball-dynasty-rankings' 
    soup = BeautifulSoup(urlopen(url),features='lxml')
    name_set = set(df['Name'])
    for tr in soup.findAll('tr')[1:]:
        data = [td.getText() for td in tr.findAll('td')]
        rank = int(data[0].split()[0][1:])
        name = clean_name(data[1].split('\n')[1], name_set)
        age = int(data[2])
        pos = data[4]
        df.loc[df.Name == name, 'Hashtag_Rank'] = rank
        df.loc[df.Name == name, 'Age'] = age
        df.loc[df.Name == name, 'Pos'] = pos
    return df

def carmelo_clean_name(name):
    name = name.rstrip().replace('.','').replace(' ','-').replace("'",'').replace('Moe','Maurice').replace('Shaq', 'Shaquille').replace('Wesley-I', 'Wes-I').lower()
    return name

def load_carmelo_values(df):
    url_base = 'https://projects.fivethirtyeight.com/carmelo' 
    driver = webdriver.Firefox(executable_path = 'C:\geckodriver\geckodriver.exe')
    for index, row in df.iterrows():
        name = carmelo_clean_name(row['Name'])
        url = f'{url_base}/{name}' 
        try:
            driver.get(url)
            html = driver.page_source
            soup = BeautifulSoup(html, 'lxml')
            market_val = soup.find('span', {'class': 'market-value'}).getText()
            _ = market_val[0]
        except:
            url += '-jr'
            try:
                driver.get(url)
                html = driver.page_source
                soup = BeautifulSoup(html, 'lxml')
                market_val = soup.find('span', {'class': 'market-value'}).getText()
                _ = market_val[0]
            except:
                try:
                    url = url[:-3]
                    url += '-iii'
                    driver.get(url)
                    html = driver.page_source
                    soup = BeautifulSoup(html, 'lxml')
                    market_val = soup.find('span', {'class': 'market-value'}).getText()
                    _ = market_val[0]
                except:
                    print(f"Couldn't find page at url {url[:-4]}")
        try:
            if market_val[0] == '-':
                df.loc[index, 'CARMELO_5_YR_Value'] = -float(market_val[2:-1])
            else:
                df.loc[index, 'CARMELO_5_YR_Value'] = float(market_val[1:-1])
            if np.isnan(row['Age']):
                for el in soup.findAll('li', {'class': 'age'}):
                    if 'years' in el.getText():
                        df.loc[index, 'Age'] = int(el.getText()[:2])
        except (IndexError ,ValueError):
            print(f"Couldn't find CARMELO for {row['Name']}")
    return df

def get_score(row):
    rank_score = 218 - row['Hashtag_Rank']
    if np.isnan(rank_score):
        rank_score = 0
    next_season_score = row['Proj_Value'] + row['Last_Season_Value'] * 8
    if np.isnan(row['Proj_Value']):
        next_season_score = row['Last_Season_Value'] * 2
    elif np.isnan(row['Last_Season_Value']):
        next_season_score = row['Proj_Value'] * 2
    if np.isnan(next_season_score):
        next_season_score = 0
    long_term_score = 40 - row['Age'] + row['Per_36_Value'] * 10 + row['CARMELO_5_YR_Value'] * .07
    if np.isnan(row['Per_36_Value']):
        long_term_score = 40 - row['Age'] + row['CARMELO_5_YR_Value'] * .09
    elif np.isnan(row['CARMELO_5_YR_Value']):
        long_term_score = 40 - row['Age'] + row['Per_36_Value'] * 20
    if np.isnan(long_term_score):
        long_term_score = 0
    score = rank_score + next_season_score * 5 + long_term_score * 8
    return score

def get_player_values(df):
    for index, row in df.iterrows():
        df.at[index, 'Score'] = get_score(row) 
    return df.sort_values('Score', ascending = False)

if __name__ == '__main__':
    main()
