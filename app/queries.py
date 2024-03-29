user_query = """
SELECT u.user_id, u.display_name, u.spotify_url, u.image_url, u.last_updated, up.code, up.public 
FROM "Users" u
JOIN "UserProfiles" up
ON u.user_id = up.user_id
WHERE u.user_id = %(user_id)s
"""

top_artists_query = """
SELECT ta.rank, ta.artist_id, ta.timeframe, a.artist, a.genres, a.artist_url, a.artist_image, a.popularity
FROM "TopArtists" ta 
JOIN "Artists" a 
ON ta.artist_id = a.artist_id
WHERE ta.user_id = %(user_id)s
ORDER BY ta.timeframe, ta.rank
"""

top_tracks_query = """
SELECT tt.rank, tt.track_id, tt.timeframe, t.track, t.artists, t.album, t.album_image, t.release_date, t.track_url,
       mf.danceability, mf.energy, mf.loudness, mf.acousticness, mf.instrumentalness, mf.liveness, mf.valence, mf.tempo
FROM "TopTracks" tt
JOIN "Tracks" t
ON tt.track_id = t.track_id
JOIN "MusicFeatures" mf
ON tt.track_id = mf.track_id
WHERE tt.user_id = %(user_id)s
ORDER BY tt.timeframe, tt.rank
"""

top_genres_query = """
SELECT *
FROM "TopGenres" tg
WHERE tg.user_id = %(user_id)s
"""

user_update_query = """
UPDATE "Users"
SET display_name = %(display_name)s, spotify_url = %(spotify_url)s, image_url = %(image_url)s,
    followers = %(followers)s, last_updated = %(last_updated)s
WHERE user_id = %(user_id)s
"""

user_privacy_query = """
UPDATE "UserProfiles"
SET public = NOT public 
WHERE user_id = %(user_id)s
"""

user_code_query = """
UPDATE "UserProfiles"
SET code = %(code)s
WHERE user_id = %(user_id)s
"""

artists_update_query = """
UPDATE "Artists" as a
SET artist = ta.artist, genres = ta.genres, artist_image = ta.artist_image, artist_url = ta.artist_url, popularity = ta.popularity 
FROM "TempArtists" as ta
WHERE a.artist_id = ta.artist_id
"""

tracks_update_query = """
UPDATE "Tracks" as t
SET album_image = tt.album_image, track_url = tt.track_url 
FROM "TempTracks" as tt
WHERE t.track_id = tt.track_id 
"""

artists_insert_query = """
INSERT INTO "Artists" (artist_id, artist, genres, artist_image, artist_url, popularity)
SELECT ta.artist_id, ta.artist, ta.genres, ta.artist_image, ta.artist_url, ta.popularity
FROM "TempArtists" ta
ON CONFLICT (artist_id) DO NOTHING
"""

tracks_insert_query = """
INSERT INTO "Tracks" (track_id, track, artists, album, album_image, release_date, track_url)
SELECT tt.track_id, tt.track, tt.artists, tt.album, tt.album_image, tt.release_date, tt.track_url
FROM "TempTracks" tt
ON CONFLICT (track_id) DO NOTHING
"""

features_insert_query = """
INSERT INTO "MusicFeatures" (track_id, danceability, energy, loudness, speechiness, acousticness, instrumentalness,
    liveness, valence, tempo, key, mode, duration_ms, time_signature)
SELECT tf.track_id, tf.danceability, tf.energy, tf.loudness, tf.speechiness, tf.acousticness, tf.instrumentalness,
    tf.liveness, tf.valence, tf.tempo, tf.key, tf.mode, tf.duration_ms, tf.time_signature
FROM "TempFeatures" tf
ON CONFLICT (track_id) DO NOTHING
"""

users2_query = """
SELECT u.user_id, u.display_name, u.spotify_url, u.image_url, up.code
FROM "Users" u
JOIN "UserProfiles" up
ON u.user_id = up.user_id
WHERE u.user_id in %(user_ids)s
"""

top_artists2_query = """
SELECT ta.user_id, ta.rank, ta.artist_id, ta.timeframe, a.artist, a.genres, a.artist_url, a.artist_image
FROM "TopArtists" ta 
JOIN "Artists" a
ON ta.artist_id = a.artist_id
WHERE ta.user_id in %(user_ids)s
ORDER BY ta.timeframe, ta.rank
"""

top_tracks2_query = """
SELECT tt.user_id, tt.rank, tt.track_id, tt.timeframe, t.track, t.artists, t.album, t.album_image, t.release_date, t.track_url,
       mf.danceability, mf.energy, mf.loudness, mf.acousticness, mf.instrumentalness, mf.liveness, mf.valence, mf.tempo
FROM "TopTracks" tt
JOIN "Tracks" t
ON tt.track_id = t.track_id
JOIN "MusicFeatures" mf
ON tt.track_id = mf.track_id
WHERE tt.user_id in %(user_ids)s
ORDER BY tt.timeframe, tt.rank
"""

top_genres2_query = """
SELECT *
FROM "TopGenres" tg
WHERE tg.user_id in %(user_ids)s
"""

