let instructionSpace = document.getElementById('instruction-space');
let instructions = document.getElementById('model-instructions');

const instructionHeader = document.getElementById('instruction-header');
const instructionCollapse = document.getElementById('instruction-collapse');


function populateInstructions(input_instructions) {
    steps = input_instructions['steps'];
    steps_html = '<ol>' + steps.map(item => `<li>${item}</li>`).join(''); + '</ol>';
    instructions.innerHTML = steps_html;
}