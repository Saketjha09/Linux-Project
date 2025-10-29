from flask import Flask, render_template, request, make_response, g, jsonify, redirect, url_for
from redis import Redis
import os
import socket
import random
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from auth import hash_password, verify_password, create_jwt_token, verify_jwt_token, login_required, admin_required, get_current_user, get_auth_token_from_request, AuthError

option_a = os.getenv('OPTION_A', "Cats")
option_b = os.getenv('OPTION_B', "Dogs")
hostname = socket.gethostname()

# Redis Configuration from environment
redis_host = os.getenv('REDIS_HOST', 'redis')
redis_port = int(os.getenv('REDIS_PORT', 6379))

# Database Configuration from environment
db_host = os.getenv('DB_HOST', 'db')
db_port = int(os.getenv('DB_PORT', 5432))
db_name = os.getenv('DB_NAME', 'postgres')
db_user = os.getenv('POSTGRES_USER', 'postgres')
db_password = os.getenv('POSTGRES_PASSWORD', 'postgres')
db_connection_string = f"dbname={db_name} user={db_user} password={db_password} host={db_host} port={db_port}"

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

gunicorn_error_logger = logging.getLogger('gunicorn.error')
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.INFO)

def get_redis():
    if not hasattr(g, 'redis'):
        g.redis = Redis(host=redis_host, port=redis_port, db=0, socket_timeout=5)
    return g.redis

def get_db():
    """Get database connection"""
    if not hasattr(g, 'db'):
        try:
            g.db = psycopg2.connect(db_connection_string)
        except psycopg2.Error as e:
            app.logger.error(f"Database connection failed: {e}")
            raise
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.route("/register", methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        if not all([username, email, password, confirm_password]):
            return render_template('register.html', error='All fields are required')
        
        if len(username) < 3:
            return render_template('register.html', error='Username must be at least 3 characters')
        
        if len(password) < 6:
            return render_template('register.html', error='Password must be at least 6 characters')
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')

        try:
            db = get_db()
            cursor = db.cursor()
            
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
            if cursor.fetchone():
                cursor.close()
                return render_template('register.html', error='Username or email already exists')
            
            # Create user
            password_hash = hash_password(password)
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
                (username, email, password_hash)
            )
            user_id = cursor.fetchone()[0]
            db.commit()
            cursor.close()
            
            # Create token and redirect to competitions
            token = create_jwt_token(user_id, username, is_admin=False)
            resp = make_response(redirect(url_for('competitions')))
            resp.set_cookie('auth_token', token, httponly=True, max_age=86400)
            return resp
        
        except Exception as e:
            app.logger.error(f"Registration error: {e}")
            return render_template('register.html', error='Registration failed. Please try again.')
    
    return render_template('register.html')


