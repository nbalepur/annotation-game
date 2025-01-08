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

let allowSwapsGlobal = null; // true/false
let gameState = 'idle'; // idle, playing, contest
let currentAction = 'idle'; // idle, buzz, chat, 

let currentTime;
let startTime;
let endTime;
let buzzStartTime;
let buzzPassedTime = 0;
let graceTime = 3;
let buzzTime = 5;

let readingTime = 30;
// let readingTime = 3; // seconds to read the question
let readingPassedTime = 0;

let questionTime = 10000000;
// let questionTime = 3; // secconds to answer the question
let questionPassedTime = 0;

let isTutorial = false;

let question;
let category;
let players;
let messages;
let changeLocked = false;

let logNoneComparison = false;

let isFeedbackLoaded = false;

let experimentType = null;

// Set up client
document.addEventListener("DOMContentLoaded", () => {
  gamesock.onopen = () => {
    // Ensure the DOM is ready and elements exist
    //retrieveUserdata();
    
    if (userID === undefined) {
      newUser();
    } else {
      join();
    }

    nameInput.value = userName ? userName : "";
    emailInput.value = userEmail ? userEmail : "";

    // Set up current time if newly joined
    currentTime = buzzStartTime;
  };
});

/**
 * Update game locally
 */
function update() {
  // console.log(gameState);
  //console.log('update:', question, gameState);
  if (question === undefined) {
    return;
  }

  let timePassed = currentTime - startTime;
  let duration = endTime - startTime;

  switch (gameState) {

    case 'idle':
      lockedOut = false;
      logNoneComparison = false;
      readingPassedTime = 0;
      
      // if (answerHeader.innerHTML === '') {
      //   getAnswer();
      // }

      // if (!isFeedbackLoaded) {
      //   isFeedbackLoaded = true;
      //   getCurrentFeedback();
      // }
      contentProgress.style.width = '0%';
      break;

    case 'compare':
      // Update if game is going
      questionPassedTime = 0;

      if (!isTutorial) {
        width = Math.min(100, (100 * ((1.01 * readingPassedTime) / (2 * readingTime))));
        instructionProgress.style.width = width + '%';
      }

      currentTime += 0.1;

      instructionProgress.style.display = '';
      buzzProgress.style.display = 'none';
      contentProgress.style.display = 'none'
      // answerHeader.innerHTML = '';

      if (readingPassedTime >= 2 * readingTime && !logNoneComparison && !isTutorial) {
        selectPlan("None");
        instructionProgress.style.width = '0%';
        logNoneComparison = true;
      }
      readingPassedTime += 0.1;
      break;

    case 'instruct':
      // Update if game is going
      questionPassedTime = 0;

      if (!isTutorial) {
        width = Math.min(100, (100 * ((1.01 * readingPassedTime) / readingTime)));
        instructionProgress.style.width = width + '%';
      }

      currentTime += 0.1;

      instructionProgress.style.display = '';
      buzzProgress.style.display = 'none';
      contentProgress.style.display = 'none'
      // answerHeader.innerHTML = '';

      if (readingPassedTime >= readingTime && !logNoneComparison && !isTutorial) {
        skip();
        instructionProgress.style.width = '0%';
        logNoneComparison = true;
      }
      readingPassedTime += 0.1;
      break;
      
    case 'playing':

      // Update if game is going
      const passed_prop = (1.01 * questionPassedTime / questionTime)
      if (!isTutorial) {
        contentProgress.style.width = (100 * passed_prop).toFixed(4) + '%';
      }

      // if (passed_prop > 0) {
      //   reportBtn.style.display = '';
      // }

      buzzPassedTime = 0;
      currentTime += 0.1;

      contentProgress.style.display = '';
      buzzProgress.style.display = 'none';
      instructionProgress.style.display = 'none'
      // answerHeader.innerHTML = '';

      if (questionPassedTime >= questionTime && !isTutorial) {
        sendRequest('no_buzz');
        contentProgress.style.width = '0%';
      }
      questionPassedTime += 0.1;

      break;

    case 'contest':
      timePassed = buzzStartTime - startTime;

      buzzProgress.style.width = (100 * (1.01 * buzzPassedTime / buzzTime)).toFixed(4) + '%';
      instructionProgress.style.display = 'none'
      contentProgress.style.display = 'none';
      buzzProgress.style.display = '';
      buzzProgress.style.visibility = 'visible';

      // auto answer if over buzz time
      if (buzzPassedTime >= buzzTime) {
        answer(requestContentInput.value);
        buzzProgress.style.width = '0%';
      }
      buzzPassedTime += 0.1;
      break;
  }

}

