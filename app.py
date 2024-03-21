from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
import os
from datetime import datetime
import boto3

app = Flask(__name__)
app.secret_key = os.urandom(16)

# Placeholder for user storage (consider using a database in production)
users = {'admin': 'password'}
roles = {'admin': 'DevOps', 'performance_tester': 'Performance Tester'}

# Load environment-specific configurations
env = None
START_CONTAINER_URL = None
STOP_CONTAINER_URL = None
LIST_IMAGES_URL = None
WHITELIST_IP_API_URL = None
SCALE_CONTAINERS_URL = None

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    functionalities = ['Start and Stop Services', 'Deployment History Overview', 'Whitelist IP', 'Autoscaling']
    return render_template('dashboard.html', functionalities=functionalities)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['username'] = username
            session['role'] = roles.get(username, 'DevOps')
            return redirect(url_for('select_environment'))  # Redirect to select_environment after login
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
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
            roles[username] = 'DevOps'
            flash('User registered successfully. Please login.')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/select_environment', methods=['GET', 'POST'])
def select_environment():
    if request.method == 'POST':
        global env, START_CONTAINER_URL, STOP_CONTAINER_URL, LIST_IMAGES_URL, WHITELIST_IP_API_URL, SCALE_CONTAINERS_URL
        env = request.form['environment']
        if env == 'BF1':
            from config_bf1 import START_CONTAINER_URL, STOP_CONTAINER_URL, LIST_IMAGES_URL, WHITELIST_IP_API_URL, SCALE_CONTAINERS_URL
        elif env == 'BF2':
            from config_bf2 import START_CONTAINER_URL, STOP_CONTAINER_URL, LIST_IMAGES_URL, WHITELIST_IP_API_URL, SCALE_CONTAINERS_URL
        elif env == 'BF3':
            from config_bf3 import START_CONTAINER_URL, STOP_CONTAINER_URL, LIST_IMAGES_URL, WHITELIST_IP_API_URL, SCALE_CONTAINERS_URL
        else:
            flash('Invalid environment selected')
            return render_template('select_environment.html')
        return redirect(url_for('dashboard'))
    return render_template('select_environment.html')

INDEX_HTML = 'index.html'

@app.route('/manage_containers', methods=['GET'])
def manage_containers():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template(INDEX_HTML)

ERROR_MESSAGE = 'You are not authorized to perform this action'

START_CONTAINER_MESSAGE = 'Starting container...'

STOP_CONTAINER_MESSAGE = 'Stopping container...'


@app.route('/start', methods=['POST'])
def start_container():
    if 'username' in session and START_CONTAINER_URL:
        response = requests.post(START_CONTAINER_URL, json={})
        if response.status_code == 200:
            flash(START_CONTAINER_MESSAGE)
        else:
            flash(f'Failed to start containers. Error: {response.text}')
    else:
        if 'username' not in session:
            flash(ERROR_MESSAGE)
        else:
            flash('Please select an environment first.')
    return render_template(INDEX_HTML)

@app.route('/stop', methods=['POST'])
def stop_container():
    if 'username' in session and STOP_CONTAINER_URL:
        response = requests.post(STOP_CONTAINER_URL, json={})
        if response.status_code == 200:
            flash(STOP_CONTAINER_MESSAGE)
        else:
            flash(f'Failed to stop containers. Error: {response.text}')
    else:
        if 'username' not in session:
            flash(ERROR_MESSAGE)
        else:
            flash('Please select an environment first.')
    return render_template(INDEX_HTML)

def is_new_image(image_pushed_at, threshold_hours=24):
    pushed_at_dt = datetime.strptime(image_pushed_at, "%Y-%m-%d %H:%M:%S")
    return (datetime.utcnow() - pushed_at_dt).total_seconds() < threshold_hours * 3600

@app.route('/list_images', methods=['GET'])
def list_images():
    if 'username' not in session:
        flash('Please log in to view the images.')
        return redirect(url_for('login'))

    try:
        response = requests.get(LIST_IMAGES_URL)
        if response.status_code == 200:
            images = response.json()
            images.sort(key=lambda x: x[0]['repositoryName'])
            for repository in images:
                repository.sort(key=lambda x: x['imagePushedAt'], reverse=True)
                for image in repository:
                    image['isNew'] = is_new_image(image['imagePushedAt'])
            return render_template('list_images.html', images=images)
        else:
            flash('Could not fetch images. Please try again.')
            return redirect(url_for('dashboard'))
    except requests.exceptions.RequestException as e:
        flash('An error occurred while trying to fetch images.')
        return redirect(url_for('dashboard'))

@app.route('/whitelist_ip', methods=['GET', 'POST'])
def whitelist_ip():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        ip_address = request.form['ip_address']
        if ip_address:
            try:
                response = requests.post(WHITELIST_IP_API_URL, json={'ip_address': ip_address})
                response.raise_for_status()  # Raise an exception for non-2xx status codes
                flash(response.text)
            except requests.exceptions.RequestException as e:
                flash(f'An error occurred while whitelisting the IP address: {str(e)}')
        else:
            flash('Please enter a valid IP address.')
    return render_template('whitelist_ip.html')

@app.route('/autoscaling', methods=['GET', 'POST'])
def autoscaling():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        action = request.form['action']
        num_instances = int(request.form['num_instances'])

        if action == 'Scale Up':
            max_instances = 12 if session['role'] == 'Performance Tester' else 4
            if num_instances > max_instances:
                flash(f'You are not allowed to scale up beyond {max_instances} instances.')
            else:
                try:
                    response = requests.post(SCALE_CONTAINERS_URL, json={'action': 'scale_up', 'num_instances': num_instances})
                    response.raise_for_status()  # Raise an exception for non-2xx status codes
                    flash(response.json()['body'])
                except requests.exceptions.RequestException as e:
                    flash(f'An error occurred while scaling up: {str(e)}')
        elif action == 'Scale Down':
            try:
                response = requests.post(SCALE_CONTAINERS_URL, json={'action': 'scale_down', 'num_instances': num_instances})
                response.raise_for_status()  # Raise an exception for non-2xx status codes
                flash(response.json()['body'])
            except requests.exceptions.RequestException as e:
                flash(f'An error occurred while scaling down: {str(e)}')
    return render_template('autoscaling.html')

if __name__ == '__main__':
    app.run(debug=True)