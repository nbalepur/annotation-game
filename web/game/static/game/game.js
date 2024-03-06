// game.js
// Plays client-side game

const wsScheme = window.location.protocol == "https:" ? "wss" : "ws";
console.log(wsScheme + '://' + window.location.host + '/ws' + window.location.pathname)
const gamesock = new WebSocket(wsScheme + '://' + window.location.host + '/ws' + window.location.pathname);

let username;
let userID;
let lockedOut;

let gameState = 'idle'; // idle, playing, contest
let currentAction = 'idle'; // idle, buzz, chat, 

let currentTime;
let startTime;
let endTime;
let buzzStartTime;
let buzzPassedTime = 0;
let graceTime = 3;
let buzzTime = 8;

let question;
let category;
let players;
let messages;
let changeLocked = false;

let isFeedbackLoaded = false;

// Set up client
gamesock.onopen = () => {

  requestContentInput.style.display = 'none';

  // set up user

  retrieveUserdata();

  if (userID === undefined) {
    newUser();
  } else {
    join();
  }

  nameInput.value = username;

  // set up current time if newly joined
  currentTime = buzzStartTime;
}

/**
 * Update game locally
 */
function update() {
  // console.log(gameState);
  if (question === undefined) {
    return;
  }

  let timePassed = currentTime - startTime;
  let duration = endTime - startTime;

  switch (gameState) {

    case 'idle':
      lockedOut = false;

      if (answerHeader.innerHTML === '') {
        getAnswer();
      }

      if (!isFeedbackLoaded) {
        isFeedbackLoaded = true;
        getCurrentFeedback();
      }
      contentProgress.style.width = '0%';
      break;

    case 'playing':

      // Update if game is going
      contentProgress.style.width = Math.round(100 * (1.05 * timePassed / duration)) + '%';

      buzzPassedTime = 0;
      currentTime += 0.1;

      contentProgress.style.display = '';
      buzzProgress.style.display = 'none';
      answerHeader.innerHTML = '';
      break;

    case 'contest':
      timePassed = buzzStartTime - startTime;

      buzzProgress.style.width = Math.round(100 * (1.05 * buzzPassedTime / buzzTime)) + '%';
      contentProgress.style.display = 'none';
      buzzProgress.style.display = '';

      // auto answer if over buzz time
      if (buzzPassedTime >= buzzTime) {
        answer();
        contentProgress.style.width = '0%';
      }
      buzzPassedTime += 0.1;
      break;
  }

}

// Handle server response
gamesock.onmessage = message => {

  const data = JSON.parse(message.data);

  if (data['response_type'] === "update") {

    // sync client with server
    gameState = data['game_state'];
    currentTime = data['current_time'];
    startTime = data['start_time'];
    endTime = data['end_time'];
    buzzStartTime = data['buzz_start_time'];
    category = data['category'];
    messages = data['messages'];
    players = data['players'];
    changeLocked = data['change_locked'];

    // Update change widgets
    categorySelect.disabled = changeLocked;
    difficultySelect.disabled = changeLocked;

    // Update scoreboard
    // TODO: Make it so we don't have to redo popover??
    updateScoreboard();

    // Update messages
    updateMessages();

    categoryHeader.innerHTML = `Category: ${category}`;
    categorySelect.value = data['room_category'];
    difficultySelect.value = data['difficulty'];
    speedSlider.value = data['speed'];

  } else if (data['response_type'] === "new_user") {

    setCookie('user_id', data['user_id']);
    setCookie('user_name', data['user_name']);
    userID = data['user_id'];
    username = data['user_name'];
    lockedOut = false;

    // Update name
    nameInput.value = username;
    ping();

  } else if (data['response_type'] === "send_answer") {

    setAnswer(data['answer']);

  } else if (data['response_type'] === "get_shown_question") {

    setQuestion(data['shown_question']);

  } else if (data['response_type'] === "get_question_feedback") {

    console.log(data)
    enableFeedbackCollapseToggle();
    expandFeedback();
    populateQuestionFeedback(data['question_feedback']);

  } else if (data['response_type'] === "lock_out") {

    lockedOut = data['locked_out'];

  } else if (data['response_type'] === "buzz_grant") {

    // Grant local client buzz
    currentAction = 'buzz';

    requestContentInput.value = '';
    requestContentInput.style.display = '';
    buzzPassedTime = 0;

    nextBtn.style.display = 'none';
    buzzBtn.style.display = 'none';
    chatBtn.style.display = 'none';

    gameState = 'contest';

    setTimeout(() => {
      requestContentInput.focus();
    }, 1);

  } else if (data['response_type'] === "kick") {
    gamesock.close();
    banAlert.style = 'display: block;'
  }
}

