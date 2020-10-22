#!/usr/bin/env python
# coding: utf-8

# In[931]:


from gurobipy import *
import json
import numpy as np
import pandas as pd


# In[932]:


with open("chess_data.txt") as chessdata:
    chessdata = json.load(chessdata)


# In[1]:


#chessdata


# In[934]:


chess = {}
for key,value in chessdata.items():
    chess[int(key)] = value


# In[935]:


m = Model("Swiss Chess")


# ### Data

# In[936]:


players = [x for x in range(1,95)]
 
#forfeited
#dictionary with player string number and a 0 or 1 based on if they forfeited
f = {x:0 for x in players} 
f[11] = 1
f[21] = 1


# In[937]:


#bye
#dictionary with player string number and 0 or 1 based on if they have received a bye 
e = {x:0 for x in players}
e[93] = 1
e[85] = 1


# In[938]:


#points 
#dictionary with the players string number and the number of points after round 7
#they are ordered by number of points
#ex: "7": 3.5
p={}
for key, value in chess.items():
    p[key] = value['ranking_post_7']


# In[939]:


#black (b) and white (w)
#dictionary with the  number of times player has been black
b = {x: 0 for x in players}
w = {x: 0 for x in players}
#round1 
color_1 = {}
for key, value in chess.items():
    color_1[key] = value['round1']
for key, value in color_1.items():
    color_1[key] = value['color']

for each in color_1:
    if color_1[each] == 0:
        b[each] += 1
    elif color_1[each] == 1:
        w[each] += 1


# In[940]:


#country
countries = {x:0 for x in players}
for key, value in chess.items():
    countries[key] = value['federation']


# In[941]:


#rating
ratings = {x:0 for x in players}
for key, value in chess.items():
    ratings[key] = value['rating']


# In[942]:


#pairings
pairs = {}
for key,value in chess.items():
    opponents = []
    for i in range(1,8):
        opp = value['round{}'.format(i)]['opponent']
        opponents.append(opp)
    pairs[key] = opponents


# In[943]:


#colors at which round
colors = {}
for key,value in chess.items():
    color_rounds = [value['round{}'.format(r)]['color'] for r in range(1,8)]
    colors[key] = color_rounds


# In[944]:


#pi7 country against which player i played in round 7
opponent_country_dict = {} 
for key,value in chess.items():
    opponent = value['round7']['opponent']
    if opponent != None:
        opponent_country_dict[key] = countries[opponent]


# In[945]:


#cij is 1 if ci = cj
big_C = {}
for i in countries.keys():
    for j in countries.keys():
        if countries[i] == countries[j]:
            big_C[(i,j)] = 1
        else:
            big_C[(i,j)] = 0


# In[946]:


#rij is 1 if abs(ri-rj) >= 250
big_R = {}
for i in ratings.keys():
    for j in ratings.keys():
        if abs(ratings[i] - ratings[j]) >= 250:
            big_R[(i,j)] = 1
        else:
            big_R[(i,j)] = 0 


# In[947]:


#patterni indicates whether player i follows the pattern BWWB
pattern = {}
for i in colors.keys():
    pat = [0,1,1,0]
    if colors[i][3:] == pat:
        pattern[i] = 1
    else:
        pattern[i] = 0


# In[948]:


#if the country is unique
uniques = {country:0 for country in set(countries.values())}

for country2 in uniques.keys():
    ps = []
    for key,country in countries.items():
        if country == country2:
            ps.append(key)
            uniques[country] = ps

unique_players = []
for val in uniques.values():
    if len(val) == 1:
        unique_players.append(val[0])


# In[949]:


#U is the set of players that weren't paired at round 7
u = []
for key,value in chess.items():
    if value['round7']['opponent'] == None:
        u.append(key)


# In[950]:


#player number to player name
number2name = {}
for key,value in chess.items():
    number2name[key] = value['name']


# ### Helper Functions

# In[951]:


def paired(i,j):
    if j in pairs[i]:
        return 1
    else:
        return 0


# In[952]:


def if_even(players,f):
    num_forfeit = sum([1 for value in f.values() if value == 0])
    if (len(players) - num_forfeit) % 2 == 0:
        z = 1
    else:
        z = 0
    return z


# In[953]:


