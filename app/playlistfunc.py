import pandas as pd
import requests
import base64
import datetime as dt
from sqlalchemy import create_engine
from io import BytesIO
from PIL import Image
from app.queries import users2_query, top_artists2_query, top_tracks2_query, generated_playlist_query
from secrets import secrets

DATABASE_URL = secrets['DATABASE_URL']

def create_playlist(sp, u1, u2):
    engine = create_engine(DATABASE_URL)
    df = pd.read_sql_query(generated_playlist_query, engine, params={'user_id': u1, 'target_id': u2})
    users = pd.read_sql(users2_query, engine, params={'user_ids': (u1, u2)})
    if len(df) > 0:
        if (dt.datetime.now() - df['date_created'].item()).days < 1:
            playlist_id = df['playlist_id'].item()
            engine.dispose()
            return users.to_dict('records'), playlist_id
    tracks, p_name, p_desc, p_img = generate_playlist(u1, u2, users, engine)
    p_snap = sp.user_playlist_create(u1, p_name, public=True, collaborative=False, description=p_desc)
    sp.user_playlist_add_tracks(u1, p_snap['id'], tracks)
    sp.playlist_upload_cover_image(p_snap['id'], p_img)
    df_p = pd.DataFrame([[u1, u2, p_snap['id'], p_name, dt.datetime.now()]],
                        columns=['user_id', 'target_id', 'playlist_id', 'playlist_name', 'date_created'])
    df_p.to_sql('GeneratedPlaylists', engine, index=False, if_exists='append')
    playlist_id = p_snap['id']
    engine.dispose()
    return users.to_dict('records'), playlist_id

def generate_playlist(u1, u2, users, engine):
    TOTAL_SONGS = 30
    # Get data from database
    df_a = pd.read_sql(top_artists2_query, engine, params={'user_ids': (u1, u2)})
    df_t = pd.read_sql(top_tracks2_query, engine, params={'user_ids': (u1, u2)})
    # Similar tracks
    similar_tracks = df_t.loc[df_t.duplicated(subset=['track_id', 'timeframe'])]
    # Split by users
    u1_a = df_a.loc[(df_a['user_id'] == u1) & (df_a['rank'] <= 20)]
    u1_t = df_t.loc[(df_t['user_id'] == u1) & (df_t['rank'] <= 20)]
    u2_a = df_a.loc[(df_a['user_id'] == u2) & (df_a['rank'] <= 20)]
    u2_t = df_t.loc[(df_t['user_id'] == u2) & (df_t['rank'] <= 20)]
    # Get base playlist
    playlist_dicts = get_tracks_weight(u1_t, u2_a)
    playlist_dicts.extend(get_tracks_weight(u2_t, u1_a))
    df_p = pd.DataFrame.from_dict(playlist_dicts).sort_values(by='weight', ascending=False)
    df_p = df_p.loc[~df_p['track_id'].isin(similar_tracks['track_id'])].drop_duplicates(subset=['track_id'])
    # Final playlist
    df_f = similar_tracks.drop_duplicates().rename(columns={'points': 'weight'})
    df_f = df_f[['track_id', 'track', 'artists', 'album', 'track_url', 'album_image']]
    n_sample = TOTAL_SONGS - len(df_f)
    df_f = df_f.append(df_p.sample(weights=df_p['weight'], n=n_sample).sort_values(by='weight', ascending=False))
    # Playlist name
    code1 = users.loc[users['user_id'] == u1]['code'].item()
    code2 = users.loc[users['user_id'] == u2]['code'].item()
    p_name = code1.split('-')[0] + ' ' + code2.split('-')[0] + ' ' + code2.split('-')[1]
    if p_name[0] in ['a', 'e', 'i', 'o' 'u']:
        p_name = 'An ' + p_name
    else:
        p_name = 'A ' + p_name
    p_name = p_name.title() + '\'s Playlist'
    # Playlist description
    name1 = users.loc[users['user_id'] == u1]['display_name'].item()
    name2 = users.loc[users['user_id'] == u2]['display_name'].item()
    p_desc = "A playlist created for " + name1 + " and " + name2 + " by Soundbud."
    # Playlist image
    p_img = create_playlist_image(df_f)
    p_img_str = convert_to_jpeg(p_img)
    return df_f['track_id'].tolist(), p_name, p_desc, p_img_str

def create_playlist_image(df):
    p_img = Image.new('RGB', (400, 400))
    i = 0
    count = 0
    img_used = []
    while True and count <= 10:
        this_url = df['album_image'].iloc[count]
        if this_url not in img_used:
            img_used.append(this_url)
            img = Image.open(requests.get(this_url, stream=True).raw)
            img.thumbnail((400, 400))
            if i == 0:
                p_img.paste(img.crop((0, 0, 200, 200)), (0, 0))
            elif i == 1:
                p_img.paste(img.crop((200, 0, 400, 200)), (200, 0))
            elif i == 2:
                p_img.paste(img.crop((0, 200, 200, 400)), (0, 200))
            elif i == 3:
                p_img.paste(img.crop((200, 200, 400, 400)), (200, 200))
                break
            i += 1
        count += 1
    logo = Image.open('app/static/img/watermark.png')
    logo.thumbnail((400, 400))
    p_img.paste(logo, (0, 0), logo)
    return p_img

def convert_to_jpeg(img):
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue())
    return img_str

def get_tracks_weight(user_t, other_a):
    dict_list = []
    for _, t in user_t.iterrows():
        weight = 21 - t['rank']
        artist = t['artists'].split(';')[0]
        if other_a['artist'].str.contains(artist).any():
            weight += 26 - other_a.loc[other_a['artist'].str.contains(artist)]['rank'].mean()
        dict_list.append({
            'track_id': t['track_id'],
            'track': t['track'],
            'artists': t['artists'],
            'album': t['album'],
            'track_url': t['track_url'],
            'album_image': t['album_image'],
            'weight': weight
        })
    return dict_list