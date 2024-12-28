const toolContainer = document.getElementById('toolbox-container');

const instructionHeader = document.getElementById('instruction-header');
const instructionCollapse = document.getElementById('instruction-collapse');

const calculatorTool = document.getElementById('calculator-tool');
const calculatorOperators = document.getElementById('calculator-operators');
const googleTool = document.getElementById('google-tool');
const contentSelectorTool = document.getElementById('content-selector-tool');

const calculatorResultBtn = document.getElementById('calc-copy-btn');
const calculatorToolBtn = document.getElementById('calc-expression-btn');
const googleToolBtn = document.getElementById('google-query-btn');
const contentSelectorToolBtn = document.getElementById('content-search-btn');

const calculatorResult = document.getElementById('calc-result');

const calculatorToolInput = document.getElementById('calc-expression');
const googleToolInput = document.getElementById('google-query');
const contentSelectorToolInput = document.getElementById('content-search');

const instructionsFrame = document.getElementById('instruction-frame');

const docViewer = document.getElementById('doc-viewer');
const docContent = document.getElementById('view-page-collapse')

const statusText = document.getElementById('status-text');

const mathClearBtn = document.getElementById('calc-clear-btn');
const findClearBtn = document.getElementById('find-clear-btn');
const searchClearBtn = document.getElementById('search-clear-btn');

const copySearchBtn = document.getElementById('copy-search-btn');
const copyMathBtn = document.getElementById('calculator-tool-result');

function toggleFollowCheckbox(isVisible) {
  const iframe = instructionsFrame;
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
  const followPlanDiv = iframeDoc.getElementById('follow-plan-div');
  if (followPlanDiv) {
    if (isVisible && followPlanDiv.style.visibility === 'hidden') {
      followPlanDiv.style.visibility = '';
      followPlanDiv.checked = false;
    } else {
      followPlanDiv.style.visibility = isVisible ? '' : 'hidden';
    }
  }
}

function parseInstructions(instr_object) {
    steps = instr_object['steps'];
    steps_html = '<ol>' + steps.map(item => `<li>${item}</li>`).join('') + '</ol>';
    return steps_html;
}

function closeLastButton() {
  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
  const container = iframeDoc.getElementById('instructions-container');
  if (container) {
    const newLastStep = container.querySelector('.step-div:first-child');
    if (newLastStep) {
      const closeButton = newLastStep.querySelector('.close-btn');
      if (closeButton) {
        closeButton.click();
      }
    }
  }
}

function focusLastInstruction() {
  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
  const container = iframeDoc.getElementById('instructions-container');
  if (container) {
    const newLastStep = container.querySelector('.step-div:first-child');
    if (newLastStep) {
      const textArea = newLastStep.querySelector('textarea');
      textArea.focus();
    }
  }
}

function addBlankInstruction() {

  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
  const container = iframeDoc.getElementById('instructions-container');

  const currentLastStep = container.querySelector('.step-div:first-child .close-btn');
  if (currentLastStep) {
    currentLastStep.remove();
  }

  const lastIndex = container.querySelectorAll('.step-div').length;
  const lastInstruction = "Edit this step to fit your needs"

  const shouldEdit = true;

  const stepDiv = iframeDoc.createElement('div');
  stepDiv.className = 'p-4 mb-2 border bg-light position-relative step-div';
  stepDiv.id = `step-div-${lastIndex + 1}`

  stepDiv.innerHTML = `
  <button type="button" class="close-btn" style="position: absolute; top: 0px; right: 0px; border: none; background: none; font-size: 20px; cursor: pointer;">&times;</button>
  <p style="margin-bottom: 5px;"><strong>Step ${lastIndex + 1}: </strong><span id="step-${lastIndex + 1}" class="instructions-edit" contenteditable="${shouldEdit}">${lastInstruction}</span></p>
  <div class="input-group">
    <textarea id="answer-step-${lastIndex + 1}" class="form-control input-sm" placeholder="Enter the answer here" rows="1"></textarea>
    <button type="button" class="btn btn-sm btn-warning copy-btn" data-copy-id="answer-step-${lastIndex + 1}">
      <i class="bi bi-copy"></i> Copy to Tool
    </button>
  </div>
`;

container.prepend(stepDiv);

const closeButton = stepDiv.querySelector('.close-btn');
closeButton.addEventListener('click', () => {
  removeStep(stepDiv, false);
});

const clipboardButtons = stepDiv.querySelectorAll('.copy-btn');
clipboardButtons.forEach(button => {
  button.addEventListener('click', function() {
    const inputId = this.getAttribute('data-copy-id');
    const textToCopy = iframeDoc.getElementById(inputId).value;
    copyTextToTool(textToCopy);
  });
});
}


