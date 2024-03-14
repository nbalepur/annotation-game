// Feedback section
let feedbackSpace = document.getElementById('feedback-space');
let initialFeedback = document.getElementById('initial-feedback');
let additionalFeedback = document.getElementById('additional-feedback');

// Feedback variables to send back
let interestingnessRating = 0;
let guessedGenerationMethod = "";
let clueOrder;
let factualMaskList;

// Flag for when user has completed feedback
let completedFeedback = true;

// ============================== INTERESTINGNESS START ==============================
let ratingStars = document.querySelectorAll('input[name="rating3"]');
function initializeRatingStars() {
    ratingStars = document.querySelectorAll('input[name="rating3"]');
    
    function handleRatingChange() {
        ratingStars.forEach(input => {
            if (input.checked) {
                interestingnessRating = input.value;
            }
        });
    }

    // Call the function initially to log the initial selected value
    handleRatingChange();
    
    // Add event listener to each radio input
    ratingStars.forEach(input => {
        input.addEventListener("change", handleRatingChange);
    });
}
// ============================== INTERESTINGNESS END ==============================

// ============================== AI OR HUMAN START ==============================
let humanWrittenRadio = document.getElementById('human-written');
let aiGeneratedRadio = document.getElementById('ai-generated');
function initializeGenerationMethod() {
    humanWrittenRadio = document.getElementById('human-written');
    aiGeneratedRadio = document.getElementById('ai-generated');

    function handleUpdate() {
        if (humanWrittenRadio.checked) {
            guessedGenerationMethod = humanWrittenRadio.value;
        } else if (aiGeneratedRadio.checked) {
            guessedGenerationMethod = aiGeneratedRadio.value;
        }
    }

    humanWrittenRadio.addEventListener('change', handleUpdate);
    aiGeneratedRadio.addEventListener('change', handleUpdate);
}
// ============================== AI OR HUMAN END ==============================

// ============================== MISC FIELDS START ==============================
let feedbackTextForm = document.getElementById('feedback-text');
const setFeedbackTextForm = (text) => {
    feedbackTextForm = document.getElementById('feedback-text');
    feedbackTextForm.value = text;
}
let improvedQuestionForm = document.getElementById('improved-question');
const setImprovedQuestionForm = (text) => {
    improvedQuestionForm = document.getElementById('improved-question');
    improvedQuestionForm.value = text;
}
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
    if (gameState === 'idle' && questionSpace.innerText !== '') {
        // Enable collapsing
        enableFeedbackCollapseToggle();
    } else {
        // Disable
        disableFeedbackCollapseToggle();
    }
}
// ============================== FEEDBACK INITIATING END ==============================

