let instructionSpace = document.getElementById('instruction-space');
let instructions = document.getElementById('model-instructions');

let instructionHeader = document.getElementById('instruction-header');
let instructionCollapse = document.getElementById('instruction-collapse');

let calculatorTool = document.getElementById('calculator-tool');
let googleTool = document.getElementById('google-tool');
let contentSelectorTool = document.getElementById('content-selector-tool');

let calculatorToolBtn = document.getElementById('calc-expression-btn');
let googleToolBtn = document.getElementById('google-query-btn');
let contentSelectorToolBtn = document.getElementById('content-search-btn');

let calculatorToolInput = document.getElementById('calc-expression');
let googleToolInput = document.getElementById('google-query');
let contentSelectorToolInput = document.getElementById('content-search');

let calculatorToolResult = document.getElementById('calc-expression-result');

let docViewer = document.getElementById('doc-viewer');
let docContent = document.getElementById('view-page-collapse')

let statusText = document.getElementById('status-text');

function populateInstructions(input_instructions) {
    steps = input_instructions['steps'];
    steps_html = '<ol>' + steps.map(item => `<li>${item}</li>`).join(''); + '</ol>';
    instructions.innerHTML = steps_html;
}

function updateTools(use_calc, use_doc, use_web) {
    calculatorTool.style.display = use_calc ? '' : 'none';
    googleTool.style.display = use_web ? '' : 'none';
    contentSelectorTool.style.display = use_doc ? '' : 'none';
 
    calculatorToolBtn.style.display = use_calc ? '' : 'none';
    googleToolBtn.style.display = use_web ? '' : 'none';
    contentSelectorToolBtn.style.display = use_doc ? '' : 'none';

    calculatorToolResult.style.display = use_calc ? '' : 'none';

    calculatorToolBtn.disabled = false;
    googleToolBtn.disabled = false;
    contentSelectorToolBtn.disabled = false;

    calculatorToolInput.disabled = false;
    googleToolInput.disabled = false;
    contentSelectorToolInput.disabled = false;


    // if (use_doc && !use_web) {
    //     console.log('doc only!', contentSelectorToolCol);
    //     contentSelectorToolCol.className = 'col-12';
    // } else if (use_doc && use_web) {
    //     googleToolCol.className = 'col-6';
    //     contentSelectorToolCol.className = 'col-6';
    // }
}

function disableButtons() {
    console.log('disabling!');
    calculatorToolBtn.disabled = true;
    googleToolBtn.disabled = true;
    contentSelectorToolBtn.disabled = true;

    calculatorToolInput.disabled = true;
    googleToolInput.disabled = true;
    contentSelectorToolInput.disabled = true;
}

function updateDoc(use_doc, doc_content) {
    docViewer.style.display = use_doc ? 'block' : 'none';
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
    // console.log("Answer:", answer);
    // console.log("Status:", status);
    if (status === "idle") {
        if (answer !== "") {
            statusText.innerHTML = `Status: <span class=text-secondary>The correct answer is:</span> <span class=text-primary>${answer}</span>. Hit "next" to continue...`;
        } else {
            statusText.innerHTML = `Status: <span class=text-secondary>Hit "next" to continue...</span>`;
        }
    } else if (status === "instruct") {
        statusText.innerHTML = 'Status: <span class=text-primary>Read the question + instructions</span>';
    } else if (status === "playing") {
        statusText.innerHTML = 'Status: <span class=text-secondary>Waiting for buzzes...</span>';
    } else if (status === "contest") {
        statusText.innerHTML = `Status: <span class=text-secondary>Player <span class=text-primary>${player}</span> has buzzed</span>`;
    } else if (status === "buzz_correct") {
        statusText.innerHTML = `Status: <span class=text-secondary>Player <span class=text-primary>${player}</span> buzzed </span><span class=text-success>correctly (<i>${answer}</i>)</span>`;
    } else if (status === "buzz_incorrect") {
        statusText.innerHTML = `Status: <span class=text-secondary>Player <span class=text-primary>${player}</span> buzzed </span><span class=text-danger>incorrectly (<i>${answer}</i>)</span>`;
    } else if (status === "buzz_abstain") {
        statusText.innerHTML = `Status: <span class=text-secondary>Player <span class=text-primary>${player}</span> buzzed and </span><span class=text-danger>did not answer</span>`;
    }
}