function clearInstructions() {
  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
  const container = iframeDoc.getElementById('instructions-container');
  container.innerHTML = '';
}

function parseFullInstructions(inputInstructions, addCloseBtn, isLastStep) {

  console.log('showing it all!');

  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

  const container = iframeDoc.getElementById('instructions-container');
  container.innerHTML = '';

  inputInstructions['steps'].forEach((instruction, index) => {
    const stepDiv = iframeDoc.createElement('div');
    stepDiv.className = 'p-4 mb-2 border bg-light position-relative step-div';
    stepDiv.id = `step-div-${index + 1}`;
    stepDiv.setAttribute('is-custom', false);

    const buttonHTML = isLastStep && index === inputInstructions['steps'].length - 1
      ? `<button type="button" class="btn btn-sm btn-danger buzz-btn" id="step-buzz-btn">Buzz</button>`
      : `<button type="button" class="btn btn-sm btn-warning copy-btn" data-copy-id="answer-step-${index + 1}">
           <i class="bi bi-copy"></i> Copy to Tool
         </button>`;

    stepDiv.innerHTML = `
      <p style="margin-bottom: 5px;"><strong>Step ${index + 1}: </strong><span id="step-${index + 1}" class="instructions-edit">${instruction}</span></p>
      <div class="input-group">
        <textarea id="answer-step-${index + 1}" class="form-control input-sm" placeholder="Enter the answer here" rows="1"></textarea>
        ${buttonHTML}
      </div>
    `;

    if (addCloseBtn && index === inputInstructions['steps'].length - 1 && index !== 0) {
      const closeButton = iframeDoc.createElement('button');
      closeButton.type = 'button';
      closeButton.className = 'close-btn';
      closeButton.innerHTML = '&times;';
      closeButton.style.position = 'absolute';
      closeButton.style.top = '0px';
      closeButton.style.right = '0px';
      closeButton.style.border = 'none';
      closeButton.style.background = 'none';
      closeButton.style.fontSize = '20px';
      closeButton.style.cursor = 'pointer';

      closeButton.addEventListener('click', () => {
        removeStep(stepDiv, isLastStep);
      });

      stepDiv.appendChild(closeButton);
    }

    const textarea = stepDiv.querySelector('textarea');
    textarea.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        if (isLastStep && index === inputInstructions['steps'].length - 1) {
          buzz();
        } else {
          next_step();
          textarea.blur();
        }
      }
    });

    if (isLastStep && index === inputInstructions['steps'].length - 1) {
      const stepBuzzButton = stepDiv.querySelector('.buzz-btn');
      if (stepBuzzButton) {
        stepBuzzButton.addEventListener('click', () => {
          buzz();
        });
      }
      buzzBtn.style.display = '';
    } else {
      const copyButton = stepDiv.querySelector('.copy-btn');
      if (copyButton) {
        copyButton.addEventListener('click', function() {
          const inputId = this.getAttribute('data-copy-id');
          const textToCopy = iframeDoc.getElementById(inputId).value;
          copyTextToTool(textToCopy);
        });
      }

      buzzBtn.style.display = 'none';
    }

    container.prepend(stepDiv);
  });
}


