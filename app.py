# app.py
# ---------------------------------------------------------
# Main Flask server. Chalane ka tarika: python app.py
#
# NAYA STRUCTURE: Poora exam ab 6 FIXED SECTIONS (Q1-Q6) me
# bata hai, har ek ka apna question-type hai:
#   Q1 - single-select (1 mark)      Q4 - True/False (1 mark)
#   Q2 - multi-select 2/4 (2 marks)  Q5 - Match the Following
#   Q3 - multi-select 3/5 (3 marks)  Q6 - Coding (manual grading)
# Har section ke pool me se "any N of M" attempt karna hota hai.
# Poora exam EK HI PAGE par hai (Q1..Q6 tabs, JS se switch hote
# hai) - isse Next/Back par answers apne aap preserve rehte hai,
# kyunki sab EK HI <form> ka hissa hai.
# ---------------------------------------------------------

from flask import Flask, render_template, request, redirect, url_for, session, Response
import random
import json
import csv
import io
from datetime import datetime, timezone
from functools import wraps

import config
from db import get_db_connection

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


# ===========================================================
# HELPERS
# ===========================================================

def get_active_exam_settings(conn):
    return conn.execute("SELECT * FROM exam_settings WHERE id = 1").fetchone()


def shuffle_select_options(q_row, num_options):
    """
    Single/multi-select question ke options (A..D ya A..E) shuffle
    karta hai aur naye labels ke against sahi answers wapas deta hai.
    Return: (options_list [[label,text],...], new_correct_labels [list])
    """
    letters = ["A", "B", "C", "D", "E"][:num_options]
    original = [(L, q_row[f"option_{L.lower()}"]) for L in letters]

    correct_labels_orig = set(x.strip().upper() for x in q_row["correct_options"].split(","))
    correct_texts = set(text for (L, text) in original if L in correct_labels_orig)

    shuffled = original.copy()
    random.shuffle(shuffled)

    new_labels = letters
    options_list = []
    new_correct = []
    for new_label, (old_label, text) in zip(new_labels, shuffled):
        options_list.append([new_label, text])
        if text in correct_texts:
            new_correct.append(new_label)

    return options_list, new_correct


def build_full_paper(conn, subject, chapter):
    """
    Poore exam ka paper banata hai - HAR SECTION (Q1-Q6) ke liye:
      1. Us section ke pool me se "num_to_attempt" questions RANDOMLY
         pick karta hai (jaise 12 me se 10) - taaki har student ko
         thodi alag selection mile.
      2. select-type questions ke options bhi shuffle karta hai.
      3. match-type questions ke right-side options bhi shuffle
         karta hai.
      4. Har question/set ka "grading info" (sahi jawaab, marks)
         alag se store karta hai - taaki SUBMIT ke waqt isi se
         marks nikale ja sake (dubara database query na karni pade
         aur data consistent rahe agar page refresh ho).

    Return: paper_data dictionary - isi ko JSON bana kar
    students.question_order column me save karte hai.
    """
    sections = conn.execute("SELECT * FROM sections ORDER BY order_index").fetchall()

    paper_sections = []
    grading = {}

    for sec in sections:
        pool = conn.execute(
            "SELECT * FROM questions WHERE section_key = ? AND subject = ? AND chapter = ?",
            (sec["section_key"], subject, chapter)
        ).fetchall()

        pick_count = min(sec["num_to_attempt"], len(pool))
        sampled = random.sample(pool, pick_count) if pool else []

        section_questions = []

        for q in sampled:
            qtype = sec["question_type"]

            if qtype in ("single_select", "multi_select"):
                options_list, correct = shuffle_select_options(q, sec["num_options"])
                section_questions.append({
                    "id": q["id"], "text": q["question_text"],
                    "options": options_list, "marks": q["marks"],
                })
                grading[str(q["id"])] = {"type": qtype, "correct": correct, "marks": q["marks"]}

            elif qtype == "true_false":
                section_questions.append({
                    "id": q["id"], "text": q["question_text"],
                    "options": [["TRUE", "True"], ["FALSE", "False"]], "marks": q["marks"],
                })
                grading[str(q["id"])] = {"type": "true_false", "correct": [q["correct_options"].strip().upper()], "marks": q["marks"]}

            elif qtype == "match":
                pairs = json.loads(q["match_pairs"])
                right_values = [p["right"] for p in pairs]
                shuffled_right = right_values.copy()
                random.shuffle(shuffled_right)

                section_questions.append({
                    "id": q["id"], "text": q["question_text"],
                    "left_items": [p["left"] for p in pairs],
                    "right_options": shuffled_right,
                    "marks": q["marks"],
                })
                grading[str(q["id"])] = {
                    "type": "match", "marks": q["marks"],
                    "pairs": pairs,   # [{"left":..,"right":correct_answer}, ...] in original left-order
                }

            elif qtype == "coding":
                section_questions.append({
                    "id": q["id"], "text": q["question_text"], "marks": q["marks"],
                })
                grading[str(q["id"])] = {"type": "coding", "marks": q["marks"]}

        paper_sections.append({
            "key": sec["section_key"], "title": sec["title"],
            "type": sec["question_type"], "instructions": sec["instructions"],
            "questions": section_questions,
        })

    return {"sections": paper_sections, "grading": grading}