def opp_country_check(j,i):
    if i not in opponent_country_dict.keys():
        return False
    else:
        return (countries[j] == opponent_country_dict[i])


# ### Decision Variables 

# In[954]:


## x indicates whether player i is paired with player j


# In[955]:


x = m.addVars(players,players, name = 'x', vtype = GRB.BINARY)


# In[956]:


## y indicates whether player i was assigned black or white at round k


# In[957]:


y = m.addVars(players, name = 'y', vtype = GRB.BINARY)


# In[958]:


## z indicates whether player i is assigned a bye at round 8


# In[959]:


z = m.addVars(players, name = 'z', vtype = GRB.BINARY)


# In[960]:


## v is the violation of constraint (4)


# In[961]:


v = m.addVars(players, players, name = 'v')


# In[962]:


## h is 1 if player i is assigned a color with which they played least


# In[963]:


h = m.addVars(players, name = 'h', vtype = GRB.BINARY)


# In[964]:


# alt is 1 if player i is given an alternating color in round 8
# equal is 1 if player i has equal number of black and white games


# In[965]:


alt = m.addVars(players, name='alt', vtype=GRB.BINARY)


# In[966]:


equal = m.addVars(players, name='equal', vtype=GRB.BINARY)


# In[967]:


## opponent countries variables where opponent_country_i indicates whether the opponent 
## for player i in round 7 is from the same country than player i's opponent in round 8
opponent_country = m.addVars(players, name = 'opponent_country', vtype = GRB.BINARY)


# In[968]:


## difference of 2 or -2 for black or whites
alpha = m.addVars(players, name = 'alpha', vtype = GRB.BINARY)


# In[969]:


## random binary variables for big M constraints


# In[970]:


lambda2b = m.addVars(players, players, name = 'lambda171', vtype = GRB.BINARY)


# In[971]:


lambda71 = m.addVars(players, name = 'lambda71', vtype = GRB.BINARY)


# In[972]:


lambda72 = m.addVars(players, name = 'lambda72', vtype = GRB.BINARY)


# In[973]:


lambda81 = m.addVars(players, name = 'lambda81', vtype = GRB.BINARY)


# In[974]:


lambda82 = m.addVars(players, name = 'lambda82', vtype = GRB.BINARY)


# In[975]:


lambda161 = m.addVars(players, name = 'lambda161', vtype = GRB.BINARY)


# In[976]:


lambda162 = m.addVars(players, name = 'lambda162', vtype = GRB.BINARY)


# In[977]:


lambda163 = m.addVars(players, name = 'lambda163', vtype = GRB.BINARY)


# In[978]:


lambda164 = m.addVars(players, name = 'lambda164', vtype = GRB.BINARY)


# In[979]:


lambda171 = m.addVars(players, players, name = 'lambda171', vtype = GRB.BINARY)


# In[980]:


lambda181 = m.addVars(players, name = 'lambda181', vtype = GRB.BINARY)


# ### Constraints

# In[981]:


# (1) Two players cannot play each other more than once.
cons1a = m.addConstrs((paired(i,j) + x[i,j] <= 1) for i in players for j in players if i!=j)
cons1b = m.addConstrs((paired(j,i) + x[j,i] <= 1) for i in players for j in players if i!=j)
cons1c = m.addConstrs(x[i,j] == x[j,i] for i in players for j in players)


# In[982]:


# For a given i, sum of x[i,j] <= 1.
cons1a = m.addConstrs(x.sum(i,'*') <= 1 for i in players)
const1b = m.addConstrs(x.sum('*',j) <= 1 for j in players)


# In[983]:


# (2) Should the number of players to be paired be odd, one player is unpaired. 
# This player receives a pairing-allocated bye: no opponent, no color and as many points as are rewarded for a win, unless the rules of the tournament state otherwise.
cons2a = m.addConstr((1 - if_even(players,f) + sum([z[i] for i in players]) - 1) >= 1)
cons2b = m.addConstr((1 - if_even(players,f) + sum([x[i,j] for i in players for j in players])) >= 1)


# In[984]:


# (2b) Players that play against each other must have opposite colors.
cons2ba = m.addConstrs(x[i,j] <= lambda2b[i,j] for i in players for j in players)
cons2bb = m.addConstrs((y[i] - 1 + y[j]) <= (1-lambda2b[i,j]) for i in players for j in players)


# In[985]:


