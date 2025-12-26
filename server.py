import os
import json
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask import render_template, redirect, url_for, flash, session
import re
from google import genai
from authlib.integrations.flask_client import OAuth
from flask import Flask, request, jsonify, send_file, send_from_directory
from datetime import datetime
from fpdf import FPDF
from docx import Document
from docx.shared import Pt
import io
import zipfile
from flask import send_file
from docx.enum.text import WD_ALIGN_PARAGRAPH
from flask_cors import CORS
import fitz  # PyMuPDF
from docx import Document
from PIL import Image
import io
from PIL import Image
import io
from flask import Flask, request, render_template
from twilio.twiml.messaging_response import MessagingResponse
from flask import request, jsonify, send_file
from flask_login import login_required, current_user
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import textwrap
import uuid
import os
import PyPDF2  
import docx as docx_reader 
import io 
import csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOPICS_CSV = os.path.join(BASE_DIR, "topics.csv")


app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
CORS(app)

app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'default-super-secret-key-change-me-immediately')
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')
app.config['GENAI_API_KEY'] = os.environ.get('GENAI_API_KEY')
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'users.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['GOOGLE_CONF_URL'] = 'https://accounts.google.com/.well-known/openid-configuration'

db = SQLAlchemy(app)

@app.context_processor
def inject_now():
    return {'now': datetime.now}

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    country_code = db.Column(db.String(5), nullable=False, default="+91")  # ✅ ADD
    phone_number = db.Column(db.String(30), unique=True, nullable=True)
    grade = db.Column(db.Integer, nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    timezone = db.Column(db.String(50), nullable=True)
    whatsapp_consent = db.Column(db.Boolean, default=False)
    newsletter_consent = db.Column(db.Boolean, default=False)
    board = db.Column(db.String(50), nullable=True)
    profile_completed = db.Column(db.Boolean, default=False)
    dob = db.Column(db.Date, nullable=True)


    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    def check_password(self, password):
        return self.password_hash and check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

class MockTest(db.Model):
    __tablename__ = "mock_test"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    duration_minutes = db.Column(db.Integer)


class MockQuestion(db.Model):
    __tablename__ = "mock_question"

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey("mock_test.id"), nullable=False)
    qno = db.Column(db.Integer)
    question_text = db.Column(db.Text)
    options_json = db.Column(db.Text)
    correct_option_index = db.Column(db.Integer)
    explanation = db.Column(db.Text)

    # ✅ ADD THESE
    def options(self):
        return json.loads(self.options_json)

    @property
    def correct_option(self):
        return self.options()[self.correct_option_index]

class MockAnswer(db.Model):
    __tablename__ = "mock_answer"

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("mock_attempt.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("mock_question.id"), nullable=False)
    selected_option = db.Column(db.Integer)

    attempt = db.relationship("MockAttempt", backref="answers")



class MockAttempt(db.Model):
    __tablename__ = "mock_attempt"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey("mock_test.id"), nullable=False)

    score = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    test = db.relationship("MockTest")  # ✅ ADD THIS LINE



