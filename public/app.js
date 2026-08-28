const USE_MOCK_DATA = false;

const QUESTIONS = [
  {
    id: "Q1",
    text: "12 + 8 / 4 * 2",
    correctSteps: "8 / 4 = 2, 2 * 2 = 4, 12 + 4 = 16",
  },
  {
    id: "Q2",
    text: "20 - 6 / 2 * 3",
    correctSteps: "6 / 2 = 3, 3 * 3 = 9, 20 - 9 = 11",
  },
  {
    id: "Q3",
    text: "(5 + 3) * 2 - 4",
    correctSteps: "5 + 3 = 8, 8 * 2 = 16, 16 - 4 = 12",
  },
  {
    id: "Q4",
    text: "18 / 3 + 2 * 5",
    correctSteps: "18 / 3 = 6, 2 * 5 = 10, 6 + 10 = 16",
  },
  {
    id: "Q5",
    text: "10 - 2 * 3 + 4",
    correctSteps: "2 * 3 = 6, 10 - 6 = 4, 4 + 4 = 8",
  },
  {
    id: "Q6",
    text: "(12 - 4) / 2 * 3",
    correctSteps: "12 - 4 = 8, 8 / 2 = 4, 4 * 3 = 12",
  },
  {
    id: "Q7",
    text: "6 * 2 - 8 / 4",
    correctSteps: "6 * 2 = 12, 8 / 4 = 2, 12 - 2 = 10",
  },
  {
    id: "Q8",
    text: "15 + 3 * (4 - 2)",
    correctSteps: "4 - 2 = 2, 3 * 2 = 6, 15 + 6 = 21",
  },
];

const MOCK_RESPONSE = {
  mistakeType: "left_to_right_assumption",
  divergedAtStep: 2,
  explanation:
    "Multiplication and division are performed before addition. You divided first, which was correct, but then added before finishing the multiplication step.",
  correction: "8 / 4 = 2, then 2 * 2 = 4, then 12 + 4 = 16",
  followUpQuestion: "Solve: 20 - 6 / 2 * 3",
};

let selectedQuestion = null;

const screens = {
  select: document.getElementById("screen-select"),
  input: document.getElementById("screen-input"),
  results: document.getElementById("screen-results"),
};

const questionListEl = document.getElementById("question-list");
const selectedQuestionTextEl = document.getElementById("selected-question-text");
const studentStepsEl = document.getElementById("student-steps");
const submitBtn = document.getElementById("submit-btn");
const inputErrorEl = document.getElementById("input-error");
const backBtn = document.getElementById("back-to-select");
const tryAgainBtn = document.getElementById("try-again-btn");
const retryBtn = document.getElementById("retry-btn");

const loadingEl = document.getElementById("loading");
const resultsContentEl = document.getElementById("results-content");
const resultsErrorEl = document.getElementById("results-error");

// ---- Screen switching ----
function showScreen(name) {
  Object.values(screens).forEach((s) => s.classList.remove("active"));
  screens[name].classList.add("active");
}

// ---- Build question list ----
function renderQuestions() {
  questionListEl.innerHTML = "";
  QUESTIONS.forEach((q) => {
    const item = document.createElement("div");
    item.className = "question-item";
    item.textContent = q.text;
    item.addEventListener("click", () => selectQuestion(q));
    questionListEl.appendChild(item);
  });
}

function selectQuestion(question) {
  selectedQuestion = question;
  selectedQuestionTextEl.textContent = question.text;
  studentStepsEl.value = "";
  inputErrorEl.classList.add("hidden");
  showScreen("input");
}

// ---- Submit flow ----
submitBtn.addEventListener("click", async () => {
  const steps = studentStepsEl.value.trim();

  if (!steps) {
    inputErrorEl.textContent = "Please type your working before submitting.";
    inputErrorEl.classList.remove("hidden");
    return;
  }

  inputErrorEl.classList.add("hidden");
  showScreen("results");
  loadingEl.classList.remove("hidden");
  resultsContentEl.classList.add("hidden");
  resultsErrorEl.classList.add("hidden");

  try {
    const result = await getDiagnosis(selectedQuestion, steps);
    renderResults(result);
  } catch (err) {
    loadingEl.classList.add("hidden");
    resultsErrorEl.classList.remove("hidden");
    console.error("Diagnosis request failed:", err);
  }
});

// ---- API call (or mock) ----
async function getDiagnosis(question, studentSteps) {
  if (USE_MOCK_DATA) {
    // Simulate network delay so the loading state is visible and testable
    await new Promise((resolve) => setTimeout(resolve, 900));
    return MOCK_RESPONSE;
  }

  const response = await fetch("/api/diagnose", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      questionId: question.id,
      question: question.text,
      correctSteps: question.correctSteps,
      studentSteps: studentSteps,
    }),
  });

  if (!response.ok) {
    throw new Error(`API returned status ${response.status}`);
  }

  const data = await response.json();

  if (data.error) {
    throw new Error(data.error);
  }

  return data;
}

// ---- Render results ----
function renderResults(result) {
  loadingEl.classList.add("hidden");
  resultsContentEl.classList.remove("hidden");

  document.getElementById("result-mistake-type").textContent = formatMistakeType(
    result.mistakeType
  );
  document.getElementById("result-explanation").textContent = result.explanation;
  document.getElementById("result-correction").textContent = result.correction;
  document.getElementById("result-followup").textContent = result.followUpQuestion;
}

function formatMistakeType(raw) {
  // Converts "left_to_right_assumption" into "Left To Right Assumption"
  return raw
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

// ---- Navigation ----
backBtn.addEventListener("click", () => showScreen("select"));
tryAgainBtn.addEventListener("click", () => showScreen("select"));
retryBtn.addEventListener("click", () => showScreen("input"));

// ---- Init ----
renderQuestions();
showScreen("select");