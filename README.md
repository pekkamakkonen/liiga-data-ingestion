# Liiga Data Ingestion

A data engineering project for collecting historical Finnish Liiga hockey data from Liiga's public-facing API.

The project currently focuses on the **data acquisition layer**: identifying the required API endpoints, collecting historical data, preserving raw responses, and creating a reproducible ingestion process.

The collected dataset covers four Liiga regular seasons:

- 2022–23
- 2023–24
- 2024–25
- 2025–26

Liiga season IDs `2023–2026` are used by the source API.

## Project goals

The main goal is to build a historical dataset that can later be processed and analyzed using Databricks.

The first version is focused primarily on player-level analysis, such as player cards and player performance metrics.

The project intentionally starts with a relatively simple batch architecture instead of real-time ingestion. Historical data is more suitable for the current use case and avoids issues caused by statistics being updated asynchronously after games.

## Data sources

Schedule files are used as control data for the ingestion process.

For each game, the ingestion script archives data from the following endpoints:

```text
/api/v2/games/{season}/{gameId}
/api/v2/games/stats/{season}/{gameId}
/api/v2/shotmap/{season}/{gameId}
```

Player statistics are fetched separately for each unique game date:

```text
/api/v2/players/stats/summed/{date}/{date}/runkosarja/false?dataType=all
```

The game dates are derived from the `start` field in the schedule data.

Example:

```json
"start": "2025-10-08T15:30:00Z"
```

Player statistics are stored using the date in the filename:

```text
player_stats_2025-10-08.json
```

This allows the date to be recovered later during ingestion and used together with `playerId` when joining datasets.

## Project structure

```text
.
├── data/
│   └── raw/
│       ├── schedule/
│       │   ├── schedule_2023_runkosarja.json
│       │   ├── schedule_2024_runkosarja.json
│       │   ├── schedule_2025_runkosarja.json
│       │   └── schedule_2026_runkosarja.json
│       │
│       ├── games/
│       │   ├── 2023/
│       │   │   ├── game/
│       │   │   ├── stats/
│       │   │   └── shotmap/
│       │   └── ...
│       │
│       └── player_stats/
│           ├── 2023/
│           ├── 2024/
│           ├── 2025/
│           └── 2026/
│
└── src/
    ├── fetch_game_data.py
    └── fetch_player_stats.py
```

Large raw API datasets are kept outside version control.

## Ingestion design

The ingestion scripts are intentionally simple batch processes.

### Game data

The schedule files provide:

- season
- game ID

Together these form the identity of a game in the source system.

Game IDs are not assumed to be globally unique between seasons, so both values are included in raw filenames.

Example:

```text
data/raw/games/2025/stats/stats_2025_123.json
```

API responses are stored without transforming or re-serializing the JSON:

```python
output_file.write_bytes(response.content)
```

This keeps the raw layer as close to the source response as possible.

### Player statistics

Player statistics are requested once per unique Liiga game date rather than once per game.

If four teams play two games on a given date and each team has a 21-player roster, the expected response contains:

```text
4 × 21 = 84 player records
```

This provides a simple sanity check for the daily player dataset.

## API observations

Some behavior of the source API is undocumented and was determined through controlled comparisons.

For the player statistics endpoint, the boolean parameter in:

```text
/runkosarja/false
```

affects how player team history is represented.

Testing showed that using `false` preserves historical team information for players who have represented multiple teams. Removing the parameter can also cause such players to disappear from the response.

For this reason the ingestion process explicitly uses `false`.

Another important distinction in the player data is:

```text
games
playedGames
```

`games` represents roster inclusion, while `playedGames` indicates whether the player actually participated in the game.

Players with `playedGames = 0` are therefore retained as valid observations.

## Reliability

The ingestion scripts include:

- request timeouts
- retry handling for temporary HTTP errors
- delays between requests
- skipping of already downloaded files

Temporary responses such as HTTP `503` are retried instead of silently dropping data.

This also makes the scripts restartable: already downloaded files do not need to be fetched again.

## Scope decisions

The current version focuses on the regular season and player-level data.

Separate team statistics are not required for the first version. Where appropriate, team-level metrics can later be derived by aggregating player-game observations.

Shot map data is archived even though it may not be used in the first analytical version. Keeping the raw source data now protects against future API changes or removal of historical endpoints.

## Next steps

The next phase of the project is to load the collected raw data into Databricks and build structured datasets for analysis.

The initial analytical focus will be player-level statistics and player cards, with team-level views derived later where useful.