import os
import random
import datetime as dt
import re
import pandas as pd
import spotipy
import lyricsgenius
from sqlalchemy import create_engine
from spotipy.oauth2 import SpotifyClientCredentials
from app.queries import recommend_artists_query, recommend_tracks_query, top_artists3_query, top_tracks3_query, popular_artists_query, \
    popular_tracks_query, popular_genres_query, new_of_day_query
from app.dbfunc import sync_data, update_artists_and_tracks
from secrets import secrets

DATABASE_URL = secrets['DATABASE_URL']
GENIUS_TOKEN = secrets['GENIUS_TOKEN']
os.environ['SPOTIPY_CLIENT_ID'] = secrets['SPOTIPY_CLIENT_ID']
os.environ['SPOTIPY_CLIENT_SECRET'] = secrets['SPOTIPY_CLIENT_SECRET']
TRY_COUNT = 5

def get_of_the_day():
    engine = create_engine(DATABASE_URL)
    df = pd.read_sql_query('SELECT * FROM "DailyMix" ORDER BY date_created DESC LIMIT 1', engine)
    if (dt.datetime.now() - df['date_created'].item()).days >= 1:
        artist, track, lyrics = get_new_of_day()
    else:
        artist = pd.read_sql_query('SELECT * FROM "Artists" WHERE artist_id = %(i)s', engine, params={'i': df['artist_id'].item()})
        track = pd.read_sql_query('SELECT * FROM "Tracks" WHERE track_id = %(i)s', engine, params={'i': df['track_id'].item()})
        lyrics = pd.read_sql_query('SELECT * FROM "Lyrics" l JOIN "Tracks" t on l.track_id = t.track_id WHERE l.track_id = %(i)s',
                                   engine, params={'i': df['lyrics_id'].item()})
        lyrics = lyrics.iloc[0]
    return artist, track, lyrics

def get_recommendations(user_id):
    engine = create_engine(DATABASE_URL)
    df = pd.read_sql_query('SELECT last_recommended FROM "Users" WHERE user_id=%(user_id)s', engine, params={'user_id': user_id})
    if not isinstance(df['last_recommended'].min(), dt.datetime):
        df_ra, df_rt = get_new_recommendations(user_id)
    elif (dt.datetime.now() - df['last_recommended'].min()).days >= 1:
        df_ra, df_rt = get_new_recommendations(user_id)
    else:
        df_ra = pd.read_sql_query(recommend_artists_query, engine, params={'user_id': user_id})
        df_rt = pd.read_sql_query(recommend_tracks_query, engine, params={'user_id': user_id})
    engine.dispose()
    return df_ra.to_dict('records'), df_rt.to_dict('records')

def get_top_all_users(timeframe):
    engine = create_engine(DATABASE_URL)
    df_a = pd.read_sql_query(popular_artists_query, engine, params={'timeframe': timeframe})
    df_t = pd.read_sql_query(popular_tracks_query, engine, params={'timeframe': timeframe})
    df_g = pd.read_sql_query(popular_genres_query, engine, params={'timeframe': timeframe})
    df_a['rank'] = df_a.index + 1
    engine.dispose()
    return df_a, df_t, df_g

def get_new_of_day():
    engine = create_engine(DATABASE_URL)
    artist = artist_of_day()
    track = song_of_day()
    lyrics = lyrics_of_day()
    engine.execute(new_of_day_query, artist_id=artist['artist_id'].item(), track_id=track['track_id'].item(), \
        lyrics_id=lyrics['track_id'], date_created=dt.datetime.now())
    engine.execute('INSERT INTO "Lyrics" (track_id, lyrics) VALUES (%(track_id)s, %(lyrics)s)', track_id=lyrics['track_id'], \
        lyrics=lyrics['lyrics'])
    engine.dispose()
    return artist, track, lyrics

def get_new_recommendations(user_id):
    engine = create_engine(DATABASE_URL)
    # Get user's top artists and tracks
    df_a = pd.read_sql_query(top_artists3_query, engine, params={'user_id': user_id})
    df_t = pd.read_sql_query(top_tracks3_query, engine, params={'user_id': user_id})
    if len(df_a) == 0 or len(df_t) == 0:
        return None, None
    # Get recommendations
    df_ra = recommend_artists(df_a)
    df_rt = recommend_tracks(df_t)
    # Sync artists and tracks
    df_ra.drop(columns=['user_id']).to_sql('TempArtists', engine, index=False, if_exists='replace')
    df_rt.drop(columns=['user_id']).to_sql('TempTracks', engine, index=False, if_exists='replace')
    update_artists_and_tracks(engine)
    # Sync user data
    engine.execute('UPDATE "Users" SET last_recommended = %(last_recommended)s WHERE user_id = %(user_id)s', \
        last_recommended=dt.datetime.now(), user_id=user_id)
    sync_data(df_ra[['user_id', 'artist_id']], 'RecommendArtists', engine)
    sync_data(df_rt[['user_id', 'track_id']], 'RecommendTracks', engine)
    # Dispose engine
    engine.dispose()
    return df_ra, df_rt

