# database/init_db.py
import sqlite3
import os
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "mcq_exam.db")


def add_column_if_missing(cursor, table, column, col_definition):
    cursor.execute(f"PRAGMA table_info({table})")
    existing_columns = [row[1] for row in cursor.fetchall()]
    if column not in existing_columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_definition}")
        print(f"   + Column '{column}' add hua table '{table}' me")


def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_key TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            question_type TEXT NOT NULL,
            num_options INTEGER,
            correct_count INTEGER,
            num_to_attempt INTEGER NOT NULL,
            order_index INTEGER NOT NULL,
            instructions TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            chapter TEXT NOT NULL,
            section_key TEXT,
            question_type TEXT,
            question_text TEXT NOT NULL,
            option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT, option_e TEXT,
            correct_option TEXT,
            correct_options TEXT,
            match_pairs TEXT,
            marks INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_no TEXT NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            submit_time TIMESTAMP,
            total_questions INTEGER,
            correct_answers INTEGER,
            total_marks INTEGER,
            obtained_marks REAL,
            coding_marks REAL,
            coding_graded INTEGER DEFAULT 0,
            score REAL,
            question_order TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            section_key TEXT,
            selected_option TEXT,
            answer_text TEXT,
            marks_obtained INTEGER,
            max_marks INTEGER,
            FOREIGN KEY (student_id) REFERENCES students (id),
            FOREIGN KEY (question_id) REFERENCES questions (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exam_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            active_subject TEXT,
            active_chapter TEXT,
            duration_minutes INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roster (
            roll_no TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            class TEXT
        )
    """)

    conn.commit()
    print("✅ Tables ban gaye (ya pehle se maujood the): sections, questions, students, answers, exam_settings, roster")
    conn.close()


def migrate_schema():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    print("🔧 Database upgrade ho raha hai...")

    add_column_if_missing(cursor, "questions", "section_key", "TEXT")
    add_column_if_missing(cursor, "questions", "question_type", "TEXT")
    add_column_if_missing(cursor, "questions", "option_e", "TEXT")
    add_column_if_missing(cursor, "questions", "correct_options", "TEXT")
    add_column_if_missing(cursor, "questions", "match_pairs", "TEXT")
    add_column_if_missing(cursor, "questions", "marks", "INTEGER DEFAULT 1")

    add_column_if_missing(cursor, "students", "total_marks", "INTEGER")
    add_column_if_missing(cursor, "students", "obtained_marks", "REAL")
    add_column_if_missing(cursor, "students", "coding_marks", "REAL")
    add_column_if_missing(cursor, "students", "coding_graded", "INTEGER DEFAULT 0")

    add_column_if_missing(cursor, "answers", "section_key", "TEXT")
    add_column_if_missing(cursor, "answers", "answer_text", "TEXT")
    add_column_if_missing(cursor, "answers", "max_marks", "INTEGER")

    cursor.execute("""
        UPDATE questions SET correct_options = correct_option
        WHERE correct_options IS NULL AND correct_option IS NOT NULL
    """)
    cursor.execute("SELECT id, correct_options FROM questions WHERE marks IS NULL OR marks = 1")
    for row in cursor.fetchall():
        qid, correct = row
        if correct:
            cursor.execute("UPDATE questions SET marks = ? WHERE id = ?", (len(correct.split(",")), qid))

    # Q5 aur Q6 ka "attempt count" 2 se 3 kar rahe hai (taaki total
    # exam 100 marks ka bane: Q1(10)+Q2(20)+Q3(30)+Q4(10)+Q5(15)+Q6(15)=100).
    # Ye UPDATE hai (fresh INSERT nahi), isliye ye tumhare EXISTING
    # database par bhi turant apply ho jayega, bina kisi data ko
    # delete kiye.
    cursor.execute("UPDATE sections SET num_to_attempt = 3, instructions = 'Attempt any 3 out of the 4 sets below. Match each item on the left with its correct match on the right.' WHERE section_key = 'Q5'")
    cursor.execute("UPDATE sections SET num_to_attempt = 3, title = 'Section 6 - Programming (Choose Any 3 of 4)', instructions = 'Attempt any 3 out of the 4 questions below. Write your code in the box provided. These will be graded manually by your teacher.' WHERE section_key = 'Q6'")

    conn.commit()
    conn.close()
    print("✅ Database upgrade complete.\n")


def insert_sections():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sections")
    if cursor.fetchone()[0] > 0:
        print("ℹ️  Sections pehle se defined hai - skip kar rahe hai.")
        conn.close()
        return

    sections = [
        ("Q1", "Section 1 - One Correct Answer (1 Mark Each)", "single_select", 4, 1, 10, 1,
         "Attempt any 10 out of the 12 questions below. Select ONE correct answer."),
        ("Q2", "Section 2 - Two Correct Answers (2 Marks Each)", "multi_select", 4, 2, 10, 2,
         "Attempt any 10 out of the 12 questions below. Select TWO correct answers for each."),
        ("Q3", "Section 3 - Three Correct Answers (3 Marks Each)", "multi_select", 5, 3, 10, 3,
         "Attempt any 10 out of the 12 questions below. Select THREE correct answers for each."),
        ("Q4", "Section 4 - True or False (1 Mark Each)", "true_false", None, 1, 10, 4,
         "Attempt any 10 out of the 12 statements below."),
        ("Q5", "Section 5 - Match the Following", "match", None, None, 3, 5,
         "Attempt any 3 out of the 4 sets below. Match each item on the left with its correct match on the right."),
        ("Q6", "Section 6 - Programming (Choose Any 3 of 4)", "coding", None, None, 3, 6,
         "Attempt any 3 out of the 4 questions below. Write your code in the box provided. These will be graded manually by your teacher."),
    ]
    cursor.executemany("""
        INSERT INTO sections (section_key, title, question_type, num_options, correct_count, num_to_attempt, order_index, instructions)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, sections)
    conn.commit()
    conn.close()
    print(f"✅ {len(sections)} sections set up (Q1-Q6).")


