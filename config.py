# config.py
# ---------------------------------------------------------
# Ye file project ki SAARI important settings ek jagah rakhti hai.
# Agar kabhi password ya exam time change karna ho, to sirf yahi
# file edit karni hai.
# ---------------------------------------------------------

SECRET_KEY = "bright-education-exam-secret-key-2026"

# Admin Panel ka password. ISE BADALNE KE LIYE: neeche wali line
# me naya password likh do.
ADMIN_PASSWORD = "bright@admin123"

# Har exam ki default duration (minutes me) - Admin Panel se
# override bhi ho sakti hai.
EXAM_DURATION_MINUTES = 60

DATABASE_PATH = "database/mcq_exam.db"
