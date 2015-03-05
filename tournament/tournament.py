#!/usr/bin/env python
# 
# tournament.py -- implementation of a Swiss-system tournament
#

import psycopg2
from itertools import izip
import bleach


def connect():
    """Connect to the PostgreSQL database.  Returns a database connection."""
    return psycopg2.connect("dbname=tournament")


def deleteMatches():
    """Remove all the match records from the database."""
    db = connect()
    c= db.cursor()
    c.execute('delete from matches;')
    db.commit()
    db.close()


def deletePlayers():
    """Remove all the player records from the database."""
    db = connect()
    c= db.cursor()
    c.execute("delete from players_no_bye;")
    statement = """delete from byed_players where
    player !=
    (select id from players where full_name = 'bye' order by id asc limit 1);
    """
    c.execute(statement)
    db.commit()
    db.close()


def countPlayers():
    """Returns the number of players currently registered."""
    db = connect()
    c= db.cursor()
    c.execute("select count(players_no_bye.id) from players_no_bye;")
    result = c.fetchall()
    db.close()
    # result looks like [(8,)], return only the integer
    return result[0][0]


def registerPlayer(name):
    """Adds a player to the tournament database.
  
    The database assigns a unique serial id number for the player.  (This
    should be handled by your SQL database schema, not in your Python code.)
  
    Args:
      name: the player's full name (need not be unique).
    """
    # a bye player is always needed to get consistent responses
    if not _byed_player_id():
        _create_player('bye')
    _create_player(name)

def _create_player(name):
    db = connect()
    c= db.cursor()
    # only user input that needs to be checked to avoid SQL injection
    sanitized_name = bleach.clean(name)
    c.execute("insert into players (full_name) values (%s);", (sanitized_name,))
    db.commit()
    db.close()


def playerStandings():
    """Returns a list of the players and their win records, sorted by wins.

    The first entry in the list should be the player in first place, or a player
    tied for first place if there is currently a tie.

    Returns:
      A list of tuples, each of which contains (id, name, wins, matches):
        id: the player's unique id (assigned by the database)
        name: the player's full name (as registered)
        wins: the number of matches the player has won
        matches: the number of matches the player has played
    """
    statement = """select * from unordered_standings order by wins desc;"""
    return _get_standings(statement)


def playerStandingsWithBye():
    # player standings query minus the next byed player
    statement = """select t1.id, t1.full_name, t1.wins, t1.games from unordered_standings as t1
    left join
        (select players_no_bye.id from players_no_bye
        left join byed_players on players_no_bye.id = byed_players.player
        where byed_players.player is null
        limit 1) as t2
    on t1.id = t2.id
    where t2.id is null
    order by t1.wins desc;"""
    return _get_standings(statement)


def _get_standings(statement):
    db = connect()
    c= db.cursor()
    c.execute(statement)
    result = c.fetchall()
    db.close()
    # classifying not only according to the swiss pairings system, but also
    # resolving ties using the OMW, as suggested in the extra credit.
    # This extension solves ties between two players, so the case in which
    # 3 or more players are tied is not solved here
    _sort_by_OMW(result)
    return result


def reportMatch(winner, loser, tie=False):
    """Records the outcome of a single match between two players.

    Args:
      winner:  the id number of the player who won
      loser:  the id number of the player who lost
      tie:    whether the game result was a tie. If True then the other
              two parameters only indicate the ids of the players
    """
    next_match_id = _next_match_id()
    byed_player_id = _byed_player_id()
    if tie or winner == byed_player_id:
        raise Exception("Bye player cannot win or tie.")
    if tie:
        # tie for both players
        statements = ["""insert into matches (id, player, result) values (%s, %s,
        (select result_types.id from result_types where result_types.result = 'tie'));"""] * 2
    else:
        statements = ["""insert into matches (id, player, result) values (%s, %s,
        (select result_types.id from result_types where result_types.result = 'win'));""",
                      """insert into matches (id, player, result) values (%s, %s,
        (select result_types.id from result_types where result_types.result = 'lose'));"""]
    db = connect()
    c= db.cursor()
    c.execute(statements[0], (next_match_id, winner))
    c.execute(statements[1], (next_match_id, loser))
    if loser == byed_player_id:
        # that player has been assigned a bye round, reflect it in the DB
        statement = "insert into byed_players(player) values (%s);"
        c.execute(statement, (winner,))
    db.commit()
    db.close()