/**
 * ==================================================
 * START OF FUNCTIONS THAT CHANGE FRONTEND
 * ==================================================
 */

function setQuestion(question_text) {
  questionSpace.innerHTML = question_text;
  question = question_text;
}

function setAnswer(answer) {
  answerHeader.innerHTML = `Answer: ${answer}`;
}


/**
 * ==================================================
 * END OF FUNCTIONS THAT CHANGE FRONTEND
 * ==================================================
 */


/**
 * ==================================================
 * START OF FUNCTIONS THAT PRIMARILY SEND TO BACKEND
 * ==================================================
 */

/**
 * Send request to server
 * @param {string} requestType - Type of request
 * @param {string} [content=""] - Request content
 */
function sendRequest(requestType, content = "") {
  const requestData = {
    user_id: userID,
    request_type: requestType,
    content: content
  };

  gamesock.send(JSON.stringify(requestData));
}

// SENDING MESSAGES TO BACKEND
function ping() {
  sendRequest("ping");
}

function getShownQuestion() {
  if (gameState === 'playing' || gameState === 'contest') {
    sendRequest("get_shown_question");
  }
}

function join() {
  sendRequest("join");
}

function leave() {
  sendRequest("leave");
}

function newUser() {
  sendRequest("new_user");
}

function setName() {
  setCookie('user_name', nameInput.value);
  sendRequest("set_name", nameInput.value);
}

function buzz() {
  if (!lockedOut && gameState === 'playing') {
    sendRequest("buzz_init");
  }
}

function answer() {
  if (gameState === 'contest') {

    nextBtn.style.display = '';
    buzzBtn.style.display = '';
    chatBtn.style.display = '';
    requestContentInput.style.display = 'none';
    // gameState = 'playing';
    currentAction = 'idle';

    sendRequest("buzz_answer", requestContentInput.value);
    getShownQuestion();
    update();
  }
}

function chatInit() {
  if (currentAction !== 'buzz') {
    currentAction = 'chat';

    // Show input bar
    requestContentInput.value = '';
    requestContentInput.style.display = '';

    // Hide buttons 
    nextBtn.style.display = 'none';
    buzzBtn.style.display = 'none';
    chatBtn.style.display = 'none';

    setTimeout(() => {
      requestContentInput.focus();
    }, 1);
  }
}

function sendChat() {
  if (currentAction === 'chat') {

    nextBtn.style.display = '';
    buzzBtn.style.display = '';
    chatBtn.style.display = '';
    requestContentInput.style.display = 'none';
    currentAction = 'idle';

    if (requestContentInput.value !== "") sendRequest("chat", requestContentInput.value);
  }
}

function next() {
  if (gameState === 'idle') {
    gameState = 'playing';
    isFeedbackLoaded = false;

    // Collapse feedback section
    disableFeedbackCollapseToggle();
    collapseFeedback();
    sendRequest("next");
  }
}

function getAnswer() {
  if (gameState === 'idle') sendRequest("get_answer");
}

function getCurrentFeedback() {
  if (gameState === 'idle') sendRequest("get_current_question_feedback");
}

function setCategory() {
  sendRequest("set_category", categorySelect.value);
}

function setDifficulty() {
  sendRequest("set_difficulty", difficultySelect.value);
}

function setSpeed() {
  if (gameState === 'idle') sendRequest("set_speed", speedSlider.value);
}

function resetScore() {
  sendRequest("reset_score");
}

function reportMessage(messageID) {
  sendRequest("report_message", messageID);
}

/**
 * ==================================================
 * END OF FUNCTIONS THAT PRIMARILY SEND TO BACKEND
 * ==================================================
 */