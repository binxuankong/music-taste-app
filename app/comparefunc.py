import pandas as pd
from sqlalchemy import create_engine
from app.codes import ADJECTIVES, NOUNS
from app.queries import users2_query, top_artists2_query, top_tracks2_query, top_genres2_query, music_features2_query, \
    similar_artists_query, similar_tracks_query, similar_users_query
from secrets import secrets

DATABASE_URL = secrets['DATABASE_URL']
TF_WEIGHTS = {0: 6, 1: 5, 2: 4}
MU_WEIGHTS = {'artist': 4, 'track': 1, 'genre': 6, 'feature': 2}

def get_user_from_code(code):
    try:
        code_parts = code.split('-')
        if len(code_parts) != 3 or code_parts[0] not in ADJECTIVES or code_parts[1] not in NOUNS or not (0 < int(code_parts[2]) < 100):
            return None
        engine = create_engine(DATABASE_URL)
        df_u = pd.read_sql('SELECT user_id FROM "UserProfiles" WHERE code = %(code)s', engine, params={'code': code})
        if len(df_u) != 1:
            return None
        return df_u['user_id'].item()
    except:
        return None

def compare_users(u1, u2):
    # Get data
    engine = create_engine(DATABASE_URL)
    users = pd.read_sql(users2_query, engine, params={'user_ids': (u1, u2)})
    df_a = pd.read_sql(top_artists2_query, engine, params={'user_ids': (u1, u2)})
    df_t = pd.read_sql(top_tracks2_query, engine, params={'user_ids': (u1, u2)})
    df_g = pd.read_sql(top_genres2_query, engine, params={'user_ids': (u1, u2)})
    df_m = pd.read_sql(music_features2_query, engine, params={'user_ids': (u1, u2)})
    # User 1
    u1_a = df_a.loc[df_a['user_id'] == u1]
    u1_t = df_t.loc[df_t['user_id'] == u1]
    u1_g = df_g.loc[df_g['user_id'] == u1]
    u1_m = df_m.loc[df_m['user_id'] == u1]
    # User 2
    u2_a = df_a.loc[df_a['user_id'] == u2]
    u2_t = df_t.loc[df_t['user_id'] == u2]
    u2_g = df_g.loc[df_g['user_id'] == u2]
    u2_m = df_m.loc[df_m['user_id'] == u2]
    # Initialization
    final_points = 0
    similar_artists = pd.DataFrame()
    similar_tracks = pd.DataFrame()
    similar_genres = pd.DataFrame()
    # Compare
    for timeframe in TF_WEIGHTS.keys():
        tf_points = 0
        # Artist
        df_artist = get_artist_similarity(u1_a, u2_a, timeframe)
        tf_points += MU_WEIGHTS['artist'] * calculate_similarity(df_artist)
        df_artist = df_artist.loc[df_artist['points'] > 0].sort_values(by='points', ascending=False)
        df_artist['rank'] = df_artist.reset_index().index + 1
        similar_artists = similar_artists.append(df_artist)
        # Track
        df_track = get_track_similarity(u1_t, u2_t, timeframe)
        tf_points += MU_WEIGHTS['track'] * calculate_similarity(df_track)
        similar_tracks = similar_tracks.append(df_track.loc[df_track['points'] > 0])
        # Genre
        df_genre = get_genre_similarity(u1_g, u2_g, timeframe)
        tf_points += MU_WEIGHTS['genre'] * calculate_similarity(df_genre)
        similar_genres = similar_genres.append(df_genre.loc[df_genre['points'] > 0])
        # Features
        tf_points += MU_WEIGHTS['feature'] * calculate_feature_similarity(u1_m, u2_m, timeframe)
        # Timeframe overall points
        tf_points /= sum(MU_WEIGHTS.values())
        final_points += TF_WEIGHTS[timeframe] * tf_points
    # Final similarity score
    final_points /= sum(TF_WEIGHTS.values())
    return final_points, users, similar_artists, similar_tracks, similar_genres

def get_similar_users(user_id):
    df_u = pd.read_sql(similar_users_query, engine, params={'user_id': user_id})
    users = [user_id] + df_u['user_id'].tolist()
    df_a = pd.read_sql(top_artists2_query, engine, params={'user_ids': tuple(users)})
    df_t = pd.read_sql(top_tracks2_query, engine, params={'user_ids': tuple(users)})
    df_g = pd.read_sql(top_genres2_query, engine, params={'user_ids': tuple(users)})
    df_m = pd.read_sql(music_features2_query, engine, params={'user_ids': tuple(users)})
    # User
    u1_a = df_a.loc[df_a['user_id'] == user_id]
    u1_t = df_t.loc[df_t['user_id'] == user_id]
    u1_g = df_g.loc[df_g['user_id'] == user_id]
    u1_m = df_m.loc[df_m['user_id'] == user_id]
    dict_list = []
    # For each other user
    for _, row in df_u.iterrows():
        u2 = row['user_id']
        u2_a = df_a.loc[df_a['user_id'] == u2]
        u2_t = df_t.loc[df_t['user_id'] == u2]
        u2_g = df_g.loc[df_g['user_id'] == u2]
        u2_m = df_m.loc[df_m['user_id'] == u2]
        points = 0
        # Compare
        for timeframe in TF_WEIGHTS.keys():
            tf_points = 0
            df_artist = get_artist_similarity(u1_a, u2_a, timeframe)
            tf_points += MU_WEIGHTS['artist'] * calculate_similarity(df_artist)
            df_track = get_track_similarity(u1_t, u2_t, timeframe)
            tf_points += MU_WEIGHTS['track'] * calculate_similarity(df_track)
            df_genre = get_genre_similarity(u1_g, u2_g, timeframe)
            tf_points += MU_WEIGHTS['genre'] * calculate_similarity(df_genre)
            tf_points += MU_WEIGHTS['feature'] * calculate_feature_similarity(u1_m, u2_m)
            tf_points /= sum(MU_WEIGHTS.values())
            points += TF_WEIGHTS[timeframe] * tf_points
        # Final similarity score
        points /= sum(TF_WEIGHTS.values())
        dict_list.append({
            'user_id': u2,
            'display_name': row['display_name'],
            'image_url': row['image_url'],
            'points': points
        })
    return pd.DataFrame.from_dict(dict_list).sort_values(by='points', ascending=False)

