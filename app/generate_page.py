import os
import datetime as dt
from flask import render_template
from app.dbfunc import top_to_dict
from app.userfunc import get_user_profile, get_user_top
from app.vizfunc import calculate_mainstream_score, genre_cloud_all, get_average_features, get_most_features, genre_cloud_data, \
    get_average_feature, get_most_feature
from app.comparefunc import compare_users, get_similar_artists, get_similar_tracks
from app.recofunc import get_of_the_day, get_recommendations, get_top_all_users

def dir_last_updated(folder):
    return str(max(os.path.getmtime(os.path.join(root_path, f))
                   for root_path, dirs, files in os.walk(folder)
                   for f in files))

def generate_page(html_page, **kwargs):
    return render_template(html_page, last_updated=dir_last_updated('app/static/css'), **kwargs)

def generate_profile_page(user_id, user_profile, is_user=False, public=True):
    if not public:
        return generate_page('profile.html', is_user=False, public=False, user=user_profile)
    df_a, df_t, df_g = get_user_top(user_id)
    # Mainstream meter
    mainstream_score = calculate_mainstream_score(df_a)
    top_artists = top_to_dict(df_a)
    top_tracks = top_to_dict(df_t)
    top_genres = genre_cloud_all(df_a, df_g)
    moods = get_average_features(df_t)
    topmoods = get_most_features(df_t)
    if is_user:
        return generate_page('profile.html', is_user=True, public=True, user=user_profile, artists=top_artists, tracks=top_tracks, \
                             genres=top_genres, moods=moods, topmoods=topmoods, mainstream=mainstream_score)
    else:
        return generate_page('profile.html', is_user=False, public=True, user=user_profile, artists=top_artists, tracks=top_tracks, \
                             genres=top_genres, moods=moods, topmoods=topmoods, mainstream=mainstream_score)

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
        similar_genres = genre_cloud_all(df_a, df_g)
    return generate_page('result.html', users=users, score=score, artists=similar_artists, tracks=similar_tracks, genres=similar_genres)

def generate_explore_page(user_id, field):
    ranges = {'trending': 0, 'popular': 1, 'top': 2}
    if field == 'explore':
        artists, tracks, lyrics = get_of_the_day()
        artist = artists.iloc[0]
        track = tracks.iloc[0]
        return generate_page('explore.html', no_user=user_id is None, active_page=field, artist=artist, track=track, lyrics=lyrics)
    elif field == 'recommendation' and user_id is not None:
        artists, tracks = get_recommendations(user_id)
        return generate_page('explore.html', no_user=user_id is None, active_page=field, artists=artists, tracks=tracks)
    elif field in ranges.keys():
        df_a, df_t, df_g = get_top_all_users(ranges[field])
        artists = df_a.to_dict('records')[:20]
        tracks = df_t.to_dict('records')[:20]
        genres = genre_cloud_data(df_a, df_g)
        moods = get_average_feature(df_t)
        topmoods = get_most_feature(df_t)
        return generate_page('explore.html', no_user=user_id is None, active_page=field, artists=artists, tracks=tracks, \
            genres=genres, moods=moods, topmoods=topmoods)
    return None