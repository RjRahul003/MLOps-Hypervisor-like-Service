from werkzeug.security import generate_password_hash, check_password_hash
from flask import request, jsonify, current_app, g
from functools import wraps
import uuid

# Basic Authentication Decorator
def basic_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not authenticate(auth.username, auth.password):
            return jsonify({'message': 'Authentication required!'}), 401
        return f(*args, **kwargs)
    return decorated

def authenticate(username, password):
    """Authenticates a user based on username and password."""
    from models import User
    with current_app.app_context():
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            g.current_user = user
            return True
    return False

def generate_invite_code():
    """Generates a unique invite code."""
    return str(uuid.uuid4())
