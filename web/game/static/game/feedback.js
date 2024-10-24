let feedbackRow = document.getElementById('feedback-row');
let questionRow = document.getElementById('question-row');

let feedbackQuestion = document.getElementById('feedback-question-body');
let planA = document.getElementById('plan-a-body');
let planB = document.getElementById('plan-b-body');

function selectPlan(selected_plan) {
    console.log('selected plan:', selected_plan);
    sendRequest("log_comparison", selected_plan);
}

function populateComparisonPane(question, instr_a, instr_b) {
    instr_a = parseInstructions(instr_a);
    instr_b = parseInstructions(instr_b);

    feedbackQuestion.innerText = question;
    planA.innerHTML = instr_a;
    planB.innerHTML = instr_b;
}


function toggleComparisonViewer(show_comparison) {
    //showButtons();
    
    instructionProgress.style.display = 'none'
    contentProgress.style.display = 'none';
    buzzProgress.style.display = '';
    buzzProgress.style.visibility = 'hidden';

    feedbackRow.style.display = show_comparison ? '' : 'none';
    questionRow.style.display = !show_comparison ? '' : 'none';
}