// Handle server response
gamesock.onmessage = message => {

  const data = JSON.parse(message.data);
  //console.log(data['response_type'], data);

  if (data['response_type'] === "update") {

    // sync client with server
    currentTime = data['current_time'];
    startTime = data['start_time'];
    endTime = data['end_time'];
    buzzStartTime = data['buzz_start_time'];
    category = data['category'];
    messages = data['messages'];
    players = data['players'];
    changeLocked = data['change_locked'];

    // Update change widgets
    // categorySelect.disabled = changeLocked;
    // difficultySelect.disabled = changeLocked;

    //showButtons();

    // Update scoreboard
    // TODO: Make it so we don't have to redo popover??
    //updateScoreboard();

    // Update messages
    updateMessages();

    //categoryHeader.innerHTML = `Question Type: ${category}`;
    // categorySelect.value = data['room_category'];
    // difficultySelect.value = data['difficulty'];
    //speedSlider.value = data['speed'];

  } else if (data['response_type'] === "new_user") {

    // setCookie('user_id', data['user_id']);
    // setCookie('user_name', data['user_name']);
    // setCookie('user_email', data['user_email']);
    userID = data['user_id'];
    userName = data['user_name'];
    userEmail = data['user_email'];
    lockedOut = false;

    // Update name
    nameInput.value = userName ? userName : "";
    emailInput.value = userEmail ? userEmail : "";
    ping();

  } else if (data['response_type'] === "set_experiment_type") {
    setExperimentInstructions(data['experiment_type'], data['category_preference'], data['prefers_auto_scroll']);
  } else if (data['response_type'] === "send_answer") {
    setAnswer(data['answer']);
  } else if (data['response_type'] === "get_shown_question") {
    setQuestion(data['shown_question'], data['state']);
    isTutorial = data['is_tutorial'];
    resetRogueCheckbox();
    clearReportData();
  } else if (data['response_type'] === 'clear_instructions') {
    clearInstructions();
  } else if (data['response_type'] === 'check_duplicate_user_data') {
    setUserData(data['username'], data['email']);
  } 
  else if (data['response_type'] === "update_instructions") {
    if (data['should_clear']) {
      clearInstructions();
    }
    populateInstructions(data['instructions'], data['step_num'], data['is_last_step'], false);
    if (data['is_last_step']) {
      stepBtn.style.display = 'none';
    }
  } else if (data['response_type'] === 'update_swapped_instructions') {
    clearInstructions();
    populateInstructions(data['instructions'], -1, data['is_last_step'], true);
    if (data['subanswers']) {
      populateSubanswers(data['subanswers']);
    }
    if (data['is_last_step']) {
      stepBtn.style.display = 'none';
    } else {
      stepBtn.style.display = '';
    }
  } else if (data['response_type'] === "populate_comparison") {
    populateComparisonPane(data['question'], data['instructions_a'], data['instructions_b']);
  } else if (data['response_type'] === 'update_tools') {
    updateTools(data['use_calculator'], data['use_doc'], data['use_web']);
  } else if (data['response_type'] === 'disable_tools') {
    toggleDisableButtons(data['should_disable']);
    if (data['should_disable']) {
      clearFields(data['should_clear_document']);
    }
  } else if (data['response_type'] === 'disable_plan') {
    disablePlan();
  } else if (data['response_type'] === 'loading_doc') {
    loadingDoc();
  } else if (data['response_type'] === 'update_doc') {
    updateDoc(data['use_doc'], data['doc_content']);
  } else if (data['response_type'] === 'update_status') {
    updateStatus(data['status'], data['player'], data['answer'], data['allow_swaps']);
  } else if (data['response_type'] === 'toggle_comparison') {
    toggleComparisonViewer(data['show_comparison']);
  } else if (data['response_type'] === "get_question_feedback") {

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

    requestContentInput.value = data['guess'];
    requestContentInput.style.display = '';
    buzzPassedTime = 0;

    hideButtons();

    // gameState = 'contest';

    setTimeout(() => {
      requestContentInput.focus();
    }, 1);

  } else if (data['response_type'] === "kick") {
    gamesock.close();
    banAlert.style = 'display: block;'
  } else if (data['response_type'] == "not_enough_players") {
    alert("Sorry! We can only begin playing once you have an opponent (two active players are necessary).")
  }
  else if (data['response_type'] === "too_many_players") {
    gamesock.close();
    alert("Sorry! You can't let you join that room since there are too many active players. Try joining another room!")
    window.location.href = "/"
  }
  /* for tool use */
  else if (data['response_type'] === 'calculation_result') {
    calc_result = data['result'];
    setCalculation(calc_result);
  }
  else if (data['response_type'] === 'navigate_web_search_result') {
    setNavigateWebSearch(data['html'], data['typed_query_web'],  data['typed_query_search'], data['select_idxs'], data['allow_forwards'], data['allow_backwards']);
  }
  else if (data['response_type'] === 'web_search_result') {
    search_result = data['result'];
    updateTools(false, true, true);
    setWebSearch(search_result, data['allow_forwards'], data['allow_backwards']);
    docSearchInput.value = data['doc_search_query'];
  }
  else if (data['response_type'] === 'content_selection_result') {
    doc_idxs = data['result'];
    num_docs = data['num_docs'];
    setContentSelectionResult(doc_idxs, num_docs);
    disableNavigation(data['allow_forwards'], data['allow_backwards']);
  } else if (data['response_type'] === 'reauthenticate') {
    window.location.href = '/?reauthenticate=true';
  }
}

