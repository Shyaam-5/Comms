// static/moduleD.js - Grammar Quiz Module (Fixed)

let quizData = null;
let currentQuestionIndex = 0;
let userAnswers = {};

function getCredentials() {
    const email = localStorage.getItem('email');
    const sessionId = localStorage.getItem('session_id');
    if (!email) {
        window.location.href = '/login';
        return null;
    }
    return { email, sessionId };
}

document.addEventListener('DOMContentLoaded', () => {
    if (!getCredentials()) return;
    console.log('Page loaded, fetching quiz...');
    loadQuiz();
});

async function loadQuiz() {
    const creds = getCredentials();
    if (!creds) return;

    try {
        console.log('Calling /api/moduleD/quiz...');

        const response = await fetch(`/api/moduleD/quiz?email=${encodeURIComponent(creds.email)}&session_id=${encodeURIComponent(creds.sessionId || '')}`, {
            method: 'GET',
            credentials: 'same-origin'
        });

        console.log('Response status:', response.status);

        if (response.status === 401) {
            console.error('Unauthorized - redirecting to login');
            window.location.href = '/login';
            return;
        }

        const data = await response.json();
        console.log('Quiz data received:', data);

        if (data.success !== false && data.questions && data.questions.length > 0) {
            quizData = data;
            currentQuestionIndex = 0;
            userAnswers = {};

            console.log('Quiz loaded successfully, displaying first question');

            // Show progress
            updateProgressUI();

            // Display first question
            displayQuestion();
        } else {
            console.error('Quiz data invalid:', data);
            showNotification('Failed to load quiz: ' + (data.error || 'Unknown error'), 'error');

            // Show the error in the UI
            document.getElementById('questionText').textContent =
                'Error loading quiz. Please refresh the page.';
        }
    } catch (error) {
        console.error('Load quiz error:', error);
        showNotification('Network error: ' + error.message, 'error');

        // Show the error in the UI
        document.getElementById('questionText').textContent =
            'Network error. Please check your connection and refresh.';
    }
}

function displayQuestion() {
    if (!quizData || !quizData.questions) {
        console.error('No quiz data available');
        return;
    }

    const question = quizData.questions[currentQuestionIndex];
    if (!question) {
        console.error('No question at index:', currentQuestionIndex);
        return;
    }

    console.log('Displaying question:', currentQuestionIndex + 1, question);

    // Update question number and text
    document.getElementById('questionNumber').textContent = `Question ${currentQuestionIndex + 1}`;
    document.getElementById('questionText').textContent = question.sentence;

    // Update Category Badge
    const categoryEl = document.getElementById('questionCategory');
    if (question.category) {
        // Format: "tenses_past_simple" -> "Tenses: Past Simple"
        const formatted = question.category
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');

        categoryEl.textContent = formatted.replace(' ', ': '); // Tenses: Past Simple
        categoryEl.style.display = 'inline-block';
    } else {
        categoryEl.style.display = 'none';
    }

    // Create text input for answer
    const optionsContainer = document.getElementById('quizOptions');
    optionsContainer.innerHTML = '';

    const inputWrapper = document.createElement('div');
    inputWrapper.className = 'quiz-input-wrapper';

    const input = document.createElement('input');
    input.type = 'text';
    input.id = 'answerInput';
    input.className = 'quiz-answer-input';
    input.placeholder = 'Type your answer here...';
    input.value = userAnswers[currentQuestionIndex] || '';

    // Save answer on input
    input.addEventListener('input', (e) => {
        userAnswers[currentQuestionIndex] = e.target.value.trim();
        console.log('Answer saved for Q' + (currentQuestionIndex + 1) + ':', userAnswers[currentQuestionIndex]);
    });

    // Allow Enter key to go to next question
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            nextQuestion();
        }
    });

    inputWrapper.appendChild(input);
    optionsContainer.appendChild(inputWrapper);

    // Focus input
    setTimeout(() => input.focus(), 100);

    // Update navigation buttons
    updateNavigationButtons();
}

