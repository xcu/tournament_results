# tournament_results
Second project for Udacity Full Stack Web Dev Nanodegree

# Implementation details
- Added the possibility to tie a game. The function signature didn't change significantly, so it is still backwards compatible with any previous code.
- Implemented the OMW ranking based on the wins against common opponents. Please note that it will only work if two players have the same number of victories. It could have been generalized for N number of players with the same number of victories, but then a pure SQL way of getting the results would have been more difficult. The current implementation uses a view that will get, for a given pair of (p1, p2) players, the number of victories of p1 against the common opponents it has with p2. A generalization of this would have required calculating this for any possible combination, making the view grow exponentially.
- I also implemented assigning a bye round to a player if the number of players is odd. To do this a special type of player was included so that a bye round is no different from any other match. However, this player is not taken into account when calculating the number of players, so any user will be oblivious of this special bye player.
- The SQL schema is explained in the tournament.sql file.
- There are new tests to prove the extra features work.
