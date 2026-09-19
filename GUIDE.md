# Bright Education — MCQ Exam System — Complete Guide

Ye guide tumhe A se Z tak sab kuch batayegi. Kahi bhi atko, to yahi file dubara padho.

---

## 1. Python Install Karna (Windows)

1. Browser me jao: **https://www.python.org/downloads/**
2. "Download Python" button dabao (latest version)
3. Installer chalao — **SABSE ZAROORI: "Add python.exe to PATH" checkbox zaroor tick karo**
4. "Install Now" dabao
5. Confirm karne ke liye Command Prompt me: `python --version`

---

## 2. Project Setup

1. `mcq_exam_system.zip` ko Extract karo (right-click → Extract All)
2. Command Prompt me us folder me jao: `cd Desktop\mcq_exam_system`
3. Library install karo (sirf ek baar): `pip install -r requirements.txt`
4. Database taiyaar karo (sirf ek baar): `python database\init_db.py`

---

## 3. Server Chalana

`start_server.bat` par double-click karo, ya terminal me: `python app.py`

Server start hote hi apna LAN IP address khud print kar dega — wahi student PCs me daalna hoga.

**Server band karna:** `CTRL + C`

---

## 4. LAN Setup (Student PCs Connect Karna)

**"Offline" ka matlab hai internet nahi chahiye — par PCs ko aapas me baat karne ke liye ek LAN chahiye:**

- **Router hai (chahe internet ho ya na ho):** Sab PCs usi WiFi/router se connect karo. Router ko internet ki zaroorat nahi, sirf power ON honi chahiye.
- **Router nahi hai, sirf Ethernet cable hai ek PC me:** Ek cheap Network Switch (₹500-800) se saare PCs ko Ethernet cable se jodo — internet ki zaroorat nahi.
- **Router bhi nahi hai:** Server PC khud WiFi Hotspot bana sakta hai (Settings → Network → Mobile Hotspot), baaki PCs usse connect ho jayenge.

Windows Firewall popup aaye to **"Allow access"** zaroor dabana (dono Private + Public tick karke).

Student ke browser me: `http://<server-ka-IP>:5000`

---

## 5. Admin Panel

`http://127.0.0.1:5000/admin/login` — Default password: `bright@admin123`

**Password change:** `config.py` file me `ADMIN_PASSWORD = "..."` line edit karo, server restart karo.

---

## 6. Exam Ka Structure (6 Fixed Sections)

| Section | Type | Marks | Pattern |
|---|---|---|---|
| Q1 | 1 sahi jawaab, 4 options | 1 mark each | Any 10 of 12 |
| Q2 | 2 sahi jawaab, 4 options | 2 marks each | Any 10 of 12 |
| Q3 | 3 sahi jawaab, 5 options | 3 marks each | Any 10 of 12 |
| Q4 | True/False | 1 mark each | Any 10 of 12 |
| Q5 | Match the Following | Pairs ke hisab se | Any 2 of 3 |
| Q6 | Coding (manual grading) | Tum decide karoge | Any 2 of 4 |

Har student ko section ke pool me se random questions milte hai (jaise 12 me se 10) — isliye do students ka paper kabhi exact match nahi hota.

**Partial marking (Q2/Q3):** Jitne sahi options select kiye utne marks milte hai, galat select karne se marks nahi katte.

---

## 7. Naya Question Add Karna

### Admin Panel se (sab types ke liye kaam karta hai)
1. Admin Panel → "Questions" → "Add New Question"
2. Pehle **Section** choose karo (Q1-Q6) — form apne aap us section ke hisab se fields dikha dega
3. Bhar ke "Save Question" dabao

### CSV se Bulk Add (SIRF Q1, Q2, Q3, Q4 ke liye)
`database/questions_template.csv` Excel me kholo, `section_key` column me Q1/Q2/Q3/Q4 likho, baaki fields bharo, save karke chalao:
```
python database\import_questions.py
```
**Q5 (Match) aur Q6 (Coding) CSV se add NAHI hote** — inka structure zyada complex hai (pairs, marks), isliye ye do sirf Admin Panel se hi add karne honge.

---

## 8. Student Roster (Naam/Roll Number Verify Karna)

`database/students_roster_template.csv` bharo, chalao:
```
python database\import_roster.py
```
Roster khali ho to verification skip ho jata hai (testing ke liye theek hai).

---

## 9. Coding Answers Grade Karna (NAYA — Q6 ke liye zaroori)

Jis student ne Q6 (coding) attempt kiya hai, uska result tab tak **"Pending"** rahega jab tak tum manually grade nahi karte:

1. Admin Panel → "Grade Coding" — pending students ki list dikhegi
2. "Grade Now" dabao — student ka likha hua code padho
3. Har coding question ke liye marks do (0 se uski max marks tak)
4. "Save Marks & Finalize Result" dabao — final score automatically calculate ho jayega

Jab tak grading nahi hoti, Results page me us student ka status "Pending" dikhega.

---

## 10. Results Dekhna Aur Export Karna

Admin Panel → "Results" — sab students ke marks (students khud apna score nahi dekh sakte). "Export as CSV" se Excel-compatible file milegi.

---

## 11. Exam Din Ka Checklist

- [ ] Roster CSV bhar ke import kar lo
- [ ] Sab sections (Q1-Q6) me kaafi questions daal lo (pool size >= "attempt N" wali number)
- [ ] Exam Settings me sahi subject/chapter active karo, duration set karo
- [ ] Server start karo, IP note kar lo
- [ ] Firewall allow ho chuka hai confirm karo
- [ ] Ek PC se test karke dekho poora exam (Q1 se Q6 tak) sahi chal raha hai
- [ ] Exam khatam hone ke baad, "Grade Coding" me jaake Q6 grade karo
- [ ] Results check karke CSV export kar lo

---

## 12. Common Problems

| Problem | Solution |
|---|---|
| "python is not recognized" | Python dubara install karo, "Add to PATH" tick karo |
| Student PC se site nahi khulti | Firewall check karo, dono PC same network par hai confirm karo |
| Kisi section me questions nahi dikh rahe | Us section me pool me kam se kam utne questions hone chahiye jitna "attempt N" set hai |
| Q6 ka result "Pending" hi dikh raha hai | Admin Panel → "Grade Coding" me jaake us student ko grade karo |
| Purani database se naya format kaam nahi kar raha | Purani `mcq_exam.db` delete karke `init_db.py` dubara chalao |
| CSV se Q5/Q6 add nahi ho raha | Ye normal hai — Q5 aur Q6 sirf Admin Panel se add hote hai |

---

## 13. Project Files Reference

| File | Kaam |
|---|---|
| `app.py` | Main server — poora exam + admin logic |
| `config.py` | Password, duration settings |
| `database/init_db.py` | Database + 6 sections + demo questions banata hai |
| `database/mcq_exam.db` | Actual data |
| `database/questions_template.csv` + `import_questions.py` | Bulk add (Q1-Q4 only) |
| `database/students_roster_template.csv` + `import_roster.py` | Roster |
| `templates/exam.html` | Sectioned exam page (Q1-Q6 tabs) |
| `templates/admin_grade_coding*.html` | Coding grading pages |
| `static/js/exam.js` | Section navigation + timer |
| `start_server.bat` | Double-click se server start |
