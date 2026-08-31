// ==========================================
// 1. GLOBAL CORE VARIABLES & STATE INIT
// ==========================================
let masterDataset = [];
let quizData = [];
let isShuffleMode = false;
let timerInterval = null;
let totalSecondsLeft = 100 * 60;
let activeSelectedYears = new Set();

// ==========================================
// CUSTOM UI CONTROLLERS
// ==========================================
function toggleTopicDropdown() {
    const container = document.getElementById('topicCheckboxContainer');
    const arrow = document.getElementById('topicSelectArrow');
    if (container.style.display === 'none') {
        container.style.display = 'flex';
        arrow.style.transform = 'rotate(180deg)'; // Flips the triangle up
    } else {
        container.style.display = 'none';
        arrow.style.transform = 'rotate(0deg)'; // Flips it back down
    }
}

// Close the dropdown if the user clicks anywhere else on the page
document.addEventListener('click', function (event) {
    const dropdown = document.getElementById('topicCheckboxContainer');
    const selector = document.getElementById('customTopicSelect');
    if (dropdown && dropdown.style.display !== 'none' && !dropdown.contains(event.target) && !selector.contains(event.target)) {
        dropdown.style.display = 'none';
        document.getElementById('topicSelectArrow').style.transform = 'rotate(0deg)';
    }
});

// ==========================================
// 2. DYNAMIC CORRESPONDING DATA FETCH ENGINE
// ==========================================
async function loadQuiz() {
    try {
        // 1. Gather all checked boxes
        const checkedBoxes = Array.from(document.querySelectorAll('.topic-checkbox:checked'));
        const selectedFiles = checkedBoxes.map(cb => cb.value);

        // Guard against unchecking everything
        if (selectedFiles.length === 0) {
            document.getElementById('quiz-container').innerHTML = `<h3 style="padding:10px; color:#555;">Please select at least one topic from the dropdown menu.</h3>`;
            updateMainTitle("NO TOPIC SELECTED");
            //  document.getElementById('topicSelectText').innerText = "Select topics...";
            return;
        }

        // 2. Save selections to memory
        localStorage.setItem('activeQuizTopics', JSON.stringify(selectedFiles));

        // 3. Update Text UI intelligently without missing elements
        if (selectedFiles.length === 1) {
            const singleTopicName = checkedBoxes[0].dataset.name;
            updateMainTitle(singleTopicName);
        } else {
            updateMainTitle(`MIXED MOCK TEST (${selectedFiles.length} Topics)`);
        }

        console.log(`Fetching datasets:`, selectedFiles);

        // 4. Fetch ALL selected JSON files concurrently
        const fetchPromises = selectedFiles.map(file =>
            fetch(`./${file}`, { cache: 'no-store' }).then(res => {
                if (!res.ok) throw new Error(`Failed to load ${file}`);
                return res.json();
            })
        );

        const multipleDatasets = await Promise.all(fetchPromises);
        const combinedDataset = multipleDatasets.flat();

        // 5. Map and deploy the data
        masterDataset = combinedDataset.map((item, idx) => {
            return { ...item, originalIndex: (idx + 1) };
        });

        activeSelectedYears = new Set();
        buildDynamicYearFilters();
        buildDynamicExamLevelFilters();
        processQuestionsDataset();
        startCountdown();

    } catch (error) {
        console.error("Quiz initialization fatal failure:", error);
        document.getElementById('quiz-container').innerHTML = `
            <div style="padding: 20px; background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; border-radius: 4px;">
                <h3>Failed to load dataset entries</h3>
                <p>Details: ${error.message}</p>
            </div>`;
    }
}

