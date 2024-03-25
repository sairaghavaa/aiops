from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
import os
from datetime import datetime
import boto3
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(16)

# Placeholder for user storage (consider using a database in production)
users = {'admin': 'password'}
roles = {'admin': 'DevOps', 'performance_tester': 'Performance Tester'}

env = None
START_CONTAINER_URL = None
STOP_CONTAINER_URL = None
LIST_IMAGES_URL = None
WHITELIST_IP_API_URL = None
SCALE_CONTAINERS_URL = None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
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
            next_url = request.args.get('next')
            return redirect(next_url or url_for('select_environment'))
        else:
            flash('Invalid username or password', 'error')
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
            flash('Username and password are required', 'error')
        elif username in users:
            flash('Username already exists', 'error')
        else:
            users[username] = password
            roles[username] = 'DevOps'
            flash('User registered successfully. Please login.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/select_environment', methods=['GET', 'POST'])
@login_required
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
            flash('Invalid environment selected', 'error')
            return render_template('select_environment.html')
        return redirect(url_for('dashboard'))
    return render_template('select_environment.html')

@app.route('/manage_containers')
@login_required
def manage_containers():
    return render_template('manage_containers.html')

@app.route('/start_container', methods=['POST'])
@login_required
def start_container():
    if START_CONTAINER_URL:
        try:
            response = requests.post(START_CONTAINER_URL, json={})
            response.raise_for_status()
            flash('Container started successfully', 'success')
        except requests.exceptions.RequestException as e:
            flash(f'Failed to start containers. Error: {str(e)}', 'error')
    else:
        flash('Please select an environment first.', 'warning')
    return redirect(url_for('manage_containers'))

@app.route('/stop_container', methods=['POST'])
@login_required
def stop_container():
    if STOP_CONTAINER_URL:
        try:
            response = requests.post(STOP_CONTAINER_URL, json={})
            response.raise_for_status()
            flash('Container stopped successfully', 'success')
        except requests.exceptions.RequestException as e:
            flash(f'Failed to stop containers. Error: {str(e)}', 'error')
    else:
        flash('Please select an environment first.', 'warning')
    return redirect(url_for('manage_containers'))

def is_new_image(image_pushed_at, threshold_hours=24):
    pushed_at_dt = datetime.strptime(image_pushed_at, "%Y-%m-%d %H:%M:%S")
    return (datetime.utcnow() - pushed_at_dt).total_seconds() < threshold_hours * 3600

@app.route('/list_images')
@login_required
def list_images():
    try:
        response = requests.get(LIST_IMAGES_URL)
        response.raise_for_status()
        images = response.json()
        images.sort(key=lambda x: x[0]['repositoryName'])
        for repository in images:
            repository.sort(key=lambda x: x['imagePushedAt'], reverse=True)
            for image in repository:
                image['isNew'] = is_new_image(image['imagePushedAt'])
        return render_template('list_images.html', images=images)
    except requests.exceptions.RequestException as e:
        flash('An error occurred while trying to fetch images.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/whitelist_ip', methods=['GET', 'POST'])
@login_required
def whitelist_ip():
    if request.method == 'POST':
        ip_address = request.form['ip_address']
        if ip_address:
            try:
                response = requests.post(WHITELIST_IP_API_URL, json={'ip_address': ip_address})
                response.raise_for_status()
                flash(response.text, 'success')
            except requests.exceptions.RequestException as e:
                flash(f'An error occurred while whitelisting the IP address: {str(e)}', 'error')
        else:
            flash('Please enter a valid IP address.', 'warning')
    return render_template('whitelist_ip.html')
@app.route('/autoscaling', methods=['GET', 'POST'])
@login_required
def autoscaling():
    if request.method == 'POST':
        action = request.form['action']
        num_instances = int(request.form['num_instances'])

        if action == 'Scale Up':
            max_instances = 12 if session['role'] == 'Performance Tester' else 4
            if num_instances > max_instances:
                flash(f'You are not allowed to scale up beyond {max_instances} instances.', 'warning')
            else:
                try:
                    response = requests.post(SCALE_CONTAINERS_URL, json={'action': 'scale_up', 'num_instances': num_instances})
                    response.raise_for_status()
                    flash(response.json()['body'], 'success')
                except requests.exceptions.RequestException as e:
                    flash(f'An error occurred while scaling up: {str(e)}', 'error')
        elif action == 'Scale Down':
            try:
                response = requests.post(SCALE_CONTAINERS_URL, json={'action': 'scale_down', 'num_instances': num_instances})
                response.raise_for_status()
                flash(response.json()['body'], 'success')
            except requests.exceptions.RequestException as e:
                flash(f'An error occurred while scaling down: {str(e)}', 'error')
    return render_template('autoscaling.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)