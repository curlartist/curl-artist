import os
from urllib.parse import quote
import uuid
import sys
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from models import db, Work, Review, Appointment
from sqlalchemy import func

app = Flask(__name__)

# ==========================================
# 1. CONFIGURATION & SETUP
# ==========================================
app.config['SECRET_KEY'] = '56trfew34ertyuiui8stuti756rfyiouiyuertfhgjhyiukfyr6ery'

# --- DATABASE FIX: USE ABSOLUTE PATH ---
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'webp'}
# Optional: Set max upload size to 8MB to trigger 413 error on huge files
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024 

# Ensure upload directories exist
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'before'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'after'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'reviews'), exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()

# --- HARDCODED CREDENTIALS --- 
ADMIN_USER = "arpit"
ADMIN_PASS = "123" 
ARPIT_PHONE_NUMBER = "917014790175" 

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_image(file, subfolder='reviews'):
    """
    Saves an uploaded image with a unique filename.
    Returns the filename string.
    """
    if file and allowed_file(file.filename):
        # Generate unique filename: random_uuid.jpg
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        
        # Save to static/uploads/{subfolder}/filename
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, filename)
        file.save(save_path)
        return filename
    return None

def convert_reel_to_embed(url):
    """
    Converts standard Instagram URL -> Embed URL
    """
    if not url: return None
    clean_url = url.split('?')[0] # Remove query params like ?igsh=...
    if not clean_url.endswith('/'):
        clean_url += '/'
    return clean_url + "embed"

# ==========================================
# 3. PUBLIC ROUTES (The Website)
# ==========================================

@app.route('/')
def index():
    # 1. Get the filter from the URL (e.g., ?hair=Curly)
    hair_filter = request.args.get('hair', 'all') # Default to 'all'

    # 2. Start the query
    query = Work.query

    # 3. Apply Filter if specific type selected (Case Insensitive)
    if hair_filter and hair_filter.lower() != 'all':
        # Using ilike ensures 'curly' matches 'Curly' matches 'CURLY'
        query = query.filter(Work.hair_type.ilike(hair_filter))

    # 4. Execute Query
    works = query.order_by(Work.created_at.desc()).all()
    
    # Reviews logic remains the same
    featured_reviews = Review.query.filter_by(is_featured=True).limit(3).all()

    return render_template('index.html', works=works, reviews=featured_reviews, current_hair=hair_filter)

@app.route('/about-me')
def about_me():
    all_approved_reviews = Review.query.filter_by(is_approved=True).all()
    
    # Calculate Average Rating
    if all_approved_reviews:
        total_score = sum([r.rating for r in all_approved_reviews])
        avg_rating = round(total_score / len(all_approved_reviews), 1)
        total_count = len(all_approved_reviews)
    else:
        avg_rating = 5.0
        total_count = 0

    featured_reviews = Review.query.filter_by(is_featured=True).limit(3).all()
    return render_template('about_me.html', avg_rating=avg_rating, total_count=total_count, reviews=featured_reviews)

@app.route('/appointment', methods=['GET', 'POST'])
def appointment():
    if request.method == 'POST':
        # 1. Get Data from the HTML Form
        name = request.form.get('name')
        phone = request.form.get('phone')
        branch = request.form.get('branch')
        service = request.form.get('service')
        date = request.form.get('date')

        # 2. Validation
        if not all([name, phone, branch, service, date]):
            flash("Please fill in all fields.")
            return redirect(url_for('appointment'))

        # 3. Save to Database
        try:
            # Create new appointment object
            new_apt = Appointment(
                customer_name=name, 
                phone_number=phone, 
                branch=branch,
                service=service, 
                date_requested=date, 
                is_confirmed=False
            )
            
            db.session.add(new_apt)
            db.session.commit()
            print("✅ Data Saved to DB")

            # 4. GENERATE WHATSAPP LINK & REDIRECT
            # We create the message string
            msg = f"Hi Arpit, I am {name}. I'd like to book a {service} at your {branch} branch on {date}."
            
            # Encode it for URL (spaces become %20, etc.)
            encoded_msg = quote(msg)
            
            # Construct the full URL
            whatsapp_url = f"https://wa.me/{ARPIT_PHONE_NUMBER}?text={encoded_msg}"
            
            # Send the user to WhatsApp
            return redirect(whatsapp_url)

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {e}")
            flash("Something went wrong. Please try again.")
            return redirect(url_for('appointment'))

    return render_template('appointment.html')
    
