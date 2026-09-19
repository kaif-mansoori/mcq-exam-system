# database/import_questions.py
# ---------------------------------------------------------
# CSV se bulk questions add karne ka tool. SIRF Q1, Q2, Q3, Q4
# (single-select, multi-select, true/false) is CSV tarike se add
# ho sakte hai - Q5 (Match the Following) aur Q6 (Coding) ke
# liye Admin Panel use karo (unka structure CSV ke liye zyada
# complex hai).
#
# KAISE USE KARO:
#   1. database/questions_template.csv Excel me kholo
#   2. Naye questions rows me likho:
#      - section_key: Q1, Q2, Q3, ya Q4
#      - Q1: sirf option_a-d bharo, correct_options me EK letter (jaise "B")
#      - Q2: option_a-d bharo, correct_options me DO letters (jaise "A,C")
#      - Q3: option_a-e (SAB PAANCH) bharo, correct_options me TEEN letters
#      - Q4 (True/False): options SAB KHALI chhodo, correct_options me TRUE ya FALSE likho
#   3. CSV format me save karo, fir chalao:
#        python database/import_questions.py
# ---------------------------------------------------------

import csv
import sqlite3
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "mcq_exam.db")
CSV_PATH = os.path.join(CURRENT_DIR, "questions_template.csv")


def import_questions():
    if not os.path.exists(CSV_PATH):
        print(f"❌ File nahi mili: {CSV_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    sections = {row[0]: row for row in cursor.execute("SELECT section_key, question_type, correct_count FROM sections")}

    added, skipped = 0, 0

    with open(CSV_PATH, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        for row_number, row in enumerate(reader, start=2):
            section_key = row.get("section_key", "").strip().upper()
            subject = row.get("subject", "").strip()
            chapter = row.get("chapter", "").strip()
            question_text = row.get("question_text", "").strip()

            if section_key not in ("Q1", "Q2", "Q3", "Q4"):
                print(f"⚠️  Row {row_number} skip - section_key sirf Q1/Q2/Q3/Q4 ho sakta hai (CSV se Q5/Q6 add nahi hote).")
                skipped += 1
                continue

            if not subject or not chapter or not question_text:
                print(f"⚠️  Row {row_number} skip - subject/chapter/question_text khali hai.")
                skipped += 1
                continue

            sec_type, correct_count = sections[section_key][1], sections[section_key][2]
            raw_correct = row.get("correct_options", "").strip().upper()

            if sec_type == "true_false":
                if raw_correct not in ("TRUE", "FALSE"):
                    print(f"⚠️  Row {row_number} skip - Q4 ke liye correct_options TRUE ya FALSE hona chahiye.")
                    skipped += 1
                    continue
                cursor.execute(
                    "INSERT INTO questions (subject, chapter, section_key, question_type, question_text, correct_option, correct_options, marks) VALUES (?,?,?,?,?,?,?,?)",
                    (subject, chapter, section_key, sec_type, question_text, raw_correct, raw_correct, 1)
                )
                added += 1
                continue

            # single_select / multi_select
            correct_labels = [x.strip() for x in raw_correct.split(",") if x.strip()]
            num_opts = 5 if section_key == "Q3" else 4
            opts = {L: row.get(f"option_{L.lower()}", "").strip() for L in ["A", "B", "C", "D", "E"][:num_opts]}

            if not all(opts.values()) or len(correct_labels) != correct_count:
                print(f"⚠️  Row {row_number} skip - {num_opts} options chahiye aur exactly {correct_count} correct_options.")
                skipped += 1
                continue

            cursor.execute(
                """INSERT INTO questions (subject, chapter, section_key, question_type, question_text,
                   option_a, option_b, option_c, option_d, option_e, correct_option, correct_options, marks)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (subject, chapter, section_key, sec_type, question_text,
                 opts.get("A"), opts.get("B"), opts.get("C"), opts.get("D"), opts.get("E"),
                 correct_labels[0], ",".join(correct_labels), correct_count)
            )
            added += 1

    conn.commit()
    conn.close()
    print(f"\n✅ {added} naye questions add ho gaye!")
    if skipped:
        print(f"⚠️  {skipped} rows skip hui - upar dekho kyu.")


if __name__ == "__main__":
    print("📥 CSV se questions import ho rahe hai...\n")
    import_questions()
