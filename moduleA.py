import random
from jiwer import wer
from dotenv import load_dotenv
import os

load_dotenv()

sentences = [
    "The sun rises in the east and sets in the west.",
    "Python is a powerful programming language used worldwide.",
    "Artificial intelligence is transforming the future of technology.",
    "Reading books expands knowledge and sharpens the mind.",
    "A balanced diet is essential for a healthy lifestyle.",
    "The quick brown fox jumps over the lazy dog.",
    "Water is the most essential resource for all living beings.",
    "Cloud computing allows data to be stored and accessed online.",
    "The earth revolves around the sun in an elliptical orbit.",
    "Machine learning enables computers to learn from data.",
    "Listening to music can reduce stress and improve mood.",
    "Teamwork is the key to achieving great success.",
    "Renewable energy sources are vital for a sustainable future.",
    "The internet has revolutionized communication and information sharing.",
    "Practice makes perfect, so never stop learning new things."
]

def run_moduleA(transcribed_text, duration, sentence_id):
    try:
        # Choose and remember the exact sentence and an id
        if sentence_id is None or sentence_id < 0 or sentence_id >= len(sentences):
             target_sentence = sentences[0] # Default fallback
        else:
             target_sentence = sentences[sentence_id]
             
        print(f"Target sentence[{sentence_id}]: {target_sentence}")
        print(f"Transcribed: {transcribed_text}")

        # Pronunciation score via WER
        # Calculate metrics first for LLM context
        words = len(transcribed_text.split())
        wps = words / max(duration, 1e-6)
        
        # Simple fluency calc (legacy/backup)
        if wps < 1:
            fluency_score = wps * 50
        elif 1 <= wps <= 3:
            fluency_score = 80 + ((wps - 1) / 2 * 20)
        else:
            fluency_score = max(0, 100 - (wps - 3) * 20)
        fluency_score = min(100, fluency_score)

        # LLM Evaluation
        from llm_utils import evaluate_speaking_response
        metrics = {"wps": wps, "duration": duration, "fluency_score": fluency_score}
        evaluation = evaluate_speaking_response(transcribed_text, target_sentence, mode="repetition", metrics=metrics)

        # Use LLM scores
        pronunciation_score = evaluation.get("total_score", 0) # Use total score as primary
        feedback = evaluation.get("feedback", "Good effort!")
        
        # Update scores from detailed evaluation if available
        if "fluency_score" in evaluation:
             fluency_score = evaluation["fluency_score"] * 3.33 # Convert 30 scale to 100 scale roughly, or just use it raw? 
             # Actually, simpler to keep fluency_score as the 0-100 detailed metric if we want, OR just trust the total.
             # But the frontend might expect 0-100.
             # The new prompt gives fluency_score out of 30.
             # Let's upscale it for consistent database storage if needed, or just store legacycalc.
             # Ideally, we rely on the implementation plan which said "use LLM scoring".
             # Let's keep the legacy 0-100 calc for the database 'fluency_score' field to avoid breaking report graphs,
             # but use the LLM score for immediate feedback display if we had a dedicated UI for it.
             pass

        result = {
            "sentence_id": sentence_id,
            "target_sentence": target_sentence,
            "transcribed_text": transcribed_text,
            "pronunciation_score": pronunciation_score,
            "fluency_score": fluency_score, 
            "duration_sec": duration,
            "wps": wps,
            "feedback": feedback,
            "strengths": evaluation.get("strengths", []),
            "improvements": evaluation.get("improvements", [])
        }
        
        print(f"Final result: {result}")
        return result

    except Exception as e:
        print(f"ERROR in run_moduleA: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "sentence_id": sentence_id,
            "target_sentence": "Error occurred",
            "transcribed_text": "Processing failed",
            "pronunciation_score": 0,
            "fluency_score": 0,
            "feedback": f"Error: {str(e)}"
        }