function parseInstructionsBox(inputInstructions, isLastStep, stepNum) {

  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
  const container = iframeDoc.getElementById('instructions-container');

  const currentLastStep = container.querySelector('.step-div:first-child .close-btn');
  if (currentLastStep) {
    currentLastStep.remove();
  }

  const lastIndex = container.querySelectorAll('.step-div').length;
  const lastInstruction = inputInstructions['steps'][inputInstructions['steps'].length - 1];

  const stepDiv = iframeDoc.createElement('div');
  stepDiv.className = 'p-4 mb-2 border bg-light position-relative step-div';
  stepDiv.id = `step-div-${lastIndex + 1}`;

  if (stepNum === 1) {
    stepDiv.innerHTML = `
      <p style="margin-bottom: 5px;"><strong>Step ${lastIndex + 1}: </strong><span id="step-${lastIndex + 1}" class="instructions-edit">${lastInstruction}</span></p>
      <div class="input-group">
        <textarea id="answer-step-${lastIndex + 1}" class="form-control input-sm" placeholder="Enter the answer here" rows="1"></textarea>
        ${isLastStep ? `
          <button type="button" class="btn btn-sm btn-danger buzz-btn" id="step-buzz-btn">
            Buzz
          </button>
        ` : `
          <button type="button" class="btn btn-sm btn-warning copy-btn" data-copy-id="answer-step-${lastIndex + 1}">
            <i class="bi bi-copy"></i> Copy to Tool
          </button>
        `}
      </div>
    `;
  } else {
    stepDiv.innerHTML = `
      <button type="button" class="close-btn" style="position: absolute; top: 0px; right: 0px; border: none; background: none; font-size: 20px; cursor: pointer;">&times;</button>
      <p style="margin-bottom: 5px;"><strong>Step ${lastIndex + 1}: </strong><span id="step-${lastIndex + 1}" class="instructions-edit">${lastInstruction}</span></p>
      <div class="input-group">
        <textarea id="answer-step-${lastIndex + 1}" class="form-control input-sm" placeholder="Enter the answer here" rows="1"></textarea>
        ${isLastStep ? `
          <button type="button" class="btn btn-sm btn-danger buzz-btn" id="step-buzz-btn">
            Buzz
          </button>
        ` : `
          <button type="button" class="btn btn-sm btn-warning copy-btn" data-copy-id="answer-step-${lastIndex + 1}">
            <i class="bi bi-copy"></i> Copy to Tool
          </button>
        `}
      </div>
    `;
  }

  container.prepend(stepDiv);

  if (stepNum !== 1) {
    const closeButton = stepDiv.querySelector('.close-btn');
    closeButton.addEventListener('click', () => {
      removeStep(stepDiv, isLastStep);
    });
  }

  const textarea = stepDiv.querySelector('textarea');
  textarea.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      if (isLastStep) {
        buzz();
      } else {
        next_step();
        textarea.blur();
      }
    }
  });

  if (!isLastStep) {
    const clipboardButtons = stepDiv.querySelectorAll('.copy-btn');
    clipboardButtons.forEach(button => {
      button.addEventListener('click', function() {
        const inputId = this.getAttribute('data-copy-id');
        const textToCopy = iframeDoc.getElementById(inputId).value;
        copyTextToTool(textToCopy);
      });
    });
    buzzBtn.style.display = 'none';
  } else {
    const stepBuzzButton = stepDiv.querySelector('.buzz-btn');
    if (stepBuzzButton) {
      stepBuzzButton.addEventListener('click', () => {
        buzz();
      });
    }
    buzzBtn.style.display = '';
  }
}

function toggleCloseButtonVisibility(shouldShow) {
  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
  const closeButtons = iframeDoc.querySelectorAll('.close-btn');
  
  closeButtons.forEach(button => {
    button.style.display = shouldShow ? 'block' : 'none';
  });
}

