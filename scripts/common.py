"""Shared config for the extract/load scripts: paths, username, DB connection."""
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

# Resolve paths from this file, not the shell's cwd, so scripts work from anywhere.
REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"

load_dotenv(REPO_ROOT / ".env")

USERNAME = os.getenv("LICHESS_USERNAME", "lismobegins")


def connect():
	return psycopg.connect(
		host=os.getenv("PG_HOST"),
		port=os.getenv("PG_PORT", "5432"),
		dbname=os.getenv("PG_DB"),
		user=os.getenv("PG_USER"),
		password=os.getenv("PG_PASSWORD"),
	)