def load_topics():
    topics = []
    with open('topics.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            topics.append(row)
    return topics



# ---- MOCK TEST DATA MODEL ----


@app.route('/competitive-exams')
@login_required
def competitive_exams():
    tests = MockTest.query.filter_by(category='competitive').all()
    return render_template('competitive.html', tests=tests)


@app.route('/job-exams')
@login_required
def job_exams():
    daily_tests = MockTest.query.filter_by(category='job_daily').all()
    weekly_tests = MockTest.query.filter_by(category='job_weekly').all()
    job_tests = MockTest.query.filter_by(category='job').all()

    return render_template(
        'job_exams.html',
        daily_tests=daily_tests,
        weekly_tests=weekly_tests,
        job_tests=job_tests,
        student_name=current_user.name,
        student_grade=current_user.grade,
        student_board=current_user.board
    )


def generate_gemini_questions(topic, count):

    # ✅ correct client creation (NO configure)
    client = genai.Client(
    api_key=os.environ.get("GENAI_API_KEY"))

    prompt = f"""
You are an exam question generator.

Generate {count} multiple-choice questions on:
Topic: {topic}

Rules:
- Each question must have 4 options
- Clearly specify the correct option index (0–3)
- Provide a short explanation

IMPORTANT:
- Respond with ONLY a valid JSON array
- Do NOT include explanations
- Do NOT include markdown
- Do NOT include extra text
[
  {{
    "question": "...",
    "options": ["A", "B", "C", "D"],
    "correct": 1,
    "explanation": "..."
  }}
]
"""

    response = client.models.generate_content(
        model="models/gemini-flash-latest",
        contents=prompt
    )

    try:
        return json.loads(response.text)
    except Exception as e:
        print("❌ Gemini JSON parse error:", e)
        print("RAW RESPONSE ↓↓↓")
        print(response.text)
        return []


@app.route("/start-test", methods=["POST"])
@login_required
def start_test():
    test_type = request.form.get("test_type", "job_daily")
    topic = request.form.get("topic")                     # MAJOR topic
    minor_topic = request.form.get("minor_topic")         # ✅ ADD (OPTIONAL)
    count = int(request.form.get("question_count", 5))

    # 🚨 HARD VALIDATION (MUST)
    if not topic:
        flash("Please select a topic before starting the test.", "warning")
        return redirect(url_for("job_exams"))

    # ✅ FINAL TOPIC SELECTION (SAFE FALLBACK)
    final_topic = minor_topic if minor_topic else topic   # ✅ ADD

    try:
        questions = generate_gemini_questions(final_topic, count)  # ✅ USE final_topic
    except Exception as e:
        print("❌ Gemini error:", e)
        flash("AI service is temporarily unavailable. Please try again later.", "danger")
        return redirect(url_for("job_exams"))

    # 🚨 EMPTY RESULT CHECK
    if not questions or len(questions) == 0:
        flash("Could not generate questions. Try again after some time.", "danger")
        return redirect(url_for("job_exams"))

    # ✅ Create Test
    test = MockTest(
        title=f"{final_topic} Test",                       # ✅ USE final_topic
        category=test_type,
        duration_minutes=10
    )
    db.session.add(test)
    db.session.flush()

    # ✅ Save questions safely
    for idx, q in enumerate(questions, start=1):
        if not all(k in q for k in ("question", "options", "correct", "explanation")):
            continue

        mq = MockQuestion(
            test_id=test.id,
            qno=idx,
            question_text=q["question"],
            options_json=json.dumps(q["options"]),
            correct_option_index=int(q["correct"]),
            explanation=q["explanation"]
        )
        db.session.add(mq)

    # ✅ Create attempt
    attempt = MockAttempt(
        user_id=current_user.id,
        test_id=test.id,
        total=len(questions)
    )
    db.session.add(attempt)
    db.session.commit()

    # ✅ THIS REDIRECT WILL NOW ALWAYS WORK
    return redirect(url_for("take_test", attempt_id=attempt.id))




@app.route('/submit-test/<int:attempt_id>', methods=['POST'])
@login_required
def submit_test(attempt_id):
    attempt = MockAttempt.query.get_or_404(attempt_id)
    questions = MockQuestion.query.filter_by(test_id=attempt.test_id).all()

    score = 0

    for q in questions:
        selected = request.form.get(f"q_{q.id}")
        if selected is None:
            continue

        selected = int(selected)

        ans = MockAnswer(
            attempt_id=attempt.id,
            question_id=q.id,
            selected_option=selected
        )
        db.session.add(ans)

        if selected == q.correct_option_index:
            score += 1

    attempt.score = score
    attempt.total = len(questions)
    db.session.commit()

    return redirect(url_for("my_scores"))

@app.route("/get-topics")
@login_required
def get_topics():
    board = request.args.get("board", "").strip().lower()
    grade = str(request.args.get("grade", "")).strip()
    subject = "mathematics"

    major_topics = set()

    with open(TOPICS_CSV, newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)

        for row in reader:
            row_board = row.get("board", "").strip().lower()
            row_grade = row.get("grade", "").strip()
            row_subject = row.get("subject", "").strip().lower()
            row_major = row.get("major_topic", "").strip()

            if (
                row_board == board
                and row_grade == grade
                and row_subject == subject
                and row_major
            ):
                major_topics.add(row_major)

    return jsonify(sorted(list(major_topics)))


@app.route("/get-minor-topics")
@login_required
def get_minor_topics():
    board = request.args.get("board", "").strip().lower()
    grade = str(request.args.get("grade", "")).strip()
    subject = request.args.get("subject", "Mathematics").strip().lower()
    major_topic = request.args.get("major_topic", "").strip()

    minor_topics = set()

    if not major_topic:
        return jsonify([])

    with open(TOPICS_CSV, newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)

        for row in reader:
            row_board = row.get("board", "").strip().lower()
            row_grade = row.get("grade", "").strip()
            row_subject = row.get("subject", "").strip().lower()
            row_major = row.get("major_topic", "").strip()
            row_minor = row.get("minor_topic", "").strip()

            if (
                row_board == board
                and row_grade == grade
                and row_subject == subject
                and row_major == major_topic
                and row_minor
            ):
                minor_topics.add(row_minor)

    return jsonify(sorted(list(minor_topics)))

@app.route('/my-scores')
@login_required
def my_scores():
    attempts = (
        MockAttempt.query
        .filter_by(user_id=current_user.id)
        .order_by(MockAttempt.created_at.desc())
        .all()
    )

    rows = []
    total_score = 0
    total_questions = 0

    for idx, attempt in enumerate(attempts, start=1):
        # ✅ safer than .query.get()
        test = MockTest.query.filter_by(id=attempt.test_id).first()

        score = attempt.score or 0
        total = attempt.total or 0

        total_score += score
        total_questions += total

        rows.append({
            "sr_no": idx,
            "attempt_id": attempt.id,
            "test_title": test.title if test else "Mock Test",
            "score": score,
            "total": total,
            "date": attempt.created_at.strftime("%d %b %Y, %H:%M")
        })

    # ✅ default-safe values
    accuracy = 0
    avg_score = 0
    max_total = 0

    if total_questions > 0:
        accuracy = round((total_score / total_questions) * 100, 2)

    if rows:
        avg_score = round(total_score / len(rows), 2)
        max_total = max(row["total"] for row in rows)

    return render_template(
        "my_scores.html",
        rows=rows,
        accuracy=accuracy,
        avg_score=avg_score,
        max_total=max_total
    )


# -------------------------

# --- LOGIN MANAGER SETUP ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- OAuth Setup ---
oauth = OAuth(app)
oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url=app.config['GOOGLE_CONF_URL'],
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# --- PDF Generation Class ---
class CustomPDF(FPDF):
    def __init__(self, title, sub_info, header_text="", footer_text=""):
        super().__init__()
        self.worksheet_title = title
        self.sub_info = sub_info
        self.header_text = header_text
        self.footer_text = footer_text

    def header(self):
        # --- Custom Header Text ---
        self.set_font("Arial", "B", 10)
        self.cell(0, 8, self.header_text, 0, 1, "C")

        # --- Main Title ---
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, self.worksheet_title, 0, 1, "C")

        # --- Sub Info ---
        self.set_font("Arial", "", 10)
        sub_header_text = (
            f"Date: {self.sub_info['date']}   |   "
            f"Marks: {self.sub_info['marks']}   |   "
            f"Topic: {self.sub_info['sub-title']}"
        )
        self.cell(0, 8, sub_header_text, 0, 1, "C")
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)

        # --- Footer Left Text ---
        self.cell(0, 8, self.footer_text, 0, 0, "L")

        # --- Page Number (Right) ---
        self.cell(0, 8, f"Page {self.page_no()}", 0, 0, "R")



# --- File Creation Functions ---
def create_pdf(content, title, sub_title_info, filename="worksheet.pdf",
               header_text="", footer_text=""):
    print("Generating PDF...")
    pdf = CustomPDF(
    title,
    sub_title_info,
    header_text="MathGen - AI Worksheet Generator",
    footer_text="(c) 2025 MathGen | Generated by AI"
)
    content = content.encode("latin-1", "replace").decode("latin-1")
    pdf.add_page()
    pdf.set_font("Arial", "", 12)
    try:
        pdf.multi_cell(0, 10, content)
    except UnicodeEncodeError:
        print("Warning: Encoding issue detected in PDF generation. Using latin-1 replacement.")
        pdf.multi_cell(0, 10, content.encode('latin-1', 'replace').decode('latin-1'))
    pdf.output(filename)
    return filename

