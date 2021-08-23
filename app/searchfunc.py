import pandas as pd
from sqlalchemy import create_engine
from app.queries import search_user_query, search_artist_query, search_track_query1, search_track_query2
from secrets import secrets

DATABASE_URL = secrets['DATABASE_URL']

def search_database(query):
    search1 = query + '%'
    search2 = '% ' + query + '%'
    engine = create_engine(DATABASE_URL)
    # df_u = pd.read_sql_query(search_user_query, engine, params={'search1': search1, 'search2': search2})
    df_a = pd.read_sql_query(search_artist_query, engine, params={'search1': search1, 'search2': search2})
    df_t = pd.read_sql_query(search_track_query1, engine, params={'search1': search1, 'search2': search2})
    if len(df_t) <= 10:
        df_t2 = pd.read_sql_query(search_track_query2, engine, params={'search1': search1, 'search2': search2})
        df_t = df_t.append(df_t2).iloc[:10]
    engine.dispose()
    # users = df_u.to_dict('records')
    artists = df_a.to_dict('records')
    tracks = df_t.to_dict('records')
    # if len(users) == 0:
    #    users = None
    if len(artists) == 0:
        artists = None
    if len(tracks) == 0:
        tracks = None
    # return users, artists, tracks
    return artists, tracks
