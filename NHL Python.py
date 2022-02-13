import pandas as pd
import requests
import json
from io import StringIO
import statistics
from scipy.stats import poisson
import numpy as np
from openpyxl import load_workbook
from datetime import date 

#player basis
def player_data(team1, team2):
    response = requests.get("https://moneypuck.com/moneypuck/playerData/seasonSummary/2021/regular/skaters.csv")
    s=str(response.content,'utf-8')

    data = StringIO(s) 

    df=pd.read_csv(data)
    df = df[(df['team'] == team1) | (df['team'] == team2)]
    #df['icetime_per'] = df['icetime'] / (df['games_played'] * 60 * 60)
    df['icetime_per'] = df['icetime'] / (df['timeOnBench'] + df['icetime']) 
    df['shots_per_min'] = ((df['I_F_shotAttempts'] - df['I_F_rebounds']) / (df['icetime']/60)) * df['icetime_per']
    df['blocks_per_min'] = (df['shotsBlockedByPlayer'] / (df['icetime']/60)) * df['icetime_per'] 
    df['misses_per_min'] = (df['I_F_missedShots'] / (df['icetime']/60)) * df['icetime_per'] 
    df['rebshots_per_min'] = (df['I_F_rebounds'] / (df['icetime']/60)) * df['icetime_per'] 
    df['rebgoals_per_min'] = (df['I_F_reboundGoals'] / (df['icetime']/60)) * df['icetime_per'] 
    
    #sort by team and ice time wieght
    df = df.sort_values(by=['team','icetime'],ascending=False)
    #cut to when full strength
    all_scen = df[df['situation'] == 'all'] 
    full_strength = df[df['situation'] == '5on5']
    man_adv = df[df['situation'] == '5on4']
    short_handed = df[df['situation'] == '4on5']
    return full_strength, man_adv, short_handed, all_scen 

def ByPlayerGameAnalysis(team1,team2):
    
    full_strength, man_adv, short_handed, all_scen = player_data(team1,team2)
    #create empty df to fill
    df = pd.DataFrame(columns = ['team','fs_shots', 'ma_shots', 'sh_shots', 'fs_blocked_shots','ma_blocked_shots','sh_blocked_shots','fs_missed_shots','ma_missed_shots','sh_missed_shots','fs_reb_goals','ma_reb_goals','sh_reb_goals','pen_taken','pen_drawn'], 
                   index = ['Team1', 'Team2'])
 
    
    
    teams = [team1,team2]
    count = 1
    for i in teams:
    #team 1 anaylsis
        #cut to just one team 
        fs_tm = full_strength[full_strength['team'] == i]
        ma_tm = man_adv[man_adv['team'] == i]
        sh_tm = short_handed[short_handed['team'] == i]
        as_tm = all_scen[all_scen['team'] == i] 
        
        #sort again to be sure
        fs_tm = fs_tm.sort_values(by=['icetime'],ascending=False)
        ma_tm = ma_tm.sort_values(by=['icetime'],ascending=False)
        sh_tm = sh_tm.sort_values(by=['icetime'],ascending=False)
        as_tm = as_tm.sort_values(by=['icetime'],ascending=False)
        
        #shots in all scenerios 
        fs_shots = fs_tm['shots_per_min'].iloc[0:18].sum()
        ma_shots = ma_tm['shots_per_min'].iloc[0:18].sum()
        sh_shots = sh_tm['shots_per_min'].iloc[0:18].sum()
        
        #blocked shots in all scenerios
        fs_blocked_shots = fs_tm['blocks_per_min'].iloc[0:18].sum()
        ma_blocked_shots = ma_tm['blocks_per_min'].iloc[0:18].sum()
        sh_blocked_shots = sh_tm['blocks_per_min'].iloc[0:18].sum()
        
        #Missed shots in all scenerios
        fs_missed_shots = fs_tm['misses_per_min'].iloc[0:18].sum()
        ma_missed_shots = ma_tm['misses_per_min'].iloc[0:18].sum()
        sh_missed_shots = sh_tm['misses_per_min'].iloc[0:18].sum()
        
        #Rebound goals in all scenerios
        fs_reb_goals = fs_tm['rebgoals_per_min'].iloc[0:18].sum()
        ma_reb_goals = ma_tm['rebgoals_per_min'].iloc[0:18].sum()
        sh_reb_goals = sh_tm['rebgoals_per_min'].iloc[0:18].sum()
        
        #penalty minutes
        as_tm['penmin_gm'] = as_tm['penalityMinutes'] / as_tm['games_played']
        as_tm['pendrawn_gm'] = as_tm['penalityMinutesDrawn'] / as_tm['games_played']
        
        pen_taken = as_tm['penmin_gm'].iloc[0:18].sum()
        pen_drawn = as_tm['pendrawn_gm'].iloc[0:18].sum()
        #Upload rows to df
        df.loc[f'Team{count}'] = [i,fs_shots,ma_shots,sh_shots,fs_blocked_shots,ma_blocked_shots,sh_blocked_shots,fs_missed_shots,ma_missed_shots,sh_missed_shots,fs_reb_goals,ma_reb_goals,sh_reb_goals,pen_taken,pen_drawn]
        count += 1
    return df 
        
