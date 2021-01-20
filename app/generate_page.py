import os
import datetime as dt
from flask import render_template
from app.dbfunc import top_to_dict
from app.userfunc import get_user_profile, get_top_artists, get_top_tracks, get_top_genres, get_music_features
from app.vizfunc import calculate_mainstream_score, genre_cloud_data, plot_genre_chart, plot_mood_gauge
from app.comparefunc import compare_users, get_similar_artists, get_similar_tracks
from app.recofunc import get_of_the_day, get_recommendations, get_top_artists_and_tracks

def dir_last_updated(folder):
    return str(max(os.path.getmtime(os.path.join(root_path, f))
                   for root_path, dirs, files in os.walk(folder)
                   for f in files))

def generate_page(html_page, **kwargs):
    return render_template(html_page, last_updated=dir_last_updated('app/static/css'), **kwargs)

def generate_profile_page(user_id, user_profile, is_user=False, public=True):
    if not public:
        return generate_page('profile.html', is_user=False, public=False, user=user_profile)
    top_artists = get_top_artists(user_id)
    top_tracks = get_top_tracks(user_id)
    top_genres = get_top_genres(user_id)
    music_features = get_music_features(user_id)
    # Mainstream meter
    mainstream_score = calculate_mainstream_score(top_artists)
    genre_data = genre_cloud_data(top_artists, top_genres)
    # To dict format
    top_artists = top_to_dict(top_artists)
    top_tracks = top_to_dict(top_tracks)
    music_features = top_to_dict(music_features)
    # Plot charts
    mood_data = plot_mood_gauge(music_features)
    if is_user:
        return generate_page('profile.html', is_user=True, public=True, user=user_profile, artists=top_artists, tracks=top_tracks, \
                             genres=genre_data, moods=mood_data, mainstream=mainstream_score)
    else:
        return generate_page('profile.html', is_user=False, public=True, user=user_profile, artists=top_artists, tracks=top_tracks, \
                             genres=genre_data, moods=mood_data, mainstream=mainstream_score)

def generate_match_page(user1, user2):
    s, df_u, df_a, df_t, df_g = compare_users(user1, user2)
    score = int(round(s * 100))
    users = df_u.to_dict('records')
    similar_artists = similar_tracks = {0: [], 1: [], 2: []}
    df_a = get_similar_artists(df_a)
    if len(df_a) > 0:
        similar_artists = top_to_dict(df_a)
    if len(df_t) > 0:
        similar_tracks = top_to_dict(get_similar_tracks(df_t))
    if len(df_g) > 0:
        similar_genres = genre_cloud_data(df_a, df_g)
    return generate_page('result.html', users=users, score=score, artists=similar_artists, tracks=similar_tracks, genres=similar_genres)

def generate_explore_page(user_id, field):
    ranges = {'trending': 0, 'popular': 1, 'top': 2}
    if field == 'explore':
        artists, tracks, lyrics = get_of_the_day()
        artist = artists.iloc[0]
        track = tracks.iloc[0]
        return generate_page('explore.html', no_user=user_id is None, active_page=field, artist=artist, track=track, lyrics=lyrics)
    elif field == 'recommendation' and user_id is not None:
        df_a, df_t = get_recommendations(user_id)
    elif field in ranges.keys():
        df_a, df_t = get_top_artists_and_tracks(ranges[field])
    else:
        return None
    artists = df_a.to_dict('records')
    tracks = df_t.to_dict('records')
    return generate_page('explore.html', no_user=user_id is None, active_page=field, artists=artists, tracks=tracks)