@app.route("/login", methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        login_role = request.form.get('login_role', 'user')  # Get selected role

        if not username or not password:
            return render_template('login.html', error='Username and password required')

        try:
            db = get_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT id, username, password_hash, is_admin FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            cursor.close()
            
            if not user or not verify_password(password, user['password_hash']):
                return render_template('login.html', error='Invalid username or password')
            
            # Check if admin login was requested for non-admin user
            if login_role == 'admin' and not user['is_admin']:
                return render_template('login.html', error='Admin access required. This account is not an admin.')
            
            # Create token and redirect based on role
            token = create_jwt_token(user['id'], user['username'], user['is_admin'])
            
            # Redirect to appropriate page based on role
            if user['is_admin'] and login_role == 'admin':
                resp = make_response(redirect(url_for('admin_dashboard')))
            else:
                resp = make_response(redirect(url_for('competitions')))
            
            resp.set_cookie('auth_token', token, httponly=True, max_age=86400)
            return resp
        
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            return render_template('login.html', error='Login failed. Please try again.')
    
    return render_template('login.html')


@app.route("/logout", methods=['GET', 'POST'])
def logout():
    """User logout"""
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('auth_token', '', expires=0)
    return resp


@app.route("/competitions", methods=['GET'])
@login_required
def competitions():
    """List available competitions"""
    try:
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        # Get all competitions
        cursor.execute("""
            SELECT id, name, description, option_a, option_b, status, created_at 
            FROM competitions 
            ORDER BY created_at DESC
        """)
        comps = cursor.fetchall()
        
        # Get vote counts for each competition
        for comp in comps:
            cursor.execute("""
                SELECT vote, COUNT(*) as count 
                FROM votes 
                WHERE competition_id = %s 
                GROUP BY vote
            """, (comp['id'],))
            votes = {row['vote']: row['count'] for row in cursor.fetchall()}
            comp['votes_a'] = votes.get('a', 0)
            comp['votes_b'] = votes.get('b', 0)
            comp['total_votes'] = comp['votes_a'] + comp['votes_b']
        
        cursor.close()
        
        current_user = get_current_user()
        return render_template('competitions.html', competitions=comps, user=current_user)
    
    except Exception as e:
        app.logger.error(f"Error loading competitions: {e}")
        return render_template('competitions.html', competitions=[], error='Failed to load competitions')


@app.route("/vote/<int:competition_id>", methods=['GET', 'POST'])
@login_required
def vote(competition_id):
    """Vote in a competition"""
    try:
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        # Get competition
        cursor.execute("""
            SELECT id, name, description, option_a, option_b, status 
            FROM competitions 
            WHERE id = %s
        """, (competition_id,))
        comp = cursor.fetchone()
        
        if not comp:
            cursor.close()
            return jsonify({'error': 'Competition not found'}), 404
        
        if comp['status'] != 'active':
            cursor.close()
            return jsonify({'error': 'This competition is closed'}), 403
        
        current_user = get_current_user()
        vote = None
        
        if request.method == 'POST':
            vote_choice = request.form.get('vote', '').strip()
            
            if vote_choice not in ['a', 'b']:
                cursor.close()
                return render_template('vote.html', competition=comp, error='Invalid vote')
            
            voter_id = f"user_{current_user['user_id']}"
            
            # Save vote to Redis for worker processing
            data = json.dumps({
                'voter_id': voter_id,
                'vote': vote_choice,
                'competition_id': competition_id,
                'user_id': current_user['user_id']
            })
            redis = get_redis()
            redis.rpush('votes', data)
            
            app.logger.info(f'User {current_user["username"]} voted for {vote_choice} in competition {competition_id}')
            vote = vote_choice
        
        # Get current vote counts
        cursor.execute("""
            SELECT vote, COUNT(*) as count 
            FROM votes 
            WHERE competition_id = %s 
            GROUP BY vote
        """, (competition_id,))
        votes_result = cursor.fetchall()
        votes_dict = {row['vote']: row['count'] for row in votes_result}
        comp['votes_a'] = votes_dict.get('a', 0)
        comp['votes_b'] = votes_dict.get('b', 0)
        
        cursor.close()
        
        return render_template('vote.html', competition=comp, vote=vote, user=get_current_user())
    
    except Exception as e:
        app.logger.error(f"Voting error: {e}")
        return render_template('vote.html', error='Voting failed. Please try again.')


@app.route("/api/competitions", methods=['GET'])
def api_competitions():
    """API endpoint for competitions list"""
    try:
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, name, description, option_a, option_b, status, created_at 
            FROM competitions 
            ORDER BY created_at DESC
        """)
        comps = cursor.fetchall()
        
        for comp in comps:
            cursor.execute("""
                SELECT vote, COUNT(*) as count 
                FROM votes 
                WHERE competition_id = %s 
                GROUP BY vote
            """, (comp['id'],))
            votes = {row['vote']: row['count'] for row in cursor.fetchall()}
            comp['votes_a'] = votes.get('a', 0)
            comp['votes_b'] = votes.get('b', 0)
        
        cursor.close()
        return jsonify(comps)
    
    except Exception as e:
        app.logger.error(f"API error: {e}")
        return jsonify({'error': 'Failed to load competitions'}), 500


@app.route("/", methods=['POST','GET'])
def hello():
    """Redirect to competitions if logged in, else to login"""
    token = get_auth_token_from_request()
    if token:
        try:
            verify_jwt_token(token)
            return redirect(url_for('competitions'))
        except AuthError:
            pass
    
    return redirect(url_for('login'))


@app.route("/health", methods=['GET'])
def health():
    """Basic liveness signal."""
    return jsonify(status="ok", hostname=hostname), 200


@app.route("/ready", methods=['GET'])
def ready():
    """Readiness check that verifies Redis connectivity."""
    try:
        redis = get_redis()
        redis.ping()
    except Exception as exc:  # pragma: no cover - readiness failures are runtime only
        app.logger.warning("Redis readiness check failed: %s", exc)
        return jsonify(status="error", reason="redis_unavailable"), 503
    return jsonify(status="ready"), 200


@app.route("/api/admin/competitions", methods=['POST'])
@admin_required
def create_competition():
    """Create a new competition (admin only) with optional scheduling"""
    try:
        name = request.json.get('name', '').strip()
        description = request.json.get('description', '').strip()
        option_a = request.json.get('option_a', '').strip()
        option_b = request.json.get('option_b', '').strip()
        scheduled_start = request.json.get('scheduled_start', '') or None
        scheduled_end = request.json.get('scheduled_end', '') or None

        if not all([name, option_a, option_b]):
            return jsonify({'error': 'Name and options required'}), 400

        # Determine initial status based on scheduling
        if scheduled_start:
            initial_status = 'scheduled'
        else:
            initial_status = 'active'

        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            INSERT INTO competitions (name, description, option_a, option_b, created_by, status, scheduled_start, scheduled_end) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
            RETURNING id, name, option_a, option_b, status, created_at, scheduled_start, scheduled_end
        """, (name, description, option_a, option_b, g.user['user_id'], initial_status, scheduled_start, scheduled_end))
        
        comp = cursor.fetchone()
        db.commit()
        cursor.close()
        
        status_info = f" (scheduled to start at {scheduled_start})" if scheduled_start else ""
        app.logger.info(f"Admin {g.user['username']} created competition: {name}{status_info}")
        return jsonify(comp), 201
    
    except Exception as e:
        app.logger.error(f"Error creating competition: {e}")
        return jsonify({'error': 'Failed to create competition'}), 500


