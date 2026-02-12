import random
import os
from dotenv import load_dotenv
from llm_utils import evaluate_speaking_response

load_dotenv()

topics = [
    "The importance of renewable energy in today's world",
    "How technology is revolutionizing modern education",
    "The role of artificial intelligence in healthcare",
    "Your favorite hobby and why it brings you joy",
    "The impact of social media on modern society",
    "How to maintain a healthy lifestyle in busy times",
    "The importance of effective time management",
    "The benefits of reading books in the digital age",
    "Climate change and its global effects",
    "Your dream vacation destination and why"
]

def run_moduleC(transcribed_text, topic_id=None):
    """Process text for Module C - Topic Speaking"""
    try:
        topic = "General Topic"
        if topic_id is not None:
             try:
                 topic_id = int(topic_id)
                 if 0 <= topic_id < len(topics):
                     topic = topics[topic_id]
             except:
                 pass
        
        user_text = transcribed_text.strip()

        # Use shared LLM utility
        evaluation = evaluate_speaking_response(user_text, topic, mode="topic")

        if "error" in evaluation and "gemini" in str(evaluation.get("error", "")).lower():
             # Fallback if AI fails? Or just return the error
             pass

        return {
            "success": True,
            "topic": topic,
            "transcription": user_text,
            "score": evaluation.get("total_score", 0),
            "relevance_score": evaluation.get("relevance_score", 0),
            "grammar_score": evaluation.get("grammar_score", 0),
            "vocabulary_score": evaluation.get("vocabulary_score", 0),
            "coherence_score": evaluation.get("coherence_score", 0),
            "feedback": evaluation.get("feedback", "No feedback available."),
            "strengths": evaluation.get("strengths", []),
            "improvements": evaluation.get("improvements", [])
        }

    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }
