// game.js
// Plays client-side game

const wsScheme = window.location.protocol == "https:" ? "wss" : "ws";
// console.log(wsScheme + '://' + window.location.host + '/ws' + window.location.pathname)
const options = {
  connectionTimeout: 1000,
  maxRetries: 10,
};
const gamesock = new ReconnectingWebSocket(wsScheme + '://' + window.location.host + '/ws' + window.location.pathname, [], options);

let userID;
let userName;
let userEmail;
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

let readingTime = 10;
let readingPassedTime = 0;

let questionTime = 10;

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

  nameInput.value = userName ? userName : "";
  emailInput.value = userEmail ? userEmail : "";

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
      readingPassedTime = 0;
      
      if (answerHeader.innerHTML === '') {
        getAnswer();
      }

      if (!isFeedbackLoaded) {
        isFeedbackLoaded = true;
        getCurrentFeedback();
      }
      contentProgress.style.width = '0%';
      break;

    case 'instruct':
      // Update if game is going
      width = Math.round(100 * (1.05 * timePassed / duration));
      instructionProgress.style.width = width + '%';

      currentTime += 0.1;

      instructionProgress.style.display = '';
      buzzProgress.style.display = 'none';
      contentProgress.style.display = 'none'
      answerHeader.innerHTML = '';

      if (readingPassedTime >= readingTime) {
        sendRequest('next');
        instructionProgress.style.width = '0%';
      }
      readingPassedTime += 0.1;
      break;
      
    case 'playing':

      // Update if game is going
      contentProgress.style.width = Math.round(100 * (1.05 * timePassed / duration)) + '%';

      buzzPassedTime = 0;
      currentTime += 0.1;

      contentProgress.style.display = '';
      buzzProgress.style.display = 'none';
      instructionProgress.style.display = 'none'
      answerHeader.innerHTML = '';
      break;

    case 'contest':
      timePassed = buzzStartTime - startTime;

      buzzProgress.style.width = Math.round(100 * (1.05 * buzzPassedTime / buzzTime)) + '%';
      instructionProgress.style.display = 'none'
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

  console.log(data);

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

    showButtons();

    // Update scoreboard
    // TODO: Make it so we don't have to redo popover??
    updateScoreboard();

    // Update messages
    updateMessages();

    categoryHeader.innerHTML = `Question Type: ${category}`;
    categorySelect.value = data['room_category'];
    difficultySelect.value = data['difficulty'];
    //speedSlider.value = data['speed'];

  } else if (data['response_type'] === "new_user") {

    setCookie('user_id', data['user_id']);
    setCookie('user_name', data['user_name']);
    setCookie('user_email', data['user_email']);
    userID = data['user_id'];
    userName = data['user_name'];
    userEmail = data['user_email'];
    lockedOut = false;

    // Update name
    nameInput.value = userName ? userName : "";
    emailInput.value = userEmail ? userEmail : "";
    ping();

  } else if (data['response_type'] === "send_answer") {

    setAnswer(data['answer']);

  } else if (data['response_type'] === "get_shown_question") {
    setQuestion(data['shown_question'], data['state']);

  } else if (data['response_type'] === "get_instructions") {
    populateInstructions(data['instructions']);
  }
  
  else if (data['response_type'] === "get_question_feedback") {

    // console.log(data)
    
    enableFeedbackCollapseToggle();
    expandFeedback();
    populateInitialQuestionFeedback(data['question_feedback']);
    populateAdditionalQuestionFeedback(data['question_feedback'])

  } else if (data['response_type'] === "lock_out") {

    lockedOut = data['locked_out'];

  } else if (data['response_type'] === "buzz_grant") {

    // Grant local client buzz
    currentAction = 'buzz';

    requestContentInput.value = '';
    requestContentInput.style.display = '';
    buzzPassedTime = 0;

    hideButtons();

    gameState = 'contest';

    setTimeout(() => {
      requestContentInput.focus();
    }, 1);

  } else if (data['response_type'] === "kick") {
    gamesock.close();
    banAlert.style = 'display: block;'
  } else if (data['response_type'] == "not_enough_players") {
    alert("Sorry! We can only begin playing once you have an opponent (two players are necessary).")
  }
  else if (data['response_type'] === "too_many_players") {
    gamesock.close();
    alert("Sorry! You can't let you join that room since there are too many active players. Rooms meant for evaluation only allow 2 players.")
    window.location.href = "/"
  }
  /* for tool use */
  else if (data['response_type'] === 'calculation_result') {
    calc_result = data['result']
    setCalculation(calc_result)
  }
  else if (data['response_type'] === 'web_search_result') {
    search_result = data['result']
    setWebSearch(search_result)
  }
  else if (data['response_type'] === 'content_selection_result') {
    select_result = data['result']
    setContentSelectionResult(select_result)
  }
}

