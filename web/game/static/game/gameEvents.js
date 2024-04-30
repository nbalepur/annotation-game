// gameEvents.js
// Listeners for events during game

const nameInput = document.getElementById('name');
const emailInput = document.getElementById('email');
const requestContentInput = document.getElementById('request-content');
const buzzProgress = document.getElementById('buzz-progress');
const contentProgress = document.getElementById('content-progress');
const questionSpace = document.getElementById('question-space');
const answerHeader = document.getElementById('answer-header');
const scoreboard = document.getElementById('scoreboard-body');
const messageSpace = document.getElementById('message-space');
const categoryHeader = document.getElementById('category-header');
const categorySelect = document.getElementById('category-select');
const difficultySelect = document.getElementById('difficulty-select');
const speedSlider = document.getElementById('speed-slider');
const nextBtn = document.getElementById('next-btn');
const buzzBtn = document.getElementById('buzz-btn');
const chatBtn = document.getElementById('chat-btn');
const resetBtn = document.getElementById('reset-btn');
const banAlert = document.getElementById('ban-alert');


// Init tooltip and popover
$(document).ready(() => {
  $('[data-toggle="tooltip"]').tooltip();
  $('[data-toggle="popover"]').popover();
});

// Timed events (ms)
window.setInterval(ping, 5000);
window.setInterval(update, 100);
window.setInterval(getShownQuestion, 50)

window.onbeforeunload = leave;

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
  
  if (!this.value || !emailRegex.test(this.value)) {
    this.classList.add('is-invalid');
    nextBtn.disabled = true; // Disable the submit button
  } else {
    this.classList.remove('is-invalid');
    this.classList.add('is-valid');
    nextBtn.disabled = false; // Enable the submit button
  }
});


document.addEventListener('keypress', (e) => {
  if (e.target.tagName != 'INPUT' && e.target.tagName != 'TEXTAREA') {
    if (e.key == 'n') {
      next();
    }
    else if (e.key == ' ') {
      buzz();
      e.preventDefault();
    }
    else if (e.key == 'c') {
      chatInit();
    }
  }
});

requestContentInput.addEventListener('keypress', (e) => {
  if (e.key == 'Enter') {
    if (currentAction == 'buzz') {
      answer();
    }
    else if (currentAction == 'chat') {
      sendChat();
    }
  }
});

categorySelect.addEventListener('change', setCategory);
difficultySelect.addEventListener('change', setDifficulty);
buzzBtn.addEventListener('click', buzz);
nextBtn.addEventListener('click', next);
resetBtn.addEventListener('click', resetScore);
chatBtn.addEventListener('click', chatInit);
speedSlider.addEventListener('change', setSpeed);