function getSubanswers() {
  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
  const container = iframeDoc.getElementById('instructions-container');

  const textareas = container.querySelectorAll('textarea.form-control');
  const subanswers = Array.from(textareas).map(textarea => textarea.value).reverse();

  return subanswers;
}

function sendSubanswers(isCorrect) {

  const instructionFrame = document.getElementById('instruction-frame')
  const iframeDoc = instructionFrame.contentDocument || instructionFrame.contentWindow.document;
  const checkbox = iframeDoc.getElementById('edit-instructions-checkbox');

  sendRequest('send_subanswers', {'subanswers': getSubanswers(), 'is_correct': isCorrect, 'followed_plan': !checkbox.checked});
}

function reassignCloseButton() {
  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
  const container = iframeDoc.getElementById('instructions-container');

  const newLastStep = container.querySelector('.step-div:first-child');
  if (newLastStep) {
    const textArea = newLastStep.querySelector('textarea');
    if (!newLastStep.querySelector('.close-btn') && textArea.id !== 'answer-step-1') {
      const closeButton = iframeDoc.createElement('button');
      closeButton.type = 'button';
      closeButton.className = 'close-btn';
      closeButton.style.cssText = 'position: absolute; top: 0px; right: 0px; border: none; background: none; font-size: 20px; cursor: pointer;';
      closeButton.innerHTML = '&times;';

      newLastStep.appendChild(closeButton);

      closeButton.addEventListener('click', () => {
        removeStep(newLastStep, false);
      });
    }
  }
}

function removeStep(stepElement, isLastStep) {
  stepElement.remove();
  reassignCloseButton();
  if (isLastStep) {
    stepBtn.style.display = '';
    buzzBtn.style.display = 'none';
  }
  sendRequest("decrease_steps");
}

function populateSubanswers(subanswers) {
  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

  subanswers.forEach((answer, index) => {
    const textArea = iframeDoc.getElementById(`answer-step-${index + 1}`);
    if (textArea) {
      textArea.value = answer;
    }
  });
}

function populateInstructions(inputInstructions, stepNum, isLastStep, addCloseBtn) {
  if (stepNum === -1) {
      parseFullInstructions(inputInstructions, addCloseBtn, isLastStep)
    } else {
      parseInstructionsBox(inputInstructions, isLastStep, stepNum);
    }
}

function updateTools(use_calc, use_doc, use_web) {
    
    toolContainer.style.display = (use_calc || use_doc || use_web) ? '' : 'none';
    
    calculatorTool.style.display = use_calc ? '' : 'none';
    calculatorOperators.style.display = use_calc ? '' : 'none';
    googleTool.style.display = use_web ? '' : 'none';
    contentSelectorTool.style.display = use_doc ? '' : 'none';
    
    calculatorToolBtn.style.display = use_calc ? '' : 'none';
    googleToolBtn.style.display = use_web ? '' : 'none';
    contentSelectorToolBtn.style.display = use_doc ? '' : 'none';

    calculatorResultBtn.style.display = use_calc ? '' : 'none';
    calculatorResult.style.display = use_calc ? '' : 'none';
    copyMathBtn.style.display = use_calc ? '' : 'none';

    calculatorTool.style.display = use_calc ? '' : 'none';
    googleTool.style.display = use_web ? '' : 'none';
    contentSelectorTool.style.display = use_doc ? '' : 'none';
}

function clear_math() {
  calculatorToolInput.value = '';
}

function clear_search() {
  googleToolInput.value = '';
}

function clear_find() {
  contentSelectorToolInput.value = '';
}

// function clearRogueCheckbox() {
//   const iframe = instructionsFrame;
//   const iframeDoc = iframe.contentWindow.document;
//   const checkbox = iframeDoc.getElementById('edit-instructions-checkbox');
//   if (checkbox) {
//     checkbox.checked = false;
//   }

