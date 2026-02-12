// static/moduleB.js - Web Speech API Implementation

const MAX_QUESTIONS = 5;
const MAX_ATTEMPTS = 2; // Limit listening to 2 times
const COUNTDOWN_DURATION = 4;

let questionCount = 0;
let currentSentenceId = null;
let currentSentence = '';
let currentAudioUrl = null;
let recognition = null;
let isRecording = false;
let hasPlayedAudio = false;
let countdownTimer = null;
let recordingTimer = null;
let recordingStartTime = null;
let attemptCount = 0;
let isLoading = false;
let isProcessing = false;

document.addEventListener('DOMContentLoaded', () => {
    loadSentence();
    checkMicrophonePermission();
    initSpeechRecognition();
});

function getCredentials() {
    const email = localStorage.getItem('email');
    const sessionId = localStorage.getItem('session_id');
    if (!email) {
        window.location.href = '/login';
        return null;
    }
    return { email, sessionId };
}

function initSpeechRecognition() {
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = function () {
            isRecording = true;
            recordingStartTime = Date.now();
            document.getElementById('waveformContainer').style.display = 'block';
            updateRecordingTime();
            console.log('Voice recognition started');
        };

        recognition.onerror = function (event) {
            console.error('Speech recognition error', event.error);
            isRecording = false;
            stopRecordingUI();
            showNotification('Error: ' + event.error, 'error');
        };

        recognition.onend = function () {
            isRecording = false;
            stopRecordingUI();
            console.log('Voice recognition ended');
        };

        recognition.onresult = function (event) {
            const transcript = event.results[0][0].transcript;
            const confidence = event.results[0][0].confidence;
            console.log('Transcript:', transcript);

            // Calculate duration
            const duration = (Date.now() - recordingStartTime) / 1000;

            submitText(transcript, duration);
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
        console.log('Permission API not supported or denied');
    }
}

async function loadSentence() {
    if (isLoading) return; // Prevent concurrent loads
    if (questionCount >= MAX_QUESTIONS) {
        goToNextModule();
        return;
    }

    const creds = getCredentials();
    if (!creds) return;

    try {
        isLoading = true;
        showLoading(true);
        // Explicitly disable button while loading
        const btn = document.getElementById('playBtn');
        const txt = document.getElementById('playText');
        if (btn) btn.disabled = true;
        if (txt) txt.textContent = 'Loading...';


        const response = await fetch(`/api/moduleB/sentence?email=${encodeURIComponent(creds.email)}&session_id=${encodeURIComponent(creds.sessionId || '')}`, {
            method: 'GET',
            credentials: 'same-origin'
        });

        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        const data = await response.json();

        if (data.success) {
            currentSentenceId = data.sentence_id;
            currentSentence = data.sentence;
            currentAudioUrl = data.audio_url || null;
            hasPlayedAudio = false;

            questionCount++;
            attemptCount = 0;
            updateProgressUI();

            closeResults();
            resetUI();
        } else {
            showNotification('Failed to load sentence: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Load sentence error:', error);
        showNotification('Network error. Please check your connection.', 'error');
    } finally {
        showLoading(false);
        isLoading = false;
    }
}

async function playAudio() {
    try {
        const btn = document.getElementById('playBtn');
        const text = document.getElementById('playText');

        if (btn.disabled) return;


        btn.disabled = true;
        text.textContent = 'Playing...';
        btn.classList.add('loading'); // Show spinner

        if (currentAudioUrl) {
            // Use server-generated audio (high quality)
            const audio = new Audio(currentAudioUrl);

            // Wait for audio to be ready to play before removing spinner? 
            // Audio.play() is a promise.

            audio.onended = () => {
                hasPlayedAudio = true;
                text.textContent = 'Play Again';
                btn.disabled = false;
                btn.classList.remove('loading');

                // Show record section after audio finishes
                document.getElementById('recordButtonWrapper').style.display = 'flex';
                document.getElementById('tipText').style.display = 'none';
            };

            audio.onerror = (e) => {
                console.error("Audio playback error", e);
                // Fallback to synthesis
                btn.classList.remove('loading');
                playSynthesis(btn, text);
            };

            await audio.play();
            btn.classList.remove('loading'); // Audio started playing
        } else {
            // Fallback
            btn.classList.remove('loading');
            playSynthesis(btn, text);
        }

    } catch (error) {
        console.error('Play audio error:', error);
        showNotification('Could not play audio', 'error');
        document.getElementById('playText').textContent = 'Start Listening';
        document.getElementById('playBtn').disabled = false;
    }
}

function playSynthesis(btn, text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel(); // Clear any previous speech

        const utterance = new SpeechSynthesisUtterance(currentSentence);
        utterance.rate = 0.85;
        utterance.pitch = 1;
        utterance.volume = 1;
        utterance.lang = 'en-US';

        utterance.onend = () => {
            hasPlayedAudio = true;
            text.textContent = 'Play Again';
            btn.disabled = false;

            // Show record section after audio finishes
            document.getElementById('recordButtonWrapper').style.display = 'flex';
            document.getElementById('tipText').style.display = 'none';
        };

        utterance.onerror = (event) => {
            console.error('Speech synthesis error:', event);
            showNotification('Audio playback failed. Please try again.', 'error');
            btn.disabled = false;
            text.textContent = 'Start Listening';
        };

        window.speechSynthesis.speak(utterance);

    } else {
        showNotification('Text-to-speech not supported in this browser', 'error');
        btn.disabled = false;
    }
}

