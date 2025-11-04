from flask import Flask, render_template, request, make_response, g, jsonify, redirect, url_for
from redis import Redis
import os
import socket
import random
import json
import logging
from datetime import datetime
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
    """List available competitions with enhanced features"""
    try:
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        current_user = get_current_user()
        
        # Get filter parameters
        search = request.args.get('search', '').strip()
        tag_filter = request.args.get('tag', '').strip()
        sort_by = request.args.get('sort', 'newest')  # newest, popular, ending_soon
        
        # Build query with filters
        sql = """
            SELECT c.id, c.name, c.description, c.option_a, c.option_b, c.status, 
                   c.created_at, c.tags, c.image_url, c.trending_score, c.view_count, 
                   c.participant_count, c.scheduled_end
            FROM competitions c
            WHERE c.deleted_at IS NULL AND c.is_archived = FALSE
        """
        params = []
        
        if search:
            sql += " AND (c.name ILIKE %s OR c.description ILIKE %s)"
            params.extend([f'%{search}%', f'%{search}%'])
        
        if tag_filter:
            sql += " AND %s = ANY(c.tags)"
            params.append(tag_filter)
        
        # Sorting
        if sort_by == 'popular':
            sql += " ORDER BY c.participant_count DESC, c.created_at DESC"
        elif sort_by == 'ending_soon':
            sql += " ORDER BY c.scheduled_end ASC NULLS LAST, c.created_at DESC"
        elif sort_by == 'trending':
            sql += " ORDER BY c.trending_score DESC, c.created_at DESC"
        else:  # newest
            sql += " ORDER BY c.created_at DESC"
        
        cursor.execute(sql, params)
        comps = cursor.fetchall()
        
        # Get vote counts and user favorites for each competition
        for comp in comps:
            # Vote counts
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
            
            # Check if user favorited
            cursor.execute("""
                SELECT id FROM user_favorites 
                WHERE user_id = %s AND competition_id = %s
            """, (current_user['user_id'], comp['id']))
            comp['is_favorited'] = cursor.fetchone() is not None
            
            # Check if user already voted
            cursor.execute("""
                SELECT vote FROM votes 
                WHERE competition_id = %s AND user_id = %s
                ORDER BY created_at DESC LIMIT 1
            """, (comp['id'], current_user['user_id']))
            vote_result = cursor.fetchone()
            comp['user_vote'] = vote_result['vote'] if vote_result else None
        
        # Get all unique tags for filter dropdown
        cursor.execute("""
            SELECT DISTINCT unnest(tags) as tag 
            FROM competitions 
            WHERE deleted_at IS NULL AND is_archived = FALSE AND tags IS NOT NULL
            ORDER BY tag
        """)
        all_tags = [row['tag'] for row in cursor.fetchall()]
        
        # Get trending competitions (top 5)
        cursor.execute("""
            SELECT id, name, trending_score 
            FROM competitions 
            WHERE deleted_at IS NULL AND is_archived = FALSE AND trending_score > 0
            ORDER BY trending_score DESC 
            LIMIT 5
        """)
        trending = cursor.fetchall()
        
        cursor.close()
        
        return render_template('competitions_enhanced.html', 
                             competitions=comps, 
                             user=current_user,
                             all_tags=all_tags,
                             trending=trending,
                             search=search,
                             tag_filter=tag_filter,
                             sort_by=sort_by)
    
    except Exception as e:
        app.logger.error(f"Error loading competitions: {e}")
        return render_template('competitions_enhanced.html', 
                             competitions=[], 
                             user=current_user,
                             all_tags=[],
                             trending=[],
                             error='Failed to load competitions')


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
            
            # Broadcast vote event for real-time updates
            redis.publish('vote_updates', json.dumps({
                'competition_id': competition_id,
                'timestamp': str(datetime.now())
            }))
            
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
    """API endpoint for competitions list with enhanced fields"""
    try:
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        # Get search and filter parameters
        search = request.args.get('search', '')
        tag_filter = request.args.get('tag', '')
        sort_by = request.args.get('sort', 'newest')
        
        # Build query with filters
        sql = """
            SELECT id, name, description, option_a, option_b, tags, image_url,
                   status, created_at, updated_at, is_archived, trending_score,
                   view_count, participant_count
            FROM competitions 
            WHERE deleted_at IS NULL AND is_archived = FALSE AND status = 'active'
        """
        params = []
        
        # Search filter
        if search:
            sql += " AND (name ILIKE %s OR description ILIKE %s)"
            params.extend([f'%{search}%', f'%{search}%'])
        
        # Tag filter
        if tag_filter:
            sql += " AND %s = ANY(tags)"
            params.append(tag_filter)
        
        # Sorting
        if sort_by == 'popular':
            sql += " ORDER BY participant_count DESC, created_at DESC"
        elif sort_by == 'ending_soon':
            sql += " ORDER BY scheduled_end ASC NULLS LAST, created_at DESC"
        elif sort_by == 'trending':
            sql += " ORDER BY trending_score DESC, created_at DESC"
        else:  # newest
            sql += " ORDER BY created_at DESC"
        
        cursor.execute(sql, params)
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
            comp['total_votes'] = comp['votes_a'] + comp['votes_b']
            
            # Add vote percentages
            if comp['total_votes'] > 0:
                comp['percentage_a'] = round((comp['votes_a'] / comp['total_votes']) * 100, 1)
                comp['percentage_b'] = round((comp['votes_b'] / comp['total_votes']) * 100, 1)
            else:
                comp['percentage_a'] = 0
                comp['percentage_b'] = 0
            
            # Check if favorited (if user is logged in)
            comp['is_favorited'] = False
            try:
                current_user = get_current_user()
                cursor.execute("""
                    SELECT id FROM user_favorites 
                    WHERE user_id = %s AND competition_id = %s
                """, (current_user['user_id'], comp['id']))
                comp['is_favorited'] = cursor.fetchone() is not None
            except:
                pass
        
        # Get all unique tags
        cursor.execute("""
            SELECT DISTINCT unnest(tags) as tag 
            FROM competitions 
            WHERE deleted_at IS NULL AND is_archived = FALSE 
                AND tags IS NOT NULL AND array_length(tags, 1) > 0
            ORDER BY tag
        """)
        all_tags = [row['tag'] for row in cursor.fetchall()]
        
        cursor.close()
        return jsonify({
            'competitions': comps,
            'all_tags': all_tags
        })
    
    except Exception as e:
        app.logger.error(f"API error: {e}")
        return jsonify({'error': 'Failed to load competitions', 'competitions': [], 'all_tags': []}), 500


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


