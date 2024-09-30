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
const skipBtn = document.getElementById('skip-btn');
const nextBtn = document.getElementById('next-btn');
const buzzBtn = document.getElementById('buzz-btn');
const chatBtn = document.getElementById('chat-btn');
const resetBtn = document.getElementById('reset-btn');
const banAlert = document.getElementById('ban-alert');

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
  if (e.target.tagName != 'INPUT' && e.target.tagName != 'TEXTAREA') {
    if (e.key == 'n') {
      next();
    } else if (e.key == 's') {
      skip();
    } else if (e.key == ' ') {
      buzz();
      e.preventDefault();
    }
    // else if (e.key == 'c') {
    //   chatInit();
    // }
  }
});

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

categorySelect.addEventListener('change', setCategory);
difficultySelect.addEventListener('change', setDifficulty);
buzzBtn.addEventListener('click', buzz);
skipBtn.addEventListener('click', skip);
nextBtn.addEventListener('click', next);
resetBtn.addEventListener('click', resetScore);
// chatBtn.addEventListener('click', chatInit);
//speedSlider.addEventListener('change', setSpeed);