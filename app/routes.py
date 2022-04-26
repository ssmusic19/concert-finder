import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request
from app import app, db, bcrypt
from app.forms import RegistrationForm, LoginForm, UpdateAccountForm, ConcertForm
from app.models import User, Schedule
from flask_login import login_user, current_user, logout_user, login_required
import requests
import json

@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
def home():
    form = ConcertForm()
    if form.validate_on_submit():
        city = form.city.data
        zipcode = form.zipcode.data
        if not city:
            city = None
        if not zipcode:
            zipcode = None
        return redirect(url_for('concert_list', city=city, zipcode=zipcode, artists=form.artists.data))
    return render_template('home.html', form=form)

@app.route('/about')
def about():
    return render_template('about.html', title='About')

@app.route('/concert-list', methods=['GET', 'POST'])
def concert_list():
    city = request.args.get('city', None)
    zipcode = request.args.get('zipcode', None)
    artists = request.args.getlist('artists', None)
    events = []
    event_ids = []

    if not zipcode:
        city_data = requests.get(f'https://api.songkick.com/api/3.0/search/locations.json?query={city}&apikey=p9ZCkP6HANplnMFc')
        city_data = json.loads(city_data.text)
        if len(city_data['resultsPage']['results']) != 0:
            city_id = city_data['resultsPage']['results']['location'][0]['metroArea']['id']

        for artist in artists:
            r = requests.get(f'https://api.songkick.com/api/3.0/events.json?apikey=p9ZCkP6HANplnMFc&artist_name={artist}&location=sk:{city_id}')
            r = json.loads(r.text)
            # pretty = json.dumps(r, sort_keys=False, indent=2)
            if len(r['resultsPage']['results']) != 0:
                for event in r['resultsPage']['results']['event']:
                    if event['status'] == "ok":
                        if event['id'] not in event_ids:
                            events.append([event['id'], event['displayName'], event['uri'], event['start']['date'], event['location']['city']])
                            event_ids.append(event['id'])
    return render_template('concert-list.html', title='Concert List', city=city, zipcode=zipcode, artists=artists, events=events)

@app.route('/schedule', methods=['GET', 'POST'])
@login_required
def schedule():
    schedule_data = Schedule.query.filter_by(user_id=current_user.id).all()
    schedule = []
    for event in schedule_data:
        r = requests.get(f'https://api.songkick.com/api/3.0/events/{event.event_id}.json?apikey=p9ZCkP6HANplnMFc')
        r = json.loads(r.text)
        if 'results' in r['resultsPage']:
            details = r['resultsPage']['results']['event']
            # pretty = json.dumps(r, sort_keys=False, indent=2)
            schedule.append([details['id'], details['displayName'], details['uri'], details['start']['date'], details['location']['city']])
    return render_template('schedule.html', title='My Schedule', schedule=schedule)

@app.route('/add-event', methods=['GET', 'POST'])
@login_required
def add_to_schedule():
    id = int(request.args.get('text'))
    event = Schedule(event_id=id, user_id=current_user.id)
    db.session.add(event)
    db.session.commit()
    print(event)
    flash('Event was added to your schedule!', 'success')
    return redirect(url_for('schedule'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form)
