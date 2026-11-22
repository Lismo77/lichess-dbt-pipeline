import os
import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("LICHESS_TOKEN")
username = "lismobegins"

output_path = f"data/raw/{username}_games.jsonl"

response = requests.get(
    f"https://lichess.org/api/games/user/{username}",
    headers={
        "Accept": "application/x-ndjson",
        "Authorization": f"Bearer {token}"
    },
    params={"opening":"true"},
    stream=True
)

game_count = 0
with open(output_path, "w") as f:
    for line in response.iter_lines():
        if line:
            f.write(line.decode("utf-8") + "\n")
            game_count += 1

print(f"Saved {game_count} games to {output_path}")