/**
 * ==================================================
 * START OF FUNCTIONS THAT CHANGE FRONTEND
 * ==================================================
 */

function setQuestion(question_text, state) {
  question_text = question_text.replace('<CORRECT_BUZZ>', '<span class="badge bg-success"><i class="far fa-bell text-white"></i></span>');
  question_text = question_text.replace('<INCORRECT_BUZZ>', '<span class="badge bg-danger"><i class="far fa-bell text-white"></i></span>');
  question_text = question_text.replace('<CURRENT_BUZZ>', '<span class="badge bg-primary"><i class="far fa-bell text-white"></i></span>');
  questionSpace.innerHTML = question_text.replace(/\n\n/g, '<br /><br />');
  question = question_text;
}

function setReadingTime(is_tutorial) {
  if (is_tutorial) {

  } else {
    
  }
}


// function setAnswer(answer) {
//   answer = answer.replace("{", "<u><b>").replace("}", "</b></u>");
//   answerHeader.innerHTML = answer !== '' ? `Answer: ${answer}` : 'Answer:';
// }

// cache the instructions so we dont keep seeing it
function setExperimentInstructions(experimentType, categoryPreference, autoScroll) {
  sessionStorage.setItem('seenInstructions', true);
  categorySelect.value = categoryPreference === 'Multi-Hop' ? 'Trivia': categoryPreference;

  if (categoryPreference === 'Multi-Hop' || categoryPreference === 'Everything') {
    autoScrollContainer.style.display = '';
  } else {
    autoScrollContainer.style.display = 'none';
  }

  autoScrollCheckbox.checked = autoScroll;
}

function setAutoScroll(prefersAutoScroll) {
  autoScrollCheckbox.checked = prefersAutoScroll;
}

function setCalculation(res) {
  calculatorResult.value = res;
  
  calculatorResult.classList.add('flash-highlight');
  setTimeout(() => {
    calculatorResult.classList.remove('flash-highlight');
  }, 500);
}

function disableNavigation(allowFwd, allowBwd) {
  if (allowFwd) {
    fwdSearch.classList.remove('btn-outline-info');
    fwdSearch.classList.add('btn-info');
  } else {
    fwdSearch.classList.remove('btn-info');
    fwdSearch.classList.add('btn-outline-info');
  }

  if (allowBwd) {
    bwdSearch.classList.remove('btn-outline-info');
    bwdSearch.classList.add('btn-info');
  } else {
    bwdSearch.classList.remove('btn-info');
    bwdSearch.classList.add('btn-outline-info');
  }

  bwdSearch.disabled = !allowBwd;
  fwdSearch.disabled = !allowFwd;
}

function setWebSearch(res, allowFwd, allowBwd) {
  document.getElementById('view-page-collapse').srcdoc = res;
  disableNavigation(allowFwd, allowBwd);
}

function setNavigateWebSearch(html, typedQueryWeb, typedQuerySearch, docIdxs, allowFwd, allowBwd) {
  const iframe = document.getElementById('view-page-collapse');
  iframe.onload = () => {
    webSearchInput.value = typedQueryWeb;
    docSearchInput.value = typedQuerySearch;
    setContentSelectionResult(docIdxs, 1);
    iframe.onload = null;
  };
  setWebSearch(html, allowFwd, allowBwd);
}