//   console.log('clearing checkbox');
//   iframe.style.display = checkbox.checked ? '' : 'none';
//   notes.style.display = checkbox.checked ? 'none' : '';
// }

function clearFields(should_clear_document) {

    calculatorToolInput.value = '';
    googleToolInput.value = '';
    contentSelectorToolInput.value = '';
    calculatorResult.value = ''

    if (should_clear_document) {
        docContent.srcdoc = `<!DOCTYPE html>
            <html lang="en">
            <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Embedded Page</title>
            <!-- Bootstrap CSS -->
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body>
            <div style="margin-left:10px; margin-right:10px;">
                <p>Search to make a document appear!</p>
            </div>
            </body>
            </html>`
    }
}

function toggleDisableButtons(flag) {

    calculatorResultBtn.disabled = flag;
    calculatorToolBtn.disabled = flag;
    googleToolBtn.disabled = flag;
    contentSelectorToolBtn.disabled = flag;

    calculatorToolInput.disabled = flag;
    googleToolInput.disabled = flag;
    contentSelectorToolInput.disabled = flag;

    mathClearBtn.disabled = flag;
    searchClearBtn.disabled = flag;
    findClearBtn.disabled = flag;

    for (const btn of calculatorOperators.querySelectorAll('.btn')) {
      btn.disabled = flag;
    }     
}

function updateDoc(use_doc, doc_content) {
    docViewer.style.display = use_doc ? '' : 'none';
    if (use_doc) {
        doc_content = doc_content == '' ? `
  <!DOCTYPE html>
  <html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Embedded Page</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
  </head>
  <body>
    Search to make a document appear!
  </body>
  </html>
` : doc_content;
        docContent.srcdoc = doc_content;
    }
}

function updateStatus(status, player, answer, allowSwaps) {
    gameState = status;
    if (status === "compare") {
        statusText.innerHTML = `Status: <span class=text-secondary>Complete the <span class=text-primary>pairwise comparison</span> to continue...</span>`;
        //statusText.scrollIntoView({ block: 'start' });        
    } else if (status === "compare_correct") {
        statusText.innerHTML = `Status: <span class=text-secondary>Your answer was <span class=text-success>correct</span>. Complete the <span class=text-primary>pairwise comparison</span> to continue...</span>`;     
    } else if (status === "compare_incorrect") {
        statusText.innerHTML = `Status: <span class=text-secondary>You <span class=text-danger>ran out of time</span>. Complete the <span class=text-primary>pairwise comparison</span> to continue...</span>`;
    } else if (status === "idle") {
        if (answer !== "") {
            statusText.innerHTML = `Status: <span class=text-secondary>The correct answer is: <span class=text-primary>${answer}</span>. Hit "next" to continue... </span>`;
            reportBtn.style.display = '';
            sendSubanswers(false);
        } else {
            statusText.innerHTML = `Status: <span class=text-secondary>Hit "next" to continue...</span>`;
            reportBtn.style.display = 'none';
        }
    } else if (status === "instruct") {
        statusText.innerHTML = 'Status: <span class=text-primary>Read the question + plan</span>';
        //statusText.scrollIntoView({ block: 'start' });
    } else if (status === "playing") {
        statusText.innerHTML = 'Status: <span class=text-secondary>Waiting for buzzes...</span>';
    } else if (status === "contest") {
        statusText.innerHTML = `Status: <span class=text-secondary><span class=text-primary>${player}</span> buzzed</span>`;
    } else if (status === "buzz_correct") {
        statusText.innerHTML = `Status: <span class=text-secondary><span class=text-primary>${player}</span> buzzed </span><span class=text-success>correctly</span> with <span class=text-success>"${answer}"</span></span>`;
        sendSubanswers(true);
        gameState = 'idle';
      } else if (status === "buzz_incorrect") {
        statusText.innerHTML = `Status: <span class=text-secondary><span class=text-primary>${player}</span> buzzed </span><span class=text-danger>incorrectly</span> with <span class=text-danger>"${answer}"</span>`;
        gameState = 'playing';
        toggleCloseButtonVisibility(true);
    } else if (status === "buzz_abstain") {
        statusText.innerHTML = `Status: <span class=text-secondary><span class=text-primary>${player}</span> buzzed and </span><span class=text-danger>did not answer</span>`;
        gameState = 'playing';
        toggleCloseButtonVisibility(true);
    }
    showButtonsForState(gameState, allowSwaps);
}

