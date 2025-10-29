"""Authentication module for voting app"""
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g, session, redirect, url_for
import jwt

JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRY_HOURS = 24


class AuthError(Exception):
    """Custom authentication error"""
    pass


def hash_password(password: str) -> str:
    """Hash password using PBKDF2"""
    salt = secrets.token_hex(32)
    iterations = 100000
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), iterations)
    return f"{salt}${hash_obj.hex()}"


def verify_password(password: str, hash_obj: str) -> bool:
    """Verify password against hash"""
    try:
        salt, stored_hash = hash_obj.split('$')
        iterations = 100000
        computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), iterations).hex()
        return computed_hash == stored_hash
    except (ValueError, AttributeError):
        return False


def create_jwt_token(user_id: int, username: str, is_admin: bool = False) -> str:
    """Create JWT token for user"""
    payload = {
        'user_id': user_id,
        'username': username,
        'is_admin': is_admin,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> dict:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError('Token expired')
    except jwt.InvalidTokenError:
        raise AuthError('Invalid token')


def get_auth_token_from_request() -> str:
    """Extract JWT token from request (cookie or Authorization header)"""
    # Check cookie first
    token = request.cookies.get('auth_token')
    if token:
        return token
    
    # Check Authorization header
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    
    return None


def login_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_auth_token_from_request()
        if not token:
            return redirect(url_for('login'))
        
        try:
            g.user = verify_jwt_token(token)
        except AuthError:
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    
    return decorated_function


def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_auth_token_from_request()
        if not token:
            return jsonify({'error': 'Unauthorized'}), 401
        
        try:
            payload = verify_jwt_token(token)
            if not payload.get('is_admin'):
                return jsonify({'error': 'Admin access required'}), 403
            g.user = payload
        except AuthError:
            return jsonify({'error': 'Unauthorized'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_user():
    """Get current user from g or token"""
    if hasattr(g, 'user'):
        return g.user
    
    token = get_auth_token_from_request()
    if token:
        try:
            return verify_jwt_token(token)
        except AuthError:
            return None
    
    return None
