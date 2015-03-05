# tournament_results
Second project for Udacity Full Stack Web Dev Nanodegree

# Implementation details
- Added the possibility to tie a game. The function signature didn't change significantly, so it is still backwards compatible with any previous code.
- Implemented the OMW ranking based on the wins against common opponents. Please note that it will only work if two players have the same number of victories. It could have been generalized for N number of players with the same number of victories, but then a pure SQL way of getting the results would have been more difficult. The current implementation uses a view that will get, for a given pair of (p1, p2) players, the number of victories of p1 against the common opponents it has with p2. A generalization of this would have required calculating this for any possible combination, making the view grow exponentially.
- I also implemented assigning a bye round to a player if the number of players is odd. To do this a special type of player was included so that a bye round is no different from any other match. However, this player is not taken into account when calculating the number of players, so any user will be oblivious of this special bye player.
- The SQL schema is explained in the tournament.sql file.
- There are new tests to prove the extra features work.

# Dependencies
Have into account that the code has been tested with the included versions, but it might work as well with different versions.
- python 2.7.6
- psycopg2 2.4.5
- psql 9.3.5
- bleach 1.4.1

# How to run it
- Create a tournament database
```sh
$ createdb tournament
```
- Run the tournament.sql file to create tables and views
```sh
$ psql -d tournament -a -f tournament/tournament.sql
```
- Run the tests to ensure all of them pass
```sh
$ python tournament/tournament_test.py
```
