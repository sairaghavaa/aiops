
from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
import os
from datetime import datetime
app = Flask(__name__)
app.secret_key = os.urandom(16)

# Replace these URLs with your actual API Gateway URLs
START_CONTAINER_URL = 'https://hxne0mx1c7.execute-api.eu-west-2.amazonaws.com/default/start-container-dev01-env01'
STOP_CONTAINER_URL = 'https://3n17o14t52.execute-api.eu-west-2.amazonaws.com/default/shutdown-container-dev01-env01'
LIST_IMAGES_URL = 'https://e05lpgn9h3.execute-api.eu-west-2.amazonaws.com/default/Test-POC-ECR'

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
    functionalities = ['Start and Stop Services','Deployment History Overview']  # Add more functionalities as needed
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

def is_new_image(image_pushed_at, threshold_hours=24):
    # Convert the string to a datetime object
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
            # Sort images by repository name
            images.sort(key=lambda x: x[0]['repositoryName'])
            # Sort and mark new images within each repository
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

if __name__ == '__main__':
    app.run(debug=True)

# JSON response with a list of images, each with a name and pushedAt field.