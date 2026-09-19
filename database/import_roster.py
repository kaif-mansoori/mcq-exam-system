# database/import_roster.py
# ---------------------------------------------------------
# CSV se student list (roll number + naam) database me daalta hai,
# taaki exam ke waqt galat naam/roll number block ho sake.
# Chalane ka tarika: python database/import_roster.py
# Ye HAR BAAR chalane par PURANI list HATA KAR CSV se NAYI list
# se replace kar deta hai.
# ---------------------------------------------------------

import csv
import sqlite3
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "mcq_exam.db")
CSV_PATH = os.path.join(CURRENT_DIR, "students_roster_template.csv")


def import_roster():
    if not os.path.exists(CSV_PATH):
        print(f"❌ File nahi mili: {CSV_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM roster")

    added, skipped = 0, 0
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        for row_number, row in enumerate(reader, start=2):
            roll_no = row.get("roll_no", "").strip()
            name = row.get("name", "").strip()
            student_class = row.get("class", "").strip()
            if not roll_no or not name:
                print(f"⚠️  Row {row_number} skip - roll_no ya name khali hai.")
                skipped += 1
                continue
            cursor.execute("INSERT OR REPLACE INTO roster (roll_no, name, class) VALUES (?, ?, ?)", (roll_no, name, student_class))
            added += 1

    conn.commit()
    conn.close()
    print(f"\n✅ Roster update ho gaya! {added} students ki list active hai.")
    if skipped:
        print(f"⚠️  {skipped} rows skip hui.")


if __name__ == "__main__":
    print("📥 CSV se student roster import ho raha hai...\n")
    import_roster()