# (3) A player who has already received a pairing-allocated bye or has already scored a (forfeit) win due 
# to an opponent not appearing in time, shall not receive the pairing-allocated bye.
cons3 = m.addConstrs((f[i] + z[i] <= 1) for i in players)


# In[986]:


# (4) In general, players are paired to others with the same score
cons4a = m.addConstrs(v[i,j] >= 0 for i in players for j in players if i != j)
cons4b = m.addConstrs(v[i,j] >= x[i,j]*abs(p[i]-p[j])-0.5 for i in players for j in players if i != j)


# In[987]:


# (5) For each player the difference between the number of black and the number of white games 
# shall not be greater than 2 or less than –2. Each system may have exceptions to this rule in the last round of a tournament.
cons5a = m.addConstrs((b[i] + y[i] - w[i] - 1 + y[i]) >= (-2) for i in players)
cons5b = m.addConstrs((b[i] + y[i] - w[i] - 1 + y[i]) <= (2) for i in players)


# In[988]:


# (6) No player shall receive the same color three times in a row.
cons6a = m.addConstrs((colors[i][5] + colors[i][6] + y[i]) >= 1 
                      for i in players if (colors[i][5] != None and colors[i][6] != None))
cons6b = m.addConstrs((colors[i][5] + colors[i][6] + y[i]) <= 2 
                      for i in players if (colors[i][5] != None and colors[i][6] != None))


# In[989]:


# (7) In general, a player is given the color with which they played fewer games.
cons7a = m.addConstrs(w[i]-b[i]+y[i] <= 1+2*(lambda71[i]) for i in players)
cons7b = m.addConstrs(1-h[i] <= 1*(1-lambda71[i]) for i in players)
cons7c = m.addConstrs(b[i]-w[i]+(1-y[i]) <= 1+2*(lambda72[i]) for i in players)
cons7d = m.addConstrs(1-h[i] <= 1*(1-lambda72[i]) for i in players)


# In[990]:


# (8) If colors are already balanced, then, in general, the player is given the color that alternates from the last one with which they played.
cons8a = m.addConstrs(equal[i]+y[i]+colors[i][6] <= 2 + 1*(lambda81[i]) 
                      for i in players if colors[i][6] != None)
cons8b = m.addConstrs(alt[i] <= 1*(1-lambda81[i]) for i in players)
cons8c = m.addConstrs(equal[i]+(1-y[i])+(1-colors[i][6]) <= 2 + 1*(lambda82[i]) 
                      for i in players if colors[i][6] != None)
cons8d = m.addConstrs(alt[i] <= 1*(1-lambda82[i]) for i in players)


# In[991]:


# (9) If a player is not on time for their round, or forfeit, 
#they do not get paired for the next rounds
cons9 = m.addConstrs((1-f[i])+(1-x[i,j]) >= 1 for i in players for j in players)


# In[992]:


# (10) A player cannot play two players from the same country in a row.
# opponent_country_bool = (country[j] != opponent_country[i] if x[i,j] == 1)
cons10 = m.addConstrs((1-x[i,j])+(1-opp_country_check(j,i))+opponent_country[i] >= 1 
                      for i in players for j in players if i != j)


# In[993]:


# (11) If two players are from the same country, they cannot play each other.
#Included in the objective


# In[994]:


# (12) The rating difference of the players paired cannot be greater than 250.
#Included in the objective


# In[995]:


# (13) Players following pattern Black – White – White – Black in rounds 4, 5, 6 and 7, 
# then the player would automatically be assigned Black in the round 8.
#Included in the objective


# In[996]:


# (14)  If a player is the only one from their country, they are black for round 8. 
#Included in the objective


# In[997]:


# (15) A player belongs to the set U if the player was not paired at round 7.
#Included in the objective


# In[998]:


# (16) A player belongs to the set D if the difference between the number of whites 
# and number of blacks is equal to 2 or -2.
cons16a = m.addConstrs(((w[i] + 1 - y[i]) - (b[i] + y[i]) - 2) <= 2*lambda161[i] for i in players)
cons16b = m.addConstrs(alpha[i] <= (1-lambda161[i]) for i in players)

cons16c = m.addConstrs(-(w[i] + 1 - y[i]) + (b[i] + y[i]) + 2 <= 5*lambda162[i] for i in players)
cons16d = m.addConstrs(alpha[i] <= (1-lambda162[i]) for i in players)