// ==========================================
// 3. RUNTIME DATA EXTRACTION & DYNAMIC FILTERS
// ==========================================
function buildDynamicYearFilters() {
    const targetDiv = document.getElementById('yearContainer');
    if (!targetDiv) return;
    targetDiv.innerHTML = '';

    let uniqueYears = [...new Set(masterDataset.map(q => q.year).filter(Boolean))];
    uniqueYears.sort((a, b) => b - a);

    if (uniqueYears.length === 0) {
        targetDiv.innerHTML = '<span style="color:#777; font-style:italic;">No year markers found</span>';
        return;
    }

    uniqueYears.forEach(year => {
        const wrapper = document.createElement('label');
        wrapper.style.cssText = "display: flex; align-items: center; gap: 4px; padding: 2px 4px; margin: 0; font-size: 13px;";

        const cb = document.createElement('input');
        cb.type = "checkbox";
        cb.value = year;
        cb.onchange = function () {
            if (this.checked) {
                activeSelectedYears.add(this.value);
            } else {
                activeSelectedYears.delete(this.value);
            }
            processQuestionsDataset();
        };

        wrapper.appendChild(cb);
        wrapper.appendChild(document.createTextNode(year));
        targetDiv.appendChild(wrapper);
    });
}

function processQuestionsDataset() {
    const countDisplay = document.getElementById('totalQuestionsCount');

    let filteredData = masterDataset.filter(q => {
        // A. Multi-Year Selection Filter
        if (activeSelectedYears.size > 0 && !activeSelectedYears.has(q.year?.toString())) {
            return false;
        }

        // B. Clear Explicit Exam Level Tag Filter (Mains vs Advanced)
        const selectedLevel = document.getElementById('levelFilterSelect').value;
        if (selectedLevel !== 'all' && q.exam_level !== selectedLevel) {
            return false;
        }

        // C. Question Format Layout Filter (MCQ, Integer, Matching)
        const selectedFormat = document.getElementById('formatFilterSelect').value;
        if (selectedFormat !== 'all' && q.type !== selectedFormat) {
            return false;
        }

        return true;
    });

    if (countDisplay) {
        countDisplay.innerText = `(Filtered: ${filteredData.length} of ${masterDataset.length})`;
    }

    if (isShuffleMode) {
        quizData = selectRandomQuestions(filteredData, 25);
    } else {
        quizData = filteredData.slice(0, Math.min(25, filteredData.length));
    }

    renderQuiz();
}

function toggleShuffleMode() {
    isShuffleMode = !isShuffleMode;
    const btn = document.getElementById('shuffleToggleBtn');
    if (isShuffleMode) {
        btn.innerText = "Shuffle Mode: ON";
        btn.classList.remove('toggle-btn-inactive');
    } else {
        btn.innerText = "Shuffle Mode: OFF";
        btn.classList.add('toggle-btn-inactive');
    }
    processQuestionsDataset();
}

function selectRandomQuestions(array, count) {
    let shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled.slice(0, Math.min(count, shuffled.length));
}
// ==========================================
// 4. INTERACTIVE QUIZ DOM RENDERING ENGINE
// ==========================================


