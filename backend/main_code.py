import pandas as pd
import numpy as np
from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
from flask_cors import CORS
import requests
import re
import os
import json
 

TMDB_API_KEY = "4c4ca6bb233ef9ca3b5172891aacb992"

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://themeboxd.netlify.app"]}}, 
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True)
df = pd.read_json("themes_embedded.json")
df['embedding'] = df['embedding'].apply(np.array)


def slugify(name):
    return re.sub(r'(^-|-$)', '', re.sub(r'[^a-z0-9]+', '-', name.lower()))

def get_themes(movie_name):
    try:
        a=df[df["name"]==movie_name]
        return a["embedding"].values[0]
    except:
        return []

def recommend(themes, df, movie_name=None, top_n=6):
    from sklearn.metrics.pairwise import cosine_similarity
    theme_vec=themes.reshape(1,-1)
    vecs = np.vstack(df["embedding"].values)
    sim = cosine_similarity(theme_vec, vecs)[0]
    predict=sim.argsort()[::-1][:top_n]
    results = df.iloc[predict][["name", "theme"]]
    if movie_name:
        # Girilen film adını önerilerden çıkar (küçük harfe çevirerek karşılaştır)
        results = results[results["name"].str.lower() != movie_name.strip().lower()]
    return results

def get_tmdb_poster_url(movie_name):
    try:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_name}"
        print(f"TMDB API request: {url}")
        resp = requests.get(url, timeout=10)
        data = resp.json()
        print(f"TMDB API response for '{movie_name}': {data}")
        if data.get('results'):
            poster_path = data['results'][0].get('poster_path')
            if poster_path:
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
                print(f"Poster for {movie_name}: {poster_url}")
                return poster_url
        # Fallback: Letterboxd poster URL (çalışmazsa placeholder)
        slug = slugify(movie_name)
        fallback_url = f"https://letterboxd.com/film/{slug}/poster/"
        print(f"No TMDB poster for {movie_name}, fallback: {fallback_url}")
        return fallback_url
    except Exception as e:
        print(f"TMDB poster error: {e}")
        slug = slugify(movie_name)
        return f"https://letterboxd.com/film/{slug}/poster/"

@app.route('/api/oner', methods=['POST', 'OPTIONS'])
def api_oner():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'https://themeboxd.netlify.app')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    try:
        data = request.get_json()
        movie_name = data.get('filmAdi')
        print(f"Kullanıcıdan gelen film adı: {movie_name}")
        if not movie_name:
            return jsonify({'error': 'filmAdi alanı zorunlu!'}), 400
        movie_themes = get_themes(movie_name)
        print(f"Çekilen temalar: {movie_themes}")
        if not movie_themes:
            return jsonify({'error': 'Film teması bulunamadı!'}), 404
        predictions = recommend(movie_themes, df, movie_name=movie_name)
        result = predictions.to_dict(orient='records')
        user_film_poster = get_tmdb_poster_url(movie_name)
        print(f"User film poster: {user_film_poster}")
        for film in result:
            film['poster_url'] = get_tmdb_poster_url(film['name'])
            print(f"Poster for {film['name']}: {film['poster_url']}")
        return jsonify({'oneriler': result, 'user_film_theme': movie_themes, 'user_film_poster': user_film_poster})
    except Exception as e:
        print(f"API ERROR: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)


