#!/usr/bin/env python3

"""Code file for baseball elimination lab created for Advanced Algorithms
Spring 2020 at Olin College. The code for this lab has been adapted from:
https://github.com/ananya77041/baseball-elimination/blob/master/src/BaseballElimination.java"""

import sys
import math
import picos as pic
import networkx as nx
import itertools
import cvxopt
import matplotlib.pyplot as plt
from time import sleep

SOURCE = "s"
SINK = "t"


class Division:
    """
    The Division class represents a baseball division. This includes all the
    teams that are a part of that division, their winning and losing history,
    and their remaining games for the season.

    filename: name of a file with an input matrix that has info on teams &
    their games
    """

    def __init__(self, filename):
        self.teams = {}
        self.G = nx.DiGraph()
        self.readDivision(filename)
        self.total_cap = 0
        self.already_lost = False

    def draw_graph(self):
        """Draws a nice representation of a networkx graph object.
        Source: https://notebooks.azure.com/coells/projects/100days/html/day%2049%20-%20ford-fulkerson.ipynb"""
        graph = self.G
        plt.figure(figsize=(12, 4))
        plt.axis("off")
        nx.draw_networkx(graph, node_color="steelblue", node_size=600)
        plt.show()

    def readDivision(self, filename):
        """Reads the information from the given file and builds up a dictionary
        of the teams that are a part of this division.

        filename: name of text file representing tournament outcomes so far
        & remaining games for each team
        """
        f = open(filename, "r")
        lines = [line.split() for line in f.readlines()]
        f.close()

        lines = lines[1:]
        for ID, teaminfo in enumerate(lines):
            team = Team(
                int(ID),
                teaminfo[0],
                int(teaminfo[1]),
                int(teaminfo[2]),
                int(teaminfo[3]),
                list(map(int, teaminfo[4:])),
            )
            self.teams[ID] = team

    def get_team_IDs(self):
        """Gets the list of IDs that are associated with each of the teams
        in this division.

        return: list of IDs that are associated with each of the teams in the
        division
        """
        return self.teams.keys()


    def is_eliminated(self, teamID, solver):
        '''Uses the given solver (either Linear Programming or Network Flows)
        to determine if the team with the given ID is mathematically
        eliminated from winning the division (aka winning more games than any
        other team) this season.

        teamID: ID of team that we want to check if it is eliminated
        solver: string representing whether to use the network flows or linear
        programming solver
        return: True if eliminated, False otherwise
        '''
        flag1 = False
        team = self.teams[teamID]

        temp = dict(self.teams)
        del temp[teamID]

        for _, other_team in temp.items():
            if team.wins + team.remaining < other_team.wins:
                flag1 = True

        saturated_edges = self.create_network(teamID)
        if not flag1:
            if solver == "Network Flows":
                flag1 = self.network_flows(saturated_edges)
            elif solver == "Linear Programming":
                flag1 = self.linear_programming(teamID, saturated_edges)
        return flag1


    def create_network(self, teamID):
        '''Builds up the network needed for solving the baseball elimination
        problem as a network flows problem & stores it in self.G. Returns a
        dictionary of saturated edges that maps team pairs to the amount of
        additional games they have against each other.

        teamID: ID of team that we want to check if it is eliminated

        return: dictionary of saturated edges that maps team pairs to
        the amount of additional games they have against each other
        '''
        self.G = nx.DiGraph()
        saturated_edges = {}
        ids = list(self.get_team_IDs())
        ids.remove(teamID)
        self.already_lost = False
        self.teamID = teamID

        hypo_win = self.teams[teamID].wins + self.teams[teamID].remaining

        all_edges = []

        for index, id in enumerate(ids):
            actual_remaining = hypo_win - self.teams[id].wins

            if actual_remaining < 0:
                self.already_lost = True

            all_edges.append((self.teams[id].name, SINK, {'capacity': actual_remaining, 'flow' : 0}))
            for index2, opponent in enumerate(ids):
                if index2 > index:
                    num = self.teams[id].get_against(opponent)
                    all_edges.append((SOURCE, str(id) + "_" + str(opponent), {'capacity': num, 'flow' : 0}))
                    all_edges.append((str(id) + "_" + str(opponent), self.teams[id].name, {'capacity': num, 'flow' : 0}))
                    all_edges.append((str(id) + "_" + str(opponent), self.teams[opponent].name, {'capacity': num, 'flow' : 0}))
                    saturated_edges[(id, opponent)] = num

        self.G.add_edges_from(all_edges)

        return saturated_edges

    def network_flows(self, saturated_edges):
        '''Uses network flows to determine if the team with given team ID
        has been eliminated. You can feel free to use the built in networkx
        maximum flow function or the maximum flow function you implemented as
        part of the in class implementation activity.

        saturated_edges: dictionary of saturated edges that maps team pairs to
        the amount of additional games they have against each other
        return: True if team is eliminated, False otherwise
        '''
        # Nek

        # step 1 -- flow through the graph
        flow_value, flow_dict = nx.maximum_flow(self.G, SOURCE, SINK, capacity='capacity')

        total_cap = sum([x for y,x in saturated_edges.items()])
        if total_cap > flow_value or self.already_lost:
            return True
        else:
            return False

        # step 2 -- check if all flow from source is used

    def linear_programming(self, teamID, saturated_edges):
        """Uses linear programming to determine if the team with given team ID
        has been eliminated. We recommend using a picos solver to solve the
        linear programming problem once you have it set up.
        Do not use the flow_constraint method that Picos provides (it does all of the work for you)
        We want you to set up the constraint equations using picos (hint: add_constraint is the method you want)

        In this function, we use "Emily" to refer to the team that we're checking out (teamID)

        teamID: ID of team that we want to check if it is eliminated
        saturated_edges: dictionary of saturated edges that maps team pairs to
        the amount of additional games they have against each other
        returns True if team is eliminated, False otherwise
        """

        other_teams = [team for team in self.get_team_IDs() if team != teamID]

        # The maximum number of points that Emily could have at the end
        e_max_points = self.teams[teamID].wins + self.teams[teamID].remaining

        # How many points a team can win before it passes Emily

        p = pic.Problem()

        # Left-hand edges
        g, g_lim = {}, {}
        for pair in saturated_edges:
            g[pair] = p.add_variable(f"g_{pair}", 1, vtype="integer")
            p.add_constraint(0 <= g[pair])
            g_lim[pair] = p.add_constraint(g[pair] <= saturated_edges[pair])

        # Right-hand edges
        f, f_lim = {}, {}
        for team in other_teams:
            f[team] = p.add_variable(f"f_{team}", 1, vtype="integer")
            p.add_constraint(0 <= f[team])
            f_lim[team] = p.add_constraint(
                f[team] <= e_max_points - self.teams[team].wins
            )

        # Center edges and left-hand node constraints
        c, left_lim = {}, {}
        for pair in saturated_edges:
            c[(pair, pair[0])] = p.add_variable(
                f"c_{(pair, pair[0])}", 1, vtype="integer"
            )
            p.add_constraint(0 <= c[(pair, pair[0])])

            c[(pair, pair[1])] = p.add_variable(
                f"c_{(pair, pair[1])}", 1, vtype="integer"
            )
            p.add_constraint(0 <= c[(pair, pair[1])])

            left_lim[pair] = p.add_constraint(
                g[pair] == c[pair, pair[0]] + c[pair, pair[1]]
            )

        # Right-hand node constraints
        right_lim = {}
        for team in other_teams:
            inputs = [c[key] for key in c if key[1] == team]

            right_lim[team] = p.add_constraint(f[team] == sum(inputs))

        # Add the thing we're optimizing
        t = p.add_variable("t", 1, vtype="integer")
        t_lim = p.add_constraint(t == sum(f.values()))
        p.set_objective("max", t)

        soln = p.solve(verbose=False)
        p_val = round(p.obj_value())

        return p_val < sum(saturated_edges.values())

    def checkTeam(self, team):
        """Checks that the team actually exists in this division.
        """
        if team.ID not in self.get_team_IDs():
            raise ValueError("Team does not exist in given input.")

    def __str__(self):
        """Returns pretty string representation of a division object.
        """
        temp = ""
        for key in self.teams:
            temp = temp + f"{key}: {str(self.teams[key])} \n"
        return temp