@app.route("/api/admin/competitions/<int:comp_id>/close", methods=['POST'])
@admin_required
def close_competition(comp_id):
    """Close a competition (admin only)"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute(
            "UPDATE competitions SET status = %s, closed_at = CURRENT_TIMESTAMP WHERE id = %s",
            ('closed', comp_id)
        )
        db.commit()
        cursor.close()
        
        app.logger.info(f"Admin {g.user['username']} closed competition {comp_id}")
        return jsonify({'message': 'Competition closed'}), 200
    
    except Exception as e:
        app.logger.error(f"Error closing competition: {e}")
        return jsonify({'error': 'Failed to close competition'}), 500


@app.route("/api/admin/competitions/<int:comp_id>/open", methods=['POST'])
@admin_required
def open_competition(comp_id):
    """Reopen a competition (admin only)"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute(
            "UPDATE competitions SET status = %s, closed_at = NULL WHERE id = %s",
            ('active', comp_id)
        )
        db.commit()
        cursor.close()
        
        app.logger.info(f"Admin {g.user['username']} reopened competition {comp_id}")
        return jsonify({'message': 'Competition reopened'}), 200
    
    except Exception as e:
        app.logger.error(f"Error reopening competition: {e}")
        return jsonify({'error': 'Failed to reopen competition'}), 500


@app.route("/api/admin/competitions/<int:comp_id>", methods=['DELETE'])
@admin_required
def delete_competition(comp_id):
    """Delete a competition (admin only)"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Delete votes first (foreign key)
        cursor.execute("DELETE FROM votes WHERE competition_id = %s", (comp_id,))
        
        # Delete competition
        cursor.execute("DELETE FROM competitions WHERE id = %s", (comp_id,))
        db.commit()
        cursor.close()
        
        app.logger.info(f"Admin {g.user['username']} deleted competition {comp_id}")
        return jsonify({'message': 'Competition deleted'}), 200
    
    except Exception as e:
        app.logger.error(f"Error deleting competition: {e}")
        return jsonify({'error': 'Failed to delete competition'}), 500


@app.route("/api/admin/competitions/<int:comp_id>/scores", methods=['GET'])
def get_competition_scores(comp_id):
    """Get live scores for a competition"""
    try:
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT vote, COUNT(*) as count 
            FROM votes 
            WHERE competition_id = %s 
            GROUP BY vote
        """, (comp_id,))
        
        votes = cursor.fetchall()
        result = {
            'competition_id': comp_id,
            'a': next((v['count'] for v in votes if v['vote'] == 'a'), 0),
            'b': next((v['count'] for v in votes if v['vote'] == 'b'), 0)
        }
        cursor.close()
        return jsonify(result)
    
    except Exception as e:
        app.logger.error(f"Error getting scores: {e}")
        return jsonify({'error': 'Failed to get scores'}), 500


@app.route("/api/admin/competitions/scheduled", methods=['GET'])
@admin_required
def get_scheduled_competitions():
    """Get all scheduled competitions"""
    try:
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, name, description, option_a, option_b, status, 
                   scheduled_start, scheduled_end, created_at
            FROM competitions
            WHERE status IN ('scheduled', 'active', 'closed')
            ORDER BY scheduled_start DESC NULLS LAST, created_at DESC
        """)
        comps = cursor.fetchall()
        cursor.close()
        
        return jsonify(comps)
    except Exception as e:
        app.logger.error(f"Error fetching scheduled competitions: {e}")
        return jsonify({'error': 'Failed to fetch competitions'}), 500


@app.route("/api/admin/competitions/<int:comp_id>/schedule", methods=['POST'])
@admin_required
def schedule_competition(comp_id):
    """Update competition schedule"""
    try:
        scheduled_start = request.json.get('scheduled_start', '').strip() or None
        scheduled_end = request.json.get('scheduled_end', '').strip() or None
        
        if not scheduled_start:
            return jsonify({'error': 'scheduled_start is required'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            UPDATE competitions
            SET scheduled_start = %s, scheduled_end = %s, status = 'scheduled', updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (scheduled_start, scheduled_end, comp_id))
        db.commit()
        cursor.close()
        
        app.logger.info(f'Admin {g.user["username"]} scheduled competition {comp_id} from {scheduled_start} to {scheduled_end}')
        return jsonify({'success': True, 'message': 'Competition scheduled successfully'})
    except Exception as e:
        app.logger.error(f"Scheduling error: {e}")
        return jsonify({'error': 'Failed to schedule competition'}), 500


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    """Admin dashboard for managing competitions"""
    return render_template('admin_dashboard.html', user=get_current_user(), option_a=option_a, option_b=option_b)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True, threaded=True)
