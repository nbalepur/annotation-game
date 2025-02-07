// gameEvents.js
// Listeners for events during game

let gameState = 'idle';

const nameInput = document.getElementById("name");
const emailInput = document.getElementById("email");
const optOutInput = document.getElementById("optOutCheck");
const offcanvasElement = document.getElementById('offcanvasSettings');
const instructionAnnotationModal = document.getElementById("instruction-annotation-frame");
const instructionAnnotationPage = document.getElementById("instruction-annotation-page");
const requestContentInput = document.getElementById("request-content");
const buzzContent = document.getElementById("buzz-content");
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

const autoScrollCheckbox = document.getElementById("auto-scroll-checkbox");
const autoScrollContainer = document.getElementById("auto-scroll-container");

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

const accountSave = document.getElementById('save-user-settings');
const saveStatus = document.getElementById('save-status');

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

document.addEventListener('DOMContentLoaded', function () {

  const buttonsToChange = [contentSelectorToolBtn, contentSelectorToolBtn2, document.getElementById('calculate-btn-equals')];
  for (const customButton of buttonsToChange) { 
    if (customButton) {
      customButton.addEventListener('mouseover', function () {
        this.style.backgroundColor = '#357ABD';
      });
      customButton.addEventListener('mouseout', function () {
        this.style.backgroundColor = '#4A90E2';
      });
    }
  }

  for (const customButton of calculatorOperators.querySelectorAll('.btn-op')) {
    if (customButton) {
      customButton.addEventListener('mouseover', function () {
        this.style.backgroundColor = '#d1cfcf';
      });
      customButton.addEventListener('mouseout', function () {
        this.style.backgroundColor = '#e8e6e6';
      });
    }
  }     
  

  const urlParams = new URLSearchParams(window.location.search);
  const isModal = urlParams.get('instructions');

  if (isModal === 'false') {
    return;
  }

  var welcomeModalElement = document.getElementById('welcomeModal');
  var welcomeModal = new bootstrap.Modal(welcomeModalElement, {
    backdrop: 'static',
    keyboard: false
  });
  welcomeModal.show();

  // closeBtn1 = document.getElementById("close-instruction-modal1");
  closeBtn2 = document.getElementById("close-instruction-modal2");

  // closeBtn1.addEventListener('click', function () {
  //   stopVideosInModal();
  //   welcomeModal.hide();
  // });
  closeBtn2.addEventListener('click', function () {
    stopVideosInModal();
    welcomeModal.hide();
  });

  // Function to stop videos in iframes
function stopVideosInModal() {
  const iframes = welcomeModalElement.querySelectorAll('iframe');
  iframes.forEach((iframe) => {
    const src = iframe.src;
    iframe.src = '';
    iframe.src = src;
  });
}

// // Add event listeners for closing the modal
// closeBtn1.addEventListener('click', function () {
//   welcomeModal.hide();
// });

closeBtn2.addEventListener('click', function () {
  welcomeModal.hide();
});

requestContentInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    event.preventDefault();
    event.stopImmediatePropagation();
    buzz();
    }
});

buzzContent.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    event.preventDefault();
    event.stopImmediatePropagation();
    buzz();
    }
});

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
        // console.log("Clipboard read access granted");
      } else if (result.state === "prompt") {
        // console.log("Clipboard read access needs to be granted by user");
      } else if (result.state === "denied") {
        // console.log("Clipboard read access denied");
      }
    })
    .catch((error) => {
      console.error("Error requesting clipboard-read permission: ", error);
    });
});

function validateUserName() {
  const usernameRegex = /^[a-zA-Z0-9_.]+$/;
  if (this.value.length < 1) {
    this.classList.add("is-invalid");
    accountSave.disabled = true;
  } else if (!usernameRegex.test(this.value)) {
    this.classList.add("is-invalid");
    accountSave.disabled = true;
  } else {
    this.classList.remove("is-invalid");
    this.classList.add("is-valid");
    accountSave.disabled = false;
  }
}

function validateEmail() {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  if (this.value && emailRegex.test(this.value)) {
    this.classList.remove("is-invalid");
    this.classList.add("is-valid");
    accountSave.disabled = false;
  } else {
    this.classList.add("is-invalid");
    accountSave.disabled = true;
  }
}