def create_docx(content, title, sub_title_info, filename="worksheet.docx"):
    print("Generating DOCX...")
    doc = Document()
    header = doc.add_heading(title, level=1)
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_header_text = f"Date: {sub_title_info['date']}   |   Marks: {sub_title_info['marks']}   |   Topic: {sub_title_info['sub-title']}"
    sub_header = doc.add_paragraph(sub_header_text)
    sub_header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("--------------------------------------------------")
    doc.add_paragraph(content)
    footer_section = doc.sections[0].footer
    if not footer_section.is_linked_to_previous:
         footer_p = footer_section.paragraphs[0] if footer_section.paragraphs else footer_section.add_paragraph()
         if footer_p:
            footer_p.text = "Generated by AI Worksheet Tool"
            footer_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    doc.save(filename)
    return filename

def create_txt(content, title, sub_title_info, filename="worksheet.txt"):
    print("Generating TXT...")

    with open(filename, "w", encoding="utf-8") as f:
        # ---------- HEADER ----------
        f.write("=" * 50 + "\n")
        f.write(f"{title}\n")
        f.write("=" * 50 + "\n\n")

        f.write(f"Date   : {sub_title_info.get('date', '')}\n")
        f.write(f"Time   : {sub_title_info.get('time', '')}\n")
        f.write(f"Marks  : {sub_title_info.get('marks', '')}\n")
        f.write(f"Topic  : {sub_title_info.get('sub-title', '')}\n")
        f.write("\n")

        # ---------- INSTRUCTIONS ----------
        f.write("-" * 50 + "\n")
        f.write("Instructions:\n")
        f.write("• Read each question carefully.\n")
        f.write("• Show your working clearly.\n")
        f.write("• Write answers in the space provided.\n")
        f.write("-" * 50 + "\n\n")

        # ---------- QUESTIONS ----------
        f.write(content.strip())
        f.write("\n\n")

        # ---------- FOOTER ----------
        f.write("-" * 50 + "\n")
        f.write("End of Worksheet\n")
        f.write("-" * 50 + "\n")

    return filename


# --- Helper functions to read uploaded files ---
def get_text_from_pdf(file_storage):
    """Extracts text from a text-based PDF file (FileStorage object)."""
    try:
        pdf_reader = PyPDF2.PdfReader(file_storage.stream)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text if text else None
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None

def get_text_from_docx(file_storage):
    """Extracts text from a DOCX file (FileStorage object)."""
    try:
        doc = docx_reader.Document(file_storage.stream)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text if text else None
    except Exception as e:
        print(f"Error reading DOCX: {e}")
        return None
    
def create_image(content, title, sub_title_info, fmt="png"):
    width, height = 1240, 1754
    margin_x, margin_y = 60, 60
    line_height = 30

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    font_title = ImageFont.truetype("DejaVuSans.ttf", 36)
    font_body = ImageFont.truetype("DejaVuSans.ttf", 22)

    y = margin_y
    draw.text((margin_x, y), title, font=font_title, fill="black")
    y += 60

    subtitle = f"Date: {sub_title_info['date']} | Marks: {sub_title_info['marks']} | Topic: {sub_title_info['sub-title']}"
    draw.text((margin_x, y), subtitle, font=font_body, fill="black")
    y += 40

    for line in content.split("\n"):
        wrapped = textwrap.wrap(line, 80) or [""]
        for w in wrapped:
            if y > height - margin_y:
                break
            draw.text((margin_x, y), w, font=font_body, fill="black")
            y += line_height

    filename = f"worksheet_{uuid.uuid4()}.{fmt}"
    img.save(filename)
    return filename

# ----------------------------------------------------

# --- Static File and Main Page Routes ---


@app.route('/')
def landing_page():
    """
    Serves the new marketing landing page.
    This page is public, so @login_required is removed.
    """
    return render_template('landing.html')

@app.route('/generator')
@login_required
def serve_index():
    return render_template(
        'index.html',
        user_grade=current_user.grade,
        user_board=current_user.board
    )

@app.route('/static/<path:filename>')
def serve_static(filename):
     return send_from_directory(app.static_folder, filename)

# --- NEW: Static Page Routes ---
@app.route('/about')
@login_required # Protect this page
def about():
    return render_template('about.html')

@app.route('/features')
@login_required # Protect this page
def features():
    return render_template('features.html')
# --- END NEW ROUTES ---


