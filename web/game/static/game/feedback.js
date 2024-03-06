// ============================== INTERESTINGNESS START ==============================
const ratingStars = document.querySelectorAll('input[name="rating3"]');
let interestingnessRating = 0;

function handleRatingChange() {
    let selectedValue = null;

    ratingStars.forEach(input => {
        if (input.checked) {
            interestingnessRating = input.value;
        }
    });

}

// Add event listener to each radio input
ratingStars.forEach(input => {
    input.addEventListener("change", handleRatingChange);
});

// Call the function initially to log the initial selected value
handleRatingChange();
// ============================== INTERESTINGNESS END ==============================

// ============================== AI OR HUMAN START ==============================
const humanWrittenRadio = document.getElementById('human-written');
const aiGeneratedRadio = document.getElementById('ai-generated');
let guessedGenerationMethod = "";

function handleUpdate() {
    if (humanWrittenRadio.checked) {
        guessedGenerationMethod = humanWrittenRadio.value;
    } else if (aiGeneratedRadio.checked) {
        guessedGenerationMethod = aiGeneratedRadio.value;
    }
}

humanWrittenRadio.addEventListener('change', handleUpdate);
aiGeneratedRadio.addEventListener('change', handleUpdate);
// ============================== AI OR HUMAN END ==============================

// ============================== MISC FIELDS START ==============================
const buzzPositionNormForm = document.getElementById('buzz-position-norm');
const buzzPositionWordForm = document.getElementById('buzz-position-word');
const answeredCorrectlyForm = document.getElementById('answered-correctly');
const feedbackTextForm = document.getElementById('feedback-text');
const improvedQuestionForm = document.getElementById('improved-question');
// ============================== MISC FIELDS END ==============================

// ============================== FEEDBACK INITIATING START ==============================

const feedbackHeader = document.getElementById('feedback-header');
const feedbackCollapse = document.getElementById('feedback-collapse');

feedbackHeader.addEventListener('click', handleGameStateChange);

const disableFeedbackCollapseToggle = () => feedbackHeader.removeAttribute('data-bs-toggle', 'collapse');
const enableFeedbackCollapseToggle = () => feedbackHeader.setAttribute('data-bs-toggle', 'collapse');

const collapseFeedback = () => feedbackCollapse.classList.remove('show');
const expandFeedback = () => feedbackCollapse.classList.add('show');

function handleGameStateChange() {
    if (gameState === 'idle' && questionSpace.innerText !== "") {
        // Enable collapsing
        enableFeedbackCollapseToggle();
    } else {
        // Disable
        disableFeedbackCollapseToggle();
    }
}
// ============================== FEEDBACK INITIATING END ==============================

// ============================== POPULATES ALL FEEDBACK FIELDS START ==============================
function populateQuestionFeedback(feedback) {
    interestingnessRating = feedback['interestingness_rating'];
    guessedGenerationMethod = feedback['guessed_generation_method'];

    humanWrittenRadio.check = (guessedGenerationMethod === humanWrittenRadio.value);
    aiGeneratedRadio.check = (guessedGenerationMethod === aiGeneratedRadio.value);

    populatePyramidalityFactualAccuracyList(feedback)

    buzzPositionNormForm.value = feedback['buzz_position_norm'];
    buzzPositionWordForm.value = feedback['buzz_position_word'];
    answeredCorrectlyForm.value = feedback['answered_correctly'];
    
    // Set values for feedback text and improved question
    feedbackTextForm.value = feedback['feedback_text'];
    improvedQuestionForm.value = feedback['improved_question'];

    console.log(feedback)
}
// ============================== POPULATES ALL FEEDBACK FIELDS END ==============================


// ============================== PYRAMIDALITY FACTUAL ACCURACY START ==============================
let pyrFactClueList = document.getElementById('pyramidality-factual-accuracy-list');

