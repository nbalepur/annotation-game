// gameEvents.js
// Listeners for events during game

const nameInput = document.getElementById("name");
const emailInput = document.getElementById("email");
const optOutInput = document.getElementById("optOutCheck");
const requestContentInput = document.getElementById("request-content");
const buzzProgress = document.getElementById("buzz-progress");
const contentProgress = document.getElementById("content-progress");
const instructionProgress = document.getElementById("instruction-progress");
const questionSpace = document.getElementById("question-space");
const answerFooter = document.getElementById("answer-footer");
// const answerHeader = document.getElementById('answer-header');
const scoreboard = document.getElementById("scoreboard-body");
const messageSpace = document.getElementById("message-space");
const categoryHeader = document.getElementById("category-header");
const categorySelect = document.getElementById("category-select");
const difficultySelect = document.getElementById("difficulty-select");
//const speedSlider = document.getElementById('speed-slider');
const skipBtn = document.getElementById('skip-btn');
const nextBtn = document.getElementById("next-btn");
const buzzBtn = document.getElementById("buzz-btn");
const stepBtn = document.getElementById("step-btn");
const swapBtn = document.getElementById("swap-btn");
const reportBtn = document.getElementById("report-btn");
const settingsBtn = document.getElementById("settings-btn");
const chatBtn = document.getElementById("chat-btn");
const resetBtn = document.getElementById("reset-btn");
const banAlert = document.getElementById("ban-alert");

const calcInput = document.getElementById("calc-expression");
const webSearchInput = document.getElementById("google-query");
const docSearchInput = document.getElementById("content-search");
const scratchpadInput = document.getElementById("user-notes");

// Init tooltip and popover
$(document).ready(() => {
  // $('[data-bs-toggle="tooltip"]').tooltip();
  const tooltipTriggerList = document.querySelectorAll(
    '[data-bs-toggle="tooltip"]'
  );
  const tooltipList = [...tooltipTriggerList].map(
    (tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl)
  );
  $('[data-toggle="popover"]').popover();
});

// Timed events (ms)
window.setInterval(ping, 5000);
window.setInterval(update, 100);
// window.setInterval(getShownQuestion, 150)

window.onbeforeunload = leave;

window.addEventListener("load", function () {
  navigator.permissions
    .query({ name: "clipboard-read" })
    .then((result) => {
      if (result.state === "granted") {
        console.log("Clipboard read access granted");
      } else if (result.state === "prompt") {
        console.log("Clipboard read access needs to be granted by user");
      } else if (result.state === "denied") {
        console.log("Clipboard read access denied");
      }
    })
    .catch((error) => {
      console.error("Error requesting clipboard-read permission: ", error);
    });
});

nameInput.addEventListener("input", debounce(setUserData, 300));
nameInput.addEventListener("input", function validateUserName() {
  if (!this.value) {
    this.classList.add("is-invalid");
  } else {
    this.classList.remove("is-invalid");
    this.classList.add("is-valid");
  }
});

emailInput.addEventListener("input", debounce(setUserData, 300));
emailInput.addEventListener("input", function validateEmail() {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  if (optOutInput.checked || (this.value && emailRegex.test(this.value))) {
    this.classList.remove("is-invalid");
    this.classList.add("is-valid");
    nextBtn.disabled = false; // Enable the next button
  } else {
    this.classList.add("is-invalid");
    nextBtn.disabled = true; // Disable the next button
  }
});

optOutInput.addEventListener("click", function optOut() {
  if (optOutInput.checked) {
    nextBtn.disabled = false; // Enable the next button
    emailInput.value = "";
    emailInput.disabled = true;
    emailInput.classList.remove("is-invalid");
    emailInput.classList.add("is-valid");
  } else {
    nextBtn.disabled = true; // Disable the next button
    emailInput.disabled = false;
    emailInput.classList.remove("is-valid");
    if (!emailInput.value) emailInput.classList.add("is-invalid");
  }
  setUserData();
});

function handleKeyPress(e) {
  console.log('key press:', e);
  if (feedbackRow && feedbackRow.style.display === "") {
    if (e.key === "[") {
      selectPlan("A");
    } else if (e.key === "]") {
      selectPlan("B");
    } else if (e.key === "Enter") {
      selectPlan("Tie");
    }
  } else if (
    e.target.tagName !== "INPUT" &&
    e.target.tagName !== "TEXTAREA"
  ) {
    if (e.key == "n") {
      if (nextBtn.style.display === '' && (nextBtn.style.visibility === '' || nextBtn.style.visibility === 'visible')) {
        next();
      } else if (stepBtn.style.display === '' && (stepBtn.style.visibility === '' || stepBtn.style.visibility === 'visible')) {
        next_step();
      }
    } else if (e.key == " ") {
      if (buzzBtn.style.display === "") {
        buzz();
        e.preventDefault();
      }
    } else if (e.key == "m") {
      focusTextInput("calc-expression");
      e.preventDefault();
    } else if (e.key == "w") {
      focusTextInput("google-query");
      e.preventDefault();
    } else if (e.key == "f") {
      focusTextInput("content-search");
      e.preventDefault();
    } else if (e.key === "c") {
      if (copyMathBtn.style.display === "") {
        copyMathResult();
      } else if (copySearchBtn.style.display === "") {
        copyDocText();
      }
    } else if (e.key === "s") {
      if (skipBtn.style.display === '') {
        skip();
        e.preventDefault();
      }
      if (swapBtn.style.display === '') {
        swap_plan();
        e.preventDefault();
      }
    } else if (e.key === "p") {
      focusLastInstruction();
      e.preventDefault();
    }
    // else if (e.key == "s") {
    //   focusTextInput("user-notes");
    //   e.preventDefault();
    // }
  }
  e.stopPropagation();
}

