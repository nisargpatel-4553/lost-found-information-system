from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import re
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secretkey"

# ------------------ UPLOAD FOLDER ------------------
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---------- EMAIL VALIDATION ----------
def is_valid_gmail(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@gmail\.com$'
    return re.match(pattern, email)

# ------------------ DATABASE INIT ------------------
def init_db():
    conn = sqlite3.connect('database.db')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            item_name TEXT,
            description TEXT,
            type TEXT,
            contact TEXT,
            photo TEXT
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS admin(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT
        )
    ''')

    conn.execute("INSERT OR IGNORE INTO admin (id, username, password) VALUES (1, 'admin', 'admin123')")

    conn.commit()
    conn.close()

init_db()

# ------------------ HOME ------------------
@app.route('/')
def home():
    if 'user' not in session:
        return redirect('/login')
    return render_template('index.html')

# ------------------ SIGNUP ------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if not is_valid_gmail(email):
            return "Only @gmail.com allowed!"

        conn = sqlite3.connect('database.db')
        try:
            conn.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
            conn.commit()
        except:
            return "Email already registered!"
        finally:
            conn.close()

        return redirect('/login')

    return render_template('signup.html')

# ------------------ LOGIN ------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        ).fetchone()
        conn.close()

        if user:
            session['user'] = email
            return redirect('/')
        else:
            return "Invalid Email or Password!"

    return render_template('login.html')

# ------------------ LOGOUT ------------------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

# ------------------ REPORT LOST ------------------
@app.route('/report_lost', methods=['GET', 'POST'])
def report_lost():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        item_name = request.form['item_name']
        description = request.form['description']
        contact = request.form['contact']
        email = session['user']

        photo = request.files['photo']
        filename = secure_filename(photo.filename)
        photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn = sqlite3.connect('database.db')
        conn.execute(
            "INSERT INTO items (user_email, item_name, description, type, contact, photo) VALUES (?, ?, ?, 'Lost', ?, ?)",
            (email, item_name, description, contact, filename)
        )
        conn.commit()
        conn.close()

        return redirect('/view_items')

    return render_template('report_lost.html')

# ------------------ REPORT FOUND ------------------
@app.route('/report_found', methods=['GET', 'POST'])
def report_found():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        item_name = request.form['item_name']
        description = request.form['description']
        contact = request.form['contact']
        email = session['user']

        photo = request.files['photo']
        filename = secure_filename(photo.filename)
        photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn = sqlite3.connect('database.db')
        conn.execute(
            "INSERT INTO items (user_email, item_name, description, type, contact, photo) VALUES (?, ?, ?, 'Found', ?, ?)",
            (email, item_name, description, contact, filename)
        )
        conn.commit()
        conn.close()

        return redirect('/view_items')

    return render_template('report_found.html')

# ------------------ VIEW ITEMS ------------------
@app.route('/view_items')
def view_items():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    items = conn.execute("SELECT * FROM items").fetchall()
    conn.close()

    return render_template('view_items.html', items=items)

# ------------------ ADMIN LOGIN ------------------
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        admin = conn.execute(
            "SELECT * FROM admin WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        conn.close()

        if admin:
            session['admin'] = username
            return redirect('/admin_dashboard')
        else:
            return "Invalid Admin Credentials!"

    return render_template('admin_login.html')

# ------------------ ADMIN DASHBOARD ------------------
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/admin_login')

    conn = sqlite3.connect('database.db')
    items = conn.execute("SELECT * FROM items").fetchall()
    conn.close()

    return render_template('admin_dashboard.html', items=items)
# ------------------ ADMIN DELETE ------------------
@app.route('/admin_delete/<int:id>')
def admin_delete(id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Check item exists ke nai
    cursor.execute("SELECT * FROM items WHERE id=?", (id,))
    item = cursor.fetchone()

    if item:
        cursor.execute("DELETE FROM items WHERE id=?", (id,))
        conn.commit()

    conn.close()

    return redirect(url_for('admin_dashboard'))


# ------------------ ADMIN EDIT ------------------

@app.route('/admin_edit/<int:id>', methods=['GET', 'POST'])
def admin_edit(id):

    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':

        item_name = request.form['item_name']
        description = request.form['description']
        contact = request.form['contact']
        photo = request.files['photo']

        # Get old image name
        cursor.execute("SELECT photo FROM items WHERE id=?", (id,))
        old_photo = cursor.fetchone()[0]

        filename = old_photo  # default old image

        if photo and photo.filename != "":
            filename = photo.filename
            photo.save(os.path.join('static/uploads', filename))

        cursor.execute("""
            UPDATE items
            SET item_name=?, description=?, contact=?, photo=?
            WHERE id=?
        """, (item_name, description, contact, filename, id))

        conn.commit()
        conn.close()

        return redirect(url_for('admin_dashboard'))

    cursor.execute("SELECT * FROM items WHERE id=?", (id,))
    item = cursor.fetchone()
    conn.close()

    return render_template('admin_edit.html', item=item)

# ------------------ ADMIN LOGOUT ------------------
@app.route('/admin_logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin_login')


# .........admin user name and password..............
@app.route('/admin_change_credentials', methods=['GET', 'POST'])
def admin_change_credentials():

    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        new_username = request.form['username']
        new_password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE admin SET username=?, password=? WHERE id=1",
            (new_username, new_password)
        )

        conn.commit()
        conn.close()

        # Important: session update karo
        session['admin'] = new_username

        return redirect(url_for('admin_logout'))  # force re-login

    return render_template('admin_change_credentials.html')


# ------------------ RUN APP ------------------
if __name__ == '__main__':
    app.run(debug=True)