def insert_demo_questions():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM questions")
    if cursor.fetchone()[0] > 0:
        print(f"ℹ️  Database me pehle se questions maujood hai - demo data skip kar rahe hai.")
        conn.close()
        return

    SUBJECT = "Information Technology (IT) Exam"
    CHAPTER = "Practice Test 1"
    rows = []

    q1_data = [
        ("What does CPU stand for?", "Central Processing Unit", "Computer Personal Unit", "Central Program Utility", "Central Processor Unit-2", "A"),
        ("Which of these is used to type text into a computer?", "Monitor", "Keyboard", "Speaker", "Printer", "B"),
        ("What is the full form of RAM?", "Read Access Memory", "Random Access Memory", "Rapid Access Memory", "Run Access Memory", "B"),
        ("Which of these is an Operating System?", "MS Word", "Windows", "Google Chrome", "Photoshop", "B"),
        ("What does WWW stand for?", "World Wide Web", "World Web Wide", "Wide World Web", "Web World Wide", "A"),
        ("Which key is used to delete a character to the left of the cursor?", "Delete", "Backspace", "Enter", "Shift", "B"),
        ("What is the full form of URL?", "Universal Resource Locator", "Uniform Resource Locator", "Uniform Route Locator", "Universal Route Locator", "B"),
        ("Which of these is an Output device?", "Keyboard", "Mouse", "Monitor", "Scanner", "C"),
        ("What does USB stand for?", "Universal Serial Bus", "United Serial Bus", "Universal System Bus", "United System Bus", "A"),
        ("Which software is mainly used to create spreadsheets?", "MS Word", "MS PowerPoint", "MS Excel", "MS Paint", "C"),
        ("Which of these is a valid file extension for a Word document?", ".docx", ".exe", ".mp3", ".jpg", "A"),
        ("What is the shortcut key to Copy?", "Ctrl+C", "Ctrl+V", "Ctrl+X", "Ctrl+Z", "A"),
    ]
    for qtext, a, b, c, d, correct in q1_data:
        rows.append(("Q1", "single_select", qtext, a, b, c, d, None, correct, None, 1))

    q2_data = [
        ("Which TWO of these are Input devices? (Select 2)", "Keyboard", "Monitor", "Mouse", "Printer", "A,C"),
        ("Which TWO of these are Output devices? (Select 2)", "Keyboard", "Monitor", "Mouse", "Printer", "B,D"),
        ("Which TWO of these are Web Browsers? (Select 2)", "Google Chrome", "MS Word", "Mozilla Firefox", "MS Excel", "A,C"),
        ("Which TWO of these are Storage devices? (Select 2)", "Hard Disk", "Monitor", "Pen Drive", "Keyboard", "A,C"),
        ("Which TWO of these are Programming Languages? (Select 2)", "Python", "MS Word", "Java", "Photoshop", "A,C"),
        ("Which TWO of these are Antivirus software? (Select 2)", "Norton", "MS Paint", "McAfee", "VLC Player", "A,C"),
        ("Which TWO of these are Social Media platforms? (Select 2)", "Facebook", "MS Word", "Instagram", "MS Excel", "A,C"),
        ("Which TWO of these are Operating Systems? (Select 2)", "Windows", "MS Word", "Linux", "Photoshop", "A,C"),
        ("Which TWO of these are Search Engines? (Select 2)", "Google", "MS Excel", "Bing", "MS Word", "A,C"),
        ("Which TWO of these are types of Computer Memory? (Select 2)", "RAM", "Mouse", "ROM", "Keyboard", "A,C"),
        ("Which TWO of these are Cloud Storage services? (Select 2)", "Google Drive", "MS Paint", "Dropbox", "VLC Player", "A,C"),
        ("Which TWO of these are Video Editing software? (Select 2)", "Adobe Premiere", "MS Excel", "Filmora", "MS Access", "A,C"),
    ]
    for qtext, a, b, c, d, correct in q2_data:
        rows.append(("Q2", "multi_select", qtext, a, b, c, d, None, correct, None, 2))

    q3_data = [
        ("Which THREE of these are types of Computer Networks? (Select 3)", "LAN", "WAN", "MAN", "USB", "RAM"),
        ("Which THREE of these are Microsoft Office applications? (Select 3)", "MS Word", "MS Excel", "MS PowerPoint", "Google Chrome", "Adobe Reader"),
        ("Which THREE of these are Input devices? (Select 3)", "Keyboard", "Mouse", "Scanner", "Monitor", "Printer"),
        ("Which THREE of these are Output devices? (Select 3)", "Monitor", "Printer", "Speaker", "Keyboard", "Mouse"),
        ("Which THREE of these are Web Browsers? (Select 3)", "Google Chrome", "Mozilla Firefox", "Safari", "MS Word", "MS Excel"),
        ("Which THREE of these are Operating Systems? (Select 3)", "Windows", "Linux", "macOS", "MS Excel", "MS Word"),
        ("Which THREE of these are Storage devices? (Select 3)", "Hard Disk", "Pen Drive", "CD/DVD", "Mouse", "Monitor"),
        ("Which THREE of these are Programming Languages? (Select 3)", "Python", "Java", "C++", "MS Word", "MS Excel"),
        ("Which THREE of these are Social Media platforms? (Select 3)", "Facebook", "Instagram", "Twitter", "MS Excel", "MS Access"),
        ("Which THREE of these are Antivirus software? (Select 3)", "Norton", "McAfee", "Avast", "MS Paint", "VLC Player"),
        ("Which THREE of these are types of Computer Memory? (Select 3)", "RAM", "ROM", "Cache", "Mouse", "Keyboard"),
        ("Which THREE of these are Database Management Systems? (Select 3)", "MySQL", "Oracle", "MongoDB", "MS Word", "MS Paint"),
    ]
    for qtext, a, b, c, d, e in q3_data:
        rows.append(("Q3", "multi_select", qtext, a, b, c, d, e, "A,B,C", None, 3))

    q4_data = [
        ("A byte consists of 8 bits.", "TRUE"),
        ("RAM is a type of permanent storage.", "FALSE"),
        ("HTML stands for Hyper Text Markup Language.", "TRUE"),
        ("A compiler translates high-level code into machine code.", "TRUE"),
        ("MS Excel is a word processing software.", "FALSE"),
        ("The mouse is an output device.", "FALSE"),
        ("The Internet and the World Wide Web are exactly the same thing.", "FALSE"),
        ("Python is a programming language.", "TRUE"),
        ("A firewall helps protect a computer network from unauthorized access.", "TRUE"),
        ("JPEG is an audio file format.", "FALSE"),
        ("A database is used to store and organize data.", "TRUE"),
        ("CSS is used to create the structure of a webpage.", "FALSE"),
    ]
    for qtext, correct in q4_data:
        rows.append(("Q4", "true_false", qtext, "True", "False", None, None, None, correct, None, 1))

    match_sets = [
        ("Match each term with its correct definition.",
         [{"left": "CPU", "right": "Brain of the computer"},
          {"left": "RAM", "right": "Temporary memory"},
          {"left": "ROM", "right": "Permanent memory"},
          {"left": "ALU", "right": "Performs calculations"},
          {"left": "Cache", "right": "High-speed memory close to the CPU"}]),
        ("Match each abbreviation with its full form.",
         [{"left": "HTML", "right": "Hyper Text Markup Language"},
          {"left": "CSS", "right": "Cascading Style Sheets"},
          {"left": "URL", "right": "Uniform Resource Locator"},
          {"left": "CPU", "right": "Central Processing Unit"},
          {"left": "USB", "right": "Universal Serial Bus"}]),
        ("Match each software with its category.",
         [{"left": "MS Word", "right": "Word Processor"},
          {"left": "MS Excel", "right": "Spreadsheet Software"},
          {"left": "Google Chrome", "right": "Web Browser"},
          {"left": "Windows", "right": "Operating System"},
          {"left": "VLC Player", "right": "Media Player"}]),
        ("Match each networking term with its meaning.",
         [{"left": "LAN", "right": "Connects computers within a small area"},
          {"left": "WAN", "right": "Connects computers over a large geographical area"},
          {"left": "Router", "right": "Directs data between networks"},
          {"left": "Modem", "right": "Connects a computer to the internet"},
          {"left": "Firewall", "right": "Protects a network from unauthorized access"}]),
    ]
    for qtext, pairs in match_sets:
        rows.append(("Q5", "match", qtext, None, None, None, None, None, None, json.dumps(pairs), len(pairs)))

    q6_data = [
        ("Write basic HTML code to create a webpage with a heading and a paragraph.", 5),
        ("Write basic CSS code to change the background color and font size of a webpage.", 5),
        ("Write a basic HTML and CSS program together to display a heading in blue color.", 5),
        ("Write a basic JavaScript program to display an alert message when a button is clicked.", 5),
    ]
    for qtext, marks in q6_data:
        rows.append(("Q6", "coding", qtext, None, None, None, None, None, None, None, marks))

    cursor.executemany("""
        INSERT INTO questions
        (section_key, question_type, subject, chapter, question_text, option_a, option_b, option_c, option_d, option_e, correct_option, correct_options, match_pairs, marks)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (section_key, qtype, SUBJECT, CHAPTER, qtext, a, b, c, d, e,
         (correct.split(",")[0] if correct else None), correct, match_json, marks)
        for (section_key, qtype, qtext, a, b, c, d, e, correct, match_json, marks) in rows
    ])

    conn.commit()
    conn.close()
    print(f"✅ {len(rows)} demo questions added across 6 sections (Q1-Q6).")


def set_default_active_exam():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM exam_settings")
    if cursor.fetchone()[0] > 0:
        print("ℹ️  exam_settings pehle se set hai - skip kar rahe hai.")
        conn.close()
        return
    cursor.execute("""
        INSERT INTO exam_settings (id, active_subject, active_chapter, duration_minutes)
        VALUES (1, ?, ?, ?)
    """, ("Information Technology (IT) Exam", "Practice Test 1", 90))
    conn.commit()
    print("✅ Default active exam set: Information Technology (IT) Exam - Practice Test 1")
    conn.close()


if __name__ == "__main__":
    print("🔧 Database setup shuru ho raha hai...")
    create_tables()
    migrate_schema()
    insert_sections()
    insert_demo_questions()
    set_default_active_exam()
    print("🎉 Database setup complete! File yaha bani hai:", DB_PATH)
