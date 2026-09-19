// static/js/exam.js
// ---------------------------------------------------------
// 1. Ek waqt me sirf EK QUESTION dikhana (Previous/Next se move karo)
// 2. Sidebar se seedha kisi bhi question/section par jump karna
// 3. Sidebar status dots update karna (answered = green)
// 4. Countdown timer + time khatam hone par auto-submit
// ---------------------------------------------------------

// FLAT_QUESTIONS exam.html ke <script> tags se already bhar chuka hai -
// [{section:"Q1", qid:12}, {section:"Q1", qid:5}, ..., {section:"Q6", qid:9}]
// Poore exam ka EK LAMBA order hai (sections ek ke baad ek), taaki
// Next/Previous section ki boundary cross karte waqt bhi sahi se kaam kare.

let currentIndex = 0;   // abhi FLAT_QUESTIONS me kaunsa index dikh raha hai

function showSlide(index) {
    if (index < 0 || index >= FLAT_QUESTIONS.length) return;

    const target = FLAT_QUESTIONS[index];

    // Pehle SAB section-panels aur SAB slides chhupa do
    document.querySelectorAll(".section-panel").forEach(p => p.classList.remove("active-panel"));
    document.querySelectorAll(".question-slide").forEach(s => s.classList.remove("active-slide"));
    document.querySelectorAll(".sidebar-section-label").forEach(l => l.classList.remove("active-tab"));
    document.querySelectorAll(".status-dot").forEach(d => d.classList.remove("current-dot"));

    // Ab sirf TARGET section ka panel aur TARGET question ki slide dikhao
    document.getElementById("panel-" + target.section).classList.add("active-panel");
    document.getElementById("slide-" + target.qid).classList.add("active-slide");
    document.querySelector('[data-section="' + target.section + '"].sidebar-section-label').classList.add("active-tab");

    const dot = document.getElementById("dot-" + target.qid);
    if (dot) dot.classList.add("current-dot");

    currentIndex = index;
    updateNavButtons();
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateNavButtons() {
    const prevBtn = document.getElementById("prev-btn");
    const nextBtn = document.getElementById("next-btn");
    const submitBtn = document.getElementById("submit-btn-global");

    // Pehle question par "Previous" chhupa do
    prevBtn.style.display = (currentIndex === 0) ? "none" : "inline-block";

    // Sabse aakhri question par "Next" ki jagah "Submit Exam" dikhao
    if (currentIndex === FLAT_QUESTIONS.length - 1) {
        nextBtn.style.display = "none";
        submitBtn.style.display = "inline-block";
    } else {
        nextBtn.style.display = "inline-block";
        submitBtn.style.display = "none";
    }
}

function nextQuestion() { showSlide(currentIndex + 1); }
function prevQuestion() { showSlide(currentIndex - 1); }

function jumpToQuestion(questionId) {
    const index = FLAT_QUESTIONS.findIndex(item => item.qid === questionId);
    if (index !== -1) showSlide(index);
}

function jumpToSectionFirstQuestion(sectionKey) {
    const index = FLAT_QUESTIONS.findIndex(item => item.section === sectionKey);
    if (index !== -1) showSlide(index);
}

function markAnswered(questionId) {
    const dot = document.getElementById("dot-" + questionId);
    if (!dot) return;
    const inputs = document.querySelectorAll('[data-qid="' + questionId + '"]');
    let answered = false;
    inputs.forEach(input => {
        if (input.tagName === "TEXTAREA") {
            if (input.value.trim().length > 0) answered = true;
        } else if (input.checked) {
            answered = true;
        }
    });
    if (answered) dot.classList.add("answered");
    else dot.classList.remove("answered");
}

// ---------------------------------------------------------
// MULTI-SELECT QUESTIONS (Q2 = 2 correct, Q3 = 3 correct):
// Bina isके, student galti se saare 4/5 options tick kar sakta
// tha (jaisa pehle ho raha tha) - us case me system automatically
// SAHI wale gin leta hai (koi crash nahi), lekin student ko
// pata hi nahi chalta ki usse sirf N options hi chunne the.
// Ye function checkbox ko us LIMIT se aage badhne hi nahi deta -
// jaise hi maxSelect se zyada tick ho, turant WAPAS UNCHECK kar
// deta hai jo abhi-abhi click hua tha.
// ---------------------------------------------------------
function enforceCheckboxLimit(questionId, maxSelect, changedCheckbox) {
    const checkboxes = document.querySelectorAll('input[type="checkbox"][data-qid="' + questionId + '"]');
    let checkedCount = 0;
    checkboxes.forEach(cb => { if (cb.checked) checkedCount++; });

    if (checkedCount > maxSelect) {
        // Limit paar ho gayi - jo abhi click hua use turant wapas uncheck kar do
        changedCheckbox.checked = false;
    }

    markAnswered(questionId);
}

function checkMatchAnswered(questionId, totalPairs) {
    const dot = document.getElementById("dot-" + questionId);
    if (!dot) return;
    const selects = document.querySelectorAll('select[data-qid="' + questionId + '"]');
    let filledCount = 0;
    selects.forEach(sel => { if (sel.value !== "") filledCount++; });
    if (filledCount === totalPairs) dot.classList.add("answered");
    else dot.classList.remove("answered");
}

// ===========================================================
// TIMER (refresh-safe, jaisa pehle tha)
// ===========================================================
document.addEventListener("DOMContentLoaded", function () {
    // Sabse pehla question dikhao aur nav buttons sahi state me set karo
    showSlide(0);

    const timerBox = document.getElementById("timer-box");
    let secondsLeft = parseInt(timerBox.getAttribute("data-duration"), 10);
    const timerText = document.getElementById("timer-text");
    const examForm = document.getElementById("exam-form");
    let alreadySubmitted = false;

    function updateTimerDisplay() {
        const minutes = Math.floor(secondsLeft / 60);
        const seconds = secondsLeft % 60;
        timerText.textContent = String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0");
        if (secondsLeft <= 120) timerBox.classList.add("timer-warning");
    }

    updateTimerDisplay();

    const countdownInterval = setInterval(function () {
        secondsLeft -= 1;
        updateTimerDisplay();
        if (secondsLeft <= 0) {
            clearInterval(countdownInterval);
            if (!alreadySubmitted) {
                alreadySubmitted = true;
                alert("Time's up! Your exam is being submitted automatically.");
                examForm.submit();
            }
        }
    }, 1000);

    examForm.addEventListener("submit", function () {
        alreadySubmitted = true;
    });
});