def _next_match_id():
    db = connect()
    c= db.cursor()
    c.execute("select nextval('matches_id_seq');")
    result = c.fetchall()
    db.close()
    return result[0][0]


def swissPairings():
    """Returns a list of pairs of players for the next round of a match.
  
    Assuming that there are an even number of players registered, each player
    appears exactly once in the pairings.  Each player is paired with another
    player with an equal or nearly-equal win record, that is, a player adjacent
    to him or her in the standings.
  
    Returns:
      A list of tuples, each of which contains (id1, name1, id2, name2)
        id1: the first player's unique id
        name1: the first player's name
        id2: the second player's unique id
        name2: the second player's name
    """
    def pairwise_iter(standings):
        # creates pairs of items
        l = iter(standings)
        return izip(l, l)

    pairings = []
    standings = playerStandings()
    if _bye_needed(standings):
        # standings without the byed opponent
        standings = playerStandingsWithBye()
        byed_player_id = _byed_player_id()
        byed_player_opponent = _next_byed_player()
        pairings.append((byed_player_opponent, byed_player_id))
    for p1, p2 in pairwise_iter(standings):
        pairings.append((p1[0], p2[0]))
    return [(_id_name_from_player_id(p1) + _id_name_from_player_id(p2))
                                                    for (p1, p2) in pairings]


def _id_name_from_player_id(player_id):
    # returns a tuple (player_id, player_full_name) out of player_id
    db = connect()
    c= db.cursor()
    c.execute('''select players.id, players.full_name from players
    where players.id = %s;''', (player_id,))
    result = c.fetchall()
    db.close()
    return result[0]


def _sort_by_OMW(standings):
    # expects a list of player standings sorted by wins
    # if two players have the same number of wins they will be sorted by OMW,
    # the total number of wins by players they have played against
    for i, player in enumerate(standings):
        current_player, _, current_player_wins, _ = player
        try:
            next_player, _, next_player_wins, _ = standings[i+1]
        except IndexError:
            # last position, no need to do anything else
            return
        if current_player_wins == next_player_wins:
            # tie, need to sort by OMW
            p1_omw = _get_OMW(current_player, next_player)
            p2_omw = _get_OMW(next_player, current_player)
            if p2_omw > p1_omw:
                # next_player has better OMW, swap them
                standings[i], standings[i+1] = standings[i+1], standings[i]


def _get_OMW(p1_id, p2_id):
    # gets the wins of p1_id against the opponents in common to p2_id
    db = connect()
    c= db.cursor()
    c.execute(
       "select wins from wins_per_common_opponents where p1 = %s and p2 = %s;",
       (p1_id, p2_id)
    )
    result = c.fetchall()
    db.close()
    try:
        return result[0][0]
    except IndexError:
        # no occurrences for that pair, then return 0
        return 0


def _bye_needed(standings):
    # a bye is assigned if there is an odd number of players
    return len(standings) % 2


def _byed_player_id():
    # gets the id of the 'bye' player
    db = connect()
    c= db.cursor()
    c.execute('''select id from players where full_name = 'bye'
    order by id asc limit 1;''')
    result = c.fetchall()
    db.close()
    return result[0][0]


def _next_byed_player():
    # returns the id of the next player that will be assigned a bye in the
    # current round or raises an exception if all the players have been
    # assigned a bye in the competition
    db = connect()
    c= db.cursor()
    c.execute('''select players.id from players
    left join byed_players on players.id = byed_players.player
    where byed_players.player is null
    limit 1;''')
    result = c.fetchall()
    db.close()
    if not result:
        raise Exception("No player to assign a bye in this tournament")
    return result[0][0]