def use_player_stats(team1,team2, team1_goalie, team2_goalie):
    #lets calc them goals
    df = ByPlayerGameAnalysis(team1,team2)
    teams = [team1,team2]
    tm1 = df[df['team'] == team1]
    tm2 = df[df['team'] == team2] 
    tm1_pp = ((tm1['pen_drawn'][0] + tm2['pen_taken'][0]) / 2)  
    tm2_pp = ((tm2['pen_drawn'][0] + tm1['pen_taken'][0]) / 2)  
    
    #Team 1 
    net_shots_1 = (60 - tm1_pp - tm2_pp) * tm1['fs_shots'][0] + tm1_pp * tm1['ma_shots'][0] + tm2_pp * tm1['sh_shots'][0]
    net_blocks_1 = (60 - tm1_pp - tm2_pp) * tm1['fs_blocked_shots'][0] + tm1_pp * tm1['ma_blocked_shots'][0] + tm2_pp * tm1['sh_blocked_shots'][0] 
    net_misses_1 = (60 - tm1_pp - tm2_pp) * tm1['fs_missed_shots'][0] + tm1_pp * tm1['ma_missed_shots'][0] + tm2_pp * tm1['sh_missed_shots'][0]
    
    reb_goals_1 = (60 - tm1_pp - tm2_pp) * tm1['fs_reb_goals'][0] + tm1_pp * tm1['ma_reb_goals'][0] + tm2_pp * tm1['sh_reb_goals'][0]
    #Team 2 
    net_shots_2 = (60 - tm1_pp - tm2_pp) * tm2['fs_shots'][0] + tm2_pp * tm2['ma_shots'][0] + tm1_pp * tm2['sh_shots'][0]
    net_blocks_2 = (60 - tm1_pp - tm2_pp) * tm2['fs_blocked_shots'][0] + tm2_pp * tm2['ma_blocked_shots'][0] + tm1_pp * tm2['sh_blocked_shots'][0] 
    net_misses_2 = (60 - tm1_pp - tm2_pp) * tm2['fs_missed_shots'][0] + tm2_pp * tm2['ma_missed_shots'][0] + tm1_pp * tm2['sh_missed_shots'][0]
    
    reb_goals_2 = (60 - tm1_pp - tm2_pp) * tm1['fs_reb_goals'][0] + tm2_pp * tm1['ma_reb_goals'][0] + tm1_pp * tm1['sh_reb_goals'][0]
    
    
    tm1_sog = net_shots_1 - net_misses_1 - net_blocks_2
    tm2_sog = net_shots_2 - net_misses_2 - net_blocks_1
    
    tm1_goals = tm1_sog * (1- team2_goalie) + reb_goals_1
    tm2_goals = tm2_sog * (1- team1_goalie) + reb_goals_2 

    return tm1_goals, tm2_goals 
    
    