def total_paper_marks(paper_data):
    return sum(g["marks"] for g in paper_data["grading"].values())


def has_coding_section(paper_data):
    return any(sec["type"] == "coding" and len(sec["questions"]) > 0 for sec in paper_data["sections"])


def login_required(view_function):
    @wraps(view_function)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return view_function(*args, **kwargs)
    return wrapper


def get_lan_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
    except Exception:
        ip_address = "127.0.0.1"
    finally:
        s.close()
    return ip_address


# ===========================================================
# STUDENT ROUTES
# ===========================================================

@app.route("/")
def home():
    return redirect(url_for("exam_login"))


@app.route("/exam/login")
def exam_login():
    return render_template("login.html")


@app.route("/exam/start", methods=["POST"])
def start_exam():
    name = request.form.get("name", "").strip()
    roll_no = request.form.get("roll_no", "").strip()

    if not name or not roll_no:
        return render_template("login.html", error="Please enter both your name and roll number.")

    conn = get_db_connection()

    # ROSTER VERIFICATION (agar roster khali hai to skip ho jata hai)
    roster_count = conn.execute("SELECT COUNT(*) FROM roster").fetchone()[0]
    if roster_count > 0:
        roster_entry = conn.execute("SELECT * FROM roster WHERE roll_no = ?", (roll_no,)).fetchone()
        if roster_entry is None:
            conn.close()
            return render_template("login.html", error="This roll number was not found in our student list. Please check with your teacher.")
        if roster_entry["name"].strip().lower() != name.strip().lower():
            conn.close()
            return render_template("login.html", error="The name does not match our records for this roll number. Please check with your teacher.")

    settings = get_active_exam_settings(conn)
    if settings is None or not settings["active_subject"]:
        conn.close()
        return render_template("login.html", error="No exam is active right now. Please contact the exam administrator.")

    paper_data = build_full_paper(conn, settings["active_subject"], settings["active_chapter"])

    total_questions = sum(len(sec["questions"]) for sec in paper_data["sections"])
    if total_questions == 0:
        conn.close()
        return render_template("login.html", error="No questions available for this exam yet. Please contact the exam administrator.")

    duration_seconds = settings["duration_minutes"] * 60
    paper_data["duration_seconds"] = duration_seconds

    cursor = conn.execute(
        """
        INSERT INTO students (name, roll_no, total_questions, total_marks, question_order)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, roll_no, total_questions, total_paper_marks(paper_data), json.dumps(paper_data))
    )
    conn.commit()
    student_id = cursor.lastrowid
    conn.close()

    session["student_id"] = student_id
    return redirect(url_for("take_exam"))


@app.route("/exam/take")
def take_exam():
    student_id = session.get("student_id")
    if not student_id:
        return redirect(url_for("exam_login"))

    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()

    if student is None:
        conn.close()
        return redirect(url_for("exam_login"))

    if student["submit_time"] is not None:
        conn.close()
        return redirect(url_for("already_submitted"))

    paper_data = json.loads(student["question_order"])

    # Refresh-safe timer (UTC dono taraf, taaki timezone-mismatch bug na aaye)
    start_time = datetime.strptime(student["start_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    elapsed_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
    remaining_seconds = max(0, int(paper_data["duration_seconds"] - elapsed_seconds))

    if remaining_seconds <= 0:
        conn.close()
        return redirect(url_for("submit_exam"))

    conn.close()

    return render_template(
        "exam.html",
        sections=paper_data["sections"],
        student_name=student["name"],
        roll_no=student["roll_no"],
        duration_seconds=remaining_seconds,
        total_marks=student["total_marks"],
    )


@app.route("/exam/submit", methods=["GET", "POST"])
def submit_exam():
    student_id = session.get("student_id")
    if not student_id:
        return redirect(url_for("exam_login"))

    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()

    if student is None:
        conn.close()
        return redirect(url_for("exam_login"))

    if student["submit_time"] is not None:
        conn.close()
        return redirect(url_for("already_submitted"))

    paper_data = json.loads(student["question_order"])
    grading = paper_data["grading"]

    auto_obtained = 0        # Q1-Q5 (auto-graded) marks
    auto_total = 0            # Q1-Q5 total possible marks
    coding_total = 0          # Q6 total possible marks (pending grading)
    has_coding = False

    for qid_str, g in grading.items():
        qid = int(qid_str)
        qtype = g["type"]
        marks = g["marks"]

        if qtype in ("single_select", "multi_select", "true_false"):
            auto_total += marks
            correct_set = set(g["correct"])

            if qtype == "true_false" or (qtype == "single_select"):
                val = request.form.get(f"q_{qid}")
                selected = [val] if val else []
            else:
                selected = request.form.getlist(f"q_{qid}")

            selected_set = set(selected)
            marks_obtained = len(selected_set & correct_set)
            auto_obtained += marks_obtained

            conn.execute(
                "INSERT INTO answers (student_id, question_id, section_key, selected_option, marks_obtained, max_marks) VALUES (?, ?, ?, ?, ?, ?)",
                (student_id, qid, None, ",".join(selected), marks_obtained, marks)
            )

        elif qtype == "match":
            auto_total += marks
            pairs = g["pairs"]
            correct_count = 0
            student_choices = []
            for i, pair in enumerate(pairs):
                chosen = request.form.get(f"match_{qid}_{i}", "")
                student_choices.append(chosen)
                if chosen == pair["right"]:
                    correct_count += 1
            auto_obtained += correct_count

            conn.execute(
                "INSERT INTO answers (student_id, question_id, section_key, selected_option, marks_obtained, max_marks) VALUES (?, ?, ?, ?, ?, ?)",
                (student_id, qid, None, json.dumps(student_choices), correct_count, marks)
            )

        elif qtype == "coding":
            has_coding = True
            coding_total += marks
            code_text = request.form.get(f"code_{qid}", "").strip()

            # marks_obtained YAHA NULL rehta hai - Admin baad me
            # manually grade karega, tabhi ye bharega.
            conn.execute(
                "INSERT INTO answers (student_id, question_id, section_key, answer_text, marks_obtained, max_marks) VALUES (?, ?, ?, ?, NULL, ?)",
                (student_id, qid, None, code_text, marks)
            )

    # Agar exam me koi coding section hi nahi hai (ya usme 0
    # questions the), to "coding_graded" turant True kar dete hai -
    # taaki result "pending" na dikhe jab grade karne layak kuch hai hi nahi.
    coding_graded = 0 if has_coding else 1

    # Score sirf tab FINAL hai jab coding bhi grade ho chuka ho.
    # Tab tak humein bas AUTO-graded portion pata hai.
    if coding_graded:
        final_score = round((auto_obtained / student["total_marks"]) * 100, 2) if student["total_marks"] else 0
    else:
        final_score = None  # Admin grade karega tab calculate hoga

    conn.execute(
        """
        UPDATE students
        SET submit_time = CURRENT_TIMESTAMP,
            obtained_marks = ?,
            coding_graded = ?,
            score = ?
        WHERE id = ?
        """,
        (auto_obtained, coding_graded, final_score, student_id)
    )
    conn.commit()
    conn.close()

    return render_template("thankyou.html", student_name=student["name"])


@app.route("/exam/already-submitted")
def already_submitted():
    student_id = session.get("student_id")
    if not student_id:
        return redirect(url_for("exam_login"))

    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    conn.close()

    if student is None or student["submit_time"] is None:
        return redirect(url_for("exam_login"))

    return render_template("thankyou.html", student_name=student["name"])


# ===========================================================
# ADMIN PANEL
# ===========================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password", "") == config.ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))
        return render_template("admin_login.html", error="Incorrect password. Please try again.")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    conn = get_db_connection()
    total_questions = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    total_students = conn.execute("SELECT COUNT(*) FROM students WHERE submit_time IS NOT NULL").fetchone()[0]
    pending_grading = conn.execute("SELECT COUNT(*) FROM students WHERE submit_time IS NOT NULL AND coding_graded = 0").fetchone()[0]
    settings = get_active_exam_settings(conn)
    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_questions=total_questions,
        total_students=total_students,
        pending_grading=pending_grading,
        active_subject=settings["active_subject"] if settings else None,
        active_chapter=settings["active_chapter"] if settings else None,
    )


@app.route("/admin/questions")
@login_required
def admin_questions():
    conn = get_db_connection()
    filter_section = request.args.get("section", "").strip()

    if filter_section:
        questions = conn.execute("SELECT * FROM questions WHERE section_key = ? ORDER BY id", (filter_section,)).fetchall()
    else:
        questions = conn.execute("SELECT * FROM questions ORDER BY section_key, id").fetchall()

    sections = conn.execute("SELECT * FROM sections ORDER BY order_index").fetchall()
    conn.close()

    return render_template("admin_questions.html", questions=questions, sections=sections, filter_section=filter_section)


@app.route("/admin/questions/add", methods=["GET", "POST"])
@login_required
def admin_add_question():
    conn = get_db_connection()
    sections = conn.execute("SELECT * FROM sections ORDER BY order_index").fetchall()

    if request.method == "POST":
        section_key = request.form.get("section_key", "")
        section = conn.execute("SELECT * FROM sections WHERE section_key = ?", (section_key,)).fetchone()

        if section is None:
            conn.close()
            return render_template("admin_question_form.html", edit=False, sections=sections, error="Please choose a valid section.", form_data=request.form)

        subject = request.form.get("subject", "").strip()
        chapter = request.form.get("chapter", "").strip()
        question_text = request.form.get("question_text", "").strip()
        qtype = section["question_type"]

        if not subject or not chapter or not question_text:
            conn.close()
            return render_template("admin_question_form.html", edit=False, sections=sections, error="Subject, chapter and question text are required.", form_data=request.form)

        if qtype in ("single_select", "multi_select"):
            num_opts = section["num_options"]
            letters = ["A", "B", "C", "D", "E"][:num_opts]
            option_values = {L: request.form.get(f"option_{L.lower()}", "").strip() for L in letters}
            correct_list = request.form.getlist("correct_options")

            if not all(option_values.values()) or len(correct_list) != section["correct_count"]:
                conn.close()
                return render_template("admin_question_form.html", edit=False, sections=sections,
                                        error=f"All {num_opts} options are required, and exactly {section['correct_count']} correct answer(s) must be selected.",
                                        form_data=request.form)

            conn.execute(
                """INSERT INTO questions (subject, chapter, section_key, question_type, question_text,
                   option_a, option_b, option_c, option_d, option_e, correct_option, correct_options, marks)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (subject, chapter, section_key, qtype, question_text,
                 option_values.get("A"), option_values.get("B"), option_values.get("C"), option_values.get("D"), option_values.get("E"),
                 correct_list[0], ",".join(sorted(correct_list)), section["correct_count"])
            )

        elif qtype == "true_false":
            correct = request.form.get("tf_correct", "")
            if correct not in ("TRUE", "FALSE"):
                conn.close()
                return render_template("admin_question_form.html", edit=False, sections=sections, error="Please select True or False as the correct answer.", form_data=request.form)
            conn.execute(
                """INSERT INTO questions (subject, chapter, section_key, question_type, question_text, correct_option, correct_options, marks)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (subject, chapter, section_key, qtype, question_text, correct, correct, 1)
            )

        elif qtype == "match":
            lefts = request.form.getlist("match_left")
            rights = request.form.getlist("match_right")
            pairs = [{"left": l.strip(), "right": r.strip()} for l, r in zip(lefts, rights) if l.strip() and r.strip()]
            if len(pairs) < 2:
                conn.close()
                return render_template("admin_question_form.html", edit=False, sections=sections, error="Please provide at least 2 matching pairs.", form_data=request.form)
            conn.execute(
                """INSERT INTO questions (subject, chapter, section_key, question_type, question_text, match_pairs, marks)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (subject, chapter, section_key, qtype, question_text, json.dumps(pairs), len(pairs))
            )

        elif qtype == "coding":
            try:
                marks = int(request.form.get("coding_marks", "5"))
            except ValueError:
                marks = 5
            conn.execute(
                """INSERT INTO questions (subject, chapter, section_key, question_type, question_text, marks)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (subject, chapter, section_key, qtype, question_text, marks)
            )

        conn.commit()
        conn.close()
        return redirect(url_for("admin_questions"))

    conn.close()
    return render_template("admin_question_form.html", edit=False, sections=sections, question=None)


@app.route("/admin/questions/edit/<int:question_id>", methods=["GET", "POST"])
@login_required
def admin_edit_question(question_id):
    conn = get_db_connection()
    sections = conn.execute("SELECT * FROM sections ORDER BY order_index").fetchall()
    question = conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()

    if question is None:
        conn.close()
        return redirect(url_for("admin_questions"))

    section = conn.execute("SELECT * FROM sections WHERE section_key = ?", (question["section_key"],)).fetchone()

    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        chapter = request.form.get("chapter", "").strip()
        question_text = request.form.get("question_text", "").strip()
        qtype = section["question_type"]

        if qtype in ("single_select", "multi_select"):
            num_opts = section["num_options"]
            letters = ["A", "B", "C", "D", "E"][:num_opts]
            option_values = {L: request.form.get(f"option_{L.lower()}", "").strip() for L in letters}
            correct_list = request.form.getlist("correct_options")
            conn.execute(
                """UPDATE questions SET subject=?, chapter=?, question_text=?,
                   option_a=?, option_b=?, option_c=?, option_d=?, option_e=?,
                   correct_option=?, correct_options=? WHERE id=?""",
                (subject, chapter, question_text,
                 option_values.get("A"), option_values.get("B"), option_values.get("C"), option_values.get("D"), option_values.get("E"),
                 correct_list[0] if correct_list else "", ",".join(sorted(correct_list)), question_id)
            )

        elif qtype == "true_false":
            correct = request.form.get("tf_correct", "")
            conn.execute(
                "UPDATE questions SET subject=?, chapter=?, question_text=?, correct_option=?, correct_options=? WHERE id=?",
                (subject, chapter, question_text, correct, correct, question_id)
            )

        elif qtype == "match":
            lefts = request.form.getlist("match_left")
            rights = request.form.getlist("match_right")
            pairs = [{"left": l.strip(), "right": r.strip()} for l, r in zip(lefts, rights) if l.strip() and r.strip()]
            conn.execute(
                "UPDATE questions SET subject=?, chapter=?, question_text=?, match_pairs=?, marks=? WHERE id=?",
                (subject, chapter, question_text, json.dumps(pairs), len(pairs), question_id)
            )

        elif qtype == "coding":
            try:
                marks = int(request.form.get("coding_marks", "5"))
            except ValueError:
                marks = 5
            conn.execute(
                "UPDATE questions SET subject=?, chapter=?, question_text=?, marks=? WHERE id=?",
                (subject, chapter, question_text, marks, question_id)
            )

        conn.commit()
        conn.close()
        return redirect(url_for("admin_questions"))

    conn.close()
    # match_pairs JSON string ko yaha Python me hi parse kar rahe hai
    # (Jinja template ke andar JSON parse karne ke liye "fromjson"
    # naam ka koi built-in filter nahi hota, isliye yaha karna zaroori hai)
    existing_pairs = json.loads(question["match_pairs"]) if question["match_pairs"] else []

    return render_template("admin_question_form.html", edit=True, sections=sections, question=question, section=section, existing_pairs=existing_pairs)


@app.route("/admin/questions/delete/<int:question_id>", methods=["POST"])
@login_required
def admin_delete_question(question_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_questions"))


@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    conn = get_db_connection()

    if request.method == "POST":
        active_subject = request.form.get("active_subject", "").strip()
        active_chapter = request.form.get("active_chapter", "").strip()
        try:
            duration_minutes = int(request.form.get("duration_minutes", "90"))
        except ValueError:
            duration_minutes = 90

        conn.execute(
            "INSERT OR REPLACE INTO exam_settings (id, active_subject, active_chapter, duration_minutes) VALUES (1, ?, ?, ?)",
            (active_subject, active_chapter, duration_minutes)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("admin_settings", saved=1))

    subject_chapters = conn.execute("SELECT DISTINCT subject, chapter FROM questions ORDER BY subject, chapter").fetchall()
    current_settings = get_active_exam_settings(conn)
    conn.close()

    return render_template("admin_settings.html", subject_chapters=subject_chapters, current_settings=current_settings, saved=request.args.get("saved"))


@app.route("/admin/results")
@login_required
def admin_results():
    conn = get_db_connection()
    results = conn.execute("SELECT * FROM students WHERE submit_time IS NOT NULL ORDER BY submit_time DESC").fetchall()
    conn.close()
    return render_template("admin_results.html", results=results)


@app.route("/admin/results/export")
@login_required
def admin_export_results():
    conn = get_db_connection()
    results = conn.execute(
        """SELECT name, roll_no, obtained_marks, coding_marks, total_marks, coding_graded, score, start_time, submit_time
           FROM students WHERE submit_time IS NOT NULL ORDER BY submit_time DESC"""
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Roll No", "Auto Marks (Q1-Q5)", "Coding Marks (Q6)", "Total Marks", "Grading Status", "Score (%)", "Start Time", "Submit Time"])
    for row in results:
        status = "Final" if row["coding_graded"] else "Pending Coding Grading"
        writer.writerow([row["name"], row["roll_no"], row["obtained_marks"], row["coding_marks"], row["total_marks"], status, row["score"], row["start_time"], row["submit_time"]])

    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=exam_results.csv"})


# -----------------------------------------------------------
# GRADE CODING ANSWERS (Q6) - MANUAL GRADING
# Jab tak ye na ho, student ka FINAL result "Pending" rehta hai.
# -----------------------------------------------------------
@app.route("/admin/grade-coding")
@login_required
def admin_grade_coding_list():
    conn = get_db_connection()
    pending_students = conn.execute(
        "SELECT * FROM students WHERE submit_time IS NOT NULL AND coding_graded = 0 ORDER BY submit_time ASC"
    ).fetchall()
    graded_students = conn.execute(
        "SELECT * FROM students WHERE submit_time IS NOT NULL AND coding_graded = 1 ORDER BY submit_time DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return render_template("admin_grade_coding.html", pending_students=pending_students, graded_students=graded_students)


@app.route("/admin/grade-coding/<int:student_id>", methods=["GET", "POST"])
@login_required
def admin_grade_coding_student(student_id):
    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if student is None:
        conn.close()
        return redirect(url_for("admin_grade_coding_list"))

    # Is student ke Q6 (coding) answers nikal rahe hai
    coding_answers = conn.execute(
        """SELECT answers.id as answer_id, answers.answer_text, answers.max_marks, answers.marks_obtained,
                  questions.question_text, questions.id as question_id
           FROM answers JOIN questions ON answers.question_id = questions.id
           WHERE answers.student_id = ? AND questions.section_key = 'Q6'""",
        (student_id,)
    ).fetchall()

    if request.method == "POST":
        total_coding_marks = 0
        for ans in coding_answers:
            try:
                given = int(request.form.get(f"marks_{ans['answer_id']}", 0))
            except ValueError:
                given = 0
            given = max(0, min(given, ans["max_marks"]))  # marks max_marks se zyada na ho
            conn.execute("UPDATE answers SET marks_obtained = ? WHERE id = ?", (given, ans["answer_id"]))
            total_coding_marks += given

        # Ab final score calculate karke student record update karte hai
        final_obtained = (student["obtained_marks"] or 0) + total_coding_marks
        final_score = round((final_obtained / student["total_marks"]) * 100, 2) if student["total_marks"] else 0

        conn.execute(
            "UPDATE students SET coding_marks = ?, coding_graded = 1, score = ? WHERE id = ?",
            (total_coding_marks, final_score, student_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("admin_grade_coding_list"))

    conn.close()
    return render_template("admin_grade_coding_student.html", student=student, coding_answers=coding_answers)


if __name__ == "__main__":
    lan_ip = get_lan_ip()
    print("\n" + "=" * 55)
    print("  BRIGHT EDUCATION - MCQ EXAM SERVER")
    print("=" * 55)
    print(f"  This computer (Server) - use for Admin Panel:")
    print(f"     http://127.0.0.1:5000/admin/login")
    print()
    print(f"  Student computers (same WiFi/LAN) - open in browser:")
    print(f"     http://{lan_ip}:5000")
    print("=" * 55)
    print("  Press CTRL+C to stop the server.\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