@app.route("/vote", methods=['GET'])
def vote_redirect():
    """Redirect /vote to competitions page"""
    return redirect(url_for('competitions'))


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
        tags = request.json.get('tags', [])
        image_url = request.json.get('image_url', '').strip() or None
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
            INSERT INTO competitions (name, description, option_a, option_b, tags, image_url, created_by, status, scheduled_start, scheduled_end) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
            RETURNING id, name, description, option_a, option_b, tags, image_url, status, created_at, updated_at, scheduled_start, scheduled_end
        """, (name, description, option_a, option_b, tags, image_url, g.user['user_id'], initial_status, scheduled_start, scheduled_end))
        
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
    return render_template('admin_dashboard_enhanced.html', user=get_current_user(), option_a=option_a, option_b=option_b)


@app.route("/admin/profile")
@admin_required
def admin_profile():
    """Admin profile page"""
    return render_template('admin_profile.html', user=get_current_user())


# ==================== PHASE 1 & 2 USER FEATURES ====================

@app.route("/api/user/stats", methods=['GET'])
@login_required
def get_user_stats():
    """Get user statistics dashboard"""
    try:
        current_user = get_current_user()
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        # Total votes cast
        cursor.execute("""
            SELECT COUNT(*) as total_votes 
            FROM votes 
            WHERE user_id = %s
        """, (current_user['user_id'],))
        total_votes = cursor.fetchone()['total_votes']
        
        # Competitions participated in
        cursor.execute("""
            SELECT COUNT(DISTINCT competition_id) as participated 
            FROM votes 
            WHERE user_id = %s
        """, (current_user['user_id'],))
        participated = cursor.fetchone()['participated']
        
        # Favorite category (most voted tag)
        cursor.execute("""
            SELECT unnest(c.tags) as tag, COUNT(*) as count
            FROM votes v
            JOIN competitions c ON v.competition_id = c.id
            WHERE v.user_id = %s AND c.tags IS NOT NULL
            GROUP BY tag
            ORDER BY count DESC
            LIMIT 1
        """, (current_user['user_id'],))
        fav_result = cursor.fetchone()
        favorite_category = fav_result['tag'] if fav_result else 'None'
        
        # Favorites count
        cursor.execute("""
            SELECT COUNT(*) as favorites 
            FROM user_favorites 
            WHERE user_id = %s
        """, (current_user['user_id'],))
        favorites_count = cursor.fetchone()['favorites']
        
        cursor.close()
        
        return jsonify({
            'total_votes': total_votes,
            'competitions_participated': participated,
            'favorite_category': favorite_category,
            'favorites_count': favorites_count,
            'username': current_user['username']
        })
    
    except Exception as e:
        app.logger.error(f"Error getting user stats: {e}")
        return jsonify({'error': 'Failed to load statistics'}), 500


@app.route("/api/user/profile", methods=['GET'])
@login_required
def get_user_profile():
    """Get user profile information"""
    try:
        current_user = get_current_user()
        return jsonify(current_user), 200
    except Exception as e:
        app.logger.error(f"Error getting user profile: {e}")
        return jsonify({'error': 'Failed to load profile'}), 500


@app.route("/api/user/profile", methods=['PUT'])
@login_required
def update_user_profile():
    """Update user profile information"""
    try:
        current_user = get_current_user()
        data = request.get_json()
        
        full_name = data.get('full_name', '').strip()
        email = data.get('email', '').strip() or None
        phone = data.get('phone', '').strip() or None
        bio = data.get('bio', '').strip() or None
        location = data.get('location', '').strip() or None
        avatar_url = data.get('avatar_url', '').strip() or None
        
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            UPDATE users 
            SET full_name = %s, email = %s, phone = %s, bio = %s, location = %s, avatar_url = %s
            WHERE id = %s
            RETURNING id, username, full_name, email, phone, bio, location, avatar_url, created_at
        """, (full_name, email, phone, bio, location, avatar_url, current_user['user_id']))
        
        updated_user = cursor.fetchone()
        db.commit()
        cursor.close()
        
        app.logger.info(f"User {current_user['username']} updated their profile")
        return jsonify(updated_user), 200
    
    except Exception as e:
        app.logger.error(f"Error updating user profile: {e}")
        return jsonify({'error': 'Failed to update profile'}), 500


