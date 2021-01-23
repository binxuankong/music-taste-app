import pandas as pd
import datetime as dt
import spotipy
from spotipy.oauth2 import SpotifyOAuth

RANGES = {'short_term': 0, 'medium_term': 1, 'long_term': 2}
LIMIT = 50

def get_user_df(sp):
    user = sp.me()
    df_user = pd.DataFrame({
        'user_id': user['id'],
        'display_name': user['display_name'],
        'spotify_url': user['external_urls']['spotify'],
        'image_url': user['images'][0]['url'] if len(user['images']) > 0 else None,
        'followers': user['followers']['total'],
        'date_created': dt.datetime.now(),
        'last_updated': dt.datetime.now()
    }, index=[0])
    return df_user

def get_top_artists_df(sp):
    user_id = sp.me()['id']
    top_list = []
    for r in RANGES:
        top_artists = sp.current_user_top_artists(time_range=r, limit=LIMIT)
        for i, a in enumerate(top_artists['items']):
            this_top = {
                'user_id': user_id,
                'rank': i+1,
                'artist_id': a['id'],
                'timeframe': RANGES[r],
                'artist': a['name'],
                'genres': "; ".join(g for g in a['genres']),
                'artist_url': a['external_urls']['spotify'],
                'artist_image': a['images'][0]['url'],
                'popularity': a['popularity'],
            }
            top_list.append(this_top)
    return pd.DataFrame.from_dict(top_list)

def get_top_tracks_df(sp):
    user_id = sp.me()['id']
    top_list = []
    audio_features = ['danceability', 'energy', 'loudness', 'speechiness', 'acousticness', 'instrumentalness', \
                      'liveness', 'valence', 'tempo']
    for r in RANGES:
        top_tracks = sp.current_user_top_tracks(time_range=r, limit=LIMIT)
        for i, t in enumerate(top_tracks['items']):
            this_top = {
                'user_id': user_id,
                'rank': i+1,
                'track_id': t['id'],
                'timeframe': RANGES[r],
                'track_id': t['id'],
                'track': t['name'],
                'artists': "; ".join(a['name'] for a in t['artists']),
                'album': t['album']['name'],
                'album_image': t['album']['images'][0]['url'],
                'release_date': t['album']['release_date'],
                'track_url': t['external_urls']['spotify'],
                'timeframe': RANGES[r]
            }
            top_list.append(this_top)
    return pd.DataFrame.from_dict(top_list)

def get_top_genres_df(top_artists, shift=4):
    df_genre = pd.DataFrame(columns=['user_id', 'rank', 'genre', 'points', 'timeframe'])
    user_id = top_artists[2][0]['user_id']
    top_genres_list = []
    for timeframe in RANGES.values():
        top_genres = {}
        for artist in top_artists[timeframe]:
            try:
                points = shift**2 / ((0.1 * (artist['rank'] - 1) + shift) ** 2)
                genres = artist['genres'].split(';')
                for genre in genres:
                    genre = genre.strip().title()
                    if genre in top_genres:
                        top_genres[genre] += points
                    else:
                        top_genres[genre] = points
            except:
                pass
        top_genres = {k: v for k, v in sorted(top_genres.items(), key=lambda item: item[1], reverse=True)}
        genres = [g for g in list(top_genres.keys())[:LIMIT]]
        points = [p for p in list(top_genres.values())[:LIMIT]]
        user_ids = [user_id for i in range(len(top_genres))]
        ranks = [i for i in range(1, len(top_genres)+1)]
        timeframes = [timeframe for i in range(len(top_genres))]
        df_genre = df_genre.append(pd.DataFrame(list(map(list, zip(*[user_ids, ranks, genres, points, timeframes]))), \
                                                columns=['user_id', 'rank', 'genre', 'points', 'timeframe']))
    return df_genre.reset_index(drop=True)

def get_music_features_df(sp, top_tracks):
    audio_features = ['danceability', 'energy', 'loudness', 'speechiness', 'acousticness', 'instrumentalness', \
                      'liveness', 'valence', 'tempo']
    dict_list = []
    track_ids = top_tracks['track_id'].unique().tolist()
    split = round(len(track_ids) / 3)
    for i in range(3):
        if i == 2:
            subset_ids = track_ids[i*split:]
        else:
            subset_ids = track_ids[i*split:i*split+split]
        this_features = sp.audio_features(subset_ids)
        dict_list.extend(this_features)
    df_feat = pd.DataFrame.from_dict(dict_list).rename(columns={'id': 'track_id'}).drop_duplicates()
    return df_feat

def get_recently_played_df(sp):
    user_id = sp.me()['id']
    recently_played = sp.current_user_recently_played()
    dict_list = []
    for rp in recently_played['items']:
        this_track = {
            'user_id': user_id,
            'track': rp['track']['name'],
            'artists': "; ".join(a['name'] for a in rp['track']['artists']),
            'album': rp['track']['album']['name'],
            'release_date': rp['track']['album']['release_date'],
            'track_url': rp['track']['external_urls']['spotify'],
            'played_at': rp['played_at']
        }
        dict_list.append(this_track)
    return pd.DataFrame.from_dict(dict_list)

def get_current_playlists_df(sp):
    user_id = sp.me()['id']
    user_playlists = sp.current_user_playlists()
    dict_list = []
    for pl in user_playlists['items']:
        this_playlist = {
            'user_id': user_id,
            'playlist_id': pl['id'],
            'name': pl['name'],
            'description': pl['description'],
            'owner_display_name': pl['owner']['display_name'],
            'playlist_url': pl['external_urls']['spotify'],
            'track_numbers': pl['tracks']['total']
        }
        dict_list.append(this_playlist)
    return pd.DataFrame.from_dict(dict_list)