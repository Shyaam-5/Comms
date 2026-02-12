// static/moduleC.js - Web Speech API Implementation for Topic Speaking

const MAX_QUESTIONS = 1;  // Only 5 topics for this module
const MAX_ATTEMPTS = 2; // Limit listening to 2 times
const RECORDING_DURATION = 120; // 2 minutes in seconds

let questionCount = 0;
let currentTopicId = null;
let currentTopic = '';
let recognition = null;
let isRecording = false;
let manualStop = false;
let recordingTimer = null;
let timeRemaining = RECORDING_DURATION;
let recordingStartTime = null;
let attemptCount = 0;
let isLoading = false;
let isProcessing = false;

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
    loadTopic();
    checkMicrophonePermission();
    initSpeechRecognition();
});

function initSpeechRecognition() {
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = true; // Continuous for topic speaking (long form)
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = function () {
            isRecording = true;
            recordingStartTime = Date.now();

            // Update button
            const btn = document.getElementById('recordBtn');
            const text = document.getElementById('recordText');
            btn.classList.add('recording');
            text.textContent = 'Stop Speaking';

            startTimer();
            console.log('Voice recognition started');
        };

        recognition.onerror = function (event) {
            console.warn('Speech recognition error:', event.error);

            // Only stop for fatal errors
            if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                isRecording = false;
                stopRecordingUI();
                showNotification('Error: ' + event.error, 'error');
                manualStop = true; // Prevent restart
            } else {
                // For other errors (no-speech, network, aborted, etc.), we ignore 
                // and let onend handle the restart logic
                console.log('Non-fatal error, will allow auto-restart.');
            }
        };

        recognition.onend = function () {
            if (manualStop) {
                isRecording = false;
                stopRecordingUI();
                console.log('Voice recognition ended manually');
            } else {
                console.log('Voice recognition ended automatically - attempting restart');
                // Ensure we remain in "recording" state UI-wise
                if (!document.getElementById('recordBtn').classList.contains('recording')) {
                    const btn = document.getElementById('recordBtn');
                    btn.classList.add('recording');
                    document.getElementById('recordText').textContent = 'Stop Speaking';
                }

                setTimeout(() => {
                    try {
                        if (!manualStop) {
                            recognition.start();
                            console.log('Restarted successfully');
                        }
                    } catch (e) {
                        console.error("Restart error:", e);
                    }
                }, 200);
            }
        };

        // We need to capture the full transcript for Module C
        let finalTranscript = '';

        recognition.onresult = function (event) {
            let interimTranscript = '';
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }
            console.log('Interim:', interimTranscript);
            // We could show interim results if we wanted, but requirement says "don't show text"
        };

        // Custom submit logic for continuous recognition
        recognition.submitResult = function () {
            submitText(finalTranscript);
            finalTranscript = ''; // Reset for next
        };

    } else {
        showNotification('Web Speech API is not supported in this browser. Please use Chrome.', 'error');
    }
}

async function checkMicrophonePermission() {
    if (!navigator.mediaDevices) {
        console.warn('MediaDevices API not available');
        return;
    }
    try {
        await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (error) {
        console.log('Permission API not supported');
    }
}

async function loadTopic() {
    if (questionCount >= MAX_QUESTIONS) {
        goToNextModule();
        return;
    }

    const creds = getCredentials();
    if (!creds) return;

    try {
        showLoading(true);
        const response = await fetch(`/api/moduleC/topic?email=${encodeURIComponent(creds.email)}&session_id=${encodeURIComponent(creds.sessionId || '')}`, {
            method: 'GET',
            credentials: 'same-origin'
        });

        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        const data = await response.json();

        if (data.success) {
            currentTopicId = data.topic_id;
            currentTopic = data.topic;

            // Display topic
            document.getElementById('topicText').textContent = currentTopic;

            // Increment count
            questionCount++;
            attemptCount = 0;
            updateProgressUI();

            // Reset UI
            closeResults();
            resetRecordButton();
            resetTimer();

            // Reset transcript in recognition object if needed
            if (recognition) recognition.onresult = function (event) {
                // Re-bind to clear previous closures if any, basically just standard logic
                let interimTranscript = '';
                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        // accum
                    }
                }
            };

        } else {
            showNotification('Failed to load topic: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Load topic error:', error);
        showNotification('Network error. Please check your connection.', 'error');
    } finally {
        showLoading(false);
    }
}