# --- REVIEWS ROUTE (With Filters, Sort, Uploads) ---
@app.route('/reviews', methods=['GET', 'POST'])
def reviews():
    if request.method == 'POST':
        # 1. Capture Text Data
        name = request.form.get('name')
        phone = request.form.get('phone') 
        branch = request.form.get('branch')
        rating = int(request.form.get('rating'))
        content = request.form.get('content')
        work_id = request.form.get('work_id') 

        # 2. Capture Images
        img_back_file = request.files.get('image_back')
        img_front_file = request.files.get('image_front')

        # 3. Save Images using Helper
        # THIS WAS ALREADY CORRECT, KEEPS UUID
        filename_back = save_image(img_back_file)
        filename_front = save_image(img_front_file)

        # 4. Save to DB
        new_review = Review(
            customer_name=name, 
            phone_number=phone,
            branch=branch,
            rating=rating, 
            content=content, 
            image_back=filename_back,   
            image_front=filename_front, 
            is_approved=False 
        )
        
        if work_id:
            new_review.work_id = work_id
            
        db.session.add(new_review)
        db.session.commit()
        flash("Thanks you for your time!")
        return redirect(url_for('reviews'))

    # --- GET REQUEST (FILTERING & SORTING LOGIC) ---
    
    # 1. Get Query Params (e.g. ?stars=5&sort=newest)
    filter_stars = request.args.get('stars')
    sort_by = request.args.get('sort', 'kudos') # Default sort is Kudos

    # 2. Start Query (Only Approved Reviews)
    query = Review.query.filter_by(is_approved=True)

    # 3. Apply Star Filter
    if filter_stars and filter_stars != 'all':
        query = query.filter_by(rating=int(filter_stars))

    # 4. Apply Sorting
    if sort_by == 'newest':
        query = query.order_by(Review.created_at.desc())
    else:
        # Default: Most Kudos, then Newest as tie-breaker
        query = query.order_by(Review.kudos.desc(), Review.created_at.desc())

    # 5. Execute Query
    all_reviews = query.all()

    # 6. Render Template with data needed for filter UI
    return render_template('reviews.html', 
                           reviews=all_reviews, 
                           current_filter=filter_stars, 
                           current_sort=sort_by)

# --- KUDOS API ROUTE ---
@app.route('/reviews/like/<int:review_id>', methods=['POST'])
def like_review(review_id):
    review = Review.query.get_or_404(review_id)
    review.kudos += 1
    db.session.commit()
    return jsonify({'kudos': review.kudos})

