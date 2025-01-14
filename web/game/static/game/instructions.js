const toolContainer = document.getElementById('toolbox-container');

const instructionHeader = document.getElementById('instruction-header');
const instructionCollapse = document.getElementById('instruction-collapse');

const calculatorTool = document.getElementById('calculator-tool');
const calculatorOperators = document.getElementById('calculator-operators');
const googleTool = document.getElementById('google-tool');
const contentSelectorTool = document.getElementById('content-selector-tool');

const calculatorResultBtn = document.getElementById('calc-copy-btn');

const calculatorToolBtn = document.getElementById('calc-expression-btn');
const calculatorToolBtn2 = document.getElementById('calc-expression-btn2');

const googleToolBtn = document.getElementById('google-query-btn');
const googleToolBtn2 = document.getElementById('google-query-btn2');

const contentSelectorToolBtn = document.getElementById('content-search-btn');
const contentSelectorToolBtn2 = document.getElementById('content-search-btn2');

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

const bwdSearch = document.getElementById('content-bwd-btn');
const fwdSearch = document.getElementById('content-fwd-btn');

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

function clearInstructions() {
  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
  const container = iframeDoc.getElementById('instructions-container');
  container.innerHTML = '';
}

function parseFullInstructions(inputInstructions, addCloseBtn, isLastStep) {

  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

  const container = iframeDoc.getElementById('instructions-container');
  container.innerHTML = '';

  inputInstructions['steps'].forEach((instruction, index) => {
    const stepDiv = iframeDoc.createElement('div');
    stepDiv.className = 'pt-4 px-4 pb-2 mb-2 border bg-light position-relative step-div';
    stepDiv.id = `step-div-${index + 1}`;
    stepDiv.setAttribute('is-custom', false);

    if (addCloseBtn) {
      container.prepend(stepDiv);
    } else {
      container.append(stepDiv);
    }

    const buttonHTML = !addCloseBtn ? '' : (isLastStep && index === inputInstructions['steps'].length - 1
      ? `<button type="button" style="border-radius: 0 0.5rem 0.5rem 0;" class="btn btn-sm btn-primary buzz-btn" id="step-buzz-btn">Answer (Enter)</button>`
      : `<button type="button" style="border-radius: 0;" id="step-next-btn" class="btn btn-sm btn-primary step-btn" data-copy-id="answer-step-${index + 1}">
          Next Step (Enter)
        </button>
        <button type="button" style="border-radius: 0 0.5rem 0.5rem 0;" class="btn btn-sm btn-secondary copy-btn" data-copy-id="answer-step-${index + 1}">
           Copy to Tool (t)
         </button>
         `);

    stepDiv.innerHTML = `
      <p style="margin-bottom: 0px;"><strong>Step ${index + 1}: </strong><span id="step-${index + 1}" class="instructions-edit">${instruction}</span></p>
      <div class="input-group" style="margin-top: 5px;">
        <textarea id="answer-step-${index + 1}" class="form-control input-sm" placeholder="Enter the answer here" rows="1"></textarea>
        ${buttonHTML}
      </div>
      <div id="step-warning-${index + 1}" style="visibility: hidden;">
        <p class="text-danger" style="margin-top: 5px; margin-bottom: 0px;"> <i class="bi bi-exclamation-octagon-fill"></i> Please enter an answer. If it's not possible, hit "Next Step" again.</p>
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
    textarea.style.height = 'auto';
    textarea.style.height = `${textarea.scrollHeight}px`
    textarea.addEventListener('input', () => {
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight}px`;
    });

    textarea.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (isLastStep && index === inputInstructions['steps'].length - 1) {
          answerWrapper(textarea.value);
        } else {
          const shouldExit = next_step();
          if (shouldExit) {
            textarea.blur();
          }
        }
      }
    });

    if (isLastStep && index === inputInstructions['steps'].length - 1) {
      const stepBuzzButton = stepDiv.querySelector('.buzz-btn');
      if (stepBuzzButton) {
        stepBuzzButton.addEventListener('click', () => {
          answerWrapper(textarea.value);
        });
      }
      // buzzBtn.style.display = '';
      // stepBtn.style.display = 'none';
    } else if (addCloseBtn) {
      const copyButton = stepDiv.querySelector('.copy-btn');
      if (copyButton) {
        copyButton.addEventListener('click', function() {
          const inputId = this.getAttribute('data-copy-id');
          const textToCopy = iframeDoc.getElementById(inputId).value;
          copyTextToTool(textToCopy);
        });
      }
      

      const stepButton = stepDiv.querySelector('.step-btn');
      if (stepButton) {
        if (index === inputInstructions['steps'].length - 1) {
          stepButton.style.display = '';
          stepButton.addEventListener('click', function(e) {
            next_step();
          });
        } else {
          stepButton.style.display = 'none';
        }
      }

      // buzzBtn.style.display = 'none';
      // stepBtn.style.display = '';
    }
  });

  const clipboardButtons = container.querySelectorAll('.copy-btn');
  if (clipboardButtons.length > 0) {
    const referenceWidth = clipboardButtons[0].offsetWidth;
    clipboardButtons.forEach((button, buttonIdx) => {
      if (buttonIdx !== 0) {
        button.innerText = 'Copy to Tool';
      }
    });
  }
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
  stepDiv.className = 'pt-4 px-4 pb-2 mb-2 border bg-light position-relative step-div';
  stepDiv.id = `step-div-${lastIndex + 1}`;

  if (isLastStep) {
    const stepButtons = container.querySelectorAll('.step-btn');
    stepButtons.forEach((button, index) => {
      button.style.display = 'none';
    });
  }

  if (stepNum === 1) {
    stepDiv.innerHTML = `
      <p style="margin-bottom: 0px;"><strong>Step ${lastIndex + 1}: </strong><span id="step-${lastIndex + 1}" class="instructions-edit">${lastInstruction}</span></p>
      <div class="input-group" style="margin-top: 5px;">
        <textarea id="answer-step-${lastIndex + 1}" class="form-control input-sm" placeholder="Enter the answer here" rows="1"></textarea>
        ${isLastStep ? `
          <button type="button" style="border-radius: 0 0.5rem 0.5rem 0;" class="btn btn-sm btn-primary buzz-btn" id="step-buzz-btn">
            Answer (Enter)
          </button>
        ` : `
          <button type="button" style="border-radius: 0;" id="step-next-btn" class="btn btn-sm btn-primary step-btn" data-copy-id="answer-step-${lastIndex + 1}">
            Next Step (Enter)
          </button>
          <button type="button" style="border-radius: 0 0.5rem 0.5rem 0;" class="btn btn-sm btn-secondary copy-btn" data-copy-id="answer-step-${lastIndex + 1}">
            Copy to Tool (t)
          </button>
        `}
      </div>
      <div id="step-warning-${lastIndex + 1}" style="visibility: hidden;">
        <p class="text-danger" style="margin-top: 5px; margin-bottom: 0px;"> <i class="bi bi-exclamation-octagon-fill"></i> Please enter an answer. If it's not possible, hit "Next Step" again.</p>
      </div>
    `;

  } else {
    stepDiv.innerHTML = `
      <button type="button" class="close-btn" style="position: absolute; top: 0px; right: 0px; border: none; background: none; font-size: 20px; cursor: pointer;">&times;</button>
      <p style="margin-bottom: 0px;"><strong>Step ${lastIndex + 1}: </strong><span id="step-${lastIndex + 1}" class="instructions-edit">${lastInstruction}</span></p>
      <div class="input-group" style="margin-top: 5px;">
        <textarea id="answer-step-${lastIndex + 1}" class="form-control input-sm" placeholder="Enter the answer here" rows="1"></textarea>
        ${isLastStep ? `
          <button type="button" style="border-radius: 0 0.5rem 0.5rem 0;" class="btn btn-sm btn-primary buzz-btn" id="step-buzz-btn">
            Answer (Enter)
          </button>
        ` : `
          <button type="button" style="border-radius: 0;" id="step-next-btn" class="btn btn-sm btn-primary step-btn" data-copy-id="answer-step-${lastIndex + 1}">
            Next Step (Enter)
          </button>
          <button type="button" style="border-radius: 0 0.5rem 0.5rem 0;" class="btn btn-sm btn-secondary copy-btn" data-copy-id="answer-step-${lastIndex + 1}">
            Copy to Tool (t)
          </button>
        `}
      </div>
      <div id="step-warning-${lastIndex + 1}" style="visibility: hidden;">
        <p class="text-danger" style="margin-top: 5px; margin-bottom: 0px;"> <i class="bi bi-exclamation-octagon-fill"></i> Please enter an answer. If it's not possible, hit "Next Step" again.</p>
      </div>
    `;
  }

  container.prepend(stepDiv);

  const clipboardButtons = container.querySelectorAll('.copy-btn');
  if (clipboardButtons.length > 0) {
    const referenceWidth = clipboardButtons[0].offsetWidth;
    clipboardButtons.forEach((button, buttonIdx) => {
      if (buttonIdx !== 0) {
        button.innerText = 'Copy to Tool';
      }
    });
  }

  if (stepNum !== 1) {
    const closeButton = stepDiv.querySelector('.close-btn');
    closeButton.addEventListener('click', () => {
      removeStep(stepDiv, isLastStep);
    });
  }

  const textarea = stepDiv.querySelector('textarea');
  textarea.style.height = 'auto';
  textarea.style.height = `${textarea.scrollHeight}px`
  textarea.addEventListener('input', () => {
    textarea.style.height = 'auto';
    textarea.style.height = `${textarea.scrollHeight}px`;
  });
  textarea.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (isLastStep) {
        answerWrapper(textarea.value);
      } else {
        const shouldExit = next_step();
        if (shouldExit) {
          textarea.blur();
        }
      }
    }
  });

  // copy to tool
  if (!isLastStep) {
    const clipboardButtons = stepDiv.querySelectorAll('.copy-btn');
    clipboardButtons.forEach(button => {
      button.addEventListener('click', function() {
        const inputId = this.getAttribute('data-copy-id');
        const textToCopy = iframeDoc.getElementById(inputId).value;
        copyTextToTool(textToCopy);
      });
    });

    const stepButtons = container.querySelectorAll('.step-btn');
    stepButtons.forEach((button, index) => {
      if (index === 0) {
        button.addEventListener('click', function (e) {
          next_step();
        });
      } else {
        button.style.display = 'none';
      }
    });

    // buzzBtn.style.display = 'none';
    // stepBtn.style.display = '';
  } else {
    const stepBuzzButton = stepDiv.querySelector('.buzz-btn');
    if (stepBuzzButton) {
      stepBuzzButton.addEventListener('click', () => {
        answerWrapper(textarea.value);
      });
    }
    // buzzBtn.style.display = '';
    // stepBtn.style.display = 'none';
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

function getLastCopy() {
  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
  const subanswers = getSubanswers();
  if (subanswers.length === 0) {
    return '';
  }
  const closeButtons = iframeDoc.querySelectorAll('.copy-btn');
  return subanswers[closeButtons.length - 1];
}

function sendSubanswers(isCorrect, isFinal) {

  const instructionFrame = document.getElementById('instruction-frame')
  const iframeDoc = instructionFrame.contentDocument || instructionFrame.contentWindow.document;
  const checkbox = iframeDoc.getElementById('edit-instructions-checkbox');
  const notes = iframeDoc.getElementById('rogue-notes-area').value;

  sendRequest('send_subanswers', {'subanswers': getSubanswers(), 
                                  'is_correct': isCorrect,
                                  'is_final': isFinal,
                                  'followed_plan': !checkbox.checked,
                                  'notes': notes,
                                });
}

function reassignCloseAndStepButton() {
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

    const stepButton = newLastStep.querySelector('.step-btn');
    if (stepButton) {
      stepButton.style.display = '';
    }
  }
}