def all_games(home_teams,away_teams,home_goalie,away_goalie):
    home_team = []
    away_team = []
    home_goal = []
    away_goal = []
    style = input("Would you like the sheet style or powerplay style? (Enter: the sheet/powerplay)")
    if style == "the sheet":
        for i in range(len(home_teams)):
            home_goals, away_goals = the_sheet_style(home_teams[i],away_teams[i], home_goalie[i], away_goalie[i])
        
            home_team.append(home_teams[i])
            away_team.append(away_teams[i])
            home_goal.append(home_goals)
            away_goal.append(away_goals)
    elif style == "powerplay":  
        for i in range(len(home_teams)):
            home_goals, away_goals = use_player_stats(home_teams[i],away_teams[i], home_goalie[i], away_goalie[i])
        
            home_team.append(home_teams[i])
            away_team.append(away_teams[i])
            home_goal.append(home_goals)
            away_goal.append(away_goals)
    df = pd.DataFrame()
    df['Home Team'] = home_team
    df['Away Team'] = away_team
    df['Home Goals'] = home_goal
    df['Away Goals'] = away_goal
    home_odds = []
    away_odds = []
    tie_odds = [] 
    home_ml = []
    away_ml = []
    for i in range(len(df['Home Goals'])):
        home_score = poisson.rvs(df['Home Goals'][i], size = 10000)
        away_score = poisson.rvs(df['Away Goals'][i], size = 10000)
        home_win = 0
        away_win = 0
        tie = 0 
        for i in range(len(home_score)):
            if home_score[i] > away_score[i]:
                home_win += 1
            elif away_score[i] > home_score[i]:
                away_win += 1
            elif away_score[i] == home_score[i]:
                tie += 1
        home_w_per = (home_win + (tie/2)) / 10000
        away_w_per = (away_win + (tie/2)) / 10000
        tie_per = tie / 10000
        home_odds.append(home_w_per)
        away_odds.append(away_w_per)
        tie_odds.append(tie_per)
        if home_w_per > .50:
            home_mls = (home_w_per/ (1 - home_w_per)) * -100
        else:
            home_mls = ((1-home_w_per)/home_w_per) * 100
        
        if away_w_per > .50:
            away_mls = (away_w_per/ (1 - away_w_per)) * -100
        else:
            away_mls = ((1-away_w_per)/away_w_per) * 100
        home_ml.append(home_mls)
        away_ml.append(away_mls)
    df['Home Odds'] = home_odds 
    df['Away Odds'] = away_odds 
    df['Tie'] = tie_odds
    df['Home ML'] = home_ml
    df['Away ML'] = away_ml
    
    today = date.today()
    d4 = today.strftime("%b-%d-%Y")

    with pd.ExcelWriter('hockey_predictions.xlsx',engine='openpyxl', mode='a') as writer:  
        df.to_excel(writer, sheet_name="d4")
    print(df)
        
    
###########################################END OF MAIN FUNCTION##########################################################


#Like the sheeeeeeeeeeeeeeeeet style
def the_sheet_style(team1, team2, team1_goalie, team2_goalie):
    response = requests.get("https://moneypuck.com/moneypuck/playerData/seasonSummary/2021/regular/skaters.csv")
    s=str(response.content,'utf-8')

    data = StringIO(s) 

    df=pd.read_csv(data)
    df = df[(df['team'] == team1) | (df['team'] == team2)]
    df = df[df['situation'] == 'all']
    
    df['shots_per_game'] = df['I_F_shotAttempts'] / df['games_played']
    df['misses_per_game'] = df['I_F_missedShots'] / df['games_played']
    df['shots_blocked_per_game'] = df['shotsBlockedByPlayer'] / df['games_played']
    df['icetime_weight'] = df['icetime'] / df['games_played']
    
    #cut down
    tm1 = df[df['team'] == team1]
    tm2 = df[df['team'] == team2]
    
    #sort values 
    tm1 = tm1.sort_values(by=['icetime_weight'],ascending=False)
    tm2 = tm2.sort_values(by=['icetime_weight'],ascending=False)
    
    #calc per game values 
    tm1_shots = tm1['shots_per_game'].iloc[0:18].sum()
    tm1_shots_missed = tm1['misses_per_game'].iloc[0:18].sum()
    tm1_shots_blocked = tm1['shots_blocked_per_game'].iloc[0:18].sum()
    
    #shots blocked per game
    tm2_shots = tm2['shots_per_game'].iloc[0:18].sum()
    tm2_shots_missed = tm2['misses_per_game'].iloc[0:18].sum()
    tm2_shots_blocked = tm2['shots_blocked_per_game'].iloc[0:18].sum()
    
    tm1_goals = (tm1_shots - tm1_shots_missed - tm2_shots_blocked) * (1 - team2_goalie)
    tm2_goals = (tm2_shots - tm2_shots_missed - tm1_shots_blocked) * (1 - team1_goalie)
    
    return tm1_goals, tm2_goals 
#On a team basis
response2 = requests.get("https://moneypuck.com/moneypuck/playerData/seasonSummary/2021/regular/teams.csv")
s2=str(response2.content,'utf-8')

data2 = StringIO(s2) 

df_team=pd.read_csv(data2)
df_team['low_shot_per'] = df_team['lowDangerShotsFor'] / df_team['unblockedShotAttemptsFor']
df_team['med_shot_per'] = df_team['mediumDangerShotsFor'] / df_team['unblockedShotAttemptsFor']
df_team['high_shot_per'] = df_team['highDangerShotsFor'] / df_team['unblockedShotAttemptsFor']

