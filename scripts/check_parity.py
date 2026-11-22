"""Verify Postgres and Databricks builds agree: every model, compared as row sets.

Run after `dbt build` on both targets. Passing tests only prove each platform is
self-consistent; this proves they produce the same answers.

Usage: venv/bin/python scripts/check_parity.py
Exit code 1 on any difference.
"""
import os
import sys
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal

from databricks import sql

from common import connect

MODELS = ["stg_games", "fct_my_games", "dim_openings", "agg_outcome_by_openings", "agg_outcome_summary_by_speed"]


def norm(v):
	"""Erase representation differences that aren't data differences."""
	if isinstance(v, datetime):  # Postgres timestamptz vs Databricks naive UTC
		v = v.astimezone(timezone.utc) if v.tzinfo else v.replace(tzinfo=timezone.utc)
		return v.isoformat()
	if isinstance(v, (Decimal, float)):  # numeric vs double/decimal scale
		return round(float(v), 4)
	return v


def fetch(cur, query):
	cur.execute(query)
	cols = [d[0] for d in cur.description]
	return cols, {tuple(norm(v) for v in r) for r in cur.fetchall()}


def main():
	dbx = sql.connect(
		server_hostname=os.environ["DATABRICKS_HOST"],
		http_path=os.environ["DATABRICKS_HTTP_PATH"],
		access_token=os.environ["DATABRICKS_TOKEN"],
	)
	all_ok = True
	with connect() as pg, closing(dbx), closing(dbx.cursor()) as dcur:
		dcur.execute("set time zone 'UTC'")
		for m in MODELS:
			pcols, prows = fetch(pg.cursor(), f"select * from dbt_dev.{m}")
			dcols, drows = fetch(dcur, f"select * from analytics.dbt_dev.{m}")
			ok = pcols == dcols and prows == drows
			all_ok &= ok
			print(f"{'OK  ' if ok else 'DIFF'} {m:30} postgres={len(prows):5}  databricks={len(drows):5}")
			if pcols != dcols:
				print(f"     columns differ: {pcols} vs {dcols}")
			for label, extra in (("only in postgres  ", prows - drows), ("only in databricks", drows - prows)):
				for r in sorted(extra, key=str)[:3]:
					print(f"     {label}: {r}")
	print("All models identical." if all_ok else "Differences found.")
	sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
	main()
