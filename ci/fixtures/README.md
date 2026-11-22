# CI fixtures

`games.jsonl` — 25 real games sampled from `raw.games`, picked to cover every edge case the
models handle: stream-setup AI games, anonymous opponents, a 0-ply game, each kind of draw,
a null ECO, every speed, and rated wins/losses/draws as both colors.

Opponent usernames/ids are replaced with `opponent_N`. Everything else is the untouched
Lichess API payload, so the fixture exercises the real JSON shape.

When a model starts handling a new edge case, add a game that hits it here so CI covers it.
