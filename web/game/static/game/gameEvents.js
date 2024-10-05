// gameEvents.js
// Listeners for events during game

const nameInput = document.getElementById('name');
const emailInput = document.getElementById('email');
const optOutInput = document.getElementById('optOutCheck');
const requestContentInput = document.getElementById('request-content');
const buzzProgress = document.getElementById('buzz-progress');
const contentProgress = document.getElementById('content-progress');
const instructionProgress = document.getElementById('instruction-progress');
const questionSpace = document.getElementById('question-space');
const answerFooter = document.getElementById('answer-footer');
const answerHeader = document.getElementById('answer-header');
const scoreboard = document.getElementById('scoreboard-body');
const messageSpace = document.getElementById('message-space');
const categoryHeader = document.getElementById('category-header');
const categorySelect = document.getElementById('category-select');
const difficultySelect = document.getElementById('difficulty-select');
//const speedSlider = document.getElementById('speed-slider');
// const skipBtn = document.getElementById('skip-btn');
const nextBtn = document.getElementById('next-btn');
const buzzBtn = document.getElementById('buzz-btn');
const settingsBtn = document.getElementById('settings-btn');
const chatBtn = document.getElementById('chat-btn');
const resetBtn = document.getElementById('reset-btn');
const banAlert = document.getElementById('ban-alert');

const calcInput = document.getElementById('calc-expression');
const webSearchInput = document.getElementById('google-query');
const docSearchInput = document.getElementById('content-search');
const scratchpadInput = document.getElementById('user-notes');

// Init tooltip and popover
$(document).ready(() => {
  // $('[data-bs-toggle="tooltip"]').tooltip();
  const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
  $('[data-toggle="popover"]').popover();
});

// Timed events (ms)
window.setInterval(ping, 5000);
window.setInterval(update, 100);
// window.setInterval(getShownQuestion, 150)

window.onbeforeunload = leave;

window.addEventListener('load', function() {
  navigator.permissions.query({ name: 'clipboard-read' }).then((result) => {
    if (result.state === 'granted') {
      console.log('Clipboard read access granted');
    } else if (result.state === 'prompt') {
      console.log('Clipboard read access needs to be granted by user');
    } else if (result.state === 'denied') {
      console.log('Clipboard read access denied');
    }
  }).catch((error) => {
    console.error('Error requesting clipboard-read permission: ', error);
  });
});

nameInput.addEventListener('input', debounce(setUserData, 300));
nameInput.addEventListener('input', function validateUserName() {
  if (!this.value) {
    this.classList.add('is-invalid');
  } else {
    this.classList.remove('is-invalid');
    this.classList.add('is-valid');
  }
});

emailInput.addEventListener('input', debounce(setUserData, 300));
emailInput.addEventListener('input', function validateEmail() {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  
  if (optOutInput.checked || (this.value && emailRegex.test(this.value))) {
    this.classList.remove('is-invalid');
    this.classList.add('is-valid');
    nextBtn.disabled = false; // Enable the next button
  } else {
    this.classList.add('is-invalid');
    nextBtn.disabled = true; // Disable the next button
  }
});

optOutInput.addEventListener('click', function optOut() {
  if (optOutInput.checked) {
    nextBtn.disabled = false; // Enable the next button
    emailInput.value = ""
    emailInput.disabled = true;
    emailInput.classList.remove('is-invalid');
    emailInput.classList.add('is-valid');
  } else {
    nextBtn.disabled = true; // Disable the next button
    emailInput.disabled = false;
    emailInput.classList.remove('is-valid');
    if (!emailInput.value) emailInput.classList.add('is-invalid');
  }
  setUserData();
});

document.addEventListener('keypress', (e) => {
  if (e.target.tagName != 'INPUT' && e.target.tagName != 'TEXTAREA' && e.target.id != 'user-notes') {
    if (e.key == 'n') {
      next();
    } else if (e.key == ' ') {
      buzz();
      e.preventDefault();
    } else if (e.key == 'c') {
      focusTextInput("calc-expression");
      e.preventDefault();
    } else if (e.key == 'g') {
      focusTextInput("google-query");
      e.preventDefault();
    } else if (e.key == 'f') {
      focusTextInput("content-search");
      e.preventDefault();
    } else if (e.key == 's') {
      focusTextInput("user-notes");
      e.preventDefault();
    } else if (e.key == ']' || e.key == '[') {
      settings();
    }
    // else if (e.key == 'c') {
    //   chatInit();
    // }
  }
});

document.addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
    focusTextInput("content-search");
    e.preventDefault();
  } else if ((e.ctrlKey || e.metaKey) && e.key == 'c') {
        navigator.clipboard.readText()
        .then(text => {
          sendToNotes(text);
        })
    }
  }
);


requestContentInput.addEventListener('keypress', (e) => {
  if (e.key == 'Enter') {
    if (currentAction == 'buzz') {
      answer();
    }
    // else if (currentAction == 'chat') {
    //   sendChat();
    // }
  }
});

function moveCursorToSecondBullet() {
  const secondBullet = scratchpadInput.querySelector('ul li:nth-child(2)');
  
  const range = document.createRange();
  range.setStart(secondBullet, 0);
  range.collapse(true); // Collapse the range to the start of the second <li>

  const selection = window.getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
}

scratchpadInput.addEventListener('keydown', (e) => {
  if (e.key == 'Escape') {
    scratchpadInput.blur();
  } else if(e.key == 'Enter') {
    content = scratchpadInput.innerHTML;
    if (!content.includes('</ul>')) {
      e.preventDefault();
      scratchpadInput.innerHTML = `<ul style="padding-left: 5px; margin-left: 10px;"><li>${content}</li><li></li></ul>`;
      moveCursorToSecondBullet();
    }
  }
});


calcInput.addEventListener('keydown', (e) => {
  if (e.key == 'Enter') {
    calculatorToolBtn.click();
  } else if (e.key == 'Escape') {
    calcInput.blur();
  }
});

webSearchInput.addEventListener('keydown', (e) => {
  if (e.key == 'Enter') {
    googleToolBtn.click();
  } else if (e.key == 'Escape') {
    webSearchInput.blur();
  }
});

docSearchInput.addEventListener('keydown', (e) => {
  if (e.key == 'Enter') {
    contentSelectorToolBtn.click();
  } else if (e.key == 'Escape') {
    docSearchInput.blur();
  }
});



categorySelect.addEventListener('change', setCategory);
difficultySelect.addEventListener('change', setDifficulty);
buzzBtn.addEventListener('click', buzz);
// skipBtn.addEventListener('click', skip);
nextBtn.addEventListener('click', next);
resetBtn.addEventListener('click', resetScore);
// chatBtn.addEventListener('click', chatInit);
//speedSlider.addEventListener('change', setSpeed);