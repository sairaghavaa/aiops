# loign register and dashboard start stop container

from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
import os

app = Flask(__name__)
app.secret_key = os.urandom(16)

# Replace these URLs with your actual API Gateway URLs
START_CONTAINER_URL = 'https://example.com/start'
STOP_CONTAINER_URL = 'https://example.com/stop'

# Placeholder for user storage (consider using a database in production)
users = {'admin': 'password'}

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    functionalities = ['Start and Stop Containers']  # Add more functionalities as needed
    return render_template('dashboard.html', functionalities=functionalities)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not (username and password):
            flash('Username and password are required')
        elif username in users:
            flash('Username already exists')
        else:
            users[username] = password
            flash('User registered successfully. Please login.')
            return redirect(url_for('login'))
    return render_template('register.html')

INDEX_HTML = 'index.html'

@app.route('/manage_containers', methods=['GET'])
def manage_containers():
    if 'username' not in session:
        return redirect(url_for('login'))
    # Assuming index.html is your container management page
    return render_template(INDEX_HTML)

ERROR_MESSAGE = 'You are not authorized to perform this action'

START_CONTAINER_MESSAGE = 'Starting container...'

@app.route('/start', methods=['POST'])
def start_container():
    if 'username' in session:
        requests.post(START_CONTAINER_URL, json={})  # Modify as needed
        flash(START_CONTAINER_MESSAGE)
    else:
        flash(ERROR_MESSAGE)
    return render_template(INDEX_HTML)  # Change from redirect to render_template

STOP_CONTAINER_MESSAGE = 'Stopping container...'

@app.route('/stop', methods=['POST'])
def stop_container():
    if 'username' in session:
        requests.post(STOP_CONTAINER_URL, json={})  # Modify as needed
        flash(STOP_CONTAINER_MESSAGE)
    else:
        flash(ERROR_MESSAGE)
    return render_template(INDEX_HTML)  # Change from redirect to render_template

if __name__ == '__main__':
    app.run(debug=True)
