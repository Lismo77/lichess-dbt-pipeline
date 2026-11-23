"""Render the rating-history chart for the README from agg_rating_daily (Postgres).

Writes docs/rating_history_light.png and docs/rating_history_dark.png; the README
shows whichever matches the reader's GitHub theme.

Usage: venv/bin/python scripts/plot_rating_history.py   (after `dbt build`)

Design choices:
- Step line (steps-post): rating only changes on days I play and is flat in
  between, so straight diagonals between play days would imply drift that
  didn't happen.
- Provisional days omitted (agg_rating_daily.includes_provisional): the jump
  from Lichess's 1500 starting rating would flatten the rest of the history.
- Speeds with fewer than MIN_DAYS of established play are skipped (bullet: 1 game).
- Colors are the validated categorical slots 1-2 (CVD-checked, light and dark).
"""
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")  # render to file; no display needed
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from common import REPO_ROOT, connect

MIN_DAYS = 5
OUT_DIR = REPO_ROOT / "docs"

# Fixed order: blitz always slot 1, rapid always slot 2 (color follows the entity).
SPEED_SLOTS = ["blitz", "rapid"]

THEMES = {
	"light": {
		"surface": "#fcfcfb", "text": "#0b0b0b", "text_secondary": "#52514e",
		"muted": "#898781", "grid": "#e1e0d9", "series": ["#2a78d6", "#eb6834"],
	},
	"dark": {
		"surface": "#1a1a19", "text": "#f0efec", "text_secondary": "#c3c2b7",
		"muted": "#898781", "grid": "#2c2c2a", "series": ["#3987e5", "#d95926"],
	},
}

QUERY = """
	select speed, played_on, closing_rating
	from dbt_dev.agg_rating_daily
	where not includes_provisional
	order by speed, played_on
"""


def load():
	series = defaultdict(lambda: ([], []))
	with connect() as conn:
		for speed, played_on, rating in conn.execute(QUERY):
			series[speed][0].append(played_on)
			series[speed][1].append(rating)
	return {s: series[s] for s in SPEED_SLOTS if len(series[s][0]) >= MIN_DAYS}


def render(series, theme_name):
	t = THEMES[theme_name]
	plt.rcParams["font.family"] = "sans-serif"
	fig, ax = plt.subplots(figsize=(10, 4.6), dpi=150)
	fig.patch.set_facecolor(t["surface"])
	ax.set_facecolor(t["surface"])

	# A rating holds until the next game, so carry every line flat to the latest
	# day in the data — a speed I haven't played lately still has that rating today.
	last_day = max(days[-1] for days, _ in series.values())

	for slot, speed in enumerate(SPEED_SLOTS):
		if speed not in series:
			continue
		days, ratings = series[speed]
		if days[-1] < last_day:
			days, ratings = days + [last_day], ratings + [ratings[-1]]
		color = t["series"][slot]
		ax.plot(days, ratings, drawstyle="steps-post", color=color, linewidth=2, label=speed.capitalize(), solid_joinstyle="round")
		# End marker + direct label: identity is never color-alone.
		ax.plot(days[-1], ratings[-1], "o", markersize=8, color=color, markeredgecolor=t["surface"], markeredgewidth=2, zorder=3)
		ax.annotate(f"{speed.capitalize()}  {ratings[-1]}", (days[-1], ratings[-1]), xytext=(10, 0),
			textcoords="offset points", va="center", fontsize=10, fontweight="bold", color=t["text"])

	# Recessive frame: horizontal hairline grid only, muted axis text.
	ax.grid(axis="y", color=t["grid"], linewidth=0.8)
	ax.set_axisbelow(True)
	for side in ("top", "right", "left"):
		ax.spines[side].set_visible(False)
	ax.spines["bottom"].set_color(t["grid"])
	ax.tick_params(colors=t["muted"], labelsize=9, length=0, pad=6)
	ax.xaxis.set_major_locator(mdates.MonthLocator())
	ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
	ax.margins(x=0.02)
	ax.set_xlim(right=ax.get_xlim()[1] + 12)  # room for end labels

	# Legend in the header row (figure coords), clear of the data.
	legend = fig.legend(loc="upper left", bbox_to_anchor=(0.053, 0.875), frameon=False, fontsize=9, ncol=2,
		labelcolor=t["text_secondary"], handlelength=1.6)
	for handle in legend.legend_handles:
		handle.set_linewidth(3)

	fig.text(0.06, 0.95, "Lichess rating by day", fontsize=14, fontweight="bold", color=t["text"])
	fig.text(0.06, 0.895, "Closing rating on days played · rated games vs humans · provisional days omitted · days in America/New_York",
		fontsize=9, color=t["text_secondary"])
	fig.subplots_adjust(left=0.06, right=0.9, top=0.79, bottom=0.1)

	out = OUT_DIR / f"rating_history_{theme_name}.png"
	fig.savefig(out, facecolor=t["surface"])
	plt.close(fig)
	return out


def main():
	OUT_DIR.mkdir(exist_ok=True)
	series = load()
	for theme in THEMES:
		print(f"Wrote {render(series, theme).relative_to(REPO_ROOT)}")


if __name__ == "__main__":
	main()