function setContentSelectionResult(doc_idxs, num_docs) {

  if (doc_idxs.length === 1) {
    const iframe = document.getElementById('view-page-collapse');
    const iframeDocument = iframe.contentDocument || iframe.contentWindow.document;
    
    // console.log(num_docs);

    for (let i = 0; i < num_docs; i++) {
      const currElem = iframeDocument.getElementById('element-' + i);
      if (currElem && currElem.classList.contains('highlight')) {
        currElem.classList.remove('highlight');
        // console.log('removed!');
      }
    }

    const targetElement = iframeDocument.getElementById('element-' + doc_idxs[0]);
    console.log(targetElement);
    if (targetElement) {
      targetElement.scrollIntoView({ behavior: 'smooth', block: doc_idxs[0] > 3 ? 'center' : 'nearest'});
      targetElement.classList.add('highlight');
    }
  }
}

function sendToNotes(copied_text) {
  let content = scratchpadInput.innerHTML;

  if (content.includes('</ul>')) {
    const ul = scratchpadInput.querySelector('ul');
    const newListItem = document.createElement('li');
    newListItem.textContent = copied_text;
    ul.appendChild(newListItem);
  } else {
    const newList = `<ul style="padding-left: 5px; margin-left: 10px;"><li>${copied_text}</li></ul>`;
    scratchpadInput.innerHTML = newList;
  }
}

function hideButtons() {
  // skipBtn.style.display = 'none';
  nextBtn.style.display = 'none';
  buzzBtn.style.display = 'none';
  //chatBtn.style.display = 'none';
}

function resetTime() {
  readingPassedTime = 0;
  questionPassedTime = 0;
  buzzPassedTime = 0;
}

function shouldShowStepBtn() {
  const instructionFrame = document.getElementById('instruction-frame')
  const iframeDoc = instructionFrame.contentDocument || instructionFrame.contentWindow.document;
  const checkbox = iframeDoc.getElementById('edit-instructions-checkbox');
  if (checkbox.checked) {
    return false;
  }

  const container = iframeDoc.getElementById('instructions-container');
  const lastStep = container.querySelector('.step-div:first-child');
  return (lastStep.querySelector('#step-buzz-btn') === null);
}

function showButtonsForState(currGameState, allowSwaps) {
  allowSwapsGlobal = allowSwaps;
  switch (currGameState) {
    case 'compare':
      reportBtn.style.display = 'none';
      nextBtn.style.display = 'none';
      skipBtn.style.display = 'none';
      stepBtn.style.display = 'none';
      buzzBtn.style.display = 'none';
      swapBtn.style.display = 'none';
      settingsBtn.style.display = '';
      settingsBtn.style.visibility = 'hidden';
      toggleFollowCheckbox(false);
      break;
    case 'compare_correct':
        reportBtn.style.display = 'none';
        nextBtn.style.display = 'none';
        skipBtn.style.display = 'none';
        stepBtn.style.display = 'none';
        buzzBtn.style.display = 'none';
        swapBtn.style.display = 'none';
        settingsBtn.style.display = '';
        settingsBtn.style.visibility = 'hidden';
        toggleFollowCheckbox(false);
        break;
    case 'compare_incorrect':
      reportBtn.style.display = 'none';
      nextBtn.style.display = 'none';
      skipBtn.style.display = 'none';
      stepBtn.style.display = 'none';
      buzzBtn.style.display = 'none';
      swapBtn.style.display = 'none';
      settingsBtn.style.display = '';
      settingsBtn.style.visibility = 'hidden';
      toggleFollowCheckbox(false);
      break;
    case 'playing':
      // skipBtn.style.display = '';

      // is it time for the next step or to buzz?
      const shouldShowStep = shouldShowStepBtn();

      reportBtn.style.display = '';
      nextBtn.style.display = 'none';
      skipBtn.style.display = 'none';
      stepBtn.style.display = shouldShowStep ? '' : 'none';
      buzzBtn.style.display = shouldShowStep ? 'none' : '';
      swapBtn.style.display = allowSwaps ? '' : 'none';
      settingsBtn.style.display = '';
      settingsBtn.style.visibility = 'hidden';
      toggleFollowCheckbox(true);
      //chatBtn.style.display = '';
      break;
    case 'idle':
      // skipBtn.style.display = 'none';
      nextBtn.style.display = '';
      skipBtn.style.display = 'none';
      buzzBtn.style.display = 'none';
      stepBtn.style.display = 'none';
      swapBtn.style.display = 'none';
      settingsBtn.style.display = '';
      settingsBtn.style.visibility = 'visible';
      reportBtn.style.display = '';
      toggleFollowCheckbox(false);
      resetTime();
      //chatBtn.style.display = '';
      break;
    case 'contest':
      // skipBtn.style.display = 'none';
      nextBtn.style.display = 'none';
      skipBtn.style.display = 'none';
      buzzBtn.style.display = 'none';
      reportBtn.style.display = 'none';
      stepBtn.style.display = 'none';
      swapBtn.style.display = 'none';
      //settingsBtn.style.visibility = 'hidden';
      settingsBtn.style.display = 'none';
      toggleFollowCheckbox(false);
      //chatBtn.style.display = 'none';
      break;
    case 'instruct':
      // skipBtn.style.display = 'none';
      nextBtn.style.display = 'none';
      skipBtn.style.display = '';
      buzzBtn.style.display = 'none';
      settingsBtn.style.display = '';
      reportBtn.style.display = 'none';
      settingsBtn.style.visibility = 'hidden';
      stepBtn.style.display = 'none';
      swapBtn.style.display = 'none';
      toggleFollowCheckbox(false);
      //chatBtn.style.display = 'none';
      break;

    case 'buzz_correct':
      nextBtn.style.display = '';
      skipBtn.style.display = 'none';
      buzzBtn.style.display = 'none';
      stepBtn.style.display = '';
      swapBtn.style.display = '';
      settingsBtn.style.display = '';
      settingsBtn.style.visibility = 'visible';
      reportBtn.style.display = '';
      toggleFollowCheckbox(false);
      break;    
  }
}

