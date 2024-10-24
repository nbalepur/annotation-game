const toolContainer = document.getElementById('toolbox-container');

const instructionSpace = document.getElementById('instruction-space');
const instructions = document.getElementById('model-instructions');

const instructionHeader = document.getElementById('instruction-header');
const instructionCollapse = document.getElementById('instruction-collapse');

const calculatorTool = document.getElementById('calculator-tool');
const googleTool = document.getElementById('google-tool');
const contentSelectorTool = document.getElementById('content-selector-tool');

const calculatorResultBtn = document.getElementById('calc-copy-btn');
const calculatorToolBtn = document.getElementById('calc-expression-btn');
const googleToolBtn = document.getElementById('google-query-btn');
const contentSelectorToolBtn = document.getElementById('content-search-btn');

const calculatorResult = document.getElementById('calc-result')

const calculatorToolInput = document.getElementById('calc-expression');
const googleToolInput = document.getElementById('google-query');
const contentSelectorToolInput = document.getElementById('content-search');

const docViewer = document.getElementById('doc-viewer');
const docContent = document.getElementById('view-page-collapse')

const statusText = document.getElementById('status-text');

const copySearchBtn = document.getElementById('copy-search-btn');
const copyMathBtn = document.getElementById('calculator-tool-result');

function parseInstructions(instr_object) {
    steps = instr_object['steps'];
    steps_html = '<ol>' + steps.map(item => `<li>${item}</li>`).join('') + '</ol>';
    return steps_html;
}

function populateInstructions(input_instructions) {
    steps_html = parseInstructions(input_instructions);
    instructions.innerHTML = steps_html;
}

function updateTools(use_calc, use_doc, use_web) {
    
    toolContainer.style.display = (use_calc || use_doc || use_web) ? '' : 'none';
    
    calculatorTool.style.display = use_calc ? '' : 'none';
    googleTool.style.display = use_web ? '' : 'none';
    contentSelectorTool.style.display = use_doc ? '' : 'none';
    
    calculatorToolBtn.style.display = use_calc ? '' : 'none';
    googleToolBtn.style.display = use_web ? '' : 'none';
    contentSelectorToolBtn.style.display = use_doc ? '' : 'none';

    calculatorResultBtn.style.display = use_calc ? '' : 'none';
}

function clearFields(should_clear_document) {

    clearToolHistory();

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

function updateStatus(status, player, answer) {
    showButtonsForState(status);
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
        } else {
            statusText.innerHTML = `Status: <span class=text-secondary>Hit "next" to continue...</span>`;
            reportBtn.style.display = 'none';
        }
    } else if (status === "instruct") {
        statusText.innerHTML = 'Status: <span class=text-primary>Read the question + instructions</span>';
        //statusText.scrollIntoView({ block: 'start' });
    } else if (status === "playing") {
        statusText.innerHTML = 'Status: <span class=text-secondary>Waiting for buzzes...</span>';
    } else if (status === "contest") {
        statusText.innerHTML = `Status: <span class=text-secondary>Player <span class=text-primary>${player}</span> has buzzed</span>`;
    } else if (status === "buzz_correct") {
        statusText.innerHTML = `Status: <span class=text-secondary>Player <span class=text-primary>${player}</span> buzzed </span><span class=text-success>correctly</span> with <span class=text-success>"${answer}"</span></span>`;
    } else if (status === "buzz_incorrect") {
        statusText.innerHTML = `Status: <span class=text-secondary>Player <span class=text-primary>${player}</span> buzzed </span><span class=text-danger>incorrectly</span> with <span class=text-danger>"${answer}"</span>`;
    } else if (status === "buzz_abstain") {
        statusText.innerHTML = `Status: <span class=text-secondary>Player <span class=text-primary>${player}</span> buzzed and </span><span class=text-danger>did not answer</span>`;
    }
}

function copyMathResult() {
    const iframe = document.getElementById('tool-history-frame');
    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
    const toolEntryContainer = iframeDoc.getElementById('tool-entry-container');

    const expression = calculatorToolInput.value;
    const mathRes = calculatorResult.value;

    if (mathRes === '' || mathRes === 'Please enter an equation.' || mathRes === 'ERROR') {
      return;
    }

    const newToolEntry = iframeDoc.createElement('div');
    newToolEntry.className = 'mb-2 p-2 border rounded';
    newToolEntry.innerHTML = `
      <div style="position: relative;">
        <button class="close-btn" style="position: absolute; top: 0; right: 10px; border: none; background: none; font-size: 16px; cursor: pointer;">X</button>
      </div>
      <div>
        <strong>Calc Input:</strong> ${expression}
        <button class="copy-btn" data-copy="${expression}" style="border: none; background: none; cursor: pointer;">
          <i class="bi bi-copy"></i>
        </button>
      </div>
      <div>
        <strong>Calc Output:</strong> ${mathRes}
        <button class="copy-btn" data-copy="${mathRes}" style="border: none; background: none; cursor: pointer;">
          <i class="bi bi-copy"></i>
        </button>
      </div>
    `;

    toolEntryContainer.insertBefore(newToolEntry, toolEntryContainer.firstChild);
    const closeButton = newToolEntry.querySelector('.close-btn');
    closeButton.addEventListener('click', function() {
      newToolEntry.remove();
    });
    
    const clipboardButtons = newToolEntry.querySelectorAll('.copy-btn');
    clipboardButtons.forEach(button => {
      button.addEventListener('click', function() {
        const textToCopy = this.getAttribute('data-copy');
    
        const tempInput = iframeDoc.createElement('textarea');
        tempInput.value = textToCopy;
        iframeDoc.body.appendChild(tempInput);
        tempInput.select();
        iframeDoc.execCommand('copy');
        iframeDoc.body.removeChild(tempInput);
    
      });
    });
    
}