// ==========================================
// 4. INTERACTIVE QUIZ DOM RENDERING ENGINE
// ==========================================
function renderQuiz() {
    const container = document.getElementById('quiz-container');
    container.innerHTML = '';

    if (!quizData || quizData.length === 0) {
        container.innerHTML = `<h3 style="padding:10px; color:#555;">No matching questions found for current filter criteria.</h3>`;
        return;
    }

    quizData.forEach((q, index) => {
        try {
            const div = document.createElement('div');
            div.className = 'question-block';
            div.id = `block-${index}`;

            // 1. Build Badges (NCERT, Grade, Year, Exam Level/Custom Source)
            let ncertHtml = q.ncert ? '<span class="q-badge q-ncert-badge">NCERT</span>' : '';
            let gradeBadgeHTML = q.grade ? `<span class="q-badge" style="background:#e67e22; color:white;">${q.grade.toUpperCase()}</span>` : '';
            let yearBadgeHTML = q.year ? `<span class="q-badge q-year-badge">${q.year}</span>` : '';
            let levelBadgeHTML = q.exam_level ? `<span class="q-badge q-year-badge" style="background:#009688; margin-left:4px;">${q.exam_level.toUpperCase()}</span>` : '';

            // 2. Inject all badges into the index tag block cleanly
            let html = `<div class="question-index-tag">
                ${ncertHtml}
                ${gradeBadgeHTML}
                <span class="q-badge q-num-badge">Ref: #${q.originalIndex || q.id}</span>
                ${yearBadgeHTML}
                ${levelBadgeHTML}
            </div>`;

            html += `<h3>Q${index + 1}: ${q.question || 'Missing Question Text'}</h3>`;

            if (q.image && typeof q.image === 'string' && q.image.trim() !== '') {
                html += `<img src="${q.image.trim()}" class="question-img" alt="Question Graphic Resource">`;
            }

            // Render Input Elements based on type safety rules (MCQ, Integer, Matching, Subjective)
            if (q.type === 'mcq' && q.options) {
                Object.keys(q.options).forEach(key => {
                    html += `<label id="label-${index}-${key}"><input type="radio" name="q${index}" value="${key}" onchange="validate(${index})"> ${key.toUpperCase()}: ${q.options[key]}</label><br>`;
                });
            } else if (q.type === 'integer') {
                html += `<input type="number" id="input-${index}" placeholder="Type your answer" oninput="validate(${index})">`;
            } else if (q.type === 'subjective') {
                html += `<div style="padding: 10px; background: #fff3cd; border: 1px solid #ffeeba; border-radius: 4px; color: #856404; font-size: 13px; margin-bottom: 10px;">📝 <strong>Subjective Question:</strong> Work out your proof or derivation on your scratchpad, then reveal the solution below.</div>`;
            } else if (q.type === 'matching') {
                let list1 = q.list_1 || q.list_i || [];
                let list2 = q.list_2 || q.list_ii || [];

                let matchHTML = `<div class="matching-container">
                    <div class="list-box"><strong>List I</strong><ul>${list1.map(item => `<li>${item}</li>`).join('')}</ul></div>
                    <div class="list-box"><strong>List II</strong><ul>${list2.map(item => `<li>${item}</li>`).join('')}</ul></div>
                </div>`;

                if (q.options && Array.isArray(q.options)) {
                    q.options.forEach((opt, i) => {
                        html += `<label id="label-${index}-${i}"><input type="radio" name="q${index}" value="${i}" onchange="validate(${index})"> ${opt}</label><br>`;
                    });
                } else if (q.answer && typeof q.answer === 'object') {
                    let mapStr = `A→${q.answer.a || 1}, B→${q.answer.b || 2}, C→${q.answer.c || 3}, D→${q.answer.d || 4}`;
                    html += `<label id="label-${index}-match"><input type="radio" name="q${index}" value="true" onchange="validate(${index})"> Show Mapping: ${mapStr}</label><br>`;
                }
                html += matchHTML;
            }

            // --- CONTEXT FILTER FOR EXPLANATIONS ---
            let expContent = '';
            if (Array.isArray(q.explanation)) {
                expContent = q.explanation.map(line => line.trim()).filter(line => line !== '').join('<br>');
            } else if (typeof q.explanation === 'string') {
                expContent = q.explanation.trim();
            }

            let stepContent = '';
            if (q.step_by_step_explanation && typeof q.step_by_step_explanation === 'string') {
                stepContent = q.step_by_step_explanation.trim().replace(/\n/g, '<br>');
            }

            let finalExplanationHTML = '';
            if (expContent && stepContent) {
                finalExplanationHTML = `
                    <div class="short-explanation">${expContent}</div>
                    <div class="step-explanation-header" style="font-weight: bold; margin-top: 12px; color: #0056b3;">Detailed Step-by-Step Proof:</div>
                    <div class="step-explanation">${stepContent}</div>`;
            } else if (stepContent) {
                finalExplanationHTML = `<div class="step-explanation">${stepContent}</div>`;
            } else if (expContent) {
                finalExplanationHTML = `<div class="short-explanation">${expContent}</div>`;
            } else {
                finalExplanationHTML = `<div style="color: #666; font-style: italic;">No detailed explanation text available.</div>`;
            }

            let revealBtnHTML = q.type === 'subjective' ? `<button class="action-btn" onclick="validate(${index})" style="margin-top: 10px;">Reveal Solution & Proof</button>` : '';

            html += `<br>${revealBtnHTML}
                <div id="exp-container-${index}" class="explanation">
                    <div style="margin-bottom: 8px; font-weight: bold; color: #155724;">
                        Answer / Reference Note: <span id="correct-ans-display-${index}"></span>
                    </div>
                    <hr style="border: 0; border-top: 1px solid #b8daff; margin: 10px 0;">
                    <div class="explanation-body-content">${finalExplanationHTML}</div>
                </div>`;
            div.innerHTML = html;
            container.appendChild(div);
        } catch (innerErr) {
            console.error("Error rendering item at index " + index, innerErr);
        }
    });

    // Trigger structural typeset re-evaluation updates in MathJax
    if (window.MathJax && typeof MathJax.typesetPromise === 'function') {
        MathJax.typesetPromise();
    } else if (window.MathJax) {
        MathJax.typeset();
    }
}








