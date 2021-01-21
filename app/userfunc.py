import random
import pandas as pd
from sqlalchemy import create_engine
from app.codes import ADJECTIVES, NOUNS
from app.queries import user_query, top_artists_query, top_tracks_query, top_genres_query, music_features_query, user_update_query, \
    user_privacy_query, user_code_query
from app.dbfunc import sync_data, update_artists_and_tracks, top_to_dict
from app.spotifunc import get_user_df, get_top_artists_df, get_top_tracks_df, get_top_genres_df, get_music_features_df
from app.recofunc import get_new_recommendations
from secrets import secrets

TABLES = ['Users', 'RecentlyPlayed', 'CurrentPlaylists', 'TopArtists', 'TopTracks']
DATABASE_URL = secrets['DATABASE_URL']

def get_user_profile(user_id):
    try:
        engine = create_engine(DATABASE_URL)
        df_user = pd.read_sql_query(user_query, engine, params={'user_id': user_id})
        user_profile = df_user.to_dict('records')[0]
        engine.dispose()
        return user_profile
    except:
        return None

def get_user_top(user_id):
    engine = create_engine(DATABASE_URL)
    df_a = get_top_artists(user_id, engine)
    df_t = get_top_tracks(user_id, engine)
    df_g = get_top_genres(user_id, engine)
    df_m = get_music_features(user_id, engine)
    return df_a, df_t, df_g, df_m

def get_top_artists(user_id, engine):
    df = pd.read_sql_query(top_artists_query, engine, params={'user_id': user_id})
    return df

def get_top_tracks(user_id, engine):
    df = pd.read_sql_query(top_tracks_query, engine, params={'user_id': user_id})
    return df

def get_top_genres(user_id, engine):
    df = pd.read_sql_query(top_genres_query, engine, params={'user_id': user_id})
    return df

def get_music_features(user_id, engine):
    df = pd.read_sql_query(music_features_query, engine, params={'user_id': user_id})
    return df

def create_new_user(sp):
    df_user = get_user_df(sp)
    user_id = df_user['user_id'][0]
    update_user_profile(sp)
    # Create user profile
    engine = create_engine(DATABASE_URL)
    df_codes = pd.read_sql_query('SELECT code FROM "UserProfiles"', engine)
    existing_codes = df_codes['code'].unique().tolist()
    while True:
        code = random.choice(ADJECTIVES) + '-' + random.choice(NOUNS) + '-' + str(random.randint(10, 99))
        if code not in existing_codes:
            break
    df_profile = pd.DataFrame([[user_id, code, False]], columns=['user_id', 'code', 'public'])
    df_profile.to_sql('UserProfiles', engine, index=False, if_exists='append')
    # Dispose engine
    engine.dispose()

def sync_all_data(sp, engine):
    # Extract from Spotify API
    df_ta = get_top_artists_df(sp)
    df_tt = get_top_tracks_df(sp)
    df_tg = get_top_genres_df(top_to_dict(df_ta))
    df_mf, df_tf = get_music_features_df(sp, top_to_dict(df_tt))
    # Artists and tracks
    df_a = df_ta.drop(columns=['user_id', 'rank', 'timeframe']).drop_duplicates()
    df_t = df_tt.drop(columns=['user_id', 'rank', 'timeframe']).drop_duplicates()
    # Sync artists and tracks
    df_a.to_sql('TempArtists', engine, index=False, if_exists='replace')
    df_t.to_sql('TempTracks', engine, index=False, if_exists='replace')
    df_tf.to_sql('TempFeatures', engine, index=False, if_exists='replace')
    update_artists_and_tracks(engine, features=True)
    # Sync user data
    sync_data(df_ta[['user_id', 'rank', 'artist_id', 'timeframe']], 'TopArtists', engine)
    sync_data(df_tt[['user_id', 'rank', 'track_id', 'timeframe']], 'TopTracks', engine)
    sync_data(df_tg, 'TopGenres', engine)
    sync_data(df_mf, 'TopFeatures', engine)

def update_user_profile(sp):
    engine = create_engine(DATABASE_URL)
    df_user = get_user_df(sp)
    u = df_user.to_dict('records')[0]
    df_exist = pd.read_sql_query('SELECT * FROM "Users" u WHERE u.user_id = %(user_id)s', engine, \
                                 params={'user_id': u['user_id']})
    if len(df_exist) == 0:
        df_user.to_sql('Users', engine, if_exists='append', index=False)
    else:
        engine.execute(user_update_query, user_id=u['user_id'], display_name=u['display_name'], spotify_url=u['spotify_url'], \
            image_url=u['image_url'], followers=u['followers'], last_updated=u['last_updated'])
    sync_all_data(sp, engine)
    try:
        get_new_recommendations(u['user_id'])
    except:
        pass
    engine.dispose()
    return u

def update_user_privacy(user_id):
    try:
        engine = create_engine(DATABASE_URL)
        engine.execute(user_privacy_query, user_id=user_id)
        engine.dispose()
        return True
    except:
        return False

def update_user_code(user_id):
    try:
        engine = create_engine(DATABASE_URL)
        df_codes = pd.read_sql_query('SELECT code FROM "UserProfiles"', engine)
        existing_codes = df_codes['code'].unique().tolist()
        while True:
            code = random.choice(ADJECTIVES) + '-' + random.choice(NOUNS) + '-' + str(random.randint(10, 99))
            if code not in existing_codes:
                break
        engine.execute(user_code_query, user_id=user_id, code=code)
        engine.dispose()
        return True
    except:
        return False