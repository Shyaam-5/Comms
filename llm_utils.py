import os
import json
import re
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini Client once
gemini_client = None
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    try:
        gemini_client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"Error initializing Gemini client: {e}")

def clean_json_response(text):
    """Refined JSON cleanup to handle potential markdown formatting."""
    text = text.strip()
    # Remove markdown code blocks if present
    text = re.sub(r'^```json\s*|\s*```$', '', text, flags=re.MULTILINE)
    return text

def evaluate_speaking_response(user_text, context_text, mode="topic", metrics=None):
    """
    Evaluates a user's spoken response using Gemini.
    
    Args:
        user_text (str): The transcribed text from the user.
        context_text (str): The context (e.g., the topic or the target sentence).
        mode (str): 'topic' for Module C, 'repetition' for Modules A/B.
        
    Returns:
        dict: A dictionary containing scores and feedback.
    """
    if not gemini_client:
        return {
            "error": "Gemini API key not configured",
            "feedback": "AI evaluation unavailable.",
            "total_score": 0
        }

    if mode == "topic":
        prompt = f"""You are an English language evaluator. Evaluate the following spoken response on the topic: "{context_text}"

User's transcribed response: "{user_text}"

Evaluate based on:
1. Relevance to the topic (0-25 points)
2. Grammar and sentence structure (0-25 points)
3. Vocabulary richness (0-25 points)
4. Coherence and organization (0-25 points)

Provide your evaluation in the following JSON format:
{{
    "relevance_score": <0-25>,
    "grammar_score": <0-25>,
    "vocabulary_score": <0-25>,
    "coherence_score": <0-25>,
    "total_score": <0-100>,
    "feedback": "<detailed constructive feedback, addressing specific errors or praising specific strengths>",
    "strengths": ["<strength1>", "<strength2>"],
    "improvements": ["<improvement1>", "<improvement2>"]
}}

Only respond with valid JSON, no additional text."""

    elif mode == "repetition":
        metrics_info = ""
        if metrics and "wps" in metrics:
            wps = metrics.get('wps', 0)
            duration = metrics.get('duration', 0)
            metrics_info = f"\nUser Performance Metrics:\n- Speaking Rate: {wps:.2f} words/second\n- Duration: {duration:.2f} seconds\n(Normal conversational pace is ~2-5 wps)\n"

        prompt = f"""You are an English pronunciation and reading assistant. The user was asked to read/repeat the specific sentence: "{context_text}"

User's transcribed response: "{user_text}"
{metrics_info}
Instructions:
1. Ignore differences in capitalization and punctuation. "hello" is equal to "Hello".
2. Compare the user's response to the target sentence.

Evaluate based on:
1. Accuracy: Did they say the correct words? (0-40 points). Deduct only for missing/wrong words.
2. Clarity/Pronunciation: Is the transcription close to the target? (0-30 points).
3. Fluency/Pacing: Based on the provided metrics (if any) or text length. Is the speech rate natural? (0-30 points). 
   - If User Performance Metrics are provided, use them. < 1.5 wps is slow, > 4 wps is fast.
   - If no metrics, base it on the text quality.

Provide your evaluation in the following JSON format:
{{
    "accuracy_score": <0-40>,
    "pronunciation_score": <0-30>,
    "fluency_score": <0-30>,
    "total_score": <0-100>,
    "feedback": "<constructive feedback. Mention fluency/speed if relevant. Ignore capitalization issues. Be encouraging.>",
    "strengths": ["<strength1>", "<strength2>"],
    "improvements": ["<improvement1>", "<improvement2>"]
}}

Only respond with valid JSON, no additional text."""
    
    else:
        return {"error": "Invalid mode"}

    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        
        cleaned_json = clean_json_response(response.text)
        evaluation = json.loads(cleaned_json)
        return evaluation

    except Exception as e:
        print(f"Gemini evaluation error: {e}")
        return {
            "error": str(e),
            "feedback": "Could not generate AI feedback at this time.",
            "total_score": 0
        }