# ==========================================
# 4. ADMIN AUTHENTICATION
# ==========================================

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USER and request.form.get('password') == ADMIN_PASS:
            session['admin'] = True
            return redirect(url_for('dashboard'))
        else:
            flash("Wrong credentials.")
    return render_template('admin/login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

# ==========================================
# 5. ADMIN HUB (The Navigation)
# ==========================================

@app.route('/admin/dashboard')
def dashboard():
    if not session.get('admin'): return redirect(url_for('admin_login'))
    return render_template('admin/dashboard.html')

@app.route('/admin/transformations')
def transformations_log():
    if not session.get('admin'): return redirect(url_for('admin_login'))
    works = Work.query.order_by(Work.created_at.desc()).all()
    return render_template('admin/transformations_log.html', works=works)

@app.route('/admin/reviews_log')
def reviews_log():
    if not session.get('admin'): return redirect(url_for('admin_login'))
    pending_reviews = Review.query.filter_by(is_approved=False).all()
    approved_reviews = Review.query.filter_by(is_approved=True).order_by(Review.created_at.desc()).all()
    return render_template('admin/reviews_log.html', pending_reviews=pending_reviews, approved_reviews=approved_reviews)

@app.route('/admin/appointments_log')
def view_appointments():
    if not session.get('admin'): return redirect(url_for('admin_login'))
    
    # 1. Pending Requests (Newest first)
    pending_apts = Appointment.query.filter_by(is_confirmed=False).order_by(Appointment.created_at.desc()).all()
    
    # 2. Confirmed History (Newest first)
    confirmed_apts = Appointment.query.filter_by(is_confirmed=True).order_by(Appointment.created_at.desc()).all()
    
    return render_template('admin/appointments.html', pending=pending_apts, confirmed=confirmed_apts)

@app.route('/admin/clients')
def view_clients():
    if not session.get('admin'): return redirect(url_for('admin_login'))
    
    all_apts = Appointment.query.order_by(Appointment.created_at.desc()).all()
    all_reviews = Review.query.all()
    clients_data = {}
    
    # 1. Process Appointments
    for apt in all_apts:
        if not apt.is_confirmed:
            continue
            
        phone = apt.phone_number
        if phone not in clients_data:
            clients_data[phone] = {
                'name': apt.customer_name, 
                'phone': phone, 
                'appointments': [], 
                'reviews': [], 
                'avg_rating': 0, 
                'review_count': 0
            }
        clients_data[phone]['appointments'].append(apt)
        clients_data[phone]['name'] = apt.customer_name

    # 2. Process Reviews
    for rev in all_reviews:
        phone = rev.phone_number
        if phone:
            if phone not in clients_data:
                clients_data[phone] = {'name': rev.customer_name, 'phone': phone, 'appointments': [], 'reviews': [], 'avg_rating': 0, 'review_count': 0}
            clients_data[phone]['reviews'].append(rev)

    # 3. Calculate Averages
    for phone, data in clients_data.items():
        reviews = data['reviews']
        if reviews:
            total_stars = sum([r.rating for r in reviews])
            data['avg_rating'] = round(total_stars / len(reviews), 1)
            data['review_count'] = len(reviews)
        else:
            data['avg_rating'] = "-"
            data['review_count'] = 0

    return render_template('admin/clients.html', clients=clients_data)

# --- CLIENT PROFILE ROUTE ---
@app.route('/admin/client/<path:phone>')
def client_profile(phone):
    if not session.get('admin'): return redirect(url_for('admin_login'))
    
    # Fetch all history for this specific phone number
    appointments = Appointment.query.filter_by(phone_number=phone).order_by(Appointment.created_at.desc()).all()
    reviews = Review.query.filter_by(phone_number=phone).order_by(Review.created_at.desc()).all()
    
    if not appointments and not reviews:
        flash("Client not found.")
        return redirect(url_for('view_clients'))
    
    # Get details
    name = appointments[0].customer_name if appointments else reviews[0].customer_name
    confirmed_count = len([a for a in appointments if a.is_confirmed])
    
    return render_template('admin/client_profile.html', 
                           name=name, 
                           phone=phone, 
                           appointments=appointments, 
                           reviews=reviews,
                           confirmed_count=confirmed_count)

# ==========================================
# 6. ADMIN ACTIONS (Logic Handlers)
# ==========================================

# --- Work Actions ---
@app.route('/admin/upload', methods=['POST'])
def upload_work():
    if not session.get('admin'): return redirect(url_for('admin_login'))

    title = request.form.get('title')
    hair_type = request.form.get('hair_type')
    
    # --- NEW: Capture Cost ---
    cost = request.form.get('cost')
    # -------------------------

    reel_url = request.form.get('reel_link')
    before_file = request.files.get('before_image')
    after_file = request.files.get('after_image')

    if before_file and after_file and allowed_file(before_file.filename) and allowed_file(after_file.filename):
        b_filename = save_image(before_file, 'before')
        a_filename = save_image(after_file, 'after')

        embed_link = convert_reel_to_embed(reel_url)
        
        # --- SAVE TO DB WITH COST ---
        new_work = Work(
            title=title, 
            hair_type=hair_type,
            cost=cost,  # Add this line
            before_image=b_filename, 
            after_image=a_filename, 
            reel_link=embed_link
        )
        
        db.session.add(new_work)
        db.session.commit()
        flash("Transformation Uploaded!")
    
    return redirect(url_for('transformations_log'))

@app.route('/admin/delete_work/<int:id>')
def delete_work(id):
    if not session.get('admin'): return redirect(url_for('admin_login'))
    work = Work.query.get_or_404(id)
    
    # --- IMPROVED FILE DELETION (Safely delete both) ---
    if work.before_image:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'before', work.before_image))
        except Exception as e:
            print(f"Failed to delete before image: {e}")
            
    if work.after_image:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'after', work.after_image))
        except Exception as e:
            print(f"Failed to delete after image: {e}")
            
    db.session.delete(work)
    db.session.commit()
    flash("Work deleted")
    return redirect(url_for('transformations_log'))