async function initializeApp() {
    try {
        const response = await fetch('./topics.json', { cache: 'no-store' });
        if (!response.ok) throw new Error("Could not load topics.json");
        const topics = await response.json();

        const filteredTopics = topics.filter(topic =>
            !['model_config.json', 'topics.json'].includes(topic.file)
        );

        const container = document.getElementById('topicCheckboxContainer');
        container.innerHTML = '';

        // Retrieve saved memory for multiple topics
        let savedTopics = [];
        const savedTopicsStr = localStorage.getItem('activeQuizTopics');
        if (savedTopicsStr) {
            try { savedTopics = JSON.parse(savedTopicsStr); }
            catch (e) { console.error("Could not parse saved topics"); }
        }

        filteredTopics.forEach(topic => {
            // Build a clean wrapper matching your year filter style
            const wrapper = document.createElement('label');
            wrapper.style.cssText = "display: flex; align-items: center; gap: 6px; padding: 6px 10px; margin: 0; font-size: 13px; background: #f4f4f9; border: 1px solid #ccc; border-radius: 4px; cursor: pointer; width: 100%; box-sizing: border-box; transition: background 0.2s;";

            // Hover effect trick
            wrapper.onmouseenter = () => wrapper.style.background = '#e9ecef';
            wrapper.onmouseleave = () => wrapper.style.background = '#f4f4f9';

            const cb = document.createElement('input');
            cb.type = "checkbox";
            cb.value = topic.file;
            cb.dataset.name = topic.name; // Save the readable name for the title
            cb.className = "topic-checkbox";

            // Re-check boxes from previous session
            if (savedTopics.includes(topic.file)) {
                cb.checked = true;
            }

            // When clicked, automatically reload the quiz
            cb.onchange = loadQuiz;

            wrapper.appendChild(cb);
            wrapper.appendChild(document.createTextNode(topic.name));
            container.appendChild(wrapper);
        });

        // Fallback: If nothing is saved, select ALL topics by default
        const allCheckboxes = document.querySelectorAll('.topic-checkbox');
        if (savedTopics.length === 0 && allCheckboxes.length > 0) {
            // Loop through and check every single box
            allCheckboxes.forEach(cb => cb.checked = true);
        }
        loadQuiz();

    } catch (error) {
        console.error("Failed to map topics:", error);
        document.getElementById('topicSelectText').innerText = `Error loading topics`;
    }
}