@app.route("/api/user/favorites", methods=['GET'])
@login_required
def get_user_favorites():
    """Get user's favorite competitions"""
    try:
        current_user = get_current_user()
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT c.id, c.name, c.description, c.option_a, c.option_b, 
                   c.status, c.tags, c.image_url, c.created_at,
                   uf.created_at as favorited_at
            FROM user_favorites uf
            JOIN competitions c ON uf.competition_id = c.id
            WHERE uf.user_id = %s AND c.deleted_at IS NULL
            ORDER BY uf.created_at DESC
        """, (current_user['user_id'],))
        favorites = cursor.fetchall()
        
        # Get vote counts for each
        for comp in favorites:
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
        return jsonify(favorites)
    
    except Exception as e:
        app.logger.error(f"Error getting favorites: {e}")
        return jsonify({'error': 'Failed to load favorites'}), 500


@app.route("/api/user/favorites/<int:comp_id>", methods=['POST', 'DELETE'])
@login_required
def toggle_favorite(comp_id):
    """Add or remove competition from favorites"""
    try:
        current_user = get_current_user()
        db = get_db()
        cursor = db.cursor()
        
        if request.method == 'POST':
            # Add to favorites
            cursor.execute("""
                INSERT INTO user_favorites (user_id, competition_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, competition_id) DO NOTHING
            """, (current_user['user_id'], comp_id))
            message = 'Added to favorites'
        else:
            # Remove from favorites
            cursor.execute("""
                DELETE FROM user_favorites 
                WHERE user_id = %s AND competition_id = %s
            """, (current_user['user_id'], comp_id))
            message = 'Removed from favorites'
        
        db.commit()
        cursor.close()
        return jsonify({'message': message}), 200
    
    except Exception as e:
        app.logger.error(f"Error toggling favorite: {e}")
        return jsonify({'error': 'Failed to update favorite'}), 500


@app.route("/api/competitions/trending", methods=['GET'])
def get_trending():
    """Get trending competitions (most votes in last 24h)"""
    try:
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        # Update trending scores first
        cursor.execute("SELECT calculate_trending_score()")
        db.commit()
        
        cursor.execute("""
            SELECT id, name, description, tags, image_url, trending_score, participant_count
            FROM competitions
            WHERE deleted_at IS NULL AND is_archived = FALSE 
            AND status = 'active' AND trending_score > 0
            ORDER BY trending_score DESC
            LIMIT 10
        """)
        trending = cursor.fetchall()
        
        cursor.close()
        return jsonify(trending)
    
    except Exception as e:
        app.logger.error(f"Error getting trending: {e}")
        return jsonify({'error': 'Failed to load trending'}), 500


@app.route("/api/user/trending", methods=['GET'])
def get_user_trending():
    """Get trending competitions for user view"""
    return get_trending()


@app.route("/api/competitions/<int:comp_id>/comments", methods=['GET', 'POST'])
@login_required
def competition_comments(comp_id):
    """Get or post comments for a competition"""
    try:
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        current_user = get_current_user()
        
        if request.method == 'GET':
            # Get comments with user info
            cursor.execute("""
                SELECT cc.id, cc.comment_text, cc.parent_id, cc.likes_count, 
                       cc.created_at, cc.updated_at,
                       u.username, u.id as user_id
                FROM competition_comments cc
                JOIN users u ON cc.user_id = u.id
                WHERE cc.competition_id = %s AND cc.deleted_at IS NULL
                ORDER BY cc.created_at DESC
            """, (comp_id,))
            comments = cursor.fetchall()
            
            # Check which comments current user has liked
            cursor.execute("""
                SELECT comment_id 
                FROM comment_likes 
                WHERE user_id = %s AND comment_id = ANY(%s)
            """, (current_user['user_id'], [c['id'] for c in comments]))
            liked_ids = [row['comment_id'] for row in cursor.fetchall()]
            
            for comment in comments:
                comment['is_liked'] = comment['id'] in liked_ids
            
            cursor.close()
            return jsonify(comments)
        
        else:  # POST
            comment_text = request.json.get('comment_text', '').strip()
            parent_id = request.json.get('parent_id')
            
            if not comment_text:
                return jsonify({'error': 'Comment text required'}), 400
            
            cursor.execute("""
                INSERT INTO competition_comments (competition_id, user_id, comment_text, parent_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id, comment_text, created_at
            """, (comp_id, current_user['user_id'], comment_text, parent_id))
            
            new_comment = cursor.fetchone()
            db.commit()
            cursor.close()
            
            return jsonify({
                **new_comment,
                'username': current_user['username'],
                'user_id': current_user['user_id'],
                'likes_count': 0,
                'is_liked': False
            }), 201
    
    except Exception as e:
        app.logger.error(f"Error with comments: {e}")
        return jsonify({'error': 'Failed to process comment'}), 500


@app.route("/api/comments/<int:comment_id>/like", methods=['POST', 'DELETE'])
@login_required
def toggle_comment_like(comment_id):
    """Like or unlike a comment"""
    try:
        current_user = get_current_user()
        db = get_db()
        cursor = db.cursor()
        
        if request.method == 'POST':
            cursor.execute("""
                INSERT INTO comment_likes (comment_id, user_id)
                VALUES (%s, %s)
                ON CONFLICT (comment_id, user_id) DO NOTHING
            """, (comment_id, current_user['user_id']))
            message = 'Comment liked'
        else:
            cursor.execute("""
                DELETE FROM comment_likes 
                WHERE comment_id = %s AND user_id = %s
            """, (comment_id, current_user['user_id']))
            message = 'Comment unliked'
        
        db.commit()
        cursor.close()
        return jsonify({'message': message}), 200
    
    except Exception as e:
        app.logger.error(f"Error toggling like: {e}")
        return jsonify({'error': 'Failed to toggle like'}), 500


@app.route("/api/comments/<int:comment_id>", methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """Delete a comment (soft delete)"""
    try:
        current_user = get_current_user()
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        # Check if user owns the comment
        cursor.execute("""
            SELECT user_id FROM competition_comments WHERE id = %s
        """, (comment_id,))
        comment = cursor.fetchone()
        
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404
        
        if comment['user_id'] != current_user['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        cursor.execute("""
            UPDATE competition_comments 
            SET deleted_at = CURRENT_TIMESTAMP 
            WHERE id = %s
        """, (comment_id,))
        
        db.commit()
        cursor.close()
        return jsonify({'message': 'Comment deleted'}), 200
    
    except Exception as e:
        app.logger.error(f"Error deleting comment: {e}")
        return jsonify({'error': 'Failed to delete comment'}), 500


@app.route("/api/competitions/<int:comp_id>/view", methods=['POST'])
def increment_view_count(comp_id):
    """Increment view count for a competition"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            UPDATE competitions 
            SET view_count = view_count + 1 
            WHERE id = %s
        """, (comp_id,))
        
        db.commit()
        cursor.close()
        return jsonify({'message': 'View counted'}), 200
    
    except Exception as e:
        app.logger.error(f"Error incrementing view: {e}")
        return jsonify({'error': 'Failed to count view'}), 500


@app.route("/user/profile")
@login_required
def user_profile():
    """User profile page with statistics"""
    return render_template('user_profile.html', user=get_current_user())


@app.route("/user/favorites")
@login_required
def favorites_page():
    """User favorites page"""
    return render_template('user_favorites.html', user=get_current_user())


# ==================== NEW FEATURE ENDPOINTS ====================

@app.route("/api/admin/competitions/<int:comp_id>/archive", methods=['POST'])
@admin_required
def archive_competition(comp_id):
    """Archive a competition instead of deleting"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            UPDATE competitions 
            SET is_archived = TRUE, archived_at = CURRENT_TIMESTAMP, status = 'closed'
            WHERE id = %s
        """, (comp_id,))
        db.commit()
        cursor.close()
        
        app.logger.info(f"Admin {g.user['username']} archived competition {comp_id}")
        return jsonify({'message': 'Competition archived successfully'}), 200
    
    except Exception as e:
        app.logger.error(f"Error archiving competition: {e}")
        return jsonify({'error': 'Failed to archive competition'}), 500


@app.route("/api/admin/competitions/<int:comp_id>/unarchive", methods=['POST'])
@admin_required
def unarchive_competition(comp_id):
    """Restore an archived competition"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            UPDATE competitions 
            SET is_archived = FALSE, archived_at = NULL, status = 'active'
            WHERE id = %s
        """, (comp_id,))
        db.commit()
        cursor.close()
        
        app.logger.info(f"Admin {g.user['username']} unarchived competition {comp_id}")
        return jsonify({'message': 'Competition restored successfully'}), 200
    
    except Exception as e:
        app.logger.error(f"Error unarchiving competition: {e}")
        return jsonify({'error': 'Failed to restore competition'}), 500


@app.route("/api/admin/competitions/<int:comp_id>/duplicate", methods=['POST'])
@admin_required
def duplicate_competition(comp_id):
    """Duplicate/clone an existing competition"""
    try:
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        # Get original competition
        cursor.execute("""
            SELECT name, description, option_a, option_b, tags, image_url
            FROM competitions WHERE id = %s
        """, (comp_id,))
        original = cursor.fetchone()
        
        if not original:
            cursor.close()
            return jsonify({'error': 'Competition not found'}), 404
        
        # Create duplicate with " (Copy)" suffix
        new_name = f"{original['name']} (Copy)"
        cursor.execute("""
            INSERT INTO competitions (name, description, option_a, option_b, tags, image_url, created_by, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
            RETURNING id, name, description, option_a, option_b, tags, image_url, status, created_at, updated_at
        """, (new_name, original['description'], original['option_a'], original['option_b'], 
              original['tags'], original['image_url'], g.user['user_id']))
        
        new_comp = cursor.fetchone()
        db.commit()
        cursor.close()
        
        app.logger.info(f"Admin {g.user['username']} duplicated competition {comp_id} to {new_comp['id']}")
        return jsonify(new_comp), 201
    
    except Exception as e:
        app.logger.error(f"Error duplicating competition: {e}")
        return jsonify({'error': 'Failed to duplicate competition'}), 500


@app.route("/api/admin/competitions/<int:comp_id>/soft-delete", methods=['POST'])
@admin_required
def soft_delete_competition(comp_id):
    """Soft delete a competition (can be recovered)"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            UPDATE competitions 
            SET deleted_at = CURRENT_TIMESTAMP, status = 'closed'
            WHERE id = %s AND deleted_at IS NULL
        """, (comp_id,))
        db.commit()
        cursor.close()
        
        app.logger.info(f"Admin {g.user['username']} soft-deleted competition {comp_id}")
        return jsonify({'message': 'Competition moved to trash'}), 200
    
    except Exception as e:
        app.logger.error(f"Error soft-deleting competition: {e}")
        return jsonify({'error': 'Failed to delete competition'}), 500


@app.route("/api/admin/competitions/<int:comp_id>/restore", methods=['POST'])
@admin_required
def restore_competition(comp_id):
    """Restore a soft-deleted competition"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            UPDATE competitions 
            SET deleted_at = NULL, status = 'active'
            WHERE id = %s AND deleted_at IS NOT NULL
        """, (comp_id,))
        db.commit()
        cursor.close()
        
        app.logger.info(f"Admin {g.user['username']} restored competition {comp_id}")
        return jsonify({'message': 'Competition restored successfully'}), 200
    
    except Exception as e:
        app.logger.error(f"Error restoring competition: {e}")
        return jsonify({'error': 'Failed to restore competition'}), 500


@app.route("/api/admin/competitions/<int:comp_id>", methods=['PUT'])
@admin_required
def update_competition(comp_id):
    """Update competition details"""
    try:
        name = request.json.get('name', '').strip()
        description = request.json.get('description', '').strip()
        option_a = request.json.get('option_a', '').strip()
        option_b = request.json.get('option_b', '').strip()
        tags = request.json.get('tags', [])
        image_url = request.json.get('image_url', '').strip() or None
        scheduled_start = request.json.get('scheduled_start', '') or None
        scheduled_end = request.json.get('scheduled_end', '') or None
        
        if not all([name, option_a, option_b]):
            return jsonify({'error': 'Name and options required'}), 400
        
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            UPDATE competitions 
            SET name = %s, description = %s, option_a = %s, option_b = %s, 
                tags = %s, image_url = %s, scheduled_start = %s, scheduled_end = %s
            WHERE id = %s
            RETURNING id, name, description, option_a, option_b, tags, image_url, status, updated_at, scheduled_start, scheduled_end
        """, (name, description, option_a, option_b, tags, image_url, scheduled_start, scheduled_end, comp_id))
        
        comp = cursor.fetchone()
        db.commit()
        cursor.close()
        
        app.logger.info(f"Admin {g.user['username']} updated competition {comp_id}")
        return jsonify(comp), 200
    
    except Exception as e:
        app.logger.error(f"Error updating competition: {e}")
        return jsonify({'error': 'Failed to update competition'}), 500


@app.route("/api/admin/stats", methods=['GET'])
@admin_required
def get_admin_stats():
    """Get admin dashboard statistics"""
    try:
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        # Total competitions
        cursor.execute("SELECT COUNT(*) as total FROM competitions WHERE deleted_at IS NULL")
        total_comps = cursor.fetchone()['total']
        
        # Active competitions
        cursor.execute("SELECT COUNT(*) as total FROM competitions WHERE status = 'active' AND deleted_at IS NULL")
        active_comps = cursor.fetchone()['total']
        
        # Total votes
        cursor.execute("SELECT COUNT(*) as total FROM votes")
        total_votes = cursor.fetchone()['total']
        
        # Total users
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()['total']
        
        cursor.close()
        
        return jsonify({
            'total_competitions': total_comps,
            'active_competitions': active_comps,
            'total_votes': total_votes,
            'total_users': total_users
        })
    
    except Exception as e:
        app.logger.error(f"Error getting admin stats: {e}")
        return jsonify({'error': 'Failed to load statistics'}), 500


@app.route("/api/admin/competitions/search", methods=['GET'])
@admin_required
def search_competitions():
    """Search competitions by name, tags, or description"""
    try:
        query = request.args.get('q', '').strip()
        include_archived = request.args.get('include_archived', 'false').lower() == 'true'
        include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'
        
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        sql = """
            SELECT id, name, description, option_a, option_b, tags, image_url, 
                   status, created_at, updated_at, is_archived, archived_at, deleted_at
            FROM competitions
            WHERE (name ILIKE %s OR description ILIKE %s OR %s = ANY(tags))
        """
        params = [f'%{query}%', f'%{query}%', query]
        
        if not include_archived:
            sql += " AND is_archived = FALSE"
        
        if not include_deleted:
            sql += " AND deleted_at IS NULL"
        
        sql += " ORDER BY created_at DESC LIMIT 50"
        
        cursor.execute(sql, params)
        comps = cursor.fetchall()
        
        # Get vote counts
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
            
            # Calculate percentages
            if comp['total_votes'] > 0:
                comp['percentage_a'] = round((comp['votes_a'] / comp['total_votes']) * 100, 1)
                comp['percentage_b'] = round((comp['votes_b'] / comp['total_votes']) * 100, 1)
            else:
                comp['percentage_a'] = 0
                comp['percentage_b'] = 0
        
        cursor.close()
        return jsonify(comps)
    
    except Exception as e:
        app.logger.error(f"Error searching competitions: {e}")
        return jsonify({'error': 'Search failed'}), 500


@app.route("/api/admin/competitions/trash", methods=['GET'])
@admin_required
def get_trash():
    """Get all soft-deleted competitions"""
    try:
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, name, description, option_a, option_b, tags, image_url,
                   status, created_at, updated_at, deleted_at
            FROM competitions
            WHERE deleted_at IS NOT NULL
            ORDER BY deleted_at DESC
        """)
        comps = cursor.fetchall()
        cursor.close()
        
        return jsonify(comps)
    
    except Exception as e:
        app.logger.error(f"Error fetching trash: {e}")
        return jsonify({'error': 'Failed to fetch deleted competitions'}), 500


@app.route("/api/admin/competitions/archived", methods=['GET'])
@admin_required
def get_archived():
    """Get all archived competitions"""
    try:
        db = get_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, name, description, option_a, option_b, tags, image_url,
                   status, created_at, updated_at, is_archived, archived_at
            FROM competitions
            WHERE is_archived = TRUE AND deleted_at IS NULL
            ORDER BY archived_at DESC
        """)
        comps = cursor.fetchall()
        
        # Get vote counts
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
        return jsonify(comps)
    
    except Exception as e:
        app.logger.error(f"Error fetching archived competitions: {e}")
        return jsonify({'error': 'Failed to fetch archived competitions'}), 500