/**
 * ==================================================
 * START OF FUNCTIONS THAT CHANGE FRONTEND
 * ==================================================
 */

function setQuestion(question_text, state) {
  if (state == 'instruct') {
    question_text = 'Read the instructions!'
  } else {
    question_text = question_text.replace('<CORRECT_BUZZ>', '<span class="badge bg-success"><i class="far fa-bell text-white"></i></span>');
    question_text = question_text.replace('<INCORRECT_BUZZ>', '<span class="badge bg-danger"><i class="far fa-bell text-white"></i></span>');
    question_text = question_text.replace('<CURRENT_BUZZ>', '<span class="badge bg-primary"><i class="far fa-bell text-white"></i></span>');
  }
  questionSpace.innerHTML = question_text;
  question = question_text;
}

function setAnswer(answer) {
  answer = answer.replace("{", "<u><b>").replace("}", "</b></u>");
  answerHeader.innerHTML = answer !== '' ? `Answer: ${answer}` : '';
}

function setCalculation(res) {
  document.getElementById('calc-result').textContent = res;
}

function setWebSearch(res) {
  srcdoc = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Bootstrap demo</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-aFq/bzH65dt+w6FI2ooMVUpc+21e0SRygnTpmBvdBgSdnuTN7QbdgL+OapgHtvPp" crossorigin="anonymous">
  </head>
  <body>`
  srcdoc += res
  srcdoc += '\n</body>'
  document.getElementById('view-page-collapse').srcdoc = srcdoc
  
  res;
}

function setContentSelectionResult(res) {
  document.getElementById('calc-result').textContent = res;
}



function hideButtons() {
  skipBtn.style.display = 'none';
  nextBtn.style.display = 'none';
  buzzBtn.style.display = 'none';
  //chatBtn.style.display = 'none';
}

function showButtons() {

  if (currentAction == 'idle') {
    switch (gameState) {
      case 'playing':
        skipBtn.style.display = '';
        nextBtn.style.display = 'none';
        buzzBtn.style.display = '';
        //chatBtn.style.display = '';
        break;
      case 'idle':
        skipBtn.style.display = 'none';
        nextBtn.style.display = '';
        buzzBtn.style.display = 'none';
        //chatBtn.style.display = '';
        break;
      case 'contest':
        skipBtn.style.display = 'none';
        nextBtn.style.display = 'none';
        buzzBtn.style.display = 'none';
        //chatBtn.style.display = 'none';
        break;
      case 'instruct':
        skipBtn.style.display = 'none';
        nextBtn.style.display = 'none';
        buzzBtn.style.display = 'none';
        //chatBtn.style.display = 'none';
        break;
    }
  } else {
    skipBtn.style.display = 'none';
    nextBtn.style.display = 'none';
    buzzBtn.style.display = 'none';
    // chatBtn.style.display = 'none';
  }

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
  console.log('sending request:', requestType);
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

function setUserData() {
  setCookie('user_name', nameInput.value);
  setCookie('user_email', emailInput.value);
  setCookie('user_optOut', optOutInput.checked);
  userName = nameInput.value;
  userEmail = emailInput.value;
  sendRequest("set_user_data", {'user_name': nameInput.value, 'user_email': emailInput.value});
}

function buzz() {
  if (!lockedOut && gameState === 'playing') {
    sendRequest("buzz_init");
  }
}

function answer() {
  if (gameState === 'contest') {

    showButtons();
    requestContentInput.style.display = 'none';
    // gameState = 'playing';
    currentAction = 'idle';

    sendRequest("buzz_answer", requestContentInput.value);
    getShownQuestion();
  }
}

function submitInitialFeedback() {
  if (gameState === 'idle') {
    sendRequest("submit_initial_feedback", {'guessed_generatation_method': guessedGenerationMethod, 'interestingness_rating': interestingnessRating});
  }
}

function submitAdditionalFeedback() {
  if (gameState === 'idle') {
    sendRequest("submit_additional_feedback",
    {
      'submitted_clue_order': clueOrder,
      'submitted_factual_mask_list': factualMaskList, 
      'improved_question': improvedQuestionForm.value,
      'feedback_text': feedbackTextForm.value
    });
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

function skip() {
  if (gameState === 'playing') {
    isFeedbackLoaded = false;
    sendRequest("skip");
  }
}

function next() {
  emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  if (userName && (optOutInput.checked || (userEmail && emailRegex.test(userEmail)))) {
    if (gameState === 'idle' && completedFeedback) {
      gameState = 'playing';
      isFeedbackLoaded = false;

      // Collapse feedback section
      // disableFeedbackCollapseToggle();
      // collapseFeedback();
      sendRequest("next");
    }
  } else 
    alert("Please input a valid username and email before continuing.");
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