function handleKeyDown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === "f" && gameState === 'playing') {
    focusTextInput("content-search");
    e.preventDefault();
  } else if ((e.ctrlKey || e.metaKey) && e.key === "z" && gameState === 'playing') {
    closeLastButton();
    e.preventDefault();
  } else if ((e.ctrlKey || e.metaKey) && e.key === "s" && gameState === 'playing') {
    if (swapBtn.style.display === '' && swapBtn.style.visibility == 'visible') {
      swap_plan();
      e.preventDefault();
    }
  } else if (e.key === "Tab" && gameState === 'idle') {
    settings();
    e.preventDefault();
  }
  e.stopPropagation();
}

document.addEventListener("keypress", (e) => {
  handleKeyPress(e);
});

document.addEventListener("keydown", function (e) {
  handleKeyDown(e);
});

requestContentInput.addEventListener("keypress", (e) => {
  if (e.key == "Enter") {
    if (currentAction == "buzz") {
      answer();
    }
    // else if (currentAction == 'chat') {
    //   sendChat();
    // }
  }
});

function moveCursorToSecondBullet() {
  const secondBullet = scratchpadInput.querySelector("ul li:nth-child(2)");

  const range = document.createRange();
  range.setStart(secondBullet, 0);
  range.collapse(true); // Collapse the range to the start of the second <li>

  const selection = window.getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
}

// scratchpadInput.addEventListener('keydown', (e) => {
//   if (e.key == 'Escape') {
//     scratchpadInput.blur();
//   } else if(e.key == 'Enter') {
//     content = scratchpadInput.innerHTML;
//     if (!content.includes('</ul>')) {
//       e.preventDefault();
//       scratchpadInput.innerHTML = `<ul style="padding-left: 5px; margin-left: 10px;"><li>${content}</li><li></li></ul>`;
//       moveCursorToSecondBullet();
//     }
//   }
// });

calcInput.addEventListener("keydown", (e) => {
  if (e.key == "Enter") {
    calculatorToolBtn.click();
  } else if (e.key == "Escape") {
    calcInput.blur();
  }
});

webSearchInput.addEventListener("keydown", (e) => {
  if (e.key == "Enter") {
    googleToolBtn.click();
  } else if (e.key == "Escape") {
    webSearchInput.blur();
  }
});

docSearchInput.addEventListener("keydown", (e) => {
  if (e.key == "Enter") {
    contentSelectorToolBtn.click();
  } else if (e.key == "Escape") {
    docSearchInput.blur();
  }
});

document.getElementById("submitReportBtn").addEventListener("click", function () {
  const isBadQuestion = document.getElementById("issue1").checked;
  const isBadInstructions = document.getElementById("issue2").checked;
  const isBadAnswerVerifier = document.getElementById("issue3").checked;
  const isFrustrated = document.getElementById("issue4").checked;
  const textFeedback = document.getElementById("feedback").value;

  if (!textFeedback && !isBadQuestion && !isBadInstructions && !isBadAnswerVerifier && !isFrustrated) {
    alert("You must leave feedback to report a question!");
    return;
  }

  const reportData = {
    is_bad_question: isBadQuestion,
    is_bad_instruction: isBadInstructions,
    is_bad_answer_verifier: isBadAnswerVerifier,
    is_frustrated: isFrustrated,
    feedback: textFeedback,
  };

  sendRequest("report_issue", reportData);

  const btn = document.getElementById('report-issue-close');
  btn.click();
});


// categorySelect.addEventListener('change', setCategory);
// difficultySelect.addEventListener('change', setDifficulty);
buzzBtn.addEventListener("click", buzz);
// skipBtn.addEventListener('click', skip);
nextBtn.addEventListener("click", next);
// resetBtn.addEventListener('click', resetScore);
skipBtn.addEventListener("click", skip);
// chatBtn.addEventListener('click', chatInit);
//speedSlider.addEventListener('change', setSpeed);
stepBtn.addEventListener("click", next_step);

swapBtn.addEventListener("click", swap_plan)