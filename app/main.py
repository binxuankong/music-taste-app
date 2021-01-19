import json
import requests
import spotipy
import pandas as pd
import redis
from flask import Flask, request, url_for, session, flash, redirect
from flask_session import Session
from functools import wraps
from werkzeug.exceptions import abort
from app.generate_page import generate_page, generate_profile_page, generate_match_page, generate_explore_page
from app.spotifunc import get_user_df
from app.userfunc import get_user_profile, create_new_user, update_user_profile, update_user_privacy, update_user_code
from app.comparefunc import get_user_from_code
from secrets import secrets

app = Flask(__name__)
app.secret_key = secrets['APP_SECRET_KEY']
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.from_url(secrets['REDIS_URL'])

sess = Session()
sess.init_app(app)

API_BASE = "https://accounts.spotify.com"
REDIRECT_URI = secrets['SPOTIFY_CALLBACK_URI']
CLIENT_ID = secrets['SPOTIPY_CLIENT_ID']
CLIENT_SECRET = secrets['SPOTIPY_CLIENT_SECRET']
SCOPE = secrets['SPOTIPY_SCOPE']

@app.route('/')
def index():
    return generate_page('index.html')

@app.route('/link')
def link():
    auth_url = f"{API_BASE}/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope={SCOPE}"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    session.clear()
    session.permanent = True
    code = request.args.get('code')
    auth_token_url = f"{API_BASE}/api/token"
    res = requests.post(auth_token_url, data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    })
    res_body = res.json()
    session['token'] = res_body.get('access_token')
    sp = spotipy.Spotify(auth=session['token'])
    update_user_profile(sp)
    return redirect(url_for('profile'))

@app.route('/profile')
def profile():
    if 'user_id' in session:
        user_id = session['user_id']
        user_profile = get_user_profile(user_id)
        if user_profile is None:
            return redirect(url_for('new'))
        return generate_profile_page(user_id, user_profile, is_user=True)
    elif 'token' in session:
        try:
            sp = spotipy.Spotify(auth=session['token'])
            df_user = get_user_df(sp)
            user_id = df_user['user_id'][0]
            session['user_id'] = user_id
            user_profile = get_user_profile(user_id)
            if user_profile is None:
                return redirect(url_for('new'))
            return generate_profile_page(user_id, user_profile, is_user=True)
        except:
            return generate_page('no_link.html')
    return generate_page('no_profile.html', is_user=True)

@app.route('/new')
def new():
    if 'token' in session:
        try:
            sp = spotipy.Spotify(auth=session['token'])
            user_profile = get_user_profile(session['user_id'])
            if user_profile is None:
                create_new_user(sp)
                return redirect(url_for('profile'))
        except:
            return redirect(url_for('link'))
    return redirect(url_for('link'))

def userid_required(function_to_protect):
    @wraps(function_to_protect)
    def wrapper(*args, **kwargs):
        user_id = session.get('user_id')
        if user_id:
            user = get_user_profile(user_id)
            if user:
                return function_to_protect(*args, **kwargs)
            else:
                flash("Session exists, but user does not exist (anymore)")
                return redirect(url_for('link'))
        else:
            flash("Please link your Spotify")
            return redirect(url_for('link'))
    return wrapper

def spotify_required(function_to_protect):
    @wraps(function_to_protect)
    def wrapper(*args, **kwargs):
        token = session.get('token')
        if token:
            try:
                sp = spotipy.Spotify(auth=session['token'])
                df_user = get_user_df(sp)
                user_id = df_user['user_id'][0]
                session['user_id'] = user_id
                user_profile = get_user_profile(user_id)
                if user_profile is None:
                    return redirect(url_for('new'))
                return function_to_protect(*args, **kwargs)
            except:
                flash("Spotify session expired. Please link your Spotify.")
                return redirect(url_for('link'))
        else:
            flash("Please link your Spotify.")
            return redirect(url_for('link'))
    return wrapper

@app.route('/update')
@spotify_required
def update():
    sp = spotipy.Spotify(auth=session['token'])
    update_user_profile(sp)
    return redirect(url_for('profile'))

@app.route('/privacy')
@userid_required
def privacy():
    update_user_privacy(session['user_id'])
    return redirect(url_for('profile'))

@app.route('/code')
@userid_required
def code():
    update_user_code(session['user_id'])
    return redirect(url_for('profile'))

@app.route('/user/<ref>')
def _user(ref):
    user_id = get_user_from_code(ref)
    if user_id is None:
        user_id = ref
    if 'user_id' in session:
        if session['user_id'] == user_id:
            return redirect(url_for('profile'))
    user_profile = get_user_profile(user_id)
    if user_profile is None:
        return generate_page('no_profile.html', is_user=False)
    return generate_profile_page(user_id, user_profile, is_user=False, public=user_profile['public'])

@app.route('/match', methods=('GET', 'POST'))
def match():
    if request.method == 'POST':
        code = request.form['code']
        if not code:
            flash('Code is required!')
        else:
            user_id1 = session['user_id']
            user_id2 = get_user_from_code(code)
            if user_id2 is None:
                flash('Please enter a valid code!')
            elif user_id1 == user_id2:
                return redirect(url_for('profile'))
            else:
                return generate_match_page(user_id1, user_id2)
    if 'user_id' in session:
        return generate_page('match.html', user=True)
    return generate_page('match.html', user=False)

@app.route('/match/<code>')
def match_result(code):
    if 'user_id' in session:
        user_id1 = session['user_id']
        user_id2 = get_user_from_code(code)
        if user_id2 is None:
            return generate_page('index.html')
        if user_id1 == user_id2:
            return redirect(url_for('profile'))
        return generate_match_page(user_id1, user_id2)
    return redirect(url_for('link'))

@app.route('/explore')
def explore(field='explore'):
    if 'user_id' in session and field == 'recommendation':
        user_profile = get_user_profile(session['user_id'])
        if user_profile is None:
            return redirect(url_for('new'))
        return generate_explore_page(session['user_id'], field)
    elif 'user_id' in session:
        return generate_explore_page(session['user_id'], field)
    elif field == 'recommendation':
        return generate_explore_page(None, 'explore')
    return generate_explore_page(None, field)

@app.route('/<field>')
def explore_page(field):
    if field in ['recommendation', 'trending', 'popular', 'top']:
        return explore(field)
    return redirect(url_for('index'))

@app.route('/search')
def search():
    query = request.args['search']
    print(query)