function updateNavigationButtons() {
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');

    if (!quizData || !quizData.questions) return;

    // Previous button
    prevBtn.disabled = (currentQuestionIndex === 0);

    // Next button text
    if (currentQuestionIndex === quizData.questions.length - 1) {
        nextBtn.textContent = 'Submit Quiz';
    } else {
        nextBtn.textContent = 'Next Quiz';
    }
}

function previousQuestion() {
    if (currentQuestionIndex > 0) {
        currentQuestionIndex--;
        displayQuestion();
        updateProgressUI();
    }
}

function nextQuestion() {
    if (!quizData || !quizData.questions) return;

    if (currentQuestionIndex < quizData.questions.length - 1) {
        // Move to next question
        currentQuestionIndex++;
        displayQuestion();
        updateProgressUI();
    } else {
        // Submit quiz
        submitQuiz();
    }
}

async function submitQuiz() {
    console.log('Submitting quiz with answers:', userAnswers);

    const creds = getCredentials();
    if (!creds) return;

    // Convert userAnswers object to structured array with IDs and answers
    const answersPayload = [];
    if (quizData && quizData.questions) {
        for (let i = 0; i < quizData.questions.length; i++) {
            const question = quizData.questions[i];
            answersPayload.push({
                id: question.id,
                answer: userAnswers[i] || ''
            });
        }
    }

    console.log('Answers payload:', answersPayload);

    try {
        const response = await fetch('/api/moduleD/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                email: creds.email,
                session_id: creds.sessionId,
                answers: answersPayload
            })
        });

        console.log('Submit response status:', response.status);

        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        const result = await response.json();
        console.log('Submit result:', result);

        if (result.success !== false) {
            displayResults(result);
        } else {
            showNotification('Failed to submit quiz: ' + (result.error || 'Unknown error'), 'error');
        }

    } catch (error) {
        console.error('Submit quiz error:', error);
        showNotification('Failed to submit quiz: ' + error.message, 'error');
    }
}

function displayResults(result) {
    console.log('Displaying results:', result);

    // Update score display
    const percentage = result.percentage || Math.round((result.score / result.total) * 100) || 0;
    document.getElementById('finalScore').textContent = percentage;
    document.getElementById('correctCount').textContent = result.correct_count || result.score || 0;
    document.getElementById('totalCount').textContent = result.total || quizData.questions.length;

    // Build review content
    const reviewContent = document.getElementById('reviewContent');
    reviewContent.innerHTML = '';

    if (result.review && result.review.length > 0) {
        result.review.forEach(item => {
            const reviewItem = document.createElement('div');
            reviewItem.className = `review-item ${item.correct ? 'correct' : 'incorrect'}`;

            reviewItem.innerHTML = `
                <div class="review-question">
                    <strong>Q${item.question_number}:</strong> ${item.sentence}
                </div>
                <div class="review-answer">
                    <span class="your-answer">Your answer: <em>${item.user_answer || '(no answer)'}</em></span>
                    ${!item.correct ? `<span class="correct-answer">Correct: <em>${item.correct_answer}</em></span>` : ''}
                    <span class="result-icon">${item.correct ? '✓' : '✗'}</span>
                </div>
            `;

            reviewContent.appendChild(reviewItem);
        });
    }

    // Show results modal
    document.getElementById('results').style.display = 'flex';
}

function completeQuiz() {
    // Redirect to performance report
    window.location.href = '/report';
}

function updateProgressUI() {
    const pill = document.getElementById('progress-pill');
    if (pill && quizData && quizData.questions) {
        pill.style.display = 'block';
        pill.textContent = `${currentQuestionIndex + 1}/${quizData.questions.length}`;
    }
}

function showNotification(message, type = 'info') {
    console.log(`[${type.toUpperCase()}]`, message);
    alert(message);
}

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        localStorage.removeItem('email');
        localStorage.removeItem('username');
        localStorage.removeItem('session_id');

        fetch('/logout', { method: 'POST', credentials: 'same-origin' })
            .then(() => window.location.href = '/login')
            .catch(() => window.location.href = '/login');
    }
}
