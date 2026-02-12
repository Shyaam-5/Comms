from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, flash
import os
import random
import uuid
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

# Import module functions
from moduleA import run_moduleA, sentences as moduleA_sentences
from moduleB import run_moduleB, sentences as moduleB_sentences, generate_audio_for_sentence
from moduleC import run_moduleC, topics
from moduleD import get_quiz, submit_answers

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'temp_audio'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me-in-production')

# Create temp directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# ===== DATABASE FUNCTIONS =====

def get_db_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# ===== USER MANAGEMENT FUNCTIONS =====

def create_user(email, username, password):
    """Create a new user account"""
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (email, username, password_hash) VALUES (%s, %s, %s)",
                    (email.lower().strip(), username.strip(), generate_password_hash(password)))
        conn.commit()
        cur.close()
        return True, None
    except psycopg2.IntegrityError:
        conn.rollback()
        return False, "Email already registered"
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def verify_user(email, password):
    """Verify user credentials"""
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, email, username, password_hash FROM users WHERE email = %s", 
                   (email.lower().strip(),))
        row = cur.fetchone()
        
        if not row:
            return False, "Invalid credentials"
        if not check_password_hash(row["password_hash"], password):
            return False, "Invalid credentials"
            
        user_data = {"id": row["id"], "email": row["email"], "username": row["username"]}
        cur.close()
        return True, user_data
    except Exception as e:
        print(f"Verify user error: {e}")
        return False, str(e)
    finally:
        conn.close()

def get_user_by_email(email):
    """Get user details by email"""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, email, username FROM users WHERE email = %s", 
                   (email.lower().strip(),))
        row = cur.fetchone()
        cur.close()
        return row
    except Exception as e:
        print(f"Get user error: {e}")
        return None
    finally:
        conn.close()


# ===== PERFORMANCE TRACKING FUNCTIONS =====

def save_performance(user_id, session_id, module, question_number, score, max_score):
    """Save performance data for a question"""
    conn = get_db_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_performance (user_id, session_id, module, question_number, score, max_score)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, session_id, module, question_number, score, max_score))
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"Error saving performance: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_completed_questions(user_id, module_name):
    """Get list of question numbers already completed by user for a specific module"""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT question_number FROM user_performance
            WHERE user_id = %s AND module = %s
        """, (user_id, module_name))
        rows = cur.fetchall()
        cur.close()
        return [row[0] for row in rows]
    except Exception as e:
        print(f"Error getting completed questions: {e}")
        return []
    finally:
        conn.close()


def get_session_report(user_id, session_id):
    """Generate comprehensive performance report"""
    conn = get_db_connection()
    if not conn:
        return {'modules': [], 'overall_score': 0, 'total_questions': 0}
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get all performance data for this session grouped by module
        cur.execute("""
            SELECT module, AVG(score) as avg_score, AVG(max_score) as max_score, COUNT(*) as attempts
            FROM user_performance
            WHERE user_id = %s AND session_id = %s
            GROUP BY module
            ORDER BY module
        """, (user_id, session_id))
        
        results = cur.fetchall()
        cur.close()
        
        report = {
            'modules': [],
            'overall_score': 0,
            'total_questions': 0
        }
        
        total_percentage = 0
        module_count = 0
        
        for row in results:
            percentage = round((row['avg_score'] / row['max_score'] * 100) if row['max_score'] > 0 else 0, 1)
            module_data = {
                'name': row['module'],
                'average_score': round(row['avg_score'], 2),
                'max_score': round(row['max_score'], 2),
                'percentage': percentage,
                'questions_completed': row['attempts']
            }
            report['modules'].append(module_data)
            total_percentage += percentage
            module_count += 1
            report['total_questions'] += row['attempts']
        
        report['overall_score'] = round(total_percentage / module_count if module_count > 0 else 0, 1)
        
        return report
        
    except Exception as e:
        print(f"Error generating report: {e}")
        return {'modules': [], 'overall_score': 0, 'total_questions': 0}
    finally:
        conn.close()


# ===== AUTHENTICATION DECORATOR REMOVED =====
# Client side now handles auth check via localStorage and API validation

# ===== AUTHENTICATION ROUTES =====

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user signup"""
    if request.method == 'GET':
        return render_template('signup.html')
    
    data = request.get_json(silent=True) or request.form
    email = (data.get('email') or '').strip()
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    
    if not email or not username or not password:
        msg = 'All fields are required'
        if request.is_json:
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('signup'))

    ok, err = create_user(email, username, password)
    if not ok:
        if request.is_json:
            return jsonify({'success': False, 'error': err}), 400
        flash(err, 'error')
        return redirect(url_for('signup'))

    if request.is_json:
        return jsonify({'success': True, 'message': 'Signup successful'})
    flash('Signup successful. Please log in.', 'success')
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'GET':
        return render_template('login.html')
    
    data = request.get_json(silent=True) or request.form
    email = (data.get('email') or '').strip()
    password = (data.get('password') or '').strip()
    
    if not email or not password:
        msg = 'Email and password are required'
        if request.is_json:
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('login'))

    ok, user = verify_user(email, password)
    if not ok:
        if request.is_json:
            return jsonify({'success': False, 'error': user}), 401
        flash(user, 'error')
        return redirect(url_for('login'))

    # Generate a new session ID for this login
    new_session_id = str(uuid.uuid4())
    
    # Return user data and session_id to client
    response_data = {
        'success': True,
        'message': 'Login successful',
        'email': user['email'],
        'username': user['username'],
        'session_id': new_session_id
    }
    
    if request.is_json:
        return jsonify(response_data)
        
    # For form submission, render index with data embedded or just redirect
    # Since we need to store data in localStorage, we can't just redirect.
    # We'll render a template that sets localStorage and redirects.
    return render_template('login_success.html', user_data=response_data)


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    """Handle user logout"""
    # Client side clears local storage
    if request.is_json or request.method == 'POST':
        return jsonify({'success': True, 'message': 'Logged out'})
    return redirect(url_for('login'))