@app.route("/api/admin/vote-stream")
@admin_required
def vote_stream():
    """Server-Sent Events stream for real-time vote updates"""
    def event_stream():
        try:
            # Create a direct Redis connection without using Flask's g
            from redis import Redis
            redis_conn = Redis(host=redis_host, port=redis_port, db=0, socket_timeout=5)
            pubsub = redis_conn.pubsub()
            pubsub.subscribe('vote_updates')
            
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            
            # Listen for vote updates
            for message in pubsub.listen():
                if message['type'] == 'message':
                    yield f"data: {message['data'].decode('utf-8')}\n\n"
        except Exception as e:
            app.logger.error(f"SSE stream error: {e}")
    
    return app.response_class(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


@app.route("/api/user/vote-stream")
@login_required
def user_vote_stream():
    """Server-Sent Events stream for real-time vote updates (user version)"""
    def event_stream():
        try:
            # Create a direct Redis connection without using Flask's g
            from redis import Redis
            redis_conn = Redis(host=redis_host, port=redis_port, db=0, socket_timeout=5)
            pubsub = redis_conn.pubsub()
            pubsub.subscribe('vote_updates')
            
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            
            # Listen for vote updates
            for message in pubsub.listen():
                if message['type'] == 'message':
                    yield f"data: {message['data'].decode('utf-8')}\n\n"
        except Exception as e:
            app.logger.error(f"SSE stream error: {e}")
    
    return app.response_class(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True, threaded=True)
