import json
import time
from pathlib import Path

import requests


BASE_URL = "https://liiga.fi/api/v2"

SCHEDULE_DIR = Path("data/raw/schedule")
GAMES_DIR = Path("data/raw/games")

ENDPOINTS = {
    "game": "games/{season}/{game_id}",
    "stats": "games/stats/{season}/{game_id}",
    "shotmap": "shotmap/{season}/{game_id}",
}

REQUEST_DELAY = 1
MAX_RETRIES = 5


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


def download_game_data(season: int, game_id: int) -> None:
    for data_type, endpoint in ENDPOINTS.items():

        output_dir = GAMES_DIR / str(season) / data_type
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = (
            output_dir
            / f"{data_type}_{season}_{game_id}.json"
        )

        if output_file.exists():
            print(f"Skip: {output_file}")
            continue

        url = f"{BASE_URL}/{endpoint.format(
            season=season,
            game_id=game_id
        )}"

        response = get_with_retry(url)

        output_file.write_bytes(response.content)

        print(f"Saved: {output_file}")

        time.sleep(REQUEST_DELAY)


def process_schedule(schedule_file: Path) -> None:
    with schedule_file.open("r", encoding="utf-8") as file:
        games = json.load(file)

    for game in games:
        season = game["season"]
        game_id = game["id"]

        download_game_data(season, game_id)


def main() -> None:
    schedule_files = sorted(
        SCHEDULE_DIR.glob("schedule_*_runkosarja.json")
    )

    for schedule_file in schedule_files:
        print(f"\nProcessing: {schedule_file}")

        process_schedule(schedule_file)


if __name__ == "__main__":
    main()