def artist_of_day():
    engine = create_engine(DATABASE_URL)
    for i in range(TRY_COUNT):
        df = pd.read_sql_query('SELECT * FROM "Artists" TABLESAMPLE BERNOULLI(1) LIMIT 1;', engine)
        if len(df) > 0:
            engine.dispose()
            return df
    enginge.dispose()
    return None

def song_of_day():
    engine = create_engine(DATABASE_URL)
    for i in range(TRY_COUNT):
        df = pd.read_sql_query('SELECT * FROM "Tracks" TABLESAMPLE BERNOULLI(1) LIMIT 1;', engine)
        if len(df) > 0:
            engine.dispose()
            return df
    engine.dispose()
    return None

def lyrics_of_day():
    engine = create_engine(DATABASE_URL)
    for i in range(TRY_COUNT):
        df = pd.read_sql_query('SELECT * FROM "Tracks" TABLESAMPLE BERNOULLI(1) LIMIT 1;', engine)
        if len(df) > 0:
            for _, row in df.iterrows():
                if re.search('[a-zA-Z0-9]', row['track']) is not None:
                    lyrics = get_lyrics(row['track'], row['artists'].split(';')[0])
                    if isinstance(lyrics, str):
                        engine.dispose()
                        row['lyrics'] = lyrics
                        return row
    engine.dispose()
    return None

def recommend_artists(df):
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    user_id = df['user_id'].unique()[0]
    recom_list = []
    seed_artists = df.loc[df['timeframe'] == 0, 'artist_id'].iloc[:10].sample(n=5).tolist()
    for seed in seed_artists:
        recom = sp.artist_related_artists(seed)
        for a in recom['artists']:
            if a['id'] not in df['artist_id'].values:
                this_recom = {
                    'user_id': user_id,
                    'artist_id': a['id'],
                    'artist': a['name'],
                    'genres': "; ".join(g for g in a['genres']),
                    'artist_url': a['external_urls']['spotify'],
                    'artist_image': a['images'][0]['url'],
                    'popularity': a['popularity']
                }
                recom_list.append(this_recom)
    df_recom = pd.DataFrame.from_dict(recom_list).drop_duplicates()
    if len(df_recom) >= 20:
        return df_recom.sample(n=20)
    else:
        return df_recom

def recommend_tracks(df):
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    user_id = df['user_id'].unique()[0]
    seed_tracks = sample_seed(df, 'track_id')
    recom = sp.recommendations(seed_tracks=seed_tracks, limit=40)
    recom_list = []
    for t in recom['tracks']:
        if t['id'] not in df['track_id'].values:
            this_recom = {
                'user_id': user_id,
                'track_id': t['id'],
                'track_id': t['id'],
                'track': t['name'],
                'artists': "; ".join(a['name'] for a in t['artists']),
                'album': t['album']['name'],
                'album_image': t['album']['images'][0]['url'],
                'release_date': t['album']['release_date'],
                'track_url': t['external_urls']['spotify']
            }
            recom_list.append(this_recom)
        if len(recom_list) >= 20:
            break
    return pd.DataFrame.from_dict(recom_list)

def get_lyrics(track, artist):
    genius = lyricsgenius.Genius(GENIUS_TOKEN)
    try:
        song = genius.search_song(track, artist)
        lyrics = '['.join(song.lyrics.split(']')).split('[')
        verse = random.choice([l for l in lyrics if len(l) > 100])
        return verse
    except:
        return None

def sample_seed(df, id_type):
    seeds = df.loc[df['timeframe'] == 0]
    if len(seeds) >= 5:
        return seeds[id_type].iloc[:10].sample(n=5).tolist()
    medium = df.loc[df['timeframe'] == 1]
    seeds = seeds.merge(medium, on=['user_id', 'rank', 'artist_id'], how='outer')\
        .drop(columns=['timeframe_x', 'timeframe_y']).drop_duplicates(subset=['artist_id']).sort_values(by='rank')
    if len(seeds) >= 5:
        return seeds[id_type].iloc[:10].sample(n=5).tolist()
    long = df.loc[df['timeframe'] == 2]
    seeds = seeds.merge(long, on=['user_id', 'rank', 'artist_id'], how='outer')\
        .drop(columns=['timeframe_y']).drop_duplicates(subset=['artist_id']).sort_values(by='rank')
    if len(seeds) >= 5:
        return seeds[id_type].iloc[:10].sample(n=5).tolist()
    return seeds[id_type].tolist()
