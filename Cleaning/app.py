from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import os
from datetime import datetime
import json

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-change-this'

db = SQLAlchemy(app)

# Initialize database on app startup
with app.app_context():
    db.create_all()

# Database Models
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_token(self):
        self.token = secrets.token_urlsafe(32)
        return self.token


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.String(255), nullable=False)
    time = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255))
    capacity = db.Column(db.Integer, default=0)
    image_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'date': self.date,
            'time': self.time,
            'location': self.location,
            'capacity': self.capacity,
            'image_url': self.image_url,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


# Authentication Middleware
def verify_token(f):
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Missing token'}), 401
        
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        admin = Admin.query.filter_by(token=token).first()
        if not admin:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function


# Routes

@app.route('/')
def index():
    return send_file('index.html', mimetype='text/html')


@app.route('/admin')
def admin_dashboard():
    return send_file('admin.html', mimetype='text/html')


@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_file(f'images/{filename}')


@app.route('/api/admin/register', methods=['POST'])
def register_admin():
    """Register a new admin account"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400
    
    if Admin.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 409
    
    admin = Admin(username=data['username'])
    admin.set_password(data['password'])
    admin.generate_token()
    
    db.session.add(admin)
    db.session.commit()
    
    return jsonify({
        'message': 'Admin account created',
        'token': admin.token,
        'username': admin.username
    }), 201


@app.route('/api/admin/login', methods=['POST'])
def login_admin():
    """Login admin account and get token"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400
    
    admin = Admin.query.filter_by(username=data['username']).first()
    
    if not admin or not admin.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Regenerate token on each login
    admin.generate_token()
    db.session.commit()
    
    return jsonify({
        'message': 'Login successful',
        'token': admin.token,
        'username': admin.username
    }), 200


# Event Management Routes

@app.route('/api/events', methods=['GET'])
def get_events():
    """Get all events"""
    events = Event.query.all()
    return jsonify([event.to_dict() for event in events]), 200


@app.route('/api/events/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """Get a specific event"""
    event = Event.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    return jsonify(event.to_dict()), 200


@app.route('/api/admin/events', methods=['POST'])
@verify_token
def create_event():
    """Create a new event (Admin only)"""
    data = request.get_json()
    
    if not data or not data.get('title') or not data.get('date'):
        return jsonify({'error': 'Title and date are required'}), 400
    
    event = Event(
        title=data['title'],
        description=data.get('description', ''),
        date=data['date'],
        time=data.get('time', ''),
        location=data.get('location', ''),
        capacity=data.get('capacity', 0),
        image_url=data.get('image_url', '')
    )
    
    db.session.add(event)
    db.session.commit()
    
    return jsonify({
        'message': 'Event created successfully',
        'event': event.to_dict()
    }), 201


@app.route('/api/admin/events/<int:event_id>', methods=['PUT'])
@verify_token
def update_event(event_id):
    """Update an event (Admin only)"""
    event = Event.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    data = request.get_json()
    
    if 'title' in data:
        event.title = data['title']
    if 'description' in data:
        event.description = data['description']
    if 'date' in data:
        event.date = data['date']
    if 'time' in data:
        event.time = data['time']
    if 'location' in data:
        event.location = data['location']
    if 'capacity' in data:
        event.capacity = data['capacity']
    if 'image_url' in data:
        event.image_url = data['image_url']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Event updated successfully',
        'event': event.to_dict()
    }), 200


@app.route('/api/admin/events/<int:event_id>', methods=['DELETE'])
@verify_token
def delete_event(event_id):
    """Delete an event (Admin only)"""
    event = Event.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    db.session.delete(event)
    db.session.commit()
    
    return jsonify({'message': 'Event deleted successfully'}), 200


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok'}), 200