// ============================== POPULATES ALL FEEDBACK FIELDS START ==============================
function populateInitialQuestionFeedback(feedback) {
    if (feedback.is_submitted) {
        initialFeedback.innerHTML = '';

        if (feedback.guessed_gen_method_correctly) {
            if (feedback.guessed_generation_method == 'human') {
                initialFeedback.innerHTML = `
                <p>
                    <i class="fas fa-circle-check fa-2xl"></i>
                    Couldn't fool you! You know a human when you see one!
                </p>`
            } else {
                initialFeedback.innerHTML = `
                <p>
                    <i class="fas fa-circle-check fa-2xl"></i>
                    You got us! This question was written by AI!
                </p>`
            }
        } else {
            if (feedback.guessed_generation_method == 'human') {
                initialFeedback.innerHTML = `
                <p>
                    <i class="fas fa-circle-xmark fa-2xl"></i>
                    Gotcha! An AI actually authored this!
                </p>`
            } else {
                initialFeedback.innerHTML = `
                <p>
                    <i class="fas fa-circle-xmark fa-2xl"></i>
                    Not quite! This question was, in fact, written by a human!
                </p>`
            }
        }
    } else {
        initialFeedback.innerHTML = `
        <div class="card-body">
            <h5>Generation Method</h5>
            <!-- Asking for user belief about the question -->
            <div class="form-group">
                <label for="question-origin">Do you think is human-written or AI generated?</label>
                <div class="form-check">
                    <input class="form-check-input" type="radio" name="question-origin" id="human-written" value="human" required>
                    <label class="form-check-label" for="human-written">
                        Human-Written
                    </label>
                </div>
                <div class="form-check">
                    <input class="form-check-input" type="radio" name="question-origin" id="ai-generated" value="ai" required>
                    <label class="form-check-label" for="ai-generated">
                        AI-Generated
                    </label>
                </div>
                <div class="invalid-feedback">
                    You are required to guess how this question was written!
                </div>
            </div>
        </div>

        <div class="card-body" id="interestingness-section">
            <h5>Interestingness</h5>
            <div class="interestingness-rating">
                <label for="rating-group">How interesting is this question?</label>
                <div class="rating-group" id="interestingness-rating">
                    <input disabled class="rating__input rating__input--none" name="rating3" id="rating3-none" value="0" type="radio" checked> 
                    <label aria-label="1 star" class="rating__label form-check-label" for="rating3-1"><i class="rating__icon rating__icon--star fas fa-star"></i></label>
                    <input class="rating__input form-check-input" name="rating3" id="rating3-1" value="1" type="radio" required>
                    <label aria-label="2 stars" class="rating__label form-check-label" for="rating3-2"><i class="rating__icon rating__icon--star fas fa-star"></i></label>
                    <input class="rating__input form-check-input" name="rating3" id="rating3-2" value="2" type="radio" required>
                    <label aria-label="3 stars" class="rating__label form-check-label" for="rating3-3"><i class="rating__icon rating__icon--star fas fa-star"></i></label>
                    <input class="rating__input form-check-input" name="rating3" id="rating3-3" value="3" type="radio" required>
                    <label aria-label="4 stars" class="rating__label form-check-label" for="rating3-4"><i class="rating__icon rating__icon--star fas fa-star"></i></label>
                    <input class="rating__input form-check-input" name="rating3" id="rating3-4" value="4" type="radio" required>
                    <label aria-label="5 stars" class="rating__label form-check-label" for="rating3-5"><i class="rating__icon rating__icon--star fas fa-star"></i></label>
                    <input class="rating__input form-check-input" name="rating3" id="rating3-5" value="5" type="radio" required>
                    <div class="invalid-feedback">Please select a rating.</div>
                </div>
            </div>
        </div>

        <div class="card-body">
            <button type="submit" id="guess-and-submit-btn" class="btn btn-primary">Guess & Submit Feedback</button>
        </div>`

        initialFeedback.classList.remove('was-validated');

        initializeRatingStars();

        interestingnessRating = feedback.interestingness_rating;
        guessedGenerationMethod = feedback.guessed_generation_method;

        initializeGenerationMethod();
    
        humanWrittenRadio.check = (guessedGenerationMethod === humanWrittenRadio.value);
        aiGeneratedRadio.check = (guessedGenerationMethod === aiGeneratedRadio.value);

        initialFeedback.addEventListener('submit', function(event) {
            if (!initialFeedback.checkValidity() || interestingnessRating == 0) {
                // Since interestingness star ratings have a dummy star.
                // Default bootstrap form validation does not work because the dummy star is checked.
                // So we show the invalid-feedback
                console.log(!initialFeedback.checkValidity(), interestingnessRating == 0);
                document.querySelector('.rating-group .invalid-feedback').style.display = 'block';
            } else {
                document.querySelector('.rating-group .invalid-feedback').style.display = 'none';
                submitInitialFeedback();
            }
            
            event.preventDefault();
            event.stopPropagation();
            initialFeedback.classList.add('was-validated')

            
        }, false);
    }

    console.log(feedback)
}