// Helper to update the big H1 tag at the top of the page
function updateMainTitle(topicName) {
    const titleH1 = document.querySelector('.quiz-header-wrapper h1');
    const countSpan = document.getElementById('totalQuestionsCount');
    if (titleH1) {
        titleH1.innerHTML = `${topicName.toUpperCase()} <span id="totalQuestionsCount" style="font-size: 16px; color: #6c757d; font-weight: normal;">${countSpan ? countSpan.innerText : ''}</span>`;
    }
}

// ==========================================
// 5. INPUT RESPONSE EVALUATION ENGINE
// ==========================================
function validate(index) {
    const q = quizData[index];
    const block = document.getElementById(`block-${index}`);
    const expContainer = document.getElementById('exp-container-' + index);
    const correctAnsDisplay = document.getElementById('correct-ans-display-' + index);
    let isCorrect = false;

    if (correctAnsDisplay) {
        if (q.type === 'mcq') {
            correctAnsDisplay.innerText = `${q.answer.toUpperCase()}: ${q.options ? q.options[q.answer] : ''}`;
        } else if (q.type === 'matching') {
            if (typeof q.answer === 'object') {
                correctAnsDisplay.innerText = `A→${q.answer.a}, B→${q.answer.b}, C→${q.answer.c}, D→${q.answer.d}`;
            } else {
                correctAnsDisplay.innerText = q.options ? q.options[q.answer] : q.answer;
            }
        } else {
            correctAnsDisplay.innerText = q.answer;
        }
    }

    if (q.type === 'mcq') {
        const selectedInput = block.querySelector(`input[name="q${index}"]:checked`);
        if (!selectedInput) return;

        isCorrect = (selectedInput.value.toString() === q.answer.toString());
        block.querySelectorAll('label').forEach(lbl => lbl.classList.remove('correct', 'wrong'));

        const selectedLabel = document.getElementById(`label-${index}-${selectedInput.value}`);
        if (selectedLabel) selectedLabel.classList.add(isCorrect ? 'correct' : 'wrong');

    } else if (q.type === 'matching') {
        block.querySelectorAll('label').forEach(lbl => lbl.classList.remove('correct', 'wrong'));
        const selectedInput = block.querySelector(`input[name="q${index}"]:checked`);
        if (selectedInput) {
            selectedInput.parentNode.classList.add('correct');
        }

    } else if (q.type === 'integer') {
        const numInput = document.getElementById(`input-${index}`);
        if (!numInput || !numInput.value.trim()) return;

        isCorrect = (numInput.value.trim().toString() === q.answer.toString());
        numInput.classList.remove('correct', 'wrong');
        numInput.classList.add(isCorrect ? 'correct' : 'wrong');
    }

    if (expContainer) {
        expContainer.style.display = 'block';
        if (window.MathJax && typeof MathJax.typesetPromise === 'function') {
            MathJax.typesetPromise([expContainer]);
        }
    }
}



function buildDynamicExamLevelFilters() {
    const selectElem = document.getElementById('levelFilterSelect');
    if (!selectElem) return;

    // Remember the currently selected value so we don't accidentally reset user choice on reload
    const currentVal = selectElem.value;

    // Reset with default "All" option
    selectElem.innerHTML = '<option value="all">All Exam Levels</option>';

    // Extract unique exam levels from master dataset
    let uniqueLevels = [...new Set(masterDataset.map(q => q.exam_level).filter(Boolean))];
    uniqueLevels.sort();

    if (uniqueLevels.length === 0) return;

    uniqueLevels.forEach(lvl => {
        const opt = document.createElement('option');
        opt.value = lvl;
        opt.textContent = lvl.toUpperCase();
        selectElem.appendChild(opt);
    });

    // Restore previous selection if it still exists in the new list
    if ([...selectElem.options].some(o => o.value === currentVal)) {
        selectElem.value = currentVal;
    }
}
// ==========================================
// 6. AUTOMATED RUNTIME INITIALIZATION HOOK
// ==========================================
// window.addEventListener('DOMContentLoaded', loadQuiz);
window.addEventListener('DOMContentLoaded', initializeApp);