# --- AUTHENTICATION ROUTES ---
from datetime import datetime

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('serve_index'))

    errors = {}
    form = {}

    if request.method == 'POST':
        form = request.form.to_dict()

        # ---------- READ INPUT ----------
        name = form.get('name', '').strip()
        email = form.get('email', '').strip()
        phone_number_main = form.get('phone_number_main', '').strip()
        grade = form.get('grade', '').strip()
        board = form.get('board', '').strip()
        dob_str = form.get('dob', '').strip()
        password = form.get('password', '')
        confirm_password = form.get('confirm_password', '')
        country_code = form.get('country_code', '+91').strip()

        # ---------- REQUIRED ----------
        if not name:
            errors['name'] = 'Full name is required.'

        if not email:
            errors['email'] = 'Email is required.'

        if not phone_number_main:
            errors['phone'] = 'Phone number is required.'

        if not grade:
            errors['grade'] = 'Grade is required.'

        if not board:
            errors['board'] = 'Board is required.'

        if not password:
            errors['password'] = 'Password is required.'

        if not confirm_password:
            errors['confirm_password'] = 'Please confirm your password.'

        # ---------- GRADE ----------
        if grade:
            if not grade.isdigit() or not (1 <= int(grade) <= 12):
                errors['grade'] = 'Grade must be between 1 and 12.'

        # ---------- DOB (CRITICAL FIX) ----------
        dob = None
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            except ValueError:
                errors['dob'] = 'Invalid date format.'

        # ---------- PHONE ----------
        phone_digits = phone_number_main
        if phone_digits:
            if not phone_digits.isdigit():
                errors['phone'] = 'Mobile number must contain only digits.'
            elif len(phone_digits) != 10:
                errors['phone'] = 'Mobile number must be exactly 10 digits.'

        full_phone = f"{country_code}{phone_digits}"

        # ---------- EMAIL ----------
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if email and not re.match(email_regex, email):
            errors['email'] = 'Invalid email format.'

        # ---------- PASSWORD ----------
        if password:
            if len(password) < 8:
                errors['password'] = 'Must be at least 8 characters.'
            elif not re.search(r'[A-Z]', password):
                errors['password'] = 'Must contain an uppercase letter.'
            elif not re.search(r'[a-z]', password):
                errors['password'] = 'Must contain a lowercase letter.'
            elif not re.search(r'\d', password):
                errors['password'] = 'Must contain a number.'
            elif not re.search(r'[!@#$%^&*()_+=\-\[\]{};:\'",.<>/?~`]', password):
                errors['password'] = 'Must contain a special character.'

        if password and confirm_password and password != confirm_password:
            errors['confirm_password'] = 'Passwords do not match.'

        # ---------- UNIQUENESS ----------
        if email and User.query.filter_by(email=email).first():
            errors['email'] = 'Email already registered.'

        if phone_digits and User.query.filter_by(phone_number=full_phone).first():
            errors['phone'] = 'Phone number already registered.'

        # ---------- FIELD ERRORS ----------
        if errors:
            return render_template('register.html', errors=errors, form=form)

        # ---------- CREATE USER ----------
        try:
            new_user = User(
                name=name,
                email=email,
                phone_number=full_phone,
                country_code=country_code,
                grade=int(grade),
                board=board,
                dob=dob,                 # ✅ PYTHON DATE OBJECT
                profile_completed=True
            )

            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            flash('Account created successfully. Please login.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            db.session.rollback()
            print("❌ REGISTRATION ERROR:", e)
            errors['general'] = 'Unexpected server error. Please try again.'
            return render_template('register.html', errors=errors, form=form)

    return render_template('register.html', errors={}, form={})



@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('serve_index'))

    if request.method == 'POST':
        login_method = request.form.get('login_method')  # email / phone
        login_identifier = request.form.get('login_identifier', '').strip()
        password = request.form.get('password')

        if not login_identifier or not password:
            flash('Please enter both email/phone and password.', 'error')
            return redirect(url_for('login'))

        user = None

        if login_method == 'email':
            email = login_identifier.lower()
            user = User.query.filter_by(email=email).first()

        elif login_method == 'phone':
            # Normalize phone
            phone = re.sub(r'\D', '', login_identifier)
            user = User.query.filter_by(phone_number=phone).first()

            if phone.startswith('91') and len(phone) == 12:
                phone = phone[2:]

            user = User.query.filter_by(phone_number=phone).first()

        if user is None or not user.check_password(password):
            flash('Invalid email/phone or password.', 'error')
            return redirect(url_for('login'))

        login_user(user, remember=True)

        next_page = request.args.get('next')
        return redirect(next_page or url_for('serve_index'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been successfully logged out.', 'info')
    return redirect(url_for('login'))

# --- GOOGLE OAUTH LOGIN ROUTES ---
@app.route('/login/google')
def login_google():
    if not app.config.get('GOOGLE_CLIENT_ID') or not app.config.get('GOOGLE_CLIENT_SECRET'):
        flash('Google login is not configured on the server.', 'danger')
        return redirect(url_for('login'))

    return oauth.google.authorize_redirect(
        "https://mathgen.onrender.com/auth/google/callback"
    )


@app.route('/auth/google/callback')
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
        resp = oauth.google.get('https://openidconnect.googleapis.com/v1/userinfo')
        resp.raise_for_status()
        user_info = resp.json()

        email = user_info.get('email')
        name = user_info.get('name')

        user = User.query.filter_by(email=email).first()

        if not user:
            user = User(
                email=email,
                name=name,
                profile_completed=False
            )
            db.session.add(user)
            db.session.commit()

        login_user(user)

        # ✅ SEND NEW USERS TO PROFILE COMPLETION
        if not user.profile_completed:
            return redirect(url_for('profile'))

        # ✅ SEND EXISTING USERS TO GENERATOR
        return redirect(url_for('serve_index'))

    except Exception as e:
        print("GOOGLE AUTH ERROR:", e)
        flash("Google login failed", "danger")
        return redirect(url_for('login'))


from datetime import datetime
@app.route('/complete-profile', methods=['GET', 'POST'])
@login_required
def complete_profile():
    if current_user.profile_completed:
        return redirect(url_for('server_index'))

    if request.method == 'POST':
        current_user.name = request.form.get('name')

        # phone (optional but safe)
        phone = request.form.get('phone')
        if phone:
            current_user.phone_number = phone

        # grade
        grade = request.form.get('grade')
        if grade:
            current_user.grade = int(grade)

        current_user.board = request.form.get('board')

        # 🔴 DOB FIX (THIS WAS MISSING)
        dob_str = request.form.get('dob')
        if dob_str:
            current_user.dob = datetime.strptime(dob_str, "%Y-%m-%d").date()

        # ✅ mark profile complete ONLY after saving all
        current_user.profile_completed = True
        db.session.commit()

        return redirect(url_for('serve_index'))

    return render_template('complete_profile.html')



# --- PROFILE AND SETTINGS ROUTES ---

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    from datetime import datetime
    import re  # ✅ FIX: missing import
    from flask import get_flashed_messages

    get_flashed_messages() 

    if request.method == "POST":
        # -------------------------
        # Fetch & sanitize inputs
        # -------------------------
        name = request.form.get("name", "").strip()
        grade = request.form.get("grade", "").strip()
        age = request.form.get("age", "").strip()
        city = request.form.get("city", "").strip()
        postal_code = request.form.get("postal_code", "").strip()
        timezone = request.form.get("timezone", "").strip()
        dob_str = request.form.get("dob", "").strip()  # ✅ FIX: moved here

        whatsapp_consent = bool(request.form.get("whatsapp_consent"))
        newsletter_consent = bool(request.form.get("newsletter_consent"))

        # -------------------------
        # REQUIRED FIELD CHECK
        # -------------------------
        if not name or not grade or not age or not dob_str:
            flash("Please fill all required fields marked with *", "danger")
            return redirect(url_for("profile"))

        # -------------------------
        # NAME VALIDATION
        # -------------------------
        if len(name) < 2:
            flash("Name must be at least 2 characters long.", "danger")
            return redirect(url_for("profile"))

        # -------------------------
        # GRADE VALIDATION (1–12)
        # -------------------------
        if not grade.isdigit() or not (1 <= int(grade) <= 12):
            flash("Grade must be a number between 1 and 12.", "danger")
            return redirect(url_for("profile"))

        # -------------------------
        # AGE VALIDATION
        # -------------------------
        if not age.isdigit() or int(age) < 1:
            flash("Please enter a valid age.", "danger")
            return redirect(url_for("profile"))

        # -------------------------
        # DOB VALIDATION
        # -------------------------
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid Date of Birth format.", "danger")
            return redirect(url_for("profile"))

        # -------------------------
        # SAVE BASIC INFO
        # -------------------------
        current_user.name = name
        current_user.grade = int(grade)
        current_user.age = int(age)
        current_user.dob = dob
        current_user.city = city or None
        current_user.postal_code = postal_code or None
        current_user.timezone = timezone or None
        current_user.whatsapp_consent = whatsapp_consent
        current_user.newsletter_consent = newsletter_consent

        # -------------------------
        # ADD PHONE NUMBER (ONLY IF EMPTY)
        # -------------------------
        if current_user.phone_number is None:
            country_code = request.form.get("country_code")
            phone_number = request.form.get("phone_number_main", "").strip()

            if phone_number:
                if not country_code:
                    flash("Please select a country code.", "danger")
                    return redirect(url_for("profile"))

                full_phone = country_code + phone_number

                if not re.match(r'^\+\d{7,}$', full_phone):
                    flash("Invalid phone number format.", "danger")
                    return redirect(url_for("profile"))

                if User.query.filter_by(phone_number=full_phone).first():
                    flash("Phone number already registered.", "danger")
                    return redirect(url_for("profile"))

                current_user.phone_number = full_phone

        # -------------------------
        # COMMIT
        # -------------------------
        try:
            db.session.commit()
            flash("Profile updated successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash("Something went wrong. Please try again.", "danger")
            print("Profile update error:", e)

        return redirect(url_for("serve_index"))

    # GET request
    return render_template("profile.html", errors={}, form={})

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if not current_user.password_hash:
        flash('You logged in with Google and do not have a local password to change.', 'info')
        return render_template('settings.html')

    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password1 = request.form.get('new_password1')
        new_password2 = request.form.get('new_password2')

        if not current_user.check_password(old_password):
            flash('Incorrect old password.', 'danger')
            return redirect(url_for('settings'))
        if new_password1 != new_password2:
            flash('New passwords do not match.', 'warning')
            return redirect(url_for('settings'))
        if len(new_password1) < 8: flash('Password requires at least 8 characters.', 'warning'); return redirect(url_for('settings'))
        if not re.search(r'[A-Z]', new_password1): flash('Password requires at least one uppercase letter.', 'warning'); return redirect(url_for('settings'))
        if not re.search(r'[a-z]', new_password1): flash('Password requires at least one lowercase letter.', 'warning'); return redirect(url_for('settings'))
        if not re.search(r'\d', new_password1): flash('Password requires at least one digit.', 'warning'); return redirect(url_for('settings'))
        if not re.search(r'[!@#$%^&*()_+=\-\[\]{};\'\\:"|,.<>\/?~`]', new_password1): flash('Password requires at least one special character.', 'warning'); return redirect(url_for('settings'))
        if re.search(r'\s', new_password1): flash('Password cannot contain spaces.', 'warning'); return redirect(url_for('settings'))
        if current_user.check_password(new_password1):
            flash('New password cannot be the same as the old password.', 'warning')
            return redirect(url_for('settings'))

        current_user.set_password(new_password1)
        try:
            db.session.commit()
            flash('Password updated successfully!', 'success')
            return redirect(url_for('settings'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'danger')
            print(f"Error updating password: {e}")
            return redirect(url_for('settings'))

    return render_template('settings.html')


@app.route("/whatsapp_webhook", methods=['POST'])
def whatsapp_webhook():
    """This route is called by Twilio when a user sends you a message."""
    
    # 1. Get the message a user sent
    incoming_message = request.form.get('Body', '').lower()
    
    reply_text = ""
    
    # --- START OF MODIFIED LOGIC ---

    if "course" in incoming_message:
        reply_text = "Hi! We offer courses in Math, Science, and English. Which one are you interested in?"
    
    elif "price" in incoming_message:
        reply_text = "Our courses start at $100. You can find more details on our website."
    
    elif "hello" in incoming_message:
        reply_text = "Hi there! I'm the MathGen AI assistant. How can I help you with our courses today?"
    
    # --- NEW PART 1: Handle "worksheet" query ---
    elif "worksheet" in incoming_message:
        # ** REPLACE with your actual website URL **
        reply_text = "You can generate worksheets by visiting our main app at https://your-website-url.com" 
    
    # --- NEW PART 2: Updated fallback message with contact info ---
    else:
        # ** REPLACE with your real email and phone **
        reply_text = (
            "Sorry, I don't understand that query. You can ask me about 'courses' or 'prices'. \n\n"
            "For more help, please contact us at:\n"
            "📧 support@mathgen.com\n"
            "📞 +91 99999 88888"
        )
        
    # --- END OF MODIFIED LOGIC ---

    # 3. Create a reply and send it back to Twilio
    resp = MessagingResponse()
    resp.message(reply_text)
    
    return str(resp)

@app.route("/test/<int:attempt_id>")
@login_required
def take_test(attempt_id):
    attempt = MockAttempt.query.get_or_404(attempt_id)
    test = MockTest.query.get_or_404(attempt.test_id)
    questions = MockQuestion.query.filter_by(test_id=test.id).all()

    return render_template(
        "test_page.html",
        test=test,
        attempt=attempt,
        questions=questions
    )

@app.route("/review/<int:attempt_id>")
@login_required
def review_attempt(attempt_id):
    attempt = MockAttempt.query.get_or_404(attempt_id)

    if attempt.user_id != current_user.id:
        flash("Not allowed", "danger")
        return redirect(url_for("my_scores"))

    test = MockTest.query.get(attempt.test_id)
    questions = MockQuestion.query.filter_by(test_id=test.id).order_by(MockQuestion.qno).all()

    answers = {a.question_id: a.selected_option for a in attempt.answers}

    rows = []
    for q in questions:
        selected = answers.get(q.id)
        rows.append({
            "qno": q.qno,
            "question": q.question_text,
            "options": q.options(),
            "correct": q.correct_option,
            "selected": selected,
            "is_correct": selected == q.correct_option_index,
            "explanation": q.explanation 
            })

    return render_template("review.html", rows=rows, attempt=attempt, test=test)

def clean_ai_text(text):
    if not text:
        return ""

    replacements = {
        "**": "",
        "---": "",
        "\\left(": "(",
        "\\right)": ")",
        "\\frac{": "",
        "}{": "/",
        "}": "",
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    # Normalize blanks
    text = text.replace("(___)", "______________________")

    # Remove extra blank lines
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

def extract_json_from_ai(text):
    """
    Extracts JSON array from Gemini response safely
    """
    if not text:
        return None

    # Remove markdown blocks
    text = text.strip()
    text = text.replace("```json", "").replace("```", "")

    # Find first [ and last ]
    start = text.find("[")
    end = text.rfind("]")

    if start == -1 or end == -1:
        return None

    json_text = text[start:end + 1]

    try:
        return json.loads(json_text)
    except Exception:
        return None


def format_questions_for_exam(text):
    lines = []
    q_no = 1

    for block in text.split("\n"):
        block = block.strip()
        if not block:
            continue

        # Detect question lines
        if block[0].isdigit() or block.lower().startswith("q"):
            lines.append(f"\nQ{q_no}. {block}\n")
            lines.append("________________________________________\n")
            lines.append("________________________________________\n")
            lines.append("________________________________________\n")
            q_no += 1
        else:
            lines.append(block + "\n")

    return "".join(lines)

def normalize_questions(questions_json):
    """
    Converts AI JSON into clean, student-ready text blocks
    """
    lines = []
    for i, q in enumerate(questions_json, 1):
        lines.append(f"{i}) {q['question']}")
        for _ in range(q.get("answer_space_lines", 3)):
            lines.append("______________________________")
        lines.append("")  # spacing
    return "\n".join(lines)


@app.route('/generate-worksheet', methods=['GET', 'POST'])
@login_required
def generate_worksheet():

    if request.method == 'GET':
        return render_template('index.html')

    title = "Math Worksheet"
    info = {
        "date": datetime.now().strftime("%d %b %Y"),
        "time": datetime.now().strftime("%I:%M %p"),
        "marks": "___ / 50",
        "sub-title": "General"
    }

    try:
        client = genai.Client(api_key=os.environ.get("GENAI_API_KEY"))

        # =====================================================
        # FILE UPLOAD FLOW (ANSWER KEY ONLY)
        # =====================================================
        if 'worksheet_file' in request.files and request.files['worksheet_file'].filename:

            file = request.files['worksheet_file']
            filename = file.filename.lower()

            if filename.endswith('.pdf'):
                worksheet_text = get_text_from_pdf(file)

            elif filename.endswith('.docx'):
                worksheet_text = get_text_from_docx(file)

            elif filename.endswith('.txt'):
                worksheet_text = file.read().decode('utf-8', errors='ignore')

            elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                img = Image.open(file.stream)
                response = client.models.generate_content(
                    model="models/gemini-flash-latest",
                    contents=[
                        "Extract all math questions and generate ONLY the answer key.",
                        img
                    ]
                )
                answers_text = clean_ai_text(response.text)
                return send_file(
                    create_txt(answers_text, "Worksheet Answers", info),
                    as_attachment=True
                )

            else:
                return jsonify({"error": "Unsupported file type"}), 400

            if not worksheet_text.strip():
                return jsonify({"error": "Could not read worksheet"}), 400

            prompt = f"""
You are a math teacher.
Provide ONLY the answer key.
Number answers properly.

Worksheet:
{worksheet_text}
"""

            response = client.models.generate_content(
                model="models/gemini-flash-latest",
                contents=prompt
            )

            answers_text = clean_ai_text(response.text)
            # -------- CREATE PDF FILES IN MEMORY ----------
            worksheet_pdf_path = create_pdf(worksheet_text, title, info)

            solution_pdf_path = None
            if answers_text:
                solution_pdf_path = create_pdf(
                answers_text,
                f"{title} - Solutions",
                info,
                filename="solutions.pdf",
                header_text="MathGen – Solution Sheet",
                footer_text="For reference only | © 2025 MathGen"
            )



            return send_file(
                create_txt(answers_text, "Worksheet Answers", info),
                as_attachment=True
            )

        # =====================================================
        # NEW WORKSHEET GENERATION FLOW
        # =====================================================
        grade = request.form.get('grade') or current_user.grade
        board = request.form.get('board')
        topic = request.form.get('topic')
        subtopic = request.form.get('subtopic') or "General"
        difficulty = request.form.get('difficulty', 'Easy')
        output_format = request.form.get('format', 'txt')
        include_answers = request.form.get('answer_key') == '1'

        if not grade or not board or not topic:
            return jsonify({"error": "Grade, Board & Topic required"}), 400

        # 🔒 Subtraction digit control
        digit_rule = ""
        if any(op in topic.lower() for op in ["addition", "subtraction", "multiplication", "division"]):
            if "2" in subtopic:
                digit_rule = (
                    "STRICT RULE: Use ONLY 2-digit numbers (10 to 99). "
                    "DO NOT use single-digit numbers."
                )
            elif "3" in subtopic:
                digit_rule = (
                    "STRICT RULE: Use ONLY 3-digit numbers (100 to 999). "
                    "DO NOT use smaller numbers."
                )
            elif "4" in subtopic:
                digit_rule = (
                    "STRICT RULE: Use ONLY 4-digit numbers (1000 to 9999). "
                    "DO NOT use smaller numbers."
                )


        questions_prompt = f"""
You are a school mathematics teacher.

Generate EXACTLY 10 questions.

Return STRICT JSON ONLY in this format:

[
  {{
    "question": "Plain English math question.",
    "answer_space_lines": 3
  }}
]

Rules:
- No markdown
- No LaTeX
- No answers
- Student-ready worksheet questions
{digit_rule}

Context:
Grade: {grade}
Board: {board}
Topic: {topic}
Subtopic: {subtopic}
Difficulty: {difficulty}
"""

        q_response = client.models.generate_content(
            model="models/gemini-flash-latest",
            contents=questions_prompt
        )

        questions_json = extract_json_from_ai(q_response.text)

        if not questions_json or not isinstance(questions_json, list):
            print("❌ RAW GEMINI RESPONSE ↓↓↓")
            print(q_response.text)
            return jsonify({
                "error": "AI returned invalid question format. Please try again."
            }), 500


        # -------- FORMAT QUESTIONS ----------
        def normalize_questions(qs):
            lines = []
            for i, q in enumerate(qs, 1):
                lines.append(f"{i}) {q['question']}")
                for _ in range(q.get("answer_space_lines", 3)):
                    lines.append("______________________________")
                lines.append("")
            return "\n".join(lines)

        worksheet_text = normalize_questions(questions_json)

        title = f"Grade {grade} Math Worksheet"
        info["sub-title"] = subtopic

        # -------- ANSWERS ----------
        answers_text = None
        if include_answers:
            answers_prompt = f"""
Provide ONLY the answers.
Number answers correctly.

Questions:
{worksheet_text}
"""
            a_response = client.models.generate_content(
                model="models/gemini-flash-latest",
                contents=answers_prompt
            )
            answers_text = clean_ai_text(a_response.text)

        # =====================================================
        # OUTPUT
        # =====================================================
        # =====================================================
        # ZIP OUTPUT (WORKSHEET + SOLUTIONS)
        # =====================================================
        # =====================================================
        # CREATE PDF FILES
        # =====================================================
        worksheet_pdf_path = create_pdf(
            worksheet_text,
            title,
            info,
            filename="worksheet.pdf"
        )

        solution_pdf_path = None
        if answers_text:
            solution_pdf_path = create_pdf(
                answers_text,
                f"{title} - Solutions",
                info,
                filename="solutions.pdf"
            )

        # =====================================================
        # ZIP OUTPUT (WORKSHEET + SOLUTIONS)
        # =====================================================
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            with open(worksheet_pdf_path, "rb") as f:
                zipf.writestr("worksheet/Worksheet.pdf", f.read())

            if solution_pdf_path:
                with open(solution_pdf_path, "rb") as f:
                    zipf.writestr("solutions/Solutions.pdf", f.read())

        zip_buffer.seek(0)

        # (Optional cleanup)
        os.remove(worksheet_pdf_path)
        if solution_pdf_path:
            os.remove(solution_pdf_path)

        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="mathgen_worksheet.zip"
        )



    except Exception as e:
        import traceback
        traceback.print_exc()
        if "429" in str(e):
            return jsonify({"error": "AI quota exceeded. Try again later."}), 429
        return jsonify({"error": "Worksheet generation failed."}), 500




def extract_images_from_pdf(file_storage):
    images = []
    pdf = fitz.open(stream=file_storage.read(), filetype="pdf")

    for page_index in range(len(pdf)):
        page = pdf[page_index]
        image_list = page.get_images(full=True)

        for img in image_list:
            xref = img[0]
            base_image = pdf.extract_image(xref)
            image_bytes = base_image["image"]

            img_pil = Image.open(io.BytesIO(image_bytes))
            images.append(img_pil)

    return images

def extract_images_from_docx(file_storage):
    images = []
    doc = Document(file_storage)

    for rel in doc.part.rels.values():
        if "image" in rel.target_ref:
            image_bytes = rel.target_part.blob
            images.append(Image.open(io.BytesIO(image_bytes)))

    return images      

def requires_diagram(question_text):
    keywords = [
        "diagram", "figure", "graph", "number line",
        "draw", "construct", "triangle", "circle",
        "rectangle", "geometry"
    ]
    return any(k in question_text.lower() for k in keywords)

def requires_diagram(question_text):
    keywords = [
        "diagram", "figure", "graph", "number line",
        "draw", "construct", "triangle", "circle",
        "rectangle", "geometry"
    ]
    return any(k in question_text.lower() for k in keywords)

from docx.shared import Inches

def add_image_to_docx(doc, image):
    temp_path = "temp_img.png"
    image.save(temp_path)
    doc.add_picture(temp_path, width=Inches(3))

def create_image_with_diagram(content_lines, diagrams):
    img = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(img)
    
    from PIL import ImageFont

    try:
        font_body = ImageFont.truetype("DejaVuSans.ttf", 22)
    except:
        font_body = ImageFont.load_default()

    y = 40
    for i, line in enumerate(content_lines):
        draw.text((40, y), line, fill="black", font=font_body)
        y += 30

    y = 40
    for i, line in enumerate(content_lines):
        draw.text((40, y), line, fill="black", font=font_body)
        y += 30

        if i < len(diagrams):
            img.paste(diagrams[i], (40, y))
            y += diagrams[i].height + 20

    return img

def generate_triangle_diagram():
    img = Image.new("RGB", (400, 300), "white")
    draw = ImageDraw.Draw(img)

    points = [(200, 50), (80, 250), (320, 250)]
    draw.polygon(points, outline="black", width=3)

    return img


# --- Function to Create Database Tables AND SEED SAMPLE TESTS ---
def create_database(app_instance):
    with app_instance.app_context():
        print("Initializing database...")
        db.create_all()

        # Seed sample mock tests if database is empty
        if MockTest.query.count() == 0:
            print("Seeding sample mock tests...")

            # ------------------------------------
            # 1) COMPETITIVE SAMPLE TEST
            # ------------------------------------
            ct = MockTest(
                title="Competitive Aptitude - Sample 1",
                description="Short aptitude test: numbers, series, basic logic.",
                category="competitive",
                duration_minutes=20
            )
            db.session.add(ct)
            db.session.flush()

            q1 = MockQuestion(
                test_id=ct.id,
                qno=1,
                question_text="If 5x - 3 = 2, what is x?",
                options_json=json.dumps(["x = -1", "x = 1", "x = 2", "x = 0"]),
                correct_option_index=1,
                explanation="Solve 5x - 3 = 2 → 5x = 5 → x = 1."
            )
            q2 = MockQuestion(
                test_id=ct.id,
                qno=2,
                question_text="Which number comes next in the series: 2, 4, 7, 11, ?",
                options_json=json.dumps(["15", "16", "18", "14"]),
                correct_option_index=1,
                explanation="Differences: +2, +3, +4 → next +5 → 11 + 5 = 16."
            )
            db.session.add_all([q1, q2])

            # ------------------------------------
            # 2) DAILY JOB TEST
            # ------------------------------------
            daily = MockTest(
                title="Daily Job Aptitude Test",
                description="A short 10–minute daily practice test for job aspirants.",
                category="job_daily",
                duration_minutes=10
            )
            db.session.add(daily)
            db.session.flush()

            dq1 = MockQuestion(
                test_id=daily.id,
                qno=1,
                question_text="What is the next number in: 3, 6, 12, 24, ?",
                options_json=json.dumps(["36", "40", "48", "50"]),
                correct_option_index=2,
                explanation="Pattern: multiply by 2 → 24 × 2 = 48."
            )
            dq2 = MockQuestion(
                test_id=daily.id,
                qno=2,
                question_text="If the ratio of boys to girls is 3:2 and total students are 30, how many girls?",
                options_json=json.dumps(["10", "12", "14", "15"]),
                correct_option_index=1,
                explanation="3+2 = 5 parts → 30/5 = 6 per part → girls = 2×6 = 12."
            )
            db.session.add_all([dq1, dq2])

            # ------------------------------------
            # 3) WEEKLY JOB TEST
            # ------------------------------------
            weekly = MockTest(
                title="Weekly Full Job Mock Test",
                description="A longer, full–length mock test for weekly preparation.",
                category="job_weekly",
                duration_minutes=30
            )
            db.session.add(weekly)
            db.session.flush()

            wq1 = MockQuestion(
                test_id=weekly.id,
                qno=1,
                question_text="Find the odd one out: Cat, Dog, Cow, Mango.",
                options_json=json.dumps(["Cat", "Dog", "Cow", "Mango"]),
                correct_option_index=3,
                explanation="Mango is a fruit; others are animals."
            )
            wq2 = MockQuestion(
                test_id=weekly.id,
                qno=2,
                question_text="If A = 1, B = 2, Z = 26, then value of CAT?",
                options_json=json.dumps(["24", "26", "27", "29"]),
                correct_option_index=3,
                explanation="C=3, A=1, T=20 → 3+1+20 = 24."
            )
            db.session.add_all([wq1, wq2])

            # ------------------------------------
            # 4) JOB SCREENING TEST (General)
            # ------------------------------------
            jt = MockTest(
                title="Job Screening - Logical Reasoning 1",
                description="Basic reasoning and aptitude for job screening rounds.",
                category="job",
                duration_minutes=15
            )
            db.session.add(jt)
            db.session.flush()

            jq1 = MockQuestion(
                test_id=jt.id,
                qno=1,
                question_text="If all S are P and all P are Q, then:",
                options_json=json.dumps([
                    "All Q are S", "All S are Q", "Some S are not Q", "Cannot determine"
                ]),
                correct_option_index=1,
                explanation="S → P and P → Q gives S → Q."
            )
            jq2 = MockQuestion(
                test_id=jt.id,
                qno=2,
                question_text="Choose the odd one out: Apple, Mango, Carrot, Banana",
                options_json=json.dumps(["Apple", "Mango", "Carrot", "Banana"]),
                correct_option_index=2,
                explanation="Carrot is a vegetable; others are fruits."
            )
            db.session.add_all([jq1, jq2])

            # ------------------------------------
            # COMMIT ALL TESTS
            # ------------------------------------
            try:
                db.session.commit()
                print("Sample tests seeded successfully.")
            except Exception as e:
                db.session.rollback()
                print(f"Error seeding tests: {e}")

        print("Database initialized.")

# --- Main Execution Block ---
if __name__ == '__main__':
    # Check for required OAuth environment variables
    missing_vars = [var for var in ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET'] if not app.config.get(var)]
    if missing_vars:
        print("\n---!!! WARNING: Google OAuth Environment Variables Missing !!!---")
        print("Google login will not work until you set:")
        for var in missing_vars: print(f"  - {var}")
        print("-------------------------------------------------------\n")

    create_database(app) # Ensure database and tables are ready
    print("----------------------------------------------------")
    print("Flask server starting...")
    print(f"Database located at: {db_path}")
    print("Available Routes:")
    print("  - /                      (Main App - Public)")
    print("  - /login                 (Login Page)")
    print("  - /register              (Registration Page)")
    print("  - /logout                (Logout Action - Requires Login)")
    print("  - /login/google          (Initiate Google Login)")
    print("  - /auth/google/callback  (Google Callback)")
    print("  - /generate-worksheet    (API Endpoint - Requires Login)")
    print("  - /profile               (Profile Page - Requires Login)")
    print("  - /settings              (Settings Page - Requires Login)")
    print("  - /competitive-exams     (List Competitive Tests)")
    print("  - /job-exams             (List Job Screening Tests)")
    print("  - /mock-test/<test_id>   (Take a mock test)")
    print("  - /my-scores             (List your attempts)")
    print("  - /review/<attempt_id>   (Review an attempt)")
    print("----------------------------------------------------")
    app.run(debug=True, port=5000)