async function toggleRecording() {
    if (attemptCount >= MAX_ATTEMPTS && !isRecording) {
        showNotification('Maximum attempts reached for this topic.', 'warning');
        return;
    }

    if (!isRecording) {
        await startRecording();
    } else {
        await stopRecording();
    }
}

async function startRecording() {
    if (recognition) {
        try {
            manualStop = false;
            // Need to handle the transcript accumulation carefully
            // Re-define onresult to capture into a local scope for this session?
            // Or just use a global variable cleared on start
            window.finalTranscriptBuffer = '';

            recognition.onresult = function (event) {
                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        window.finalTranscriptBuffer += event.results[i][0].transcript + ' ';
                    }
                }
            };

            recognition.start();
            attemptCount++;
        } catch (e) {
            console.error("Recognition start error:", e);
        }
    }
}

async function stopRecording() {
    if (recognition && isRecording) {
        manualStop = true;
        recognition.stop();
        // The onend event will handle UI stop, but we need to submit AFTER stop
        // Wait a bit ensuring onend fires? Or submit in onend? 
        // Actually, onend fires when silence or stop() called.
        // We need to submit the accumulated text.

        // Let's hook the submission into the stop action or a slight delay
        setTimeout(() => {
            submitText(window.finalTranscriptBuffer || '');
        }, 500);
    }
}

function stopRecordingUI() {
    stopTimer();

    const btn = document.getElementById('recordBtn');
    const text = document.getElementById('recordText');
    btn.classList.remove('recording');
    text.textContent = 'Processing...';
    btn.disabled = true;
}

function startTimer() {
    timeRemaining = RECORDING_DURATION;
    document.getElementById('timerDisplay').style.display = 'block';
    updateTimerDisplay();

    recordingTimer = setInterval(() => {
        if (timeRemaining > 0) {
            timeRemaining--;
            updateTimerDisplay();
        }
    }, 1000);
}

function stopTimer() {
    if (recordingTimer) {
        clearInterval(recordingTimer);
        recordingTimer = null;
    }
}

function resetTimer() {
    stopTimer();
    timeRemaining = RECORDING_DURATION;
    document.getElementById('timerDisplay').style.display = 'none';
    updateTimerDisplay();
}

function updateTimerDisplay() {
    const minutes = Math.floor(timeRemaining / 60);
    const seconds = timeRemaining % 60;
    const display = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    document.getElementById('timeRemaining').textContent = display;
}

async function submitText(text) {
    if (isProcessing) return; // Prevent concurrent submissions

    if (!text || text.trim().length === 0) {
        console.warn("No text captured");
        // We might want to warn user, but let's send it anyway or handle it
    }

    const creds = getCredentials();
    if (!creds) return;

    try {
        isProcessing = true;
        console.log('Submitting text for topic_id:', currentTopicId);

        const response = await fetch('/api/moduleC', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: creds.email,
                session_id: creds.sessionId,
                topic_id: currentTopicId,
                transcribed_text: text
            }),
            credentials: 'same-origin'
        });

        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        const result = await response.json();
        console.log('Backend response:', result);

        if (result.success) {
            displayResults(result);
        } else {
            showNotification('Processing failed: ' + (result.error || 'Unknown error'), 'error');
            resetRecordButton();
        }

    } catch (error) {
        console.error('Submit text error:', error);
        showNotification('Failed to process. Please try again.', 'error');
        resetRecordButton();
    }
}