function copyDocText(elementText='') {

    const web_query = googleToolInput.value;
    const find_query = contentSelectorToolInput.value;
    if (!web_query && !find_query) {
        return;
    }

    const iframe = document.getElementById('tool-history-frame');
    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
    const toolEntryContainer = iframeDoc.getElementById('tool-entry-container');

    if (elementText === '') {

        const docIframe = docContent;
        const docIframeDocument = docIframe.contentDocument || docIframe.contentWindow.document;
        const highlightedElement = docIframeDocument.querySelector('.highlight');

        if (!highlightedElement) {
            return;
        }
        
        elementText = highlightedElement.innerText || highlightedElement.textContent;
    }

    const newToolEntry = iframeDoc.createElement('div');
    newToolEntry.className = 'mb-2 p-2 border rounded';

    if (web_query && find_query) {

        newToolEntry.innerHTML = `
        <div style="position: relative;">
          <button class="close-btn" style="position: absolute; top: 0; right: 10px; border: none; background: none; font-size: 16px; cursor: pointer;">X</button>
        </div>
        <div>
          <div><strong>Web Input:</strong> ${web_query}
          <button class="copy-btn" data-copy="${web_query}" style="border: none; background: none; cursor: pointer;">
            <i class="bi bi-copy"></i>
          </button>
        </div>
        <div>
          <div><strong>Search Input:</strong> ${find_query}
          <button class="copy-btn" data-copy="${find_query}" style="border: none; background: none; cursor: pointer;">
            <i class="bi bi-copy"></i>
          </button>
        </div>
        <div>
          <strong>Search Output:</strong> ${elementText}
          <button class="copy-btn" data-copy="${elementText}" style="border: none; background: none; cursor: pointer;">
            <i class="bi bi-copy"></i>
          </button>
        </div>
      `;
    } else if (web_query) {
        newToolEntry.innerHTML = `
        <div style="position: relative;">
          <button class="close-btn" style="position: absolute; top: 0; right: 10px; border: none; background: none; font-size: 16px; cursor: pointer;">X</button>
        </div>
        <div>
          <div><strong>Search Input:</strong> ${web_query}
          <button class="copy-btn" data-copy="${web_query}" style="border: none; background: none; cursor: pointer;">
            <i class="bi bi-copy"></i>
          </button>
        </div>
        <div>
          <strong>Search Output:</strong> ${elementText}
          <button class="copy-btn" data-copy="${elementText}" style="border: none; background: none; cursor: pointer;">
            <i class="bi bi-copy"></i>
          </button>
        </div>
      `;
    } else if (find_query) {
        newToolEntry.innerHTML = `
        <div style="position: relative;">
          <button class="close-btn" style="position: absolute; top: 0; right: 10px; border: none; background: none; font-size: 16px; cursor: pointer;">X</button>
        </div>
        <div>
          <div><strong>Search Input:</strong> ${find_query}
          <button class="copy-btn" data-copy="${find_query}" style="border: none; background: none; cursor: pointer;">
            <i class="bi bi-copy"></i>
          </button>
        </div>
        <div>
          <strong>Search Output:</strong> ${elementText}
          <button class="copy-btn" data-copy="${elementText}" style="border: none; background: none; cursor: pointer;">
            <i class="bi bi-copy"></i>
          </button>
        </div>
      `;
    }
    toolEntryContainer.insertBefore(newToolEntry, toolEntryContainer.firstChild);
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

docContent.addEventListener('load', function() {
    const iframeDocument = this.contentDocument || this.contentWindow.document;
    iframeDocument.addEventListener('copy', function(event) {
        event.preventDefault();
        const copiedText = iframeDocument.getSelection().toString();
        console.log(copiedText);
        copyDocText(copiedText);
        if (event.clipboardData) {
            event.clipboardData.setData('text/plain', copiedText);
        } else if (window.clipboardData) { 
            window.clipboardData.setData('Text', copiedText);
        }
    });
});