similar_artists_query = """
SELECT artist_id, artist, genres, artist_url, artist_image
FROM "Artists"
WHERE artist_id in %(artist_ids)s
"""

similar_tracks_query = """
SELECT track_id, track, artists, album, track_url, album_image
FROM "Tracks"
WHERE track_id in %(track_ids)s
"""

recommend_artists_query = """
SELECT a.artist_id, a.artist, a.genres, a.artist_url, a.artist_image, a.popularity
FROM "RecommendArtists" ra 
JOIN "Artists" a 
ON ra.artist_id = a.artist_id
WHERE ra.user_id = %(user_id)s
"""

recommend_tracks_query = """
SELECT t.track_id, t.track, t.artists, t.album, t.album_image, t.release_date, t.track_url
FROM "RecommendTracks" rt
JOIN "Tracks" t
ON rt.track_id = t.track_id
WHERE rt.user_id = %(user_id)s
"""

top_artists3_query = """
SELECT DISTINCT t_top.user_id, t_top.rank, t_top.artist_id, t_outer.timeframe from "TopArtists" t_outer
JOIN LATERAL (
    SELECT * FROM "TopArtists" t_inner
    WHERE t_inner.timeframe = t_outer.timeframe
    AND user_id = %(user_id)s
    ORDER BY t_inner.rank
    LIMIT 20
) t_top ON true
ORDER BY t_outer.timeframe, t_top.rank;
"""

top_tracks3_query = """
SELECT DISTINCT t_top.user_id, t_top.rank, t_top.track_id, t_outer.timeframe from "TopTracks" t_outer
JOIN LATERAL (
    SELECT * FROM "TopTracks" t_inner
    WHERE t_inner.timeframe = t_outer.timeframe
    AND user_id = %(user_id)s
    ORDER BY t_inner.rank
    LIMIT 20
) t_top ON true
ORDER BY t_outer.timeframe, t_top.rank;
"""

popular_artists_query = """
SELECT ta.artist_id, a.artist, a.genres, a.artist_image, a.artist_url
FROM (
	SELECT artist_id, SUM(60 - "rank") point
	FROM "TopArtists"
	WHERE timeframe = %(timeframe)s
	GROUP BY artist_id
	ORDER BY point DESC
	LIMIT 50
) ta
JOIN "Artists" a
ON a.artist_id = ta.artist_id
ORDER BY ta.point DESC
"""

popular_tracks_query = """
SELECT tt.track_id, t.track, t.artists, t.album, t.album_image, t.track_url,
       mf.danceability, mf.energy, mf.loudness, mf.acousticness, mf.instrumentalness, mf.liveness, mf.valence, mf.tempo
FROM (
	SELECT track_id, SUM(60 - "rank") point
	FROM "TopTracks"
	WHERE timeframe = %(timeframe)s
	GROUP BY track_id
	ORDER BY point DESC
	LIMIT 100
) tt
JOIN "Tracks" t
ON t.track_id = tt.track_id
JOIN "MusicFeatures" mf
ON tt.track_id = mf.track_id
ORDER BY tt.point DESC
"""

popular_genres_query = """
SELECT genre, SUM(points) points
FROM "TopGenres"
WHERE timeframe = %(timeframe)s
GROUP BY genre 
ORDER BY points DESC
LIMIT 10
"""

new_of_day_query = """
INSERT INTO "DailyMix" (artist_id, track_id, lyrics_id, date_created)
VALUES (%(artist_id)s, %(track_id)s, %(lyrics_id)s, %(date_created)s)
"""

similar_users_query = """
SELECT ta2.user_id, u.display_name, u.image_url,
SUM(100 - greatest(ta1.rank, ta2.rank) - abs(ta1.rank - ta2.rank)) AS point
FROM "TopArtists" ta1
LEFT JOIN "TopArtists" ta2
ON ta1.artist_id = ta2.artist_id AND ta1.user_id <> ta2.user_id
JOIN "Users" u
ON ta2.user_id = u.user_id
WHERE ta1.user_id = %(user_id)s
GROUP BY ta2.user_id, u.display_name, u.image_url
ORDER BY point desc
LIMIT 10
"""

search_user_query = """
SELECT *
FROM "Users"
WHERE display_name ILIKE %(search1)s OR display_name ILIKE %(search2)s
LIMIT 10
"""

search_artist_query = """
SELECT artist_id, artist, artist_url, artist_image
FROM "Artists"
WHERE artist ILIKE %(search1)s OR artist ILIKE %(search2)s
LIMIT 10
"""

search_track_query1 = """
SELECT track_id, track, artists, album, track_url, album_image
FROM "Tracks"
WHERE track ILIKE %(search1)s OR track ILIKE %(search2)s
LIMIT 10
"""

search_track_query2 = """
SELECT track_id, track, artists, album, track_url, album_image
FROM "Tracks"
WHERE artists ILIKE %(search1)s OR artists ILIKE %(search2)s
LIMIT 10
"""

generated_playlist_query = """
SELECT playlist_id, date_created
FROM "GeneratedPlaylists"
WHERE user_id = %(user_id)s AND target_id = %(target_id)s
ORDER BY date_created DESC
LIMIT 1
"""