// nameInput.addEventListener("input", debounce(setUserData, 300));

// emailInput.addEventListener("input", debounce(setUserData, 300));
nameInput.addEventListener("input", validateUserName);
emailInput.addEventListener("input", validateEmail);

accountSave.addEventListener('click', clearUserData)

// optOutInput.addEventListener("click", function optOut() {
//   if (optOutInput.checked) {
//     nextBtn.disabled = false; // Enable the next button
//     emailInput.value = "";
//     emailInput.disabled = true;
//     emailInput.classList.remove("is-invalid");
//     emailInput.classList.add("is-valid");
//   } else {
//     nextBtn.disabled = true; // Disable the next button
//     emailInput.disabled = false;
//     emailInput.classList.remove("is-valid");
//     if (!emailInput.value) emailInput.classList.add("is-invalid");
//   }
//   setUserData();
// });


function handleKeyPress(e) {

  
  const modalElement = document.getElementById('welcomeModal');
  if (modalElement && modalElement.classList.contains('show')) {
    return;
  }

  const instructionFrame = document.getElementById('instruction-frame')
  const iframeDoc = instructionFrame.contentDocument || instructionFrame.contentWindow.document;
  const checkbox = iframeDoc.getElementById('edit-instructions-checkbox');
  
  const swapPlanButton = iframeDoc.getElementById('swap-button-in-plan');
  const swapPlanButtonClick = iframeDoc.getElementById('swap-button-in-plan-btn');

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
      if (gameState === 'idle') {
        next();
      }
    } else if (e.key == "Enter" && gameState === "playing") {
      if (checkbox.checked || buzzBtn.style.display === "") {
        buzz();
        e.preventDefault();
      } else {
          const iframe = document.getElementById('instruction-frame');
          const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
          if (iframeDoc.getElementById('step-buzz-btn')) {
            const container = iframeDoc.getElementById('instructions-container');
            const currentLastStep = container.querySelector('.step-div:first-child');
            const guess = currentLastStep.querySelector('textarea').value;
            answerWrapper(guess);
            e.preventDefault();
          }
          if (iframeDoc.getElementById('step-next-btn')) {
            next_step();
            e.preventDefault();
          }   
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
      if (gameState === 'instruct') {
        skip();
        e.preventDefault();
      } else if (gameState === "playing" && !checkbox.checked && swapPlanButton.style.display === '') {
        swapPlanButtonClick.click();
        e.preventDefault();
      }
    } else if (e.key === "p") {
      if (checkbox.checked) {
        focusTextInputInstructions('rogue-notes-area');
      } else {
        focusLastInstruction();
      }
      e.preventDefault();
    } else if (e.key === "t") {
      const lastCopy = getLastCopy();
      if (lastCopy) {
        copyTextToTool(lastCopy);
      }
    }
  }
  e.stopPropagation();
}

function inlineExternalCSS() {
  const styleSheets = Array.from(document.styleSheets);

  styleSheets.forEach(sheet => {
    try {
      if (sheet.cssRules) {
        const rules = Array.from(sheet.cssRules).map(rule => rule.cssText).join('\n');
        const style = document.createElement('style');
        style.textContent = rules;
        document.head.appendChild(style);
      }
    } catch (e) {
      console.warn('Could not access CSS rules for', sheet.href, e);
    }
  });
}

async function fetchAndInlineCSS(url) {
  const response = await fetch(url);
  const cssText = await response.text();
  const style = document.createElement('style');
  style.textContent = cssText;
  document.head.appendChild(style);
}


function embedIframes() {
  const iframes = document.querySelectorAll('iframe');
  iframes.forEach(iframe => {
      try {
          if (iframe.id === "instruction-frame") {
            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
            const iframeHTML = iframeDoc.documentElement.outerHTML;
            const wrapper = document.createElement('div');
            wrapper.style.width = iframe.style.width;
            wrapper.style.height = iframe.style.height;
            wrapper.innerHTML = iframeHTML;
            iframe.replaceWith(wrapper);
          }
      } catch (e) {
          console.warn('Cannot access iframe content:', e);
      }
  });
}