// Function to create a list item with text and a toggle switch
function createListItem(index, text) {
    // Create a new list item
    let listItem = document.createElement('li');
    listItem.className = 'list-group-item';
    
    // Create a Bootstrap grid container
    let gridContainer = document.createElement('div');
    gridContainer.className = 'row align-items-center';


    // Create a column for the clue number
    let clueNumberColumn = document.createElement('div');
    clueNumberColumn.className = 'col-1';
    clueNumberColumn.innerHTML = `
        <div class="row">
            <div class="col-1"><i class="fas fa-up-down"></i></div>
            <div class="col-1">${index}</div>
        </div>
    `;
    
    // Create a column for the clue text
    let textColumn = document.createElement('div');
    textColumn.className = 'col-8';
    textColumn.textContent = text;
    
    // Create a column for the toggle switch
    let toggleColumn = document.createElement('div');
    toggleColumn.className = 'col-3 text-center';
    
    // Create the toggle switch container
    let toggleContainer = document.createElement('div');
    toggleContainer.className = 'form-check form-switch';
    
    // Create the toggle switch input
    let toggleInput = document.createElement('input');
    toggleInput.className = 'form-check-input';
    toggleInput.type = 'checkbox';
    toggleInput.role = 'switch';
    toggleInput.id = 'flexSwitchCheckDefault' + index;
    toggleInput.checked = true;
    
    // Create the label for the toggle switch
    let toggleLabel = document.createElement('label');
    toggleLabel.className = 'form-check-label';
    toggleLabel.setAttribute('for', 'flexSwitchCheckDefault' + index);
    // Set initial text content for the label
    toggleLabel.textContent = toggleInput.checked ? 'Factual' : 'Untrue';
    // Set initial color for the label
    toggleLabel.classList.toggle('text-danger', !toggleInput.checked);
    toggleLabel.classList.toggle('text-success', toggleInput.checked);
    
    // Append the toggle switch input and label to the container
    toggleContainer.appendChild(toggleInput);
    toggleContainer.appendChild(toggleLabel);
    
    // Append the toggle container to the toggle column
    toggleColumn.appendChild(toggleContainer);
    
    // Append the text and toggle columns to the grid container
    gridContainer.appendChild(clueNumberColumn);
    gridContainer.appendChild(textColumn);
    gridContainer.appendChild(toggleColumn);
    
    // Append the grid container to the list item
    listItem.appendChild(gridContainer);
    
    // Return the list item, toggle input, and toggle label for further use
    return [listItem, toggleInput, toggleLabel];
}

// Function to populate the list with submitted clues and toggle switches
function populatePyramidalityFactualAccuracyList(feedback) {
    while (pyrFactClueList.firstChild) {
        pyrFactClueList.removeChild(pyrFactClueList.firstChild);
    }

    // Iterate through submitted clues
    feedback.submitted_clue_order.forEach(function(index) {
        // Generate text for the clue
        let text = feedback.submitted_clue_list[index];
        // Create a list item with a toggle switch and label
        let [listItem, toggleInput, toggleLabel] = createListItem(index, text);
        // Append the list item to the list
        pyrFactClueList.appendChild(listItem);

        // Add event listener to toggle switch input
        toggleInput.addEventListener('change', function() {
            // Update label text content based on toggle state
            toggleLabel.textContent = toggleInput.checked ? 'Factual' : 'Untrue';
            // Update label color based on toggle state
            toggleLabel.classList.toggle('text-danger', !toggleInput.checked);
            toggleLabel.classList.toggle('text-success', toggleInput.checked);
        });
    });

    Sortable.create(pyrFactClueList, {
        group: "PyramidalityFactualAccuracy",
        store: {
            /**
             * Get the order of elements. Called once during initialization.
             * @param   {Sortable}  sortable
             * @returns {Array}
             */
            get: function (sortable) {
                let order = feedback.submitted_clue_order;
                return order ? order : [];
            },
    
            /**
             * Save the order of elements. Called onEnd (when the item is dropped).
             * @param {Sortable}  sortable
             */
            set: function (sortable) {
                let order = sortable.toArray();
                console.log(sortable);
                console.log("new order " + order);
            }
        }
    });
}
// ============================== PYRAMIDALITY FACTUAL ACCURACY END ==============================