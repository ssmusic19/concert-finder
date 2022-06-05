import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request
from app import app, db, bcrypt, mail
from app.forms import RegistrationForm, LoginForm, UpdateAccountForm, ConcertForm, RequestResetForm, ResetPasswordForm
from app.models import User, Schedule, SavedArtists
from flask_login import COOKIE_HTTPONLY, login_user, current_user, logout_user, login_required
import requests
import json
from time import *
from uszipcode import SearchEngine
from datetime import datetime
from flask_mail import Message

@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
def home():
    user_city = None
    if current_user.is_authenticated:
        user_city = User.query.filter_by(id=current_user.id).first().city
    form = ConcertForm(city=user_city)

    if form.validate_on_submit():
        city = form.city.data
        zipcode = form.zipcode.data
        if not city:
            city = None
        if not zipcode:
            zipcode = None
        return redirect(url_for('concert_list', 
                                city=city, 
                                zipcode=zipcode, 
                                artists=form.artists.data, 
                                search_saved_artists=form.search_saved_artists.data,
                                save_artists=form.save_artists.data,
                                save_city = form.save_city.data,
                                start_date = form.start_date.data,
                                end_date = form.end_date.data
                                ))
    return render_template('home.html', form=form)

@app.route('/about')
def about():
    return render_template('about.html', title='About')

@app.route('/concert-list', methods=['GET', 'POST'])
def concert_list():
    city = request.args.get('city', None)
    zipcode = request.args.get('zipcode', None)
    artists = request.args.getlist('artists', None)
    search_saved_artists = request.args.get('search_saved_artists', None)
    save_artists = request.args.get('save_artists', None)
    save_city = request.args.get('save_city', None)
    start_date = request.args.get('start_date', None)
    end_date = request.args.get('end_date', None)
    saved_artists = []
    events = []
    event_ids = []
    event_names_and_dates = []
    artists = [artist.lower() for artist in artists]

    if end_date is None:
        end_date = "9999-12-31"
    if start_date is None:
        start_date = datetime.today().strftime('%Y-%m-%d')

    if search_saved_artists == 'True':
        saved_artists_data = SavedArtists.query.filter_by(user_id=current_user.id).all()
        for artist in saved_artists_data:
            artist_name = artist.artist_name.lower()
            saved_artists.append(artist_name)
            if artist_name not in artists:
                artists.append(artist_name)

    if save_city == 'True':
        current_user.city = city
        db.session.commit()

    if zipcode:
        search = SearchEngine()
        try:
            city = search.by_zipcode(zipcode).major_city
        except AttributeError:
            city = 'Null'

    city_data = requests.get(f'https://api.songkick.com/api/3.0/search/locations.json?query={city}&apikey=p9ZCkP6HANplnMFc')
    city_data = json.loads(city_data.text)
    if len(city_data['resultsPage']['results']) != 0:
        city_id = city_data['resultsPage']['results']['location'][0]['metroArea']['id']

        for artist in artists:
            if save_artists == 'True' and artist not in saved_artists:
                r = requests.get(
                    f'https://api.songkick.com/api/3.0/search/artists.json?apikey=p9ZCkP6HANplnMFc&query={artist}')
                r = json.loads(r.text)
                if len(r['resultsPage']['results']) != 0:
                    artist_id = r['resultsPage']['results']['artist'][0]['id']
                    artist_name = r['resultsPage']['results']['artist'][0]['displayName']
                    if SavedArtists.query.filter_by(user_id=current_user.id, artist_id=artist_id).first() is None:
                        saved_artist = SavedArtists(user_id=current_user.id, artist_id=artist_id, artist_name=artist_name)
                        db.session.add(saved_artist)
                        db.session.commit()
            r = requests.get(
                f'https://api.songkick.com/api/3.0/events.json?apikey=p9ZCkP6HANplnMFc&artist_name={artist}&location=sk:{city_id}&min_date={start_date}&max_date={end_date}')
            r = json.loads(r.text) # pretty = json.dumps(r, sort_keys=False, indent=2)
            if len(r['resultsPage']['results']) != 0:
                for event in r['resultsPage']['results']['event']:
                    if event['status'] == "ok":
                        display_name = event['displayName']
                        date = event['start']['date']
                        id = event['id']
                        if id not in event_ids and (display_name, date) not in event_names_and_dates:
                            events.append([event['id'], event['displayName'], event['uri'], event['start']['date'], event['location']['city']])
                            event_ids.append(event['id'])
                            event_names_and_dates.append((display_name, date))
        if not artists:
            r = requests.get(f'https://api.songkick.com/api/3.0/events.json?apikey=p9ZCkP6HANplnMFc&location=sk:{city_id}&min_date={start_date}&max_date={end_date}')
            r = json.loads(r.text)
            if len(r['resultsPage']['results']) != 0:
                total_entries = r['resultsPage']['totalEntries']
                per_page = r['resultsPage']['perPage']
                page = 1
                while page <= 4 and total_entries > 0:
                    r = requests.get(
                        f'https://api.songkick.com/api/3.0/events.json?apikey=p9ZCkP6HANplnMFc&location=sk:{city_id}&min_date={start_date}&max_date={end_date}&page={page}')
                    r = json.loads(r.text)
                    for event in r['resultsPage']['results']['event']:
                        if event['status'] == "ok":
                            display_name = event['displayName']
                            date = event['start']['date']
                            id = event['id']
                            if id not in event_ids and (display_name, date) not in event_names_and_dates:
                                events.append([id, display_name, event['uri'], date, event['location']['city']])
                                event_ids.append(id)
                                event_names_and_dates.append((display_name, date))
                    page += 1
                    total_entries -= per_page
    if not city:
        for artist in artists:
            if save_artists == 'True' and artist not in saved_artists:
                r = requests.get(
                    f'https://api.songkick.com/api/3.0/search/artists.json?apikey=p9ZCkP6HANplnMFc&query={artist}')
                r = json.loads(r.text)
                if len(r['resultsPage']['results']) != 0:
                    artist_id = r['resultsPage']['results']['artist'][0]['id']
                    artist_name = r['resultsPage']['results']['artist'][0]['displayName']
                    if SavedArtists.query.filter_by(user_id=current_user.id, artist_id=artist_id).first() is None:
                        saved_artist = SavedArtists(user_id=current_user.id, artist_id=artist_id, artist_name=artist_name)
                        db.session.add(saved_artist)
                        db.session.commit()
            r = requests.get(f'https://api.songkick.com/api/3.0/events.json?apikey=p9ZCkP6HANplnMFc&artist_name={artist}')
            r = json.loads(r.text)
            if len(r['resultsPage']['results']) != 0:
                r = requests.get(f'https://api.songkick.com/api/3.0/events.json?apikey=p9ZCkP6HANplnMFc&artist_name={artist}')
                r = json.loads(r.text)
                for event in r['resultsPage']['results']['event']:
                    if event['status'] == "ok":
                        display_name = event['displayName']
                        date = event['start']['date']
                        id = event['id']
                        if id not in event_ids and (display_name, date) not in event_names_and_dates:
                            events.append([id, display_name, event['uri'], date, event['location']['city']])
                            event_ids.append(id)
                            event_names_and_dates.append((display_name, date))
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
            details = r['resultsPage']['results']['event'] # pretty = json.dumps(r, sort_keys=False, indent=2)
            schedule.append([details['id'], details['displayName'], details['uri'], details['start']['date'], details['location']['city']])
    return render_template('schedule.html', title='My Schedule', schedule=schedule)

