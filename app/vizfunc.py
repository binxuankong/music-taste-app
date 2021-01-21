import random
import pygal
from pygal.style import Style
from app.dbfunc import top_to_dict

custom_style = Style(
    background='transparent',
    plot_background='#1c1c16',
    foreground='#FFFFFF',
    foreground_strong='#FFFFFF',
    foreground_subtle='#FFFFFF',
    opacity='.8',
    opacity_hover='1',
    transition='400ms ease-in',
    value_font_size=0)

TF_WEIGHTS = {0: 3, 1: 2, 2: 1}

def calculate_mainstream_score(top_artists, shift=4):
    final_score = 0
    for timeframe in TF_WEIGHTS.keys():
        this_score = 0
        pop_scores = top_artists.loc[top_artists['timeframe'] == timeframe, 'popularity'].tolist()
        weights = [shift**2 / ((0.1 * i + shift) ** 2) for i in range(len(pop_scores))]
        for i, pop in enumerate(pop_scores):
            this_score += (pop**2 * weights[i]) / (100 * sum(weights))
        final_score += (this_score * TF_WEIGHTS[timeframe]) / sum(TF_WEIGHTS.values())
    return round(final_score)

def genre_cloud_data(df_a, df_g):
    top_dict = {}
    for tf in TF_WEIGHTS.keys():
        df = df_g.loc[df_g['timeframe'] == tf].drop_duplicates(subset=['points'])[:10]
        df_a2 = df_a.loc[df_a['timeframe'] == tf]
        artists_genres =  df_a2['genres'].str.split('; ').tolist()
        dict_list = []
        weight = 10
        col1 = list(range(5))
        col2 = list(range(5))
        random.shuffle(col1)
        random.shuffle(col2)
        if col1[-1] == col2[0]:
            col2.insert(0, col2.pop())
        colours = col1 + col2
        for _, row in df.iterrows():
            artists = []
            for i, artist_genres in enumerate(artists_genres):
                if row['genre'].lower() in artist_genres:
                    artists.append(df_a2.iloc[i].to_dict())
                if len(artists) >= 5:
                    break
            dict_list.append({
                'genre': row['genre'],
                'points': row['points'],
                'weight': weight,
                'artists': artists,
                'colour': colours[weight-1]
            })
            weight -= 1
        random.shuffle(dict_list)
        top_dict[tf] = dict_list
    return top_dict

def clean_music_features(df_m):
    top_dict = {}
    is_percent = ['danceability', 'energy', 'acousticness', 'instrumentalness', 'liveness', 'valence']
    for tf in TF_WEIGHTS.keys():
        temp_dict = df_m.loc[df_m['timeframe'] == tf].to_dict('records')[0]
        for p in is_percent:
            temp_dict[p] = round(temp_dict[p] *100)
        temp_dict['loudness'] = round(temp_dict['loudness'], 2)
        temp_dict['tempo'] = round(temp_dict['tempo'])
        top_dict[tf] = temp_dict
    return top_dict

def get_most_features(df_t):
    to_keep = ['track_id', 'track', 'artists', 'album', 'album_image', 'track_url']
    overall_dict = {}
    for tf in TF_WEIGHTS.keys():
        this_dict = {'danceability': {}, 'energy': {}, 'loudness': {}, 'acousticness': {}, 'instrumentalness': {}, \
                     'liveness': {}, 'valence': {}, 'tempo': {}}
        df = df_t.loc[df_t['timeframe'] == tf]
        for feat in this_dict.keys():
            this_dict[feat]['min'] = df.loc[df[feat].idxmin()][to_keep].to_dict()
            this_dict[feat]['max'] = df.loc[df[feat].idxmax()][to_keep].to_dict()
        overall_dict[tf] = this_dict
    return overall_dict

def plot_genre_chart(top_genres):
    try:
        chart_dict = {}
        for timeframe in TF_WEIGHTS.keys():
            pie_chart = pygal.Pie(style=custom_style)
            percent_formatter = lambda x: '{:.2f}%'.format(x)
            pie_chart.value_formatter = percent_formatter
            df = top_genres.loc[top_genres['timeframe'] == timeframe][:10]
            for _, row in df.iterrows():
                genre = row['genre']
                points = row['points'] * 100 / df['points'].sum()
                pie_chart.add(genre, points)
            chart_dict[timeframe] = pie_chart.render_data_uri()
        return chart_dict
    except:
        return None

def plot_mood_gauge(features):
    try:
        music_moods = {'valence': 'Happy', 'danceability': 'Danceable', 'energy': 'Energy', 'acousticness': 'Acoustic', \
                       'instrumentalness': 'Instrumental', 'liveness': 'Live Music', }
        gauge_dict = {}
        for timeframe in TF_WEIGHTS.keys():
            gauge = pygal.SolidGauge(half_pie=True, inner_radius=0.70, style=custom_style)
            percent_formatter = lambda x: '{:.2f}%'.format(x)
            gauge.value_formatter = percent_formatter
            feats = features[timeframe][0]
            for mood in music_moods:
                gauge.add(music_moods[mood], feats[mood] * 100)
            gauge_dict[timeframe] = gauge.render_data_uri()
        return gauge_dict
    except:
        return None