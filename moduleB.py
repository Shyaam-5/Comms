import random
from jiwer import wer
import asyncio
import edge_tts
import os

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
    "The internet has revolutionized communication and information sharing."
]

def generate_audio_for_sentence(sentence_id, output_folder='static/audio'):
    """Generate TTS audio for a sentence using Edge TTS
    
    Args:
        sentence_id: Index of the sentence
        output_folder: Folder to save audio files
        
    Returns:
        Path to the generated audio file (relative to static folder)
    """
    try:
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)

        if sentence_id < 0 or sentence_id >= len(sentences):
             return None

        sentence = sentences[sentence_id]
        filename = f"sentence_{sentence_id}.mp3"
        filepath = os.path.join(output_folder, filename)

        # Check if audio already exists
        if os.path.exists(filepath):
            return f"/static/audio/{filename}"

        # Generate TTS audio using Edge TTS
        # Voice: en-GB-SoniaNeural (British Female) 
        voice = "en-GB-SoniaNeural"
        
        async def _save_audio():
            communicate = edge_tts.Communicate(sentence, voice)
            await communicate.save(filepath)
            
        asyncio.run(_save_audio())

        return f"/static/audio/{filename}"

    except Exception as e:
        print(f"Error generating audio: {str(e)}")
        return None

def run_moduleB(transcribed_text, sentence_id, duration=0):
    """Process text for Module B - Listen & Repeat"""
    try:
        if sentence_id < 0 or sentence_id >= len(sentences):
            return {
                "error": "Invalid sentence_id",
                "success": False
            }

        expected_sentence = sentences[sentence_id]
        user_text = transcribed_text.strip() or ""
        
        # Calculate WPS for metrics
        words = len(user_text.split())
        wps = words / max(duration, 1e-6)

        # LLM Evaluation
        from llm_utils import evaluate_speaking_response
        metrics = {"wps": wps, "duration": duration}
        evaluation = evaluate_speaking_response(user_text, expected_sentence, mode="repetition", metrics=metrics)
        
        # Use LLM scoring
        total_score = evaluation.get("total_score", 0)
        feedback = evaluation.get("feedback", "Keep practicing!")

        return {
            "success": True,
            "score": total_score,
            "expected": expected_sentence,
            "transcription": user_text,
            "feedback": feedback,
            "sentence_id": sentence_id,
            "strengths": evaluation.get("strengths", []),
            "improvements": evaluation.get("improvements", [])
        }

    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }
