import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests


BASE_URL = "https://liiga.fi/api/v2"

SCHEDULE_DIR = Path("data/raw/schedule")
PLAYER_STATS_DIR = Path("data/raw/player_stats")

REQUEST_DELAY = 1
MAX_RETRIES = 5

HELSINKI_TZ = ZoneInfo("Europe/Helsinki")


def get_with_retry(url: str) -> requests.Response:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=30)

            if response.status_code in (429, 500, 502, 503, 504):
                wait = 5 * attempt

                print(
                    f"HTTP {response.status_code}: "
                    f"retry {attempt}/{MAX_RETRIES} in {wait}s"
                )

                time.sleep(wait)
                continue

            response.raise_for_status()
            return response

        except requests.RequestException as error:
            if attempt == MAX_RETRIES:
                raise

            wait = 5 * attempt

            print(
                f"Request failed: {error}. "
                f"Retry {attempt}/{MAX_RETRIES} in {wait}s"
            )

            time.sleep(wait)

    raise RuntimeError(f"Failed after {MAX_RETRIES} attempts: {url}")


def get_game_date(start: str) -> str:
    game_datetime = datetime.fromisoformat(
        start.replace("Z", "+00:00")
    )

    local_datetime = game_datetime.astimezone(HELSINKI_TZ)

    return local_datetime.date().isoformat()


def get_schedule_dates(schedule_file: Path) -> set[tuple[int, str]]:
    with schedule_file.open("r", encoding="utf-8") as file:
        games = json.load(file)

    dates = set()

    for game in games:
        season = game["season"]
        game_date = get_game_date(game["start"])

        dates.add((season, game_date))

    return dates


def download_player_stats(season: int, game_date: str) -> None:
    output_dir = PLAYER_STATS_DIR / str(season)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = (
        output_dir
        / f"player_stats_{game_date}.json"
    )

    if output_file.exists():
        print(f"Skip: {output_file}")
        return

    url = (
        f"{BASE_URL}/players/stats/summed/"
        f"{game_date}/{game_date}/"
        f"runkosarja/false"
        f"?dataType=all"
    )

    response = get_with_retry(url)

    output_file.write_bytes(response.content)

    print(f"Saved: {output_file}")

    time.sleep(REQUEST_DELAY)


def main() -> None:
    schedule_files = sorted(
        SCHEDULE_DIR.glob("schedule_*_runkosarja.json")
    )

    all_dates = set()

    for schedule_file in schedule_files:
        print(f"Reading: {schedule_file}")

        all_dates.update(
            get_schedule_dates(schedule_file)
        )

    print(f"\nFound {len(all_dates)} unique game dates.\n")

    for season, game_date in sorted(all_dates):
        download_player_stats(
            season=season,
            game_date=game_date,
        )


if __name__ == "__main__":
    main()