async function screenshot() {
  //await fetchAndInlineCSS('https://cdn.jsdelivr.net/npm/bootstrap-table@1.22.5/dist/bootstrap-table.min.css');
  //await fetchAndInlineCSS('https://gitcdn.github.io/bootstrap-toggle/2.2.2/css/bootstrap-toggle.min.css');
  //inlineExternalCSS();
  embedIframes();

  var element = document.documentElement; // Use the entire HTML document for capturing
  
  // Set options to capture the full content
  domtoimage.toSvg(element, {
    width: element.scrollWidth, // Full width of the page
    height: element.scrollHeight, // Full height of the page
  })
    .then(function (dataUrl) {
      // Create a download link for the SVG
      const link = document.createElement('a');
      link.href = dataUrl;
      link.download = 'screenshot.svg';
      link.click();
    })
    .catch(function (error) {
      console.error('Error generating SVG screenshot:', error);
    });
}



function handleKeyDown(e) {

  if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "p") {
    e.preventDefault();
    screenshot();
}



  const modalElement = document.getElementById('welcomeModal');
  if (modalElement && modalElement.classList.contains('show')) {
    return;
  }

  const instructionFrame = document.getElementById('instruction-frame')
  const iframeDoc = instructionFrame.contentDocument || instructionFrame.contentWindow.document;
  const checkbox = iframeDoc.getElementById('edit-instructions-checkbox');

  if ((e.ctrlKey || e.metaKey) && e.key === "f" && gameState === 'playing') {
    focusTextInput("content-search");
    e.preventDefault();
  } else if ((e.key === "z" || (e.ctrlKey || e.metaKey) && e.key === "z") && gameState === 'playing' && !checkbox.checked) {
    closeLastButton();
    e.preventDefault();
  } else if (e.key === "Tab" && gameState === 'idle') {
    settings();
    e.preventDefault();
  } else if (gameState === 'playing' && (e.key === "ArrowLeft" || e.key === "[")) {
    if (bwdSearch && bwdSearch.style.backgroundColor !== 'transparent') {
      navigateHistory(-1);
    }
  } else if (gameState === 'playing' &&  (e.key === "ArrowRight" || e.key === "]")) {
    if (fwdSearch && fwdSearch.style.backgroundColor !== 'transparent') {
      navigateHistory(1);
    }
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
      answer(requestContentInput.value);
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
    e.preventDefault();
    e.stopImmediatePropagation();
  } else if (e.key == "Escape") {
    calcInput.blur();
    e.preventDefault();
    e.stopImmediatePropagation();
  }
});

webSearchInput.addEventListener("keydown", (e) => {
  if (e.key == "Enter") {
    googleToolBtn.click();
    e.preventDefault();
    e.stopImmediatePropagation();
  } else if (e.key == "Escape") {
    webSearchInput.blur();
    e.preventDefault();
    e.stopImmediatePropagation();
  }
});

docSearchInput.addEventListener("keydown", (e) => {
  if (e.key == "Enter") {
    contentSelectorToolBtn.click();
    e.preventDefault();
    e.stopImmediatePropagation();
  } else if (e.key == "Escape") {
    docSearchInput.blur();
    e.preventDefault();
    e.stopImmediatePropagation();
  }
});

function clearReportData() {
  const isBadQuestion = document.getElementById("issue1");
  const isBadInstructions = document.getElementById("issue2");
  const isBadAnswerVerifier = document.getElementById("issue3");
  const textFeedback = document.getElementById("feedback");

  isBadQuestion.checked = false;
  isBadInstructions.checked = false;
  isBadAnswerVerifier.checked = false;
  textFeedback.value = '';
}

document.getElementById("submitReportBtn").addEventListener("click", function () {
  const isBadQuestion = document.getElementById("issue1").checked;
  const isBadInstructions = document.getElementById("issue2").checked;
  const isBadAnswerVerifier = document.getElementById("issue3").checked;
  const isFrustrated = false;
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
  clearReportData();
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

categorySelect.addEventListener('change', function(event) {
  const categoryPreference = event.target.value;
  if (categoryPreference === 'Trivia' || categoryPreference === 'Everything') {
    autoScrollContainer.style.display = '';
  } else {
    autoScrollContainer.style.display = 'none';
  }
  sendRequest("change_category", event.target.value);
});

autoScrollCheckbox.addEventListener('change', function(event) {
  sendRequest("change_auto_scroll", event.target.checked);
});
