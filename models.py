from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Work(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    hair_type = db.Column(db.String(50), nullable=True) 
    cost = db.Column(db.String(50), nullable=True) 

    before_image = db.Column(db.String(120), nullable=False)
    after_image = db.Column(db.String(120), nullable=False)
    reel_link = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    reviews = db.relationship('Review', backref='work', lazy=True)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(80), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    branch = db.Column(db.String(50), nullable=True) 
    image_back = db.Column(db.String(120), nullable=True)
    image_front = db.Column(db.String(120), nullable=True)
    kudos = db.Column(db.Integer, default=0)
    rating = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=False) 
    is_featured = db.Column(db.Boolean, default=False) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    work_id = db.Column(db.Integer, db.ForeignKey('work.id'), nullable=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(80), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    service = db.Column(db.String(100), nullable=False)
    date_requested = db.Column(db.String(50), nullable=False)
    branch = db.Column(db.String(50), nullable=False) 
    is_confirmed = db.Column(db.Boolean, default=False) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)