function displayResults(result) {
    const score = Math.round(result.score || 0);
    document.getElementById('score').textContent = score;

    // Populate card content
    document.getElementById('topicResult').textContent = currentTopic || "Unknown Topic";
    document.getElementById('transcription').textContent = result.transcription || result.transcribed_text || "";

    // Populate General Feedback
    document.getElementById('analysis').textContent = result.feedback || (result.analysis || 'No detailed analysis available.');

    // Populate Strengths
    const strengthsList = document.getElementById('strengthsList');
    strengthsList.innerHTML = '';
    const strengths = result.strengths || [];
    if (strengths.length > 0) {
        strengths.forEach(s => {
            const li = document.createElement('li');
            li.textContent = s;
            strengthsList.appendChild(li);
        });
    } else {
        const li = document.createElement('li');
        li.textContent = "Good effort!";
        strengthsList.appendChild(li);
    }

    // Populate Improvements
    const improvementsList = document.getElementById('improvementsList');
    improvementsList.innerHTML = '';
    const improvements = result.improvements || [];
    if (improvements.length > 0) {
        improvements.forEach(i => {
            const li = document.createElement('li');
            li.textContent = i;
            improvementsList.appendChild(li);
        });
    } else {
        const li = document.createElement('li');
        li.textContent = "Keep practicing!";
        improvementsList.appendChild(li);
    }

    document.getElementById('results').style.display = 'flex';

    // Animate Score
    animateScore('score', 0, score, 1500); // 1.5s duration
}

function animateScore(id, start, end, duration) {
    const obj = document.getElementById(id);
    const range = end - start;
    let startTime;

    const step = (timestamp) => {
        if (!startTime) startTime = timestamp;
        const progress = Math.min((timestamp - startTime) / duration, 1);

        // Ease out quart
        const ease = 1 - Math.pow(1 - progress, 4);

        obj.textContent = Math.floor(start + (range * ease));

        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            obj.textContent = end; // Ensure final value is exact
        }
    };

    window.requestAnimationFrame(step);
}

function closeResults() {
    document.getElementById('results').style.display = 'none';
}

function nextTopic() {
    loadTopic();
}

function resetRecordButton() {
    const btn = document.getElementById('recordBtn');
    const text = document.getElementById('recordText');

    btn.classList.remove('recording');
    btn.disabled = false;
    text.textContent = 'Start Speaking';
    isRecording = false;
    isProcessing = false;

    if (attemptCount >= MAX_ATTEMPTS) {
        text.textContent = 'Attempts Used';
        btn.disabled = true;
    }

    resetTimer();
}

function showLoading(show) {
    const topicEl = document.getElementById('topicText');
    if (show) {
        topicEl.textContent = 'Loading topic...';
        topicEl.style.opacity = '0.5';
    } else {
        topicEl.style.opacity = '1';
    }
}

function showNotification(message, type = 'info') {
    console.log(`[${type.toUpperCase()}]`, message);
    alert(message);
}

function updateProgressUI() {
    const pill = document.getElementById('progress-pill');
    if (pill) {
        pill.style.display = 'block';
        pill.textContent = `${questionCount}/${MAX_QUESTIONS}`;
    }
}

function goToNextModule() {
    const proceed = confirm('Fantastic! You completed Module C (Topic Speaking).\n\nReady for the final module - Grammar Quiz?');
    if (proceed) {
        window.location.href = '/moduleD';
    }
}

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        // Clear local storage
        localStorage.removeItem('email');
        localStorage.removeItem('username');
        localStorage.removeItem('session_id');

        fetch('/logout', { method: 'POST', credentials: 'same-origin' })
            .then(() => window.location.href = '/login')
            .catch(() => window.location.href = '/login');
    }
}

window.addEventListener('beforeunload', (event) => {
    if (isRecording) {
        event.preventDefault();
        event.returnValue = 'Recording in progress';
        return event.returnValue;
    }
});

window.addEventListener('unload', () => {
    if (recognition) {
        recognition.stop();
    }
    stopTimer();
});