class Team:
    """
    The Team class represents one team within a baseball division for use in
    solving the baseball elimination problem. This class includes information
    on how many games the team has won and lost so far this season as well as
    information on what games they have left for the season.

    ID: ID to keep track of the given team
    teamname: human readable name associated with the team
    wins: number of games they have won so far
    losses: number of games they have lost so far
    remaining: number of games they have left this season
    against: dictionary that can tell us how many games they have left against
    each of the other teams
    """

    def __init__(self, ID, teamname, wins, losses, remaining, against):
        self.ID = ID
        self.name = teamname
        self.wins = wins
        self.losses = losses
        self.remaining = remaining
        self.against = against

    def get_against(self, other_team=None):
        """Returns number of games this team has against this other team.
        Raises an error if these teams don't play each other.
        """
        try:
            num_games = self.against[other_team]
        except:
            raise ValueError("Team does not exist in given input.")

        return num_games

    def __str__(self):
        """Returns pretty string representation of a team object.
        """
        return f"{self.name} \t {self.wins} wins \t {self.losses} losses \t {self.remaining} remaining"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        division = Division(filename)
        for (ID, team) in division.teams.items():
            print(
                f'{team.name}: Eliminated? {division.is_eliminated(team.ID, "Linear Programming")}'
            )
    else:
        print(
            "To run this code, please specify an input file name. Example: python baseball_elimination.py teams2.txt."
        )