function showButtons() {

  if (currentAction == 'idle') {
    showButtonsForState(gameState, false);
  } else {
    // skipBtn.style.display = 'none';
    nextBtn.style.display = 'none';
    buzzBtn.style.display = 'none';
    settingsBtn.style.visibility = 'hidden';
    // chatBtn.style.display = 'none';
  }
}

// function adjustQuestionRowHeight() {
//   // Get the height of the viewport
//   const viewportHeight = window.innerHeight;

//   // Get the height of the button-timer-row
//   const buttonTimerRow = document.getElementById('button-timer-row');
//   const buttonTimerHeight = buttonTimerRow ? buttonTimerRow.offsetHeight : 0;

//   // Get the offset of the game-container
//   const gameContainer = document.getElementById('game-container');
//   const gameContainerOffset = gameContainer ? gameContainer.offsetTop : 0;

//   // Get the footer's offset from the top of the page
//   const footer = document.getElementById('footer');
//   const footerOffset = footer ? footer.offsetTop : viewportHeight; // Use viewport height if no footer found

//   // Calculate the available space above the footer
//   const availableHeight = footerOffset - gameContainerOffset - buttonTimerHeight;

//   // Set the height for question-row
//   const questionRow = document.getElementById('question-row');
//   if (questionRow) {
//       questionRow.style.height = `${availableHeight}px`;
//   }
// }

// window.addEventListener('load', adjustQuestionRowHeight);
// window.addEventListener('resize', adjustQuestionRowHeight);


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

function clearUserData() {
  nameInput.classList.remove("is-invalid");
  nameInput.classList.remove("is-valid");
  emailInput.classList.remove("is-invalid");
  emailInput.classList.remove("is-valid");

  if (nameInput.value == userName && emailInput.value == userEmail) {
    saveStatus.style.display = '';
    saveStatus.textContent = 'Account settings saved!';
    saveStatus.className = 'text-success';
    return;
  }
  sendRequest("set_user_data", {'user_name': nameInput.value, 'user_email': emailInput.value});
}

function setUserData(name, email) {
  saveStatus.style.display = '';
  if (name == '' && email == '') {
    saveStatus.textContent = 'That username and email are already in use, please try another.';
    saveStatus.className = 'text-danger';
  } else if (name == '') {
    saveStatus.textContent = 'That username is already in use, please try another.';
    saveStatus.className = 'text-danger';
  } else if (email == '') {
    saveStatus.textContent = 'That email is already in use, please try another.';
    saveStatus.className = 'text-danger';
  } else {
    userName = name;
    userEmail = email;
    saveStatus.textContent = 'Account settings saved!';
    saveStatus.className = 'text-success';
  }
}