function copyMathResult() {

    const mathRes = calculatorResult.value;
    if (mathRes === '' || mathRes === 'Please enter an equation.' || mathRes === 'ERROR') {
      return;
    }

    copyTextToClipboard(mathRes);

    const instructionIframe = document.getElementById('instruction-frame');
    const instructionDoc = instructionIframe.contentDocument || instructionIframe.contentWindow.document;
    
    const answerFields = instructionDoc.querySelectorAll('[id^="answer-step-"]');
    if (answerFields.length > 0) {
        const lastAnswerField = answerFields[0];
        lastAnswerField.value = mathRes;
        lastAnswerField.style.height = 'auto';
        lastAnswerField.style.height = lastAnswerField.scrollHeight + 'px';

        lastAnswerField.classList.add('flash-highlight');
        setTimeout(() => {
          lastAnswerField.classList.remove('flash-highlight');
        }, 500);
    }

    //next_step();
  }

function copyTextToTool(textToCopy) {
  if (textToCopy === '') {
    return;
  }
  copyTextToClipboard(textToCopy);
  if (calculatorToolInput.style.display === '') {
    calculatorToolInput.value = textToCopy;

    calculatorToolInput.classList.add('flash-highlight');
    setTimeout(() => {
      calculatorToolInput.classList.remove('flash-highlight');
    }, 500);
  }
  if (googleToolInput.style.display === '') {
    googleToolInput.value = textToCopy;

    googleToolInput.classList.add('flash-highlight');
    setTimeout(() => {
      googleToolInput.classList.remove('flash-highlight');
    }, 500);
  }
}

function copyTextToClipboard(textToCopy) {
  const tempInput = document.createElement('textarea');
  tempInput.value = textToCopy;
  document.body.appendChild(tempInput);
  tempInput.select();
  document.execCommand('copy');
  document.body.removeChild(tempInput);
}

function copyDocText(elementText='') {

    // const web_query = googleToolInput.value;
    // const find_query = contentSelectorToolInput.value;
    // if (!web_query && !find_query) {
    //     return;
    // }

    // const iframe = document.getElementById('tool-history-frame');
    // const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
    // const toolEntryContainer = iframeDoc.getElementById('tool-entry-container');

    if (elementText === '') {

        const docIframe = docContent;
        const docIframeDocument = docIframe.contentDocument || docIframe.contentWindow.document;
        const highlightedElement = docIframeDocument.querySelector('.highlight');

        if (!highlightedElement) {
            return;
        }
        
        elementText = highlightedElement.innerText || highlightedElement.textContent;
    }

    copyTextToClipboard(elementText);

    const instructionIframe = document.getElementById('instruction-frame');
    const instructionDoc = instructionIframe.contentDocument || instructionIframe.contentWindow.document;
    
    const answerFields = instructionDoc.querySelectorAll('[id^="answer-step-"]');
    if (answerFields.length > 0) {
        const lastAnswerField = answerFields[0];
        lastAnswerField.value = elementText;
        lastAnswerField.style.height = 'auto';
        lastAnswerField.style.height = lastAnswerField.scrollHeight + 'px';

        lastAnswerField.classList.add('flash-highlight');
        setTimeout(() => {
          lastAnswerField.classList.remove('flash-highlight');
        }, 500);
    }

    //next_step();
  }