# --- Review Actions ---
@app.route('/admin/approve_review/<int:id>')
def approve_review(id):
    if not session.get('admin'): return redirect(url_for('admin_login'))
    review = Review.query.get_or_404(id)
    review.is_approved = True
    db.session.commit()
    return redirect(url_for('reviews_log'))

@app.route('/admin/delete_review/<int:id>')
def delete_review(id):
    if not session.get('admin'): return redirect(url_for('admin_login'))
    
    review_to_delete = Review.query.get_or_404(id)
    
    # --- DELETE IMAGES IF THEY EXIST ---
    if review_to_delete.image_back:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'reviews', review_to_delete.image_back))
        except Exception as e:
            print(f"Failed to delete review back image: {e}")

    if review_to_delete.image_front:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'reviews', review_to_delete.image_front))
        except Exception as e:
            print(f"Failed to delete review front image: {e}")
            
    db.session.delete(review_to_delete)
    db.session.commit()
    
    flash("Review deleted permanently.")
    if request.referrer:
        return redirect(request.referrer)
        
    return redirect(url_for('reviews_log'))

@app.route('/admin/toggle_feature/<int:id>')
def toggle_feature(id):
    if not session.get('admin'): return redirect(url_for('admin_login'))
    
    review = Review.query.get_or_404(id)
    review.is_featured = not review.is_featured
    db.session.commit()
    
    if request.referrer:
        return redirect(request.referrer)

    return redirect(url_for('reviews_log'))

# --- Appointment Actions ---
@app.route('/admin/confirm_appointment/<int:id>')
def confirm_appointment(id):
    if not session.get('admin'): return redirect(url_for('admin_login'))
    apt = Appointment.query.get_or_404(id)
    apt.is_confirmed = True
    db.session.commit()
    flash("Appointment Confirmed! Added to Client Database.")
    return redirect(url_for('view_appointments'))

@app.route('/admin/delete_appointment/<int:id>')
def delete_appointment(id):
    if not session.get('admin'): return redirect(url_for('admin_login'))
    apt = Appointment.query.get_or_404(id)
    db.session.delete(apt)
    db.session.commit()
    flash("Appointment removed.")
    return redirect(url_for('view_appointments'))

# ==========================================
# 7. ERROR HANDLERS
# ==========================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error/404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('error/403.html'), 403

@app.errorhandler(500)
def internal_server_error(e):
    db.session.rollback() # Rolls back request to prevent deadlock
    return render_template('error/500.html'), 500

@app.errorhandler(400)
def bad_request(e):
    return render_template('error/400.html'), 400

@app.errorhandler(401)
def unauthorized(e):
    return render_template('error/401.html'), 401

@app.errorhandler(405)
def method_not_allowed(e):
    return render_template('error/405.html'), 405

@app.errorhandler(413)
def request_entity_too_large(e):
    # This catches large file uploads (over 8MB)
    return render_template('error/413.html'), 413

# ==========================================
# 8. APP ENTRY POINT
# ==========================================
if __name__ == '__main__':
    app.run(debug=True)