# db.py
# ---------------------------------------------------------
# Database se connection banane ka common helper - taaki
# app.py me baar-baar sqlite3.connect() na likhna pade.
# ---------------------------------------------------------

import sqlite3
import os
import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FULL_PATH = os.path.join(BASE_DIR, config.DATABASE_PATH)


def get_db_connection():
    conn = sqlite3.connect(DB_FULL_PATH)
    conn.row_factory = sqlite3.Row   # column NAME se value nikal sakein
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
