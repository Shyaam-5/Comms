import random
from typing import List, Dict, Optional, Union

# Extended question bank - Focused on Tenses, Prepositions, Articles, Adverbs
questions_bank = [
    # Tenses - Past Simple
    {"sentence": "I ___ (go) to the cinema yesterday.", "answer": "went", "category": "tenses_past_simple"},
    {"sentence": "She ___ (see) him at the park last week.", "answer": "saw", "category": "tenses_past_simple"},
    {"sentence": "They ___ (buy) a new house two years ago.", "answer": "bought", "category": "tenses_past_simple"},
    
    # Tenses - Present Continuous
    {"sentence": "Look! It ___ (rain) outside right now.", "answer": "is raining", "category": "tenses_present_continuous"},
    {"sentence": "We ___ (listen) to music at the moment.", "answer": "are listening", "category": "tenses_present_continuous"},
    
    # Tenses - Past Continuous
    {"sentence": "I ___ (sleep) when you called me.", "answer": "was sleeping", "category": "tenses_past_continuous"},
    {"sentence": "They ___ (play) football when the rain started.", "answer": "were playing", "category": "tenses_past_continuous"},
    
    # Prepositions - Time/Place
    {"sentence": "We have a meeting ___ Monday morning.", "answer": "on", "category": "prepositions_time"},
    {"sentence": "My birthday is ___ July.", "answer": "in", "category": "prepositions_time"},
    {"sentence": "The keys are ___ the table (surface).", "answer": "on", "category": "prepositions_place"},
    {"sentence": "I will meet you ___ the bus stop.", "answer": "at", "category": "prepositions_place"},
    
    # Articles
    {"sentence": "I saw ___ elephant at the zoo.", "answer": "an", "category": "articles"},
    {"sentence": "Can you pass me ___ salt, please? (Specific item)", "answer": "the", "category": "articles"},
    {"sentence": "He is ___ honest man.", "answer": "an", "category": "articles"},
    {"sentence": "She wants to buy ___ new car (general).", "answer": "a", "category": "articles"},
    
    # Adverbs
    {"sentence": "He runs very ___ (quick).", "answer": "quickly", "category": "adverbs"},
    {"sentence": "Please speak ___ (soft) in the library.", "answer": "softly", "category": "adverbs"},
    {"sentence": "She sings ___ (beautiful).", "answer": "beautifully", "category": "adverbs"},
    {"sentence": "They played ___ (happy) together.", "answer": "happily", "category": "adverbs"},
    
    # Tenses - Present Perfect
    {"sentence": "I ___ (read) that book already.", "answer": "have read", "category": "tenses_present_perfect"},
    {"sentence": "She ___ (live) here for ten years.", "answer": "has lived", "category": "tenses_present_perfect"},
    
    # Prepositions - Movement
    {"sentence": "He walked ___ the room (enter).", "answer": "into", "category": "prepositions_movement"},
    {"sentence": "The cat jumped ___ the wall.", "answer": "over", "category": "prepositions_movement"}
]

def get_quiz(num_questions: int = 5, excluded_indices: List[int] = None) -> Dict:
    """Generate a new quiz with specified number of questions, excluding completed ones"""
    
    try:
        if excluded_indices is None:
            excluded_indices = []
            
        # Filter available indices
        available_indices = [i for i in range(len(questions_bank)) if i not in excluded_indices]
        
        # If run out of questions, reset (use all indices) or handle gracefullly. 
        # For now, if fewer than required, take what's left or reset if empty.
        if not available_indices:
             available_indices = list(range(len(questions_bank)))
        
        # Sample directly from available indices
        selected_indices = random.sample(available_indices, min(num_questions, len(available_indices)))

        quiz_questions = []
        for i, idx in enumerate(selected_indices):
            question = questions_bank[idx]
            quiz_questions.append({
                "id": idx, # This corresponds to the index in questions_bank
                "sentence": question["sentence"],
                "category": question["category"],
                "number": i + 1
            })

        return {
            "success": True,
            "questions": quiz_questions,
            "total_questions": len(quiz_questions),
            "quiz_id": f"quiz_{random.randint(1000, 9999)}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate quiz: {str(e)}"
        }

def submit_answers(submissions: List[Dict]) -> Dict:
    """
    Evaluate submitted quiz answers.
    Expects submissions to be a list of dicts: [{'id': bank_index, 'answer': user_answer}, ...]
    """
    try:
        score = 0
        results = []

        for i, sub in enumerate(submissions):
            idx = int(sub.get('id', -1))
            user_answer = sub.get('answer', "").strip().lower()
            
            if 0 <= idx < len(questions_bank):
                question = questions_bank[idx]
                correct_answer = question["answer"].lower()
                is_correct = (user_answer == correct_answer)
                
                if is_correct:
                    score += 1
                
                results.append({
                    "question_number": i + 1, # Display number
                    "question_id": idx, # Bank ID
                    "sentence": question["sentence"],
                    "user_answer": user_answer or "(no answer)",
                    "correct_answer": question["answer"],
                    "correct": is_correct
                })
            else:
                 results.append({
                    "question_number": i + 1,
                    "question_id": idx,
                    "sentence": "Unknown Question",
                    "user_answer": user_answer,
                    "correct_answer": "N/A",
                    "correct": False
                })

        total_questions = len(submissions)
        percentage = (score / total_questions) * 100 if total_questions > 0 else 0

        return {
            "success": True,
            "score": score,
            "correct_count": score,
            "total": total_questions,
            "percentage": round(percentage, 1),
            "review": results
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to evaluate answers: {str(e)}"
        }