def get_similar_artists(df_a):
    engine = create_engine(DATABASE_URL)
    artists = pd.read_sql_query(similar_artists_query, engine, params={'artist_ids': tuple(df_a['artist_id'].tolist())})
    engine.dispose()
    df = df_a.merge(artists, on=['artist_id'])
    return df.sort_values(['timeframe', 'points'], ascending=False)

def get_similar_tracks(df_t):
    engine = create_engine(DATABASE_URL)
    tracks = pd.read_sql_query(similar_tracks_query, engine, params={'track_ids': tuple(df_t['track_id'].tolist())})
    engine.dispose()
    df = df_t.merge(tracks, on=['track_id'])
    return df.sort_values(['timeframe', 'points'], ascending=False)

def get_artist_similarity(u1, u2, timeframe):
    df1 = u1.loc[u1['timeframe'] == timeframe]
    df2 = u2.loc[u2['timeframe'] == timeframe]
    df = df1.merge(df2, on=['artist_id', 'timeframe'], how='outer').fillna(0)
    df['base'] = calculate_points(df[df[['rank_x', 'rank_y']] > 0].min(axis=1))
    df.loc[(df['rank_x'] != 0) & (df['rank_y'] != 0), 'points'] = calculate_points(df[['rank_x', 'rank_y']].max(axis=1))
    df['points'] = df['points'].fillna(0)
    # df = df.rename(columns={'rank_x': u1['user_id'].unique()[0], 'rank_y': u2['user_id'].unique()[0]})
    return df

def get_track_similarity(u1, u2, timeframe):
    df1 = u1.loc[u1['timeframe'] == timeframe]
    df2 = u2.loc[u2['timeframe'] == timeframe]
    df = df1.merge(df2, on=['track_id', 'timeframe'], how='outer').fillna(0)
    df['base'] = calculate_points(df[df[['rank_x', 'rank_y']] > 0].min(axis=1))
    df.loc[(df['rank_x'] != 0) & (df['rank_y'] != 0), 'points'] = calculate_points(df[['rank_x', 'rank_y']].max(axis=1))
    df['points'] = df['points'].fillna(0)
    # df = df.rename(columns={'rank_x': u1['user_id'].unique()[0], 'rank_y': u2['user_id'].unique()[0]})
    return df

def get_genre_similarity(u1, u2, timeframe):
    df1 = u1.loc[u1['timeframe'] == timeframe]
    df2 = u2.loc[u2['timeframe'] == timeframe]
    df = df1.merge(df2, on=['genre', 'timeframe'], how='outer').fillna(0)
    df['base'] = calculate_points(df[df[['rank_x', 'rank_y']] > 0].min(axis=1))
    df.loc[(df['rank_x'] != 0) & (df['rank_y'] != 0), 'points'] = calculate_points(df[df[['rank_x', 'rank_y']] > 0].max(axis=1))
    df['points'] = df['points'].fillna(0)
    # df = df.rename(columns={'rank_x': u1['user_id'].unique()[0], 'rank_y': u2['user_id'].unique()[0]})
    return df.sort_values(['timeframe', 'points'], ascending=False)

def calculate_similarity(df):
    base_score = df.loc[(df['rank_x'] != 0) & (df['rank_y'] != 0)].sum()['base']
    base_score += df.loc[(df['rank_x'] == 0) | (df['rank_y'] == 0)].sum()['base'] / 2
    return round(df.sum()['points'] / base_score, 4)

def calculate_feature_similarity(u1, u2, timeframe):
    features1 = u1.loc[u1['timeframe'] == timeframe].drop(columns=['user_id', 'timeframe']).values.tolist()[0]
    features2 = u2.loc[u2['timeframe'] == timeframe].drop(columns=['user_id', 'timeframe']).values.tolist()[0]
    points = []
    for i in range(len(features1)):
        f1 = abs(features1[i])
        f2 = abs(features2[i])
        points.append(min(f1, f2) / max(f1, f2))
    return round(sum(points) / len(points), 4)

def calculate_points(rank, weight=16, shift=4):
    return weight / ((0.1 * rank + shift) ** 2) 