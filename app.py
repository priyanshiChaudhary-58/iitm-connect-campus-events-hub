from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
import os
import hashlib
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'iitm_connect_secret_2025'

DB_PATH = 'iitm_connect.db'

# ─────────────────────────────────────────
#  DATABASE SETUP
# ─────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def find_event_by_name(conn, query_str):
    """Smart lookup: direct LIKE, then word-score fallback."""
    event = conn.execute(
        "SELECT * FROM events WHERE LOWER(name) LIKE ?", (f'%{query_str}%',)
    ).fetchone()
    if event:
        return event
    words = [w for w in query_str.lower().split() if len(w) > 2]
    if not words:
        return None
    all_events = conn.execute('SELECT * FROM events').fetchall()
    best, best_score = None, 0
    for ev in all_events:
        ev_name = ev['name'].lower()
        score = sum(1 for w in words if w in ev_name)
        if score > best_score:
            best, best_score = ev, score
    return best if best_score >= max(1, len(words) // 2) else None


def init_db():
    conn = get_db()
    c = conn.cursor()

    # ── Create tables if not exist (includes new columns) ──
    c.execute('''CREATE TABLE IF NOT EXISTS events (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        name                 TEXT NOT NULL,
        date                 TEXT NOT NULL,
        location             TEXT NOT NULL,
        description          TEXT,
        category             TEXT DEFAULT 'General',
        image_url            TEXT DEFAULT '',
        max_seats            INTEGER DEFAULT 100,
        is_paid              INTEGER DEFAULT 0,
        price                INTEGER DEFAULT 0,
        registration_deadline TEXT DEFAULT '',
        created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS registrations (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id       INTEGER NOT NULL,
        student_name   TEXT NOT NULL,
        email          TEXT NOT NULL,
        course         TEXT NOT NULL,
        enrollment     TEXT NOT NULL,
        user_id        INTEGER,
        registered_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (event_id) REFERENCES events(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        email       TEXT UNIQUE NOT NULL,
        password    TEXT NOT NULL,
        course      TEXT,
        enrollment  TEXT,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── Safe ALTER TABLE for existing databases ──
    existing_cols = [row[1] for row in c.execute("PRAGMA table_info(events)").fetchall()]
    new_cols = {
        'max_seats':             'INTEGER DEFAULT 100',
        'is_paid':               'INTEGER DEFAULT 0',
        'price':                 'INTEGER DEFAULT 0',
        'registration_deadline': "TEXT DEFAULT ''",
    }
    for col, col_def in new_cols.items():
        if col not in existing_cols:
            c.execute(f'ALTER TABLE events ADD COLUMN {col} {col_def}')

    # ── Seed sample events if empty ──
    c.execute('SELECT COUNT(*) FROM events')
    if c.fetchone()[0] == 0:
        sample_events = [
            ('Tech Fest 2026', '2026-08-15', 'Main Auditorium, IITM',
             'Annual technical festival featuring coding competitions, hackathons, paper presentations, and keynote talks by industry leaders. Open to all departments.',
             'Technical', 'https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=600&q=80',
             200, 0, 0, '2026-08-10'),
            ('Hackathon 24H', '2026-07-20', 'Computer Lab Block B, IITM',
             '24-hour non-stop coding challenge. Form your team, pick a problem statement, and build an innovative solution. Exciting prizes and internship opportunities for winners.',
             'Technical', 'https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=600&q=80',
             60, 0, 0, '2026-07-15'),
            ('Cultural Carnival 2026', '2026-09-10', 'Open Air Theatre, IITM',
             'Celebrate the vibrant culture of IITM with music, dance, drama, and art performances from students across all departments. Grand finale night not to be missed!',
             'Cultural', 'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=600&q=80',
             300, 0, 0, '2026-09-05'),
            ('AI & ML Workshop', '2026-05-12', 'Seminar Hall, Dept. of CS',
             'Hands-on workshop on Artificial Intelligence and Machine Learning tools. Learn real-world applications, explore emerging trends, and build your first ML model under expert guidance.',
             'Academic', 'https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=600&q=80',
             40, 1, 199, '2026-05-08'),
            ('Alumni Connect 2026', '2026-06-28', 'Conference Hall, IITM',
             'Annual alumni networking event. Interact with successful IITM alumni, attend career talks, explore placement opportunities, and build your professional network.',
             'Networking', 'https://images.unsplash.com/photo-1511578314322-379afb476865?w=600&q=80',
             80, 1, 99, '2026-06-20'),
            ('Annual Sports Meet', '2026-11-01', 'IITM Sports Ground',
             'Inter-department sports extravaganza! Compete in cricket, football, badminton, athletics, and more. Show your sporting spirit and bring glory to your department.',
             'Sports', 'https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=600&q=80',
             500, 0, 0, '2026-10-25'),
        ]
        c.executemany(
            '''INSERT INTO events
               (name, date, location, description, category, image_url,
                max_seats, is_paid, price, registration_deadline)
               VALUES (?,?,?,?,?,?,?,?,?,?)''',
            sample_events
        )

    # ── Seed admin user ──
    c.execute('SELECT COUNT(*) FROM users WHERE email = ?', ('admin@iitm.edu',))
    if c.fetchone()[0] == 0:
        pwd = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute(
            "INSERT INTO users (name, email, password, course, enrollment) VALUES (?,?,?,?,?)",
            ('Admin User', 'admin@iitm.edu', pwd, 'MCA', 'ADMIN001')
        )

    conn.commit()
    conn.close()


# ─────────────────────────────────────────
#  HELPERS & VALIDATORS
# ─────────────────────────────────────────

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

# [NEW] Validation helpers
def is_valid_email(email):
    return bool(re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email))

def is_valid_name(name):
    return bool(re.match(r'^[a-zA-Z ]{2,50}$', name.strip()))

def is_valid_enrollment(enroll):
    return enroll.isdigit()

def get_upcoming_events():
    conn  = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    rows  = conn.execute(
        'SELECT * FROM events WHERE date >= ? ORDER BY date ASC', (today,)
    ).fetchall()
    conn.close()
    return rows

def get_past_events():
    conn  = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    rows  = conn.execute(
        'SELECT * FROM events WHERE date < ? ORDER BY date DESC', (today,)
    ).fetchall()
    conn.close()
    return rows

# [NEW] Get seat info for an event
def get_seats_info(conn, event_id, max_seats):
    count = conn.execute(
        'SELECT COUNT(*) FROM registrations WHERE event_id = ?', (event_id,)
    ).fetchone()[0]
    seats_left = max(0, (max_seats or 100) - count)
    return count, seats_left


# ─────────────────────────────────────────
#  PUBLIC ROUTES
# ─────────────────────────────────────────

@app.route('/')
def index():
    upcoming = get_upcoming_events()
    past     = get_past_events()

    # [NEW] Attach seats_left and reg_count to each event
    conn = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    events_with_seats = []
    for ev in upcoming:
        reg_count, seats_left = get_seats_info(conn, ev['id'], ev['max_seats'])
        deadline_passed = bool(
            ev['registration_deadline'] and ev['registration_deadline'] < today
        )
        events_with_seats.append({
            'event': ev,
            'reg_count': reg_count,
            'seats_left': seats_left,
            'deadline_passed': deadline_passed,
            'is_full': seats_left <= 0
        })
    conn.close()
    return render_template('index.html', events=events_with_seats, past_events=past)


@app.route('/events')
def events():
    query       = request.args.get('q', '')
    category    = request.args.get('category', '')
    date_filter = request.args.get('date', '')

    conn   = get_db()
    sql    = 'SELECT * FROM events WHERE 1=1'
    params = []

    if query:
        sql += ' AND (name LIKE ? OR description LIKE ? OR location LIKE ?)'
        params += [f'%{query}%', f'%{query}%', f'%{query}%']
    if category:
        sql += ' AND category = ?'
        params.append(category)
    if date_filter:
        sql += ' AND date = ?'
        params.append(date_filter)

    sql += ' ORDER BY date ASC'
    raw_events = conn.execute(sql, params).fetchall()

    # [NEW] Attach seats info to each event
    today = datetime.now().strftime('%Y-%m-%d')
    events_with_seats = []
    for ev in raw_events:
        reg_count, seats_left = get_seats_info(conn, ev['id'], ev['max_seats'])
        deadline_passed = bool(
            ev['registration_deadline'] and ev['registration_deadline'] < today
        )
        events_with_seats.append({
            'event': ev,
            'reg_count': reg_count,
            'seats_left': seats_left,
            'deadline_passed': deadline_passed,
            'is_full': seats_left <= 0
        })
    conn.close()
    return render_template('events.html', events=events_with_seats, query=query, category=category)


@app.route('/register/<int:event_id>', methods=['GET', 'POST'])
def register(event_id):
    conn  = get_db()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    if not event:
        conn.close()
        flash('Event not found.', 'error')
        return redirect(url_for('index'))

    today = datetime.now().strftime('%Y-%m-%d')

    # [NEW] Check deadline
    if event['registration_deadline'] and event['registration_deadline'] < today:
        conn.close()
        flash('Registration deadline has passed for this event.', 'error')
        return redirect(url_for('index'))

    # [NEW] Check seats
    reg_count, seats_left = get_seats_info(conn, event_id, event['max_seats'])
    if seats_left <= 0:
        conn.close()
        flash('This event is full. No seats available.', 'error')
        return redirect(url_for('index'))

    user = None
    if 'user_id' in session:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if request.method == 'POST':
        name       = request.form.get('name', '').strip()
        email      = request.form.get('email', '').strip()
        course     = request.form.get('course', '').strip()
        enrollment = request.form.get('enrollment', '').strip()

        # [NEW] Enhanced backend validation
        errors = []
        if not name:
            errors.append('Name is required.')
        elif not is_valid_name(name):
            errors.append('Name should only contain letters and spaces (2–50 characters).')
        if not email:
            errors.append('Email is required.')
        elif not is_valid_email(email):
            errors.append('Please enter a valid email address.')
        if not course:
            errors.append('Please select your course.')
        if not enrollment:
            errors.append('Enrollment number is required.')
        elif not is_valid_enrollment(enrollment):
            errors.append('Enrollment must contain only numbers.')

        if errors:
            for err in errors:
                flash(err, 'error')
            conn.close()
            return render_template('register.html', event=event, user=user,
                                   seats_left=seats_left)

        # Duplicate check
        existing = conn.execute(
            'SELECT id FROM registrations WHERE event_id=? AND email=?', (event_id, email)
        ).fetchone()
        if existing:
            flash('You are already registered for this event!', 'warning')
            conn.close()
            return render_template('register.html', event=event, user=user,
                                   seats_left=seats_left)

        uid = session.get('user_id')
        conn.execute(
            'INSERT INTO registrations (event_id, student_name, email, course, enrollment, user_id) VALUES (?,?,?,?,?,?)',
            (event_id, name, email, course, enrollment, uid)
        )
        conn.commit()
        conn.close()
        flash(f'Successfully registered for {event["name"]}! 🎉', 'success')
        return redirect(url_for('index'))

    conn.close()
    return render_template('register.html', event=event, user=user, seats_left=seats_left)


# ─────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        # [NEW] Backend validation
        if not is_valid_email(email):
            flash('Please enter a valid email address.', 'error')
            return render_template('login.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('login.html')

        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE email = ? AND password = ?',
            (email, hash_password(password))
        ).fetchone()
        conn.close()
        if user:
            session['user_id']   = user['id']
            session['user_name'] = user['name']
            session['is_admin']  = (user['email'] == 'admin@iitm.edu')
            flash(f'Welcome back, {user["name"]}! 👋', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        name       = request.form.get('name', '').strip()
        email      = request.form.get('email', '').strip()
        password   = request.form.get('password', '').strip()
        course     = request.form.get('course', '').strip()
        enrollment = request.form.get('enrollment', '').strip()

        # [NEW] Enhanced backend validation
        errors = []
        if not name:
            errors.append('Name is required.')
        elif not is_valid_name(name):
            errors.append('Name should only contain letters and spaces (2–50 characters).')
        if not email:
            errors.append('Email is required.')
        elif not is_valid_email(email):
            errors.append('Please enter a valid email address (e.g. student@iitm.edu).')
        if not password:
            errors.append('Password is required.')
        elif len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if not course:
            errors.append('Please select your course.')
        if not enrollment:
         errors.append('Enrollment number is required.')
        elif not is_valid_enrollment(enrollment):
         errors.append('Enrollment must contain only numbers.')

        if errors:
            for err in errors:
                flash(err, 'error')
            return render_template('signup.html')

        conn = get_db()
        try:
            conn.execute(
                'INSERT INTO users (name, email, password, course, enrollment) VALUES (?,?,?,?,?)',
                (name, email, hash_password(password), course, enrollment)
            )
            conn.commit()
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            session['user_id']   = user['id']
            session['user_name'] = user['name']
            session['is_admin']  = False
            conn.close()
            flash(f'Account created! Welcome to IITM Connect, {name}! 🎓', 'success')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            conn.close()
            flash('Email already registered. Try logging in.', 'error')
    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully. See you soon! 👋', 'success')
    return redirect(url_for('index'))


# ─────────────────────────────────────────
#  [NEW] MY REGISTRATIONS
# ─────────────────────────────────────────

@app.route('/my-registrations')
def my_registrations():
    if not session.get('user_id'):
        flash('Please login to view your registrations.', 'error')
        return redirect(url_for('login'))

    conn = get_db()
    regs = conn.execute('''
        SELECT r.id, r.registered_at, r.course, r.enrollment,
               e.id as event_id, e.name as event_name, e.date,
               e.location, e.category, e.image_url, e.is_paid, e.price
        FROM registrations r
        JOIN events e ON r.event_id = e.id
        WHERE r.user_id = ?
        ORDER BY r.registered_at DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('my_registrations.html', registrations=regs)


# ─────────────────────────────────────────
#  ADMIN
# ─────────────────────────────────────────

@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        flash('Admin access required.', 'error')
        return redirect(url_for('login'))
    conn      = get_db()
    events    = conn.execute('SELECT * FROM events ORDER BY date DESC').fetchall()
    total_reg = conn.execute('SELECT COUNT(*) FROM registrations').fetchone()[0]
    total_ev  = conn.execute('SELECT COUNT(*) FROM events').fetchone()[0]
    total_usr = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]

    # [NEW] Attach seat info to each event in admin
    events_with_seats = []
    for ev in events:
        reg_count, seats_left = get_seats_info(conn, ev['id'], ev['max_seats'])
        events_with_seats.append({
            'event': ev,
            'reg_count': reg_count,
            'seats_left': seats_left
        })
    conn.close()
    return render_template('admin.html', events=events_with_seats,
                           total_reg=total_reg, total_events=total_ev, total_users=total_usr)


@app.route('/admin/add_event', methods=['POST'])
def add_event():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    name        = request.form.get('name', '').strip()
    date        = request.form.get('date', '').strip()
    location    = request.form.get('location', '').strip()
    description = request.form.get('description', '').strip()
    category    = request.form.get('category', 'General').strip()
    image_url   = request.form.get('image_url', '').strip()
    # [NEW] fields
    max_seats   = int(request.form.get('max_seats', 100) or 100)
    is_paid     = int(request.form.get('is_paid', 0))
    price       = int(request.form.get('price', 0) or 0) if is_paid else 0
    deadline    = request.form.get('registration_deadline', '').strip()

    if not all([name, date, location]):
        flash('Name, date and location are required.', 'error')
        return redirect(url_for('admin'))

    conn = get_db()
    conn.execute(
        '''INSERT INTO events
           (name, date, location, description, category, image_url,
            max_seats, is_paid, price, registration_deadline)
           VALUES (?,?,?,?,?,?,?,?,?,?)''',
        (name, date, location, description, category, image_url,
         max_seats, is_paid, price, deadline)
    )
    conn.commit()
    conn.close()
    flash(f'Event "{name}" added successfully! ✅', 'success')
    return redirect(url_for('admin'))


@app.route('/admin/delete_event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    conn.execute('DELETE FROM events WHERE id = ?', (event_id,))
    conn.execute('DELETE FROM registrations WHERE event_id = ?', (event_id,))
    conn.commit()
    conn.close()
    flash('Event deleted.', 'success')
    return redirect(url_for('admin'))


@app.route('/admin/registrations/<int:event_id>')
def view_registrations(event_id):
    if not session.get('is_admin'):
        flash('Admin access required.', 'error')
        return redirect(url_for('login'))
    conn  = get_db()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    regs  = conn.execute(
        'SELECT * FROM registrations WHERE event_id = ? ORDER BY registered_at DESC', (event_id,)
    ).fetchall()
    conn.close()
    return render_template('registrations.html', event=event, registrations=regs)


# ─────────────────────────────────────────
#  CHATBOT
# ─────────────────────────────────────────

@app.route('/api/chatbot', methods=['POST'])
def chatbot():
    data     = request.get_json()
    user_msg = data.get('message', '').strip().lower()

    if not user_msg:
        return jsonify({'reply': 'Please type something so I can help you! 😊'})

    conn  = get_db()
    today = datetime.now().strftime('%Y-%m-%d')

    if any(g in user_msg for g in ['hi', 'hello', 'hey', 'hii', 'namaste', 'good morning', 'good evening', 'sup', 'yo']):
        conn.close()
        return jsonify({'reply': (
            'Hey there! 👋 Welcome to IITM Connect!\n\n'
            'I can help you with:\n'
            '• "Show all events"\n'
            '• "When is Tech Fest?"\n'
            '• "Where is Hackathon?"\n'
            '• "Tell me about AI Workshop"\n'
            '• "How to register?"\n\n'
            'What would you like to know? 🎓'
        )})

    if any(w in user_msg for w in ['help', 'what can you do', 'commands', 'options']):
        conn.close()
        return jsonify({'reply': (
            '🤖 IITM Connect Bot — Commands:\n\n'
            '📅 "Show all events"\n'
            '🔍 "When is [event name]?"\n'
            '📍 "Where is [event name]?"\n'
            '📝 "Tell me about [event name]"\n'
            '🗂 "Show technical/cultural/sports events"\n'
            '✅ "How to register?"\n'
            '📊 "How many events?"\n'
            '📜 "Past events"\n\n'
            'Just ask naturally — I\'ll understand! 😊'
        )})

    m = re.search(r'(when is|date of|when does|schedule of|when will)\s+(.+)', user_msg)
    if m:
        ename = m.group(2).strip().rstrip('?').strip()
        event = find_event_by_name(conn, ename)
        conn.close()
        if event:
            paid_note = f'\n💳 Fee: ₹{event["price"]}' if event['is_paid'] else '\n✅ Free Event'
            return jsonify({'reply': (
                f'Hey! 🎉 {event["name"]} is happening on:\n\n'
                f'📆 {event["date"]}\n'
                f'📍 {event["location"]}'
                f'{paid_note}\n\n'
                f'Head to the Events page to register!'
            )})
        return jsonify({'reply': f'Hmm, couldn\'t find "{ename}" 🤔\nTry "show all events"!'})

    m = re.search(r'(where is|location of|venue of|held at)\s+(.+)', user_msg)
    if m:
        ename = m.group(2).strip().rstrip('?').strip()
        event = find_event_by_name(conn, ename)
        conn.close()
        if event:
            return jsonify({'reply': (
                f'📍 {event["name"]} is being held at:\n\n'
                f'{event["location"]}\n\n'
                f'📆 Date: {event["date"]}\n\n'
                f'See you there! 🚀'
            )})
        return jsonify({'reply': 'Couldn\'t find that event 😅 Try "show all events"!'})

    m = re.search(r'(tell me about|details of|what is|info on|describe|about)\s+(.+)', user_msg)
    if m:
        ename = m.group(2).strip().rstrip('?').strip()
        event = find_event_by_name(conn, ename)
        conn.close()
        if event:
            paid_note = f'💳 Fee: ₹{event["price"]}' if event['is_paid'] else '✅ Free Event'
            return jsonify({'reply': (
                f'🎯 {event["name"]}\n\n'
                f'📆 {event["date"]}  |  📍 {event["location"]}\n'
                f'🗂 {event["category"]}  |  {paid_note}\n\n'
                f'{event["description"]}\n\n'
                f'Visit the Events page to register!'
            )})
        return jsonify({'reply': f'No event found for "{ename}".\nType "show all events"!'})

    if re.search(r'\b(how many|count|total number|number of)\b.*\bevents\b', user_msg):
        total    = conn.execute('SELECT COUNT(*) FROM events').fetchone()[0]
        upcoming = conn.execute('SELECT COUNT(*) FROM events WHERE date >= ?', (today,)).fetchone()[0]
        conn.close()
        return jsonify({'reply': (
            f'📊 IITM Event Stats:\n\n'
            f'🗂 Total: {total}\n'
            f'🔜 Upcoming: {upcoming}\n'
            f'✅ Completed: {total - upcoming}'
        )})

    if re.search(r'(show all|all events|list events|upcoming events|what events|any events)', user_msg):
        evts = conn.execute(
            'SELECT name, date, location, is_paid, price FROM events WHERE date >= ? ORDER BY date ASC LIMIT 8', (today,)
        ).fetchall()
        conn.close()
        if not evts:
            return jsonify({'reply': 'No upcoming events right now — check back soon! 📅'})
        reply = '🎉 Upcoming Events at IITM:\n\n'
        for e in evts:
            fee = f' | ₹{e["price"]}' if e['is_paid'] else ' | Free'
            reply += f'✦ {e["name"]}\n   📆 {e["date"]}  |  📍 {e["location"]}{fee}\n\n'
        reply += 'Ask me about any event for more details!'
        return jsonify({'reply': reply.strip()})

    if re.search(r'(past events|previous events|completed events|old events)', user_msg):
        evts = conn.execute(
            'SELECT name, date FROM events WHERE date < ? ORDER BY date DESC LIMIT 5', (today,)
        ).fetchall()
        conn.close()
        if not evts:
            return jsonify({'reply': 'No past events recorded yet!'})
        reply = '📜 Past IITM Events:\n\n'
        for e in evts:
            reply += f'✔ {e["name"]} — {e["date"]}\n'
        return jsonify({'reply': reply.strip()})

    cat_map = {
        r'\btechnical\b': 'Technical', r'\btech\b': 'Technical',
        r'\bcultural\b': 'Cultural',   r'\bculture\b': 'Cultural',
        r'\bsports?\b': 'Sports',
        r'\bacademics?\b': 'Academic',
        r'\bnetworking\b': 'Networking', r'\bnetwork\b': 'Networking',
    }
    for pattern, cat in cat_map.items():
        if re.search(pattern, user_msg):
            evts = conn.execute(
                'SELECT name, date, location FROM events WHERE category = ? AND date >= ? ORDER BY date ASC',
                (cat, today)
            ).fetchall()
            conn.close()
            if not evts:
                return jsonify({'reply': f'No upcoming {cat} events at the moment. Stay tuned! 🎯'})
            reply = f'🗂 {cat} Events at IITM:\n\n'
            for e in evts:
                reply += f'• {e["name"]}\n  📆 {e["date"]}  |  📍 {e["location"]}\n\n'
            return jsonify({'reply': reply.strip()})

    if re.search(r'(register|registration|sign up|enroll|join|how to)', user_msg):
        conn.close()
        return jsonify({'reply': (
            '📝 How to Register for an Event:\n\n'
            '1️⃣ Go to the Events page\n'
            '2️⃣ Find an event you like\n'
            '3️⃣ Click "Register Now"\n'
            '4️⃣ Fill Name, Email, Course & Enrollment No.\n'
            '5️⃣ Submit — you\'re in! 🎉\n\n'
            '💡 Create an account for faster registrations!'
        )})

    all_evts = conn.execute('SELECT * FROM events').fetchall()
    for event in all_evts:
        words = [w for w in event['name'].lower().split() if len(w) > 3]
        if event['name'].lower() in user_msg or any(w in user_msg for w in words):
            conn.close()
            paid_note = f'💳 Fee: ₹{event["price"]}' if event['is_paid'] else '✅ Free'
            return jsonify({'reply': (
                f'🎯 {event["name"]}\n\n'
                f'📆 {event["date"]}  |  📍 {event["location"]}\n'
                f'🗂 {event["category"]}  |  {paid_note}\n\n'
                f'{event["description"]}'
            )})

    conn.close()
    return jsonify({'reply': (
        'Hmm, I\'m not sure about that 🤔\n\n'
        'Try:\n'
        '• "Show all events"\n'
        '• "When is Tech Fest?"\n'
        '• "Where is Hackathon?"\n'
        '• "How to register?"\n\n'
        'Type "help" for all options!'
    )})


# ─────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