df_team['low_goal_per'] = df_team['lowDangerGoalsFor'] / df_team['lowDangerShotsFor']
df_team['med_goal_per'] = df_team['mediumDangerGoalsFor'] / df_team['mediumDangerShotsFor']
df_team['high_goal_per'] = df_team['highDangerGoalsFor'] / df_team['highDangerShotsFor']

df_team['low_goal_per_against'] = (df_team['lowDangerGoalsAgainst'] / df_team['lowDangerShotsAgainst']) 
df_team['med_goal_per_against'] = (df_team['mediumDangerGoalsAgainst'] / df_team['mediumDangerShotsAgainst'])
df_team['high_goal_per_against'] = (df_team['highDangerGoalsAgainst'] / df_team['highDangerShotsAgainst'])

df_team['shots_pg_less_missed'] = (df_team['shotAttemptsFor'] - df_team['missedShotsFor']) / df_team['games_played']
df_team['shots_blocked_per'] = df_team['blockedShotAttemptsAgainst'] / (df_team['shotAttemptsFor'] - df_team['missedShotsFor'])

cut_down = df_team[df_team['situation'] == 'all']
cut_down.fillna(0)
def game_analysis(team1,team2):
    team1_df = cut_down[cut_down['name'] == team1]
    team2_df = cut_down[cut_down['name'] == team2]
    team_1_unblocked_shots = team1_df['shots_pg_less_missed'].iloc[0] * (1 - team2_df['shots_blocked_per'].iloc[0])
    team_2_unblocked_shots = team2_df['shots_pg_less_missed'].iloc[0] * (1 - team1_df['shots_blocked_per'].iloc[0])
    team_1_goals = team_1_unblocked_shots * (team1_df['low_shot_per'].iloc[0]*team2_df['low_goal_per_against'].iloc[0] + team1_df['med_shot_per'].iloc[0]*team2_df['med_goal_per_against'].iloc[0] + team1_df['med_shot_per'].iloc[0]*team2_df['med_goal_per_against'].iloc[0])
    team_2_goals = team_2_unblocked_shots * (team2_df['low_shot_per'].iloc[0]*team1_df['low_goal_per_against'].iloc[0] + team2_df['med_shot_per'].iloc[0]*team1_df['med_goal_per_against'].iloc[0] + team2_df['med_shot_per'].iloc[0]*team1_df['med_goal_per_against'].iloc[0])
    
    return team_1_goals, team_2_goals 

game_analysis('SEA', 'PIT')


def game_analysis_sv(team1,team2,goalie_1,goalie_2):
    team1_df = cut_down[cut_down['name'] == team1]
    team2_df = cut_down[cut_down['name'] == team2]
    team_1_unblocked_shots = team1_df['shots_pg_less_missed'].iloc[0] * (1 - team2_df['shots_blocked_per'].iloc[0])
    team_2_unblocked_shots = team2_df['shots_pg_less_missed'].iloc[0] * (1 - team1_df['shots_blocked_per'].iloc[0])
    team_1_goals = team_1_unblocked_shots * (1 - goalie_2)
    team_2_goals = team_2_unblocked_shots * (1 - goalie_1)
    print(team_1_goals,team_2_goals)
game_analysis_sv('PIT','DET',.886,.90)

def day_games():
    home_team = "blah"
    home_teams = [] 
    while home_team != "end":
        home_team = input("List home teams (enter 'end' to stop listing)")
        home_teams.append(home_team)
    home_teams.pop()
    away_team = "blah"
    away_teams = [] 
    while away_team != "end":
        away_team = input("List away teams (enter 'end' to stop listing)")
        away_teams.append(away_team)
    away_teams.pop()
    team1 = []
    team2 = []
    team1_goals = []
    team2_goals = []
    for i in range(len(home_teams)):
        x = 0
        y = 0
        team1.append(home_teams[i])
        team2.append(away_teams[i])
        x, y = game_analysis(home_teams[i], away_teams[i])
        team1_goals.append(x)
        team2_goals.append(y)
    
    
    df = pd.DataFrame()
    df['Team 1'] = team1
    df['Team 2'] = team2
    df['Team 1 Goals'] = team1_goals
    df['Team 2 Goals'] = team2_goals
    
    return df

def nhl_stats_pull():
    r = requests.get("https://www.nhl.com/stats/teams?reportType=season&seasonFrom=20212022&seasonTo=20212022&gameType=2&filter=gamesPlayed,gte,1&sort=points,wins&page=0&pageSize=100")
    data = json.loads(r.text)
    return data 
        
        
        
        
        