function clearToolHistory() {
    const iframe = document.getElementById('tool-history-frame');
    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
    const toolEntryContainer = iframeDoc.getElementById('tool-entry-container');
    while (toolEntryContainer.firstChild) {
        toolEntryContainer.removeChild(toolEntryContainer.firstChild);
    }
}

  function calculate() {
    const expression = calculatorToolInput.value;
    if (!expression) {
        calculatorResult.value = "Please enter an equation.";
      return;
    }
    calculatorToolInput.blur();
    sendRequest("calculate", expression);
  }


  function insertOperator(op) {
    const calculatorToolInput = document.getElementById('calc-expression');
    if (!calculatorToolInput) return;

    // Insert the operator symbol at the current cursor position or at the end
    const currentValue = calculatorToolInput.value;
    // You could also do more clever insertion if you want to respect cursor position, but a simple append is fine for most cases:
    calculatorToolInput.value = currentValue + op;

    // Set focus back to the input for convenience
    calculatorToolInput.focus();
  }

  function webSearch() {
    const query = googleToolInput.value;
    if (!query) {
      return;
    }
    googleToolInput.blur();
    sendRequest("web_search", query);
  }

  function selectContent() {
    const query = contentSelectorToolInput.value;
    const doc_content = docContent.srcdoc;
    const default_content = 'Search to make a document appear!';
    if (!query || doc_content.includes(default_content)) {
      return;
    }
    contentSelectorToolInput.blur();
    sendRequest("content_select", query);
  }

function toggleRogueCheckbox(checkbox, settingType) {
  if (checkbox.checked) {
    buzzBtn.style.display = '';
    swapBtn.style.display = 'none';
    stepBtn.style.display = 'none';
  } else {
    showButtonsForState(gameState, allowSwapsGlobal);
  }

  // swap plan for notes
  const iframeDoc = instructionsFrame.contentDocument || instructionsFrame.contentWindow.document;
  const instructions = iframeDoc.getElementById('instructions-container');
  const notes = iframeDoc.getElementById('rogue-notes');
  instructions.style.display = checkbox.checked ? 'none' : '';
  notes.style.display = checkbox.checked ? '' : 'none';

  instructionHeader.innerHTML = checkbox.checked ? '<h6>Custom Plan</h6>' : '<h6>Plan (p)</h6>';

  // add/remove the close button
  toggleCloseButtonVisibility(!checkbox.checked);
}

docContent.addEventListener('load', function() {
    const iframeDocument = this.contentDocument || this.contentWindow.document;
    iframeDocument.addEventListener('copy', function(event) {
        event.preventDefault();
        const copiedText = iframeDocument.getSelection().toString();
        copyDocText(copiedText);
        if (event.clipboardData) {
            event.clipboardData.setData('text/plain', copiedText);
        } else if (window.clipboardData) { 
            window.clipboardData.setData('Text', copiedText);
        }
    });

    iframeDocument.addEventListener("keypress", (e) => {
      handleKeyPress(e);
    });
    
    iframeDocument.addEventListener("keydown", function (e) {
      handleKeyDown(e);
    });
    
});

docContent.addEventListener("keypress", (e) => {
  handleKeyPress(e);
});
docContent.addEventListener("keydown", (e) => {
  handleKeyDown(e);
});

instructionsFrame.addEventListener("keypress", (e) => {
  handleKeyPress(e);
});
instructionsFrame.addEventListener("keydown", (e) => {
  handleKeyDown(e);
});


instructionsFrame.addEventListener('load', function() {
  const iframeDocument = this.contentDocument || this.contentWindow.document;

  iframeDocument.addEventListener("keypress", (e) => {
    handleKeyPress(e);
  });
  
  iframeDocument.addEventListener("keydown", function (e) {
    handleKeyDown(e);
  });
  
});