function buzz() {
  if (!lockedOut && gameState === 'playing') {

    const iframe = document.getElementById('instruction-frame');
    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
    const container = iframeDoc.getElementById('instructions-container');
    const checkbox = iframeDoc.getElementById('edit-instructions-checkbox');

    if (checkbox.checked) {
      const notes = iframeDoc.getElementById('rogue-notes-area');
      if (notes.value.trim() === '') {
        const rogueStatus = iframeDoc.getElementById('rogue-notes-status');
        rogueStatus.style.visibility = '';
        rogueStatus.innerHTML = '<p class="text-danger"> <i class="bi bi-exclamation-octagon-fill"></i> Please type your plan or thought process before buzzing!</p>';
        return;
      }
      sendRequest("buzz_init", '');
    } else {
      const currentLastStep = container.querySelector('.step-div:first-child');
      const guess = currentLastStep.querySelector('textarea').value;
      answerWrapper(guess);
    }
    // sendRequest("buzz_init", guess);

    // toggleCloseButtonVisibility(false);
  }
}

function answerWrapper(guess) {
  subanswers = getSubanswers();
  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
  const container = iframeDoc.getElementById('instructions-container');
  const warningDiv = container.querySelector(`#step-warning-${subanswers.length}`);

  if (guess.trim() === '') {
    warningDiv.style.visibility = '';
    warningDiv.innerHTML = '<p class="text-danger" style="margin-top: 5px; margin-bottom: 0px;"> <i class="bi bi-exclamation-octagon-fill"></i> Please enter an answer before buzzing!</p>';
    focusTextInput(`answer-step-${subanswers.length}`);
    return;
  }
  warningDiv.style.visibility = 'hidden';
  answer(guess);
}

function answer(guess) {
  showButtons();
  requestContentInput.style.display = 'none';
  currentAction = 'idle';   
  sendRequest("buzz_answer", guess);
  getShownQuestion();
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
  sendRequest('next');
  instructionProgress.style.width = '0%';
}

function settings() {
  const offcanvasElement = document.getElementById('offcanvasSettings');
  isToggled = offcanvasElement.classList.contains('show');
  if (gameState === 'idle') {
    if (isToggled) {
      document.querySelector('#settings-close-btn').click();
    } else {
      document.querySelector('#settings-btn').click();
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const offcanvasElement = document.getElementById('offcanvasSettings');

  offcanvasElement.addEventListener('hide.bs.offcanvas', () => {
      nameInput.classList.remove('is-valid', 'is-invalid');
      emailInput.classList.remove('is-valid', 'is-invalid');
      saveStatus.style.display = 'none';

      nameInput.value = userName;
      emailInput.value = userEmail;
      
      let fade = document.getElementsByClassName('offcanvas-backdrop fade show')
      for(let i = 0; i < fade.length; i++) {
        fade[i].remove();
      }
  });
});



function focusTextInput(elem_id) {
  const focusInput = document.getElementById(elem_id);
  if (focusInput) {
    focusInput.focus();
  } else {
    console.warn(`No element with ID ${elem_id} found.`);
  }
}

function focusTextInputInstructions(elem_id) {
  const instructionFrame = document.getElementById('instruction-frame')
  const iframeDoc = instructionFrame.contentDocument || instructionFrame.contentWindow.document;
  const focusInput = iframeDoc.getElementById(elem_id);
  if (focusInput) {
    focusInput.focus();
  } else {
    console.warn(`No element with ID ${elem_id} found.`);
  }
}

function next() {
  if (gameState === 'idle') {
      statusText.scrollIntoView({ block: 'start' });
      sendRequest("next");
  }
//   } else {
//     settings();
//     alert("Please input a valid username and email before continuing.");
//  }
}

function next_step() {
  const subanswers = getSubanswers();

  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
  const container = iframeDoc.getElementById('instructions-container');
  if (subanswers[subanswers.length - 1].trim() === '') {
    const warningDiv = container.querySelector(`#step-warning-${subanswers.length}`);
    if (warningDiv.style.visibility === 'hidden') {
      warningDiv.style.visibility = '';
      return;
    }
    warningDiv.style.visibility = 'hidden';
  }

  sendRequest("show_next_step", subanswers);
}



function skip_plan() {
  sendRequest("skip_plan");
}

function swap_plan() {
  subanswers = getSubanswers();
  sendRequest("swap_plan", subanswers);
  showButtonsForState(gameState, true);
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