# ===== PAGE ROUTES =====

@app.route('/')
def index():
    """Module A - Read & Speak landing page"""
    return render_template('index.html')


@app.route('/moduleB')
def moduleB_page():
    """Module B - Listen & Repeat landing page"""
    return render_template('moduleB.html')


@app.route('/moduleC')
def moduleC_page():
    """Module C - Topic Speaking landing page"""
    return render_template('moduleC.html')


@app.route('/moduleD')
def moduleD_page():
    """Module D - Grammar Quiz landing page"""
    return render_template('moduleD.html')


@app.route('/report')
def performance_report():
    """Performance report page"""
    return render_template('report.html')


@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)


# ===== API ENDPOINTS - GET CONTENT =====

@app.route('/api/moduleA/sentence', methods=['GET'])
def get_moduleA_sentence():
    """Get a random sentence for Module A - Read & Speak"""
    try:
        email = request.args.get('email')
        
        available_indices = list(range(len(moduleA_sentences)))
        
        if email:
            user = get_user_by_email(email)
            if user:
                completed = get_completed_questions(user['id'], 'Module A - Read & Speak')
                filtered = [i for i in available_indices if i not in completed]
                if filtered:
                    available_indices = filtered
        
        sentence_id = random.choice(available_indices)
        sentence = moduleA_sentences[sentence_id]
        return jsonify({
            'sentence_id': sentence_id,
            'sentence': sentence,
            'success': True
        })
    except Exception as e:
        print(f"Error in moduleA/sentence: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/moduleB/sentence', methods=['GET'])
def get_moduleB_sentence():
    """Get a random sentence for Module B - Listen & Repeat"""
    try:
        email = request.args.get('email')
        
        available_indices = list(range(len(moduleB_sentences)))
        
        if email:
            user = get_user_by_email(email)
            if user:
                completed = get_completed_questions(user['id'], 'Module B - Listen & Repeat')
                filtered = [i for i in available_indices if i not in completed]
                if filtered:
                    available_indices = filtered
                    
        sentence_id = random.choice(available_indices)
        sentence = moduleB_sentences[sentence_id]
        
        # Generate audio
        audio_url = generate_audio_for_sentence(sentence_id)
        
        return jsonify({
            'sentence_id': sentence_id,
            'sentence': sentence,
            'audio_url': audio_url,
            'success': True
        })
    except Exception as e:
        print(f"Error in moduleB/sentence: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/moduleC/topic', methods=['GET'])
def get_moduleC_topic():
    """Get a random topic for Module C - Topic Speaking"""
    try:
        email = request.args.get('email')
        
        available_indices = list(range(len(topics)))
        
        if email:
            user = get_user_by_email(email)
            if user:
                completed = get_completed_questions(user['id'], 'Module C - Topic Speaking')
                filtered = [i for i in available_indices if i not in completed]
                if filtered:
                    available_indices = filtered

        topic_id = random.choice(available_indices)
        topic = topics[topic_id]
        return jsonify({
            'topic_id': topic_id,
            'topic': topic,
            'success': True
        })
    except Exception as e:
        print(f"Error in moduleC/topic: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/moduleD/quiz', methods=['GET'])
def api_get_quiz():
    """Get a new quiz for Module D"""
    try:
        email = request.args.get('email')
        excluded_indices = []
        
        if email:
            user = get_user_by_email(email)
            if user:
                excluded_indices = get_completed_questions(user['id'], 'Module D - Grammar Quiz')
        
        quiz = get_quiz(num_questions=5, excluded_indices=excluded_indices)
        return jsonify(quiz)
    except Exception as e:
        print(f"Error in moduleD/quiz: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500


# ===== API ENDPOINTS - SUBMIT AUDIO/ANSWERS =====

@app.route('/api/moduleA', methods=['POST'])
def api_moduleA():
    """Process text for Module A - Read & Speak"""
    try:
        data = request.get_json()
        if not data:
             return jsonify({'error': 'Invalid request data', 'success': False}), 400

        email = data.get('email')
        session_id = data.get('session_id')
        sentence_id = data.get('sentence_id')
        transcribed_text = data.get('transcribed_text', '')
        duration = data.get('duration', 0)

        if not email:
            return jsonify({'error': 'Email is required', 'success': False}), 400
        
        user = get_user_by_email(email)
        if not user:
            return jsonify({'error': 'User not found', 'success': False}), 404
        
        user_id = user['id']

        # Call moduleA with text
        result = run_moduleA(transcribed_text, duration, sentence_id)

        # Save performance
        save_performance(
            user_id=user_id,
            session_id=session_id or 'unknown',
            module='Module A - Read & Speak',
            question_number=sentence_id,
            score=result.get('pronunciation_score', 0),
            max_score=100
        )

        if 'success' not in result:
            result['success'] = True

        return jsonify(result)

    except Exception as e:
        print(f"Error in moduleA: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/moduleB', methods=['POST'])
def api_moduleB():
    """Process text for Module B - Listen & Repeat"""
    try:
        data = request.get_json()
        if not data:
             return jsonify({'error': 'Invalid request data', 'success': False}), 400

        email = data.get('email')
        session_id = data.get('session_id')
        sentence_id = data.get('sentence_id')
        transcribed_text = data.get('transcribed_text', '')
        duration = data.get('duration', 0)

        if not email:
            return jsonify({'error': 'Email is required', 'success': False}), 400
            
        user = get_user_by_email(email)
        if not user:
            return jsonify({'error': 'User not found', 'success': False}), 404
            
        user_id = user['id']

        try:
            result = run_moduleB(transcribed_text, sentence_id, duration)
        except TypeError:
            # Fallback for legacy calls or if run_moduleB definition hasn't updated yet in memory (shouldn't happen with reloads but safe)
            result = run_moduleB(transcribed_text, sentence_id)

        save_performance(
            user_id=user_id,
            session_id=session_id or 'unknown',
            module='Module B - Listen & Repeat',
            question_number=sentence_id,
            score=result.get('pronunciation_score', result.get('score', 0)),
            max_score=100
        )

        if 'success' not in result:
            result['success'] = True

        return jsonify(result)

    except Exception as e:
        print(f"Error in moduleB: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/moduleC', methods=['POST'])
def api_moduleC():
    """Process text for Module C - Topic Speaking"""
    try:
        data = request.get_json()
        if not data:
             return jsonify({'error': 'Invalid request data', 'success': False}), 400

        email = data.get('email')
        session_id = data.get('session_id')
        topic_id = data.get('topic_id')
        transcribed_text = data.get('transcribed_text', '')

        if not email:
            return jsonify({'error': 'Email is required', 'success': False}), 400
            
        user = get_user_by_email(email)
        if not user:
            return jsonify({'error': 'User not found', 'success': False}), 404
            
        user_id = user['id']

        result = run_moduleC(transcribed_text, topic_id)
        result['topic_id'] = topic_id

        save_performance(
            user_id=user_id,
            session_id=session_id or 'unknown',
            module='Module C - Topic Speaking',
            question_number=topic_id,
            score=result.get('score', 0),
            max_score=100
        )

        if 'success' not in result:
            result['success'] = True

        return jsonify(result)

    except Exception as e:
        print(f"Error in moduleC: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/moduleD/submit', methods=['POST'])
def api_submit_quiz():
    """Submit quiz answers for Module D"""
    try:
        data = request.get_json()
        if not data or 'answers' not in data:
            return jsonify({'error': 'Invalid request data', 'success': False}), 400

        email = data.get('email')
        session_id = data.get('session_id')
        
        if not email:
            return jsonify({'error': 'Email is required', 'success': False}), 400
            
        user = get_user_by_email(email)
        if not user:
            return jsonify({'error': 'User not found', 'success': False}), 404
            
        user_id = user['id']

        # answers should be a list of {id:..., answer:...}
        result = submit_answers(data['answers'])

        if result.get('review'):
            for item in result['review']:
                save_performance(
                    user_id=user_id,
                    session_id=session_id or 'unknown',
                    module='Module D - Grammar Quiz',
                    question_number=item.get('question_id', 0), # Use bank ID which is question_id
                    score=100 if item.get('correct') else 0,
                    max_score=100
                )

        if 'success' not in result:
            result['success'] = True

        return jsonify(result)

    except Exception as e:
        print(f"Error in moduleD/submit: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/report', methods=['GET'])
def api_report():
    """Get performance report"""
    email = request.args.get('email')
    session_id = request.args.get('session_id')
    
    if not email:
        return jsonify({'error': 'Email required'}), 400
        
    user = get_user_by_email(email)
    if not user:
         return jsonify({'error': 'User not found'}), 404
         
    report = get_session_report(user['id'], session_id or 'unknown')
    return jsonify(report)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