@app.route('/saved-artists', methods=['GET', 'POST'])
@login_required
def saved_artists():
    saved_artist_data = SavedArtists.query.filter_by(user_id=current_user.id).all()
    artists = []
    for artist in saved_artist_data:
        artists.append(artist.artist_name)
    return render_template('saved-artists.html', title='My Schedule', artists=artists)

@app.route('/add-event', methods=['GET', 'POST'])
@login_required
def add_to_schedule():
    id = int(request.args.get('event'))
    event = Schedule(event_id=id, user_id=current_user.id)
    db.session.add(event)
    db.session.commit()
    flash('Event was added to your schedule!', 'success')
    return redirect(url_for('schedule'))

@app.route('/remove-artist', methods=['GET', 'POST'])
@login_required
def remove_artist():
    artist = request.form.get('artist')
    SavedArtists.query.filter_by(user_id=current_user.id, artist_name=artist).delete()
    db.session.commit()
    return redirect(url_for('saved_artists'))

@app.route('/remove-event', methods=['GET', 'POST'])
@login_required
def remove_event():
    event_id = request.form.get('event')
    print(event_id)
    Schedule.query.filter_by(user_id=current_user.id, event_id=event_id).delete()
    db.session.commit()
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
            flash('Login Unsuccessful. Please check username and password', 'danger')
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

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request', 
                   sender=os.environ.get('EMAIL_USER'), 
                   recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
    
If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if not user:
        flash('The token is invalid or expired.', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)