function populateAdditionalQuestionFeedback(feedback) {
    // Select the feedback-space element
    let additionalFeedback = document.getElementById("additional-feedback");

    if (!feedback.is_submitted) {
        // Initial feedback is not submitted yet. Show nothing yet
        additionalFeedback.innerHTML = '';
    } else {
        if (feedback.additional_submission_datetime == null) { // have not submitted
            if (feedback.solicit_additional_feedback) { // solicited additional feedback --> initialize form
                // Create the HTML content to be added
                additionalFeedback.classList.remove('was-validated');
                completedFeedback = false;
                nextBtn.disabled = true;
                additionalFeedback.innerHTML = `
                    <div class="card-body">
                        <h5>Pyramidality and Factual Accuracy</h5>
                        <div class="pyramidality-factual-accuracy">
                            <ul id="pyramidality-factual-accuracy-list" class="list-group">
                            </ul>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="row mb-3">
                            <div class="col">
                                <label for="feedback-text" class="form-label">Feedback Text</label>
                                <textarea class="form-control" id="feedback-text" maxlength="500" rows="3" required placeholder="Please describe what you would do to make the question better. Example: I would remove the third clue because it could mislead the player(s) to think the answer is X."></textarea>
                                <div class="invalid-feedback">Please enter feedback for the question.</div>
                            </div>
                        </div>
                        <div class="row mb-3">
                            <div class="col">
                                <label for="improved-question" class="form-label">Improved Question</label>
                                <textarea class="form-control" id="improved-question" maxlength="500" rows="6" required placeholder="Rewrite the question as you see fit here."></textarea>
                                <div class="invalid-feedback">Please rewrite the question.</div>
                            </div>
                        </div>
                        <div class="row mb-3">
                            <div class="col">
                                <button type="submit" class="btn btn-primary" id="submit-btn">Submit</button>
                            </div>
                        </div>
                    </div>`;
    
                additionalFeedback.addEventListener('submit', function(event) {
                    if (!additionalFeedback.checkValidity()) {
                    } else {
                        submitAdditionalFeedback();
                    }
                    
                    event.preventDefault();
                    event.stopPropagation();
                    additionalFeedback.classList.add('was-validated')
                }, false);
            
                populatePyramidalityFactualAccuracyList(feedback)
            
                // Set values for feedback text and improved question
                setFeedbackTextForm(feedback.feedback_text);
                setImprovedQuestionFromOrderedClues(clueOrder);
            } else {
                additionalFeedback.innerHTML = 'No need for additional feedback. Click next to continue!';
                completedFeedback = true;
                nextBtn.disabled = false;
            }
        } else {
            additionalFeedback.innerHTML = "Thanks for the additional feedback. We'll use it to make our questions better! Click next to continue.";
            completedFeedback = true;
            nextBtn.disabled = false;
        }
    }
}
// ============================== POPULATES ALL FEEDBACK FIELDS END ==============================


// ============================== PYRAMIDALITY FACTUAL ACCURACY START ==============================
let pyrFactClueList = document.getElementById('pyramidality-factual-accuracy-list');
const setImprovedQuestionFromOrderedClues = (order) => 
        setImprovedQuestionForm(
            order.map((i) => factualMaskList[i] ? document.getElementById("clue-text-"+i).textContent : '').join(' ').trim()
        );

// Function to create a list item with text and a toggle switch
function createListItem(index, text) {
    // Create a new list item
    let listItem = document.createElement('li');
    listItem.setAttribute('data-id', `${index}`)
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
    textColumn.id = 'clue-text-' + index
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
    toggleInput.id = 'factual-toggle-' + index;
    toggleInput.checked = true;
    
    // Create the label for the toggle switch
    let toggleLabel = document.createElement('label');
    toggleLabel.className = 'form-check-label';
    toggleLabel.setAttribute('for', 'factual-toggle-' + index);
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
    pyrFactClueList = document.getElementById('pyramidality-factual-accuracy-list');
    clueOrder = feedback.submitted_clue_order;
    factualMaskList = feedback.submitted_factual_mask_list;

    while (pyrFactClueList.firstChild) {
        pyrFactClueList.removeChild(pyrFactClueList.firstChild);
    }

    // Iterate through submitted clues
    clueOrder.forEach(function(index) {
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

            // update factualMask
            let match = toggleInput.id.match(/factual-toggle-(\d+)/);
            if (match) {
                let clueIndex = parseInt(match[1]);
                factualMaskList[clueIndex] = toggleInput.checked;
                setImprovedQuestionFromOrderedClues(clueOrder);
            }
        });
    });

    

    let sortable = Sortable.create(pyrFactClueList, {
        group: "PyramidalityFactualAccuracy",
        store: {
            /**
             * Get the order of elements. Called once during initialization.
             * @param   {Sortable}  sortable
             * @returns {Array}
             */
            get: function (sortable) {
                clueOrder = feedback.submitted_clue_order;

                if (clueOrder) {
                    sortable.sort(clueOrder);
                    setImprovedQuestionFromOrderedClues(clueOrder);
                }
                

                return clueOrder ? clueOrder : [];
            },
    
            /**
             * Save the order of elements. Called onEnd (when the item is dropped).
             * @param {Sortable}  sortable
             */
            set: function (sortable) {
                clueOrder = sortable.toArray().map(i => parseInt(i));
                setImprovedQuestionFromOrderedClues(clueOrder);
                console.log(sortable);
                console.log(clueOrder);
            }
        }

        
    });

    document.getElementById('submit-btn').addEventListener('click', 
        (e) => {
            clueOrder = sortable.toArray().map(i => parseInt(i));
            factualMaskList = clueOrder.toSorted().map((i) => document.getElementById('factual-toggle-'+i).checked)
            console.log(factualMaskList);
        });

    
}
// ============================== PYRAMIDALITY FACTUAL ACCURACY END ==============================