function removeStep(stepElement, isLastStep) {
  subanswers = getSubanswers();
  stepElement.remove();
  reassignCloseAndStepButton();

  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
  const container = iframeDoc.getElementById('instructions-container');
  const clipboardButtons = container.querySelectorAll('.copy-btn');
  clipboardButtons[0].innerText = 'Copy to Tool (t)';
  sendRequest("decrease_steps", subanswers);
}

function populateSubanswers(subanswers) {
  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

  subanswers.forEach((answer, index) => {
    const textArea = iframeDoc.getElementById(`answer-step-${index + 1}`);
    if (textArea) {
      textArea.value = answer;
      textArea.style.height = `${textArea.scrollHeight}px`;
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

    calculatorToolBtn2.style.display = use_calc ? '' : 'none';
    googleToolBtn2.style.display = use_web ? '' : 'none';
    contentSelectorToolBtn2.style.display = use_doc ? '' : 'none';

    calculatorResultBtn.style.display = use_calc ? '' : 'none';
    calculatorResult.style.display = use_calc ? '' : 'none';
    copyMathBtn.style.display = use_calc ? '' : 'none';
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
            <script>
          document.addEventListener("keydown", function (event) {
              if (window.parent && typeof window.parent.handleKeyDown === "function") {
                window.parent.handleKeyDown(event);
              }
          });
            document.addEventListener("keypress", function (event) {
              if (window.parent && typeof window.parent.handleKeyPress === "function") {
                window.parent.handleKeyPress(event);
              }
          });
            </script>
            </html>`
    }
}

function disablePlan() {
  const iframeDoc = instructionsFrame.contentDocument || instructionsFrame.contentWindow.document;
  const instructions = iframeDoc.getElementById('instructions-container');
  const buttonsAndTextareas = instructions.querySelectorAll('button, textarea');
  buttonsAndTextareas.forEach(element => {
    element.disabled = true;
  });
}

function toggleDisableButtons(flag) {

    calculatorResultBtn.disabled = flag;
    calculatorToolBtn.disabled = flag;
    googleToolBtn.disabled = flag;
    contentSelectorToolBtn.disabled = flag;

    calculatorToolBtn2.disabled = flag;
    googleToolBtn2.disabled = flag;
    contentSelectorToolBtn2.disabled = flag;

    calculatorToolInput.disabled = flag;
    googleToolInput.disabled = flag;
    contentSelectorToolInput.disabled = flag;

    mathClearBtn.disabled = flag;
    searchClearBtn.disabled = flag;
    findClearBtn.disabled = flag;

    copySearchBtn.disabled = flag;

    for (const btn of calculatorOperators.querySelectorAll('.btn')) {
      btn.disabled = flag;
    }     

    const instructionFrame = document.getElementById('instruction-frame')
    const iframeDoc = instructionFrame.contentDocument || instructionFrame.contentWindow.document;
    const notes = iframeDoc.getElementById('rogue-notes-area');
    notes.disabled = flag;
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
<div style="margin-left:10px; margin-right:10px;">
    <p class="text-secondary">Search to make a document appear!</p>
</div>
  </body>
              <script>
          document.addEventListener("keydown", function (event) {
              if (window.parent && typeof window.parent.handleKeyDown === "function") {
                window.parent.handleKeyDown(event);
              }
          });
            document.addEventListener("keypress", function (event) {
              if (window.parent && typeof window.parent.handleKeyPress === "function") {
                window.parent.handleKeyPress(event);
              }
          });
            </script>
  </html>
` : doc_content;
        docContent.srcdoc = doc_content;
    }
}

function loadingDoc() {
  updateTools(false, false, true);
  const content =  `
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
    <div class="d-flex align-items-center justify-content-center" style="height: 100vh;">
      <div class="spinner-border" role="status" aria-hidden="true"></div>
      <span class="ms-3">Loading...</span>
  </div>
  </body>
              <script>
          document.addEventListener("keydown", function (event) {
              if (window.parent && typeof window.parent.handleKeyDown === "function") {
                window.parent.handleKeyDown(event);
              }
          });
            document.addEventListener("keypress", function (event) {
              if (window.parent && typeof window.parent.handleKeyPress === "function") {
                window.parent.handleKeyPress(event);
              }
          });
            </script>
  </html>
`
  docContent.srcdoc = content;
}

function buzzStatsUpdate(isCorrect) {
  subanswers = getSubanswers();
  const iframe = document.getElementById('instruction-frame');
  const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
  const container = iframeDoc.getElementById('instructions-container');
  const warningDiv = container.querySelector(`#step-warning-${subanswers.length}`);

  const checkbox = iframeDoc.getElementById('edit-instructions-checkbox');

  if (!checkbox.checked) {
    if (!isCorrect) {
      warningDiv.style.visibility = '';
      warningDiv.innerHTML = '<p class="text-danger" style="margin-top: 5px; margin-bottom: 0px;"> <i class="bi bi-x-circle-fill"></i> Your answer is <strong>incorrect</strong>, try again!</p>';
      return;
    } else {
      warningDiv.style.visibility = '';
      warningDiv.innerHTML = '<p class="text-success" style="margin-top: 5px; margin-bottom: 0px;"> <i class="bi bi-check-circle-fill"></i> Your answer is <strong>correct</strong>!</p>';
      return;
    }
  } else {
    const rogueStatus = iframeDoc.getElementById('rogue-notes-status');
    if (!isCorrect) {
        rogueStatus.style.visibility = '';
        rogueStatus.innerHTML = '<p class="text-danger" style="margin-top: 5px; margin-bottom: 0px;"> <i class="bi bi-x-circle-fill"></i> Your answer is <strong>incorrect</strong>, try again!</p>';
        return;
    } else {
      rogueStatus.style.visibility = '';
      rogueStatus.innerHTML = '<p class="text-success" style="margin-top: 5px; margin-bottom: 0px;"> <i class="bi bi-check-circle-fill"></i> Your answer is <strong>correct</strong>!</p>';
      return;      
    }
    } 
  }

function updateStatus(status, player, answer, allowSwaps) {
    gameState = status;
    if (status === "compare") {
        statusText.innerHTML = `Task: <span class=text-secondary>Complete the <span class=text-secondary>pairwise comparison</span> to continue</span>`;
        //statusText.scrollIntoView({ block: 'start' });        
    } else if (status === "compare_correct") {
        statusText.innerHTML = `Task: <span class=text-secondary>Your answer was <span class=text-success>correct</span>. Complete the <span class=text-secondary>pairwise comparison</span> to continue</span>`;     
    } else if (status === "compare_incorrect") {
        statusText.innerHTML = `Task: <span class=text-secondary>You <span class=text-danger>ran out of time</span>. Complete the <span class=text-secondary>pairwise comparison</span> to continue</span>`;
    } else if (status === "idle") {
        if (answer !== "") {
            statusText.innerHTML = `Task: <span class=text-secondary>The correct answer is: <span class=text-primary>${answer}</span>. Hit <span class=text-primary>Next</span> to continue</span>`;
            reportBtn.style.display = '';
            sendSubanswers(false, true);
        } else {
            statusText.innerHTML = `Task: <span class=text-secondary>Hit <span class=text-primary>Next</span> to continue</span>`;
            reportBtn.style.display = 'none';
        }
    } else if (status === "instruct") {
        statusText.innerHTML = 'Task: <span class=text-secondary>Read the question and plan</span>';
        //statusText.scrollIntoView({ block: 'start' });
    } else if (status === "playing") {
        statusText.innerHTML = 'Task: <span class=text-secondary>Follow the plan to answer the question!</span>';
    } else if (status === "contest") {
        statusText.innerHTML = `Task: <span class=text-secondary>Type your answer</span></span>`;
    } else if (status === "buzz_correct") {
        statusText.innerHTML = `<span class=text-secondary>You buzzed <span class=text-success>correctly</span> with <span class=text-success>"${answer}"</span>! Hit <span class=text-primary>Next</span> to continue</span>`;
        buzzStatsUpdate(true);
        // statusText.classList.add('flash-highlight');
        // setTimeout(() => {
        //   statusText.classList.remove('flash-highlight');
        // }, 1000);
        sendSubanswers(true, true);
        gameState = 'idle';

      } else if (status === "buzz_incorrect") {
        statusText.innerHTML = `<span class=text-secondary>You buzzed <span class=text-danger>incorrectly</span> with <span class=text-danger>"${answer}"</span>. Try again!</span>`;
        buzzStatsUpdate(false);
        // statusText.classList.add('flash-highlight');
        // setTimeout(() => {
        //   statusText.classList.remove('flash-highlight');
        // }, 1000);
        gameState = 'playing';
        sendSubanswers(false, false);
        toggleCloseButtonVisibility(true);
    } else if (status === "buzz_abstain") {
        statusText.innerHTML = `You buzzed and </span><span class=text-danger>did not answer</span>. Try again until time's up!`;
        statusText.classList.add('flash-highlight');
        setTimeout(() => {
          statusText.classList.remove('flash-highlight');
        }, 1000);
        gameState = 'playing';
        sendSubanswers(true, false);
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
    const checkbox = instructionDoc.getElementById('edit-instructions-checkbox');
    
    if (checkbox.checked) {
      const notes = instructionDoc.getElementById('rogue-notes-area');
      const notesText = notes.value;
      let newNotes = '';
      if (notesText === '') {
        newNotes = mathRes;
      } else {
        newNotes = notesText + '\n\n' + mathRes;
      }
      notes.value = newNotes;
    } else {
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

function navigateHistory(increment) {
  pause();
  sendRequest('navigate_history', increment)
}

function copyDocText(elementText='') {

  const iframe = document.getElementById('view-page-collapse');
  const iframeDocument = iframe.contentDocument || iframe.contentWindow.document;
  const selectedText = iframeDocument.getSelection ? iframeDocument.getSelection().toString() : '';


    if (elementText === '' && selectedText === '') {

        const docIframe = docContent;
        const docIframeDocument = docIframe.contentDocument || docIframe.contentWindow.document;
        const highlightedElement = docIframeDocument.querySelector('.highlight');

        if (!highlightedElement) {
            return;
        }
        
        elementText = highlightedElement.innerText || highlightedElement.textContent;
    }

    elementText = elementText === '' ? selectedText : elementText;
    copyTextToClipboard(elementText);

    const instructionIframe = document.getElementById('instruction-frame');
    const instructionDoc = instructionIframe.contentDocument || instructionIframe.contentWindow.document;
    const iframeDoc = instructionsFrame.contentDocument || instructionsFrame.contentWindow.document;
    const checkbox = iframeDoc.getElementById('edit-instructions-checkbox');

    if (checkbox.checked) {
      const notes = iframeDoc.getElementById('rogue-notes-area');
      const notesText = notes.value;
      let newNotes = '';
      if (notesText === '') {
        newNotes = elementText;
      } else {
        newNotes = notesText + '\n\n' + elementText;
      }
      notes.value = newNotes;
    } else {
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

function pause() {
  paused = true;
  contentProgress.classList.add('paused');
}

function unpause() {
  paused = false;
  contentProgress.classList.remove('paused');
}

  function calculate() {
    const expression = calculatorToolInput.value;
    if (!expression) {
        calculatorResult.value = "Please enter an equation.";
        calculatorResult.classList.add('flash-highlight');
        setTimeout(() => {
          calculatorResult.classList.remove('flash-highlight');
        }, 500);
      return;
    }
    calculatorToolInput.blur();
    pause();
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

    loadingDoc();
    
    pause();
    // setTimeout(() => {
    //   console.log("Delay complete. Proceeding with search...");
    //   googleToolInput.blur();
    //   sendRequest("web_search", query);
    // }, 10000);

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
    pause();
    sendRequest("content_select", query);
  }

function toggleRogueCheckbox(checkbox, isPairwise) {
  const iframeDoc = instructionsFrame.contentDocument || instructionsFrame.contentWindow.document;
  const skipPlanButton = iframeDoc.getElementById('skip-button-in-plan');
  const buzzPlanButton = iframeDoc.getElementById('buzz-button-in-plan');
  const swapPlanButton = iframeDoc.getElementById('swap-button-in-plan');

  if (checkbox.checked) {
    // buzzBtn.style.display = '';
    // swapBtn.style.display = 'none';
    // stepBtn.style.display = 'none';
    skipPlanButton.style.display = '';
    if (!isPairwise) {
      swapPlanButton.style.display = 'none';
    }
    buzzPlanButton.style.display = '';
  } else {
    skipPlanButton.style.display = 'none';
    if (!isPairwise) {
      swapPlanButton.style.display = '';
    }
    buzzPlanButton.style.display = 'none';
    showButtonsForState(gameState, allowSwapsGlobal);
  }

  // swap plan for notes
  const instructions = iframeDoc.getElementById('instructions-container');
  instructions.style.display = checkbox.checked ? 'none' : '';

  const notes = iframeDoc.getElementById('rogue-notes');
  notes.style.display = checkbox.checked ? '' : 'none';

  instructionHeader.innerHTML = checkbox.checked ? '<h5 style="font-size: large;">Write your own Plan (p)</h6>' : currPlanHeader;

  // add/remove the close button
  toggleCloseButtonVisibility(!checkbox.checked);
}

function resetRogueCheckbox(isPairwise) {
  const iframeDoc = instructionsFrame.contentDocument || instructionsFrame.contentWindow.document;
  const checkbox = iframeDoc.getElementById('edit-instructions-checkbox');
  
  if (!checkbox.checked) {
    const checkboxLabel = iframeDoc.getElementById('edit-instructions-checkbox-label');
    checkboxLabel.innerText = isPairwise ? "I can't answer with the given plan" : "I can't answer with the given plans";
    const swapPlanButton = iframeDoc.getElementById('swap-button-in-plan');
    swapPlanButton.style.display = isPairwise ? 'none' : '';
    return;
  }
  
  // uncheck and reset the field
  checkbox.checked = false;
  self.toggleRogueCheckbox(checkbox, isPairwise);

  // reset the notes
  const notes = iframeDoc.getElementById('rogue-notes-area');
  notes.value = '';

  // reset/hide the status
  const rogueStatus = iframeDoc.getElementById('rogue-notes-status');
  rogueStatus.style.visibility = 'hidden';
  rogueStatus.innerHTML = '<p></p>';
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

    // iframeDocument.addEventListener("keypress", (e) => {
    //   handleKeyPress(e);
    // });
    
    // iframeDocument.addEventListener("keydown", function (e) {
    //   handleKeyDown(e);
    // });
    
});

function navigateHyperlink(link) {
  const url = new URL(link.href);
  const decodedPath = decodeURIComponent(url.pathname);
  if (!decodedPath.startsWith('/wiki/')) {
    return;
  }
  if (decodedPath.includes(':')) {
    return;
  }
  sendRequest("navigate_hyperlink", decodedPath);
}


 // Add hyperlink listener
 const iframe = document.getElementById('view-page-collapse');
 iframe.addEventListener('load', () => {
     const iframeDocument = iframe.contentDocument || iframe.contentWindow.document;
     const links = iframeDocument.querySelectorAll('a');
     links.forEach(link => {
         const href = link.getAttribute('href');
         if (href && href.startsWith('/wiki/') && !href.includes(':')) {
             link.addEventListener('click', function (event) {
                 navigateHyperlink(link);
                 event.preventDefault();
             });
         } else if (!href || (!href.includes('planstudyumd') && !href.includes('nbalepur'))) {
          link.removeAttribute('href');
          link.style.pointerEvents = 'none';
          link.style.color = 'black';
          link.style.textDecoration = 'none';
          link.style.cursor = 'default';
         }
     });
 });
 

// instructionsFrame.addEventListener('load', function() {
//   const iframeDocument = this.contentDocument || this.contentWindow.document;

//   iframeDocument.addEventListener("keydown", function(event) {
//     if (event.key === "Escape") {
//       const activeElement = iframeDocument.activeElement;
//       if (activeElement.tagName === "INPUT" || activeElement.tagName === "TEXTAREA") {
//         activeElement.blur(); // Remove focus from the input field
//       }
//     } else {
//       handleKeyDown(event);
//     }
//   });

//   iframeDocument.addEventListener("keypress", function(event) {
//     if (event.key === "Escape") {
//       const activeElement = iframeDocument.activeElement;
//       if (activeElement.tagName === "INPUT" || activeElement.tagName === "TEXTAREA") {
//         activeElement.blur(); // Remove focus from the input field
//       }
//     } else {
//       handleKeyPress(event);
//     }
//   });

// iframeDocument.getElementById("edit-instructions-checkbox").addEventListener("click", function() {
//   const phase = this.getAttribute("data-phase");
//   parent.toggleRogueCheckbox(this, phase);
// });
  
// });

// docContent.addEventListener("keypress", (e) => {
//   handleKeyPress(e);
// });
// docContent.addEventListener("keydown", (e) => {
//   handleKeyDown(e);
// });

// instructionsFrame.addEventListener("keypress", (e) => {
//   handleKeyPress(e);
// });
// instructionsFrame.addEventListener("keydown", (e) => {
//   handleKeyDown(e);
// });

// instructionsFrame.addEventListener('click', () => {
//   iframe.focus();
// });