async function toggleRecording() {
    if (!hasPlayedAudio) {
        showNotification('Please listen to the audio first', 'error');
        return;
    }

    if (attemptCount >= MAX_ATTEMPTS) {
        showNotification('Maximum attempts reached for this sentence.', 'warning');
        return;
    }

    if (!isRecording) {
        await startCountdown();
    } else {
        stopRecording();
    }
}

async function startCountdown() {
    // Hide button, show countdown
    document.getElementById('recordButtonWrapper').style.display = 'none';
    document.getElementById('countdownDisplay').style.display = 'block';

    let timeLeft = COUNTDOWN_DURATION;
    document.getElementById('countdownNumber').textContent = timeLeft;

    countdownTimer = setInterval(() => {
        timeLeft--;
        if (timeLeft > 0) {
            document.getElementById('countdownNumber').textContent = timeLeft;
        } else {
            clearInterval(countdownTimer);
            document.getElementById('countdownDisplay').style.display = 'none';
            startRecording();
        }
    }, 1000);
}

function startRecording() {
    if (recognition) {
        try {
            recognition.start();
            attemptCount++;
        } catch (e) {
            console.error("Recognition start error:", e);
        }
    }
}

function updateRecordingTime() {
    if (!isRecording) return;

    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    document.getElementById('recordingTime').textContent =
        `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

    recordingTimer = setTimeout(updateRecordingTime, 1000);
}

function stopRecording() {
    if (recognition && isRecording) {
        recognition.stop();
    }
}

function stopRecordingUI() {
    if (recordingTimer) {
        clearTimeout(recordingTimer);
        recordingTimer = null;
    }

    // Hide waveform, show processing
    document.getElementById('waveformContainer').style.display = 'none';
    document.getElementById('recordButtonWrapper').style.display = 'flex';

    const btn = document.getElementById('recordBtn');
    const text = document.getElementById('recordText');
    text.textContent = 'Processing...';
    btn.disabled = true;
}

async function submitText(text, duration) {
    if (isProcessing) return; // Prevent concurrent submissions

    const creds = getCredentials();
    if (!creds) return;

    try {
        isProcessing = true;
        const response = await fetch('/api/moduleB', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: creds.email,
                session_id: creds.sessionId,
                sentence_id: currentSentenceId,
                transcribed_text: text,
                duration: duration
            }),
            credentials: 'same-origin'
        });

        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        const result = await response.json();

        if (result.success) {
            // Ensure transcription is available for display
            if (!result.transcription && !result.transcribed_text) {
                result.transcription = text;
            }
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
    const score = Math.round(result.score || result.pronunciation_score || 0);
    document.getElementById('score').textContent = score;

    // Populate card content
    document.getElementById('expectedSentence').textContent = result.expected || result.target_sentence || "Hidden";
    document.getElementById('transcription').textContent = result.transcription || result.transcribed_text || "";

    // Populate General Feedback
    document.getElementById('feedback').textContent = result.feedback || 'No detailed feedback available.';

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
// Auto-close results and load next question after 5 seconds
// Removed auto-advance logic to allow manual navigation
// setTimeout(() => {
//     closeResults();
//     nextSentence();
// }, 5000);

function closeResults() {
    document.getElementById('results').style.display = 'none';
}

function nextSentence() {
    loadSentence();
}

function resetPlayButton() {
    const btn = document.getElementById('playBtn');
    const text = document.getElementById('playText');
    btn.disabled = false;
    text.textContent = 'Start Listening'; // Reset text when ready

}

function resetRecordButton() {
    const btn = document.getElementById('recordBtn');
    const text = document.getElementById('recordText');

    btn.disabled = false;
    text.textContent = 'Start Speaking';
    isRecording = false;
    isProcessing = false;

    if (attemptCount >= MAX_ATTEMPTS) {
        text.textContent = 'Attempts Used';
        btn.disabled = true;
    }
}

function resetUI() {
    // Reset all UI elements to initial state
    document.getElementById('playButtonWrapper').style.display = 'flex';
    document.getElementById('recordButtonWrapper').style.display = 'none';
    document.getElementById('countdownDisplay').style.display = 'none';
    document.getElementById('waveformContainer').style.display = 'none';
    document.getElementById('tipText').style.display = 'block';

    resetPlayButton();
    resetRecordButton();

    // Clear timers
    if (countdownTimer) {
        clearInterval(countdownTimer);
        countdownTimer = null;
    }
    if (recordingTimer) {
        clearTimeout(recordingTimer);
        recordingTimer = null;
    }
}

function showLoading(show) {
    // Optional loading state
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
    const proceed = confirm('Excellent! You completed Module B (Listen & Repeat).\n\nReady for Module C (Topic Speaking)?');
    if (proceed) {
        window.location.href = '/moduleC';
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
    if (countdownTimer) clearInterval(countdownTimer);
    if (recordingTimer) clearTimeout(recordingTimer);
});