cons16e = m.addConstrs(((w[i] + 1 - y[i]) - (b[i] + y[i]) + 2) <= 6*lambda163[i] for i in players)
cons16f = m.addConstrs(alpha[i] <= (1-lambda163[i]) for i in players)

cons16g = m.addConstrs((-(w[i] + 1 - y[i]) + b[i] + y[i] - 2) <= lambda164[i] for i in players)
cons16h = m.addConstrs(alpha[i] <= (1-lambda164[i]) for i in players)


# In[999]:


# (17) players that play against each other must have opposite colors
#if x[ij] = 1 then (y[i] = 1 and y[j] = 0) or (y[i] = 0 and y[j] = 1)
#if x[ij] = 1 then y[i] = 1-y[j]  
cons17a = m.addConstrs(x[i,j] <= lambda171[i,j] for i in players for j in players if i!=j)
cons17b = m.addConstrs(1 - y[i] - y[j] <= (1-lambda171[i,j]) for i in players for j in players if i!=j)


# In[1000]:


# (18) If a player is not paired for round 8, they receive a bye.
cons18a = m.addConstrs(z[i] <= lambda181[i] for i in players)
cons18b = m.addConstrs(x.sum(i,'*') <= 1 - lambda181[i] for i in players)


# ### Objective

# In[1001]:


objective = (0.7*sum([x[i,j] for i in players for j in players if i != j]) #most pairings
             - 0.01*sum([x[i,j]*big_C[(i,j)] for i in players for j in players if i != j]) #constraint (11) 
             + 0.01*sum([alt[i] for i in players]) #constraint (8)
             + 0.01*sum([h[i] for i in players]) #constraint (7)
             - 0.01*sum([v[i,j] for i in players for j in players if i!= j]) #constraint (4)
             - 0.01*sum([big_R[(i,j)]*x[i,j] for i in players for j in players if i!= j]) #constraint (12)
             + 0.01*sum([pattern[i]*y[i] for i in players]) #constraint (13) 
             + 0.15*sum([x[i,j] for i in u for j in players]) #constraint (15)
             + 0.01*sum([y[i] for i in unique_players]) #constraint (14)
             - 0.01*sum([opponent_country[i] for i in players]) #constraint (10)
             - 0.07*sum([alpha[i] for i in players]) # objective (3)
            ) 


# In[1002]:


m.setObjective(objective, GRB.MAXIMIZE)


# In[1003]:


m.optimize()


# ### Results

# In[1004]:


results = []
for i in players:
    for j in players:
        #print('({},{})'.format(i,j) + str(x[i,j]))
        if x[i,j].x == 1:
            results.append((i,j))

for tup in results:
    for tupdup in results:
        if tup[::-1] == tupdup:
            results.remove(tupdup)


# In[1005]:


assigned_colors = {}
for i in players:
    #if y[i].x == -0.0:
    #    assigned_colors[i] = 1
    assigned_colors[i] = y[i].x
print(assigned_colors)


# In[1006]:


assigned_bye = {}
for i in players:
    assigned_bye[i] = z[i].x
print(assigned_bye)


# In[1007]:


def results_table(xijs,yis):
    player1 = [pl1 for pl1,pl2 in xijs]
    player2 = [pl2 for pl1,pl2 in xijs]
    colors_pl1 = [yis[col1] for col1 in player1]
    colors_pl2 = [yis[col2] for col2 in player2]
    names_pl1 = [number2name[pl1] for pl1 in player1]
    names_pl2 = [number2name[pl2] for pl2 in player2]
    results_df = pd.DataFrame({'P1': player1,'Name P1':names_pl1,'Color P1': colors_pl1,
                               'Color P2': colors_pl2,'P2': player2,'Name P2':names_pl2})
    return results_df


# In[1008]:


results_table(results, assigned_colors)


# In[1009]:


def results_bye(assigned_bye):
    players_w_bye = [pl for pl in assigned_bye if assigned_bye[pl] == 1]
    names = [number2name[pl] for pl in players_w_bye]
    bye_df = pd.DataFrame({"Player":players_w_bye, "Player Name":names})
    return bye_df


# In[1010]:


results_bye(assigned_bye)


# In[ ]:




