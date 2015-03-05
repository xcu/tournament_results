create table players (
    id serial primary key,
    full_name text
);


-- usually it will have three values: win, lose or tie
create table result_types (
    id serial primary key,
    result text
);


create table matches (
    id serial,
    player serial references players (id),
    result serial references result_types (id),
    primary key (id, player)
);


-- players that have been assigned a bye in that tournament
create table byed_players (
    player serial references players(id) on delete cascade
);


-- all the players minus the special bye player
create view players_no_bye as
 SELECT players.id,
    players.full_name
   FROM players
  WHERE players.id <> (( SELECT players_1.id
           FROM players players_1
          WHERE players_1.full_name = 'bye'::text
          ORDER BY players_1.id
         LIMIT 1));


-- matches with the result name as well
create view allmatches as
 SELECT matches.id,
    matches.player,
    matches.result,
    result_types.result AS result_name
   FROM matches
     JOIN result_types ON matches.result = result_types.id;


-- all the matches that each player has played
create view player_matches as
 SELECT a.player,
    b.player AS opponent,
    a.result AS player_res,
    b.result AS opponent_res,
    a.id AS match
   FROM matches a
     JOIN matches b ON a.id = b.id
  WHERE a.player <> b.player;


-- each entry means that p1 has 'opponent' in common with p2, being p1_match the match in which p1 played against 'opponent'
create view common_opponents_per_pair as
 SELECT a.opponent,
    a.player AS p1,
    a.match AS p1_match,
    b.player AS p2,
    a.player_res AS p1_match_result
   FROM player_matches a
     JOIN player_matches b ON a.opponent = b.opponent
  WHERE a.player <> b.player
  ORDER BY a.player, b.player;


-- from the previous view, take only the wins and count them (loses and ties don't count for the result)
create view wins_per_common_opponents as
 SELECT c.p1,
    c.p2,
    count(c.p1_match_result) AS wins
   FROM common_opponents_per_pair c
     JOIN result_types ON c.p1_match_result = result_types.id
  WHERE result_types.result = 'win'::text
  GROUP BY c.p1, c.p2
  ORDER BY c.p1, c.p2;


create view unordered_standings as
 SELECT p.id,
    p.full_name,
    COALESCE(b.wins, 0::bigint) AS wins,
    COALESCE(a.games, 0::bigint) AS games
   FROM ( SELECT players_no_bye.id,
            players_no_bye.full_name
           FROM players_no_bye) p
     LEFT JOIN ( SELECT allmatches.player,
            count(allmatches.player) AS games
           FROM allmatches
          GROUP BY allmatches.player) a ON p.id = a.player
     LEFT JOIN ( SELECT allmatches.player,
            count(allmatches.player) AS wins
           FROM allmatches
          GROUP BY allmatches.player, allmatches.result_name
         HAVING allmatches.result_name = 'win'::text) b ON a.player = b.player;


-- result types, this is mandatory before inserting matches
insert into result_types(result) values ('win');
insert into result_types(result) values ('lose');
insert into result_types(result) values ('tie');


-- a bye round should be another player to avoid doing strange things
insert into players (full_name) values ('bye');
-- and of course, a bye player cannot be assigned a bye
insert into byed_players(player) values ((select id from players where full_name = 'bye' order by id asc limit 1));
