import streamlit as st
import pickle
import pandas as pd
import random
import requests
from datetime import datetime

# Set full-page mode and add a top anchor for scrolling if desired
st.set_page_config(layout="wide")
st.markdown("<a name='top'></a>", unsafe_allow_html=True)

# ------------------------- LOAD DATA -------------------------
movies_list = pickle.load(open('movies.pkl', 'rb'))  # Ensure it's a DataFrame
similarity = pickle.load(open('similarity.pkl', 'rb'))  # Ensure it's a NumPy array

# Detect correct column for movie ID
movie_id_col = 'id' if 'id' in movies_list.columns else 'movie_id'

# ------------------------- UTILITY FUNCTIONS -------------------------
def fetch_movie_details(movie_id):
    """Fetch movie details (poster, genre, cast, director, release date, overview) from TMDB API."""
    api_key = "c9f1937ce997e9c7ac2fc8ea30c94f09"
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}&language=en-US&append_to_response=credits"
    response = requests.get(url)
    data = response.json()

    default_poster = "https://via.placeholder.com/500x750?text=No+Image+Available"
    poster = (
        f"https://image.tmdb.org/t/p/w500/{data.get('poster_path', '')}"
        if data.get('poster_path') else default_poster
    )
    genres = ', '.join(genre['name'] for genre in data.get('genres', [])) or "Unknown Genre"
    overview = data.get('overview', 'No description available.')
    release_date = data.get('release_date', 'Unknown Release Date')

    cast_list = data.get('credits', {}).get('cast', [])
    cast = ', '.join(actor['name'] for actor in cast_list[:5]) if cast_list else "Unknown Cast"
    crew_list = data.get('credits', {}).get('crew', [])
    director = ', '.join(c['name'] for c in crew_list if c['job'] == "Director") or "Unknown Director"

    return poster, genres, cast, director, release_date, overview


def recommend(movie_title, n=20):
    """Recommend 'n' similar movies based on similarity scores."""
    recommended_titles = []
    recommended_posters = []
    try:
        movie_index = movies_list[movies_list['title'] == movie_title].index[0]
        similarity_scores = list(enumerate(similarity[movie_index]))
        # Sort in descending order, skip the first one (the same movie), then take up to 250
        sorted_similarities = sorted(similarity_scores, key=lambda x: x[1], reverse=True)[1:251]
        random.shuffle(sorted_similarities)
        for i in range(n):
            idx = sorted_similarities[i][0]
            movie_id = movies_list.iloc[idx][movie_id_col]
            recommended_titles.append(movies_list.iloc[idx]['title'])
            recommended_posters.append(fetch_movie_details(movie_id)[0])  # Only fetching poster
    except IndexError:
        st.error(f"❌ '{movie_title}' not found! Suggesting {n} random movies instead.")
        sampled_movies = movies_list.sample(n)
        recommended_titles = sampled_movies['title'].tolist()
        recommended_posters = [
            fetch_movie_details(mid)[0] for mid in sampled_movies[movie_id_col]
        ]
    return recommended_titles, recommended_posters


@st.cache_data(ttl=86400)
def get_top_picks_of_the_day(n=10):
    """Get n top picks of the day based on current date seed.
    Cached for 24 hours so the picks remain consistent throughout the day."""
    # Use today's date as a seed for consistency throughout the day
    today = datetime.now().strftime("%Y%m%d")
    seed = int(today)
    random.seed(seed)
    
    # Get trending movies from TMDB API
    api_key = "c9f1937ce997e9c7ac2fc8ea30c94f09"
    url = f"https://api.themoviedb.org/3/trending/movie/day?api_key={api_key}"
    response = requests.get(url)
    data = response.json()
    
    top_picks = []
    if 'results' in data and data['results']:
        # Filter for movies that exist in our dataset (for recommendation to work)
        trending_ids = [movie['id'] for movie in data['results']]
        for movie_id in trending_ids:
            # Check if movie exists in our dataset
            if movie_id_col in movies_list.columns and movie_id in movies_list[movie_id_col].values:
                movie_title = movies_list[movies_list[movie_id_col] == movie_id]['title'].values[0]
                poster, _, _, _, _, _ = fetch_movie_details(movie_id)
                top_picks.append((movie_title, poster))
                if len(top_picks) >= n:
                    break
    
    # If we don't have enough trending movies in our dataset, fill with random but popular ones
    if len(top_picks) < n:
        # Reset seed to ensure consistency
        random.seed(seed)
        # Get remaining count from our dataset (randomly but consistently)
        remaining = n - len(top_picks)
        random_sample = movies_list.sample(remaining * 2)  # Get more than needed in case some API calls fail
        
        for _, row in random_sample.iterrows():
            if len(top_picks) >= n:
                break
            movie_id = row[movie_id_col]
            try:
                poster, _, _, _, _, _ = fetch_movie_details(movie_id)
                top_picks.append((row['title'], poster))
            except:
                continue
    
    return top_picks

# ------------------------- CUSTOM CSS -------------------------
st.markdown(
    """
    <style>
    /* Reduce top gap */
    .block-container {
        padding-top: 10px !important;
    }
    /* Remove underline from links in top picks */
    .top-pick-container a {
        text-decoration: none;
    }
    /* Reduced hover zoom-in effect for searched movie */
    .searched-movie-container {
        transition: transform 0.2s ease-in-out;
        padding: 10px;
    }
    .searched-movie-container:hover {
        transform: scale(1.02);
    }
    /* Zoom effect for recommended movies */
    .movie-container {
        transition: transform 0.2s ease-in-out;
    }
    .movie-container:hover {
        transform: scale(1.1);
    }
    /* Hover effect for random movies */
    .random-movie-container {
        transition: transform 0.2s ease-in-out;
        text-align: center;
    }
    .random-movie-container:hover {
        transform: scale(1.1);
    }
    /* Hover effect for top picks */
    .top-pick-container {
        transition: transform 0.2s ease-in-out;
        text-align: center;
        display: inline-block;
        margin: 0 10px;
    }
    .top-pick-container:hover {
        transform: scale(1.1);
    }
    /* Horizontal scroll for top picks */
    .scrolling-wrapper {
        display: flex;
        flex-wrap: nowrap;
        overflow-x: auto;
        padding: 20px 0;
        -webkit-overflow-scrolling: touch;
    }
    .scrolling-wrapper::-webkit-scrollbar {
        height: 8px;
    }
    .scrolling-wrapper::-webkit-scrollbar-track {
        background: #1e1e1e;
        border-radius: 10px;
    }
    .scrolling-wrapper::-webkit-scrollbar-thumb {
        background: #555;
        border-radius: 10px;
    }
    .scrolling-wrapper::-webkit-scrollbar-thumb:hover {
        background: #777;
    }
    .stSelectbox label {
        font-size: 22px;
        font-weight: bold;
    }
    .stSelectbox div[data-baseweb="select"] > div {
        opacity: 1 !important;
    }
    .inline-container {
        display: flex;
        align-items: center;
        gap: 20px;
    }
    .movie-title {
        font-size: 28px;
        font-weight: bold;
        color: white;
        margin-bottom: 8px;
    }
    .movie-details {
        font-size: 20px;
        color: white;
    }
    /* Top picks title */
    .top-picks-title {
        text-align: center;
        color: white;
        font-size: 24px;
        margin-bottom: 15px;
    }
    .top-pick-title {
        color: white;
        margin-top: 8px;
        font-size: 14px;
        text-align: center;
    }
    /* Responsive override for st.columns: On mobile, force columns to be 50% width (2 per row) */
    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"] > div {
             flex: 0 0 50% !important;
             max-width: 50% !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------------- HEADER -------------------------
st.markdown(
    "<h1 style='text-align: center; color: white;'>Movie Recommendation System</h1>",
    unsafe_allow_html=True
)
st.markdown("<hr style='border:1px solid gray;'>", unsafe_allow_html=True)

# ------------------------- HANDLE QUERY PARAMS -------------------------
params = st.experimental_get_query_params()
movie_from_url = params.get('movie', "")
if isinstance(movie_from_url, list):
    movie_from_url = movie_from_url[0] if movie_from_url else ""

# Initialize session state if not already set
if 'searched' not in st.session_state:
    st.session_state.searched = False
if 'selected_movie' not in st.session_state:
    st.session_state.selected_movie = ""

# If a movie param exists in the URL and is valid, update session state
if movie_from_url and movie_from_url in movies_list['title'].values:
    st.session_state.selected_movie = movie_from_url
    st.session_state.searched = True

# ------------------------- MOVIE SELECTION UI -------------------------
# This block has been moved above Top Picks.
movies = movies_list['title'].values
default_index = 0
if st.session_state.selected_movie in movies:
    default_index = list(movies).index(st.session_state.selected_movie) + 1

option = st.selectbox('🔍 **Enter Movie Name:**', [""] + list(movies), index=default_index)
search_btn = st.button('🔎 Search')

# If user explicitly searches using the button, update session state and URL
if search_btn and option:
    st.session_state.selected_movie = option
    st.session_state.searched = True
    st.experimental_set_query_params(movie=option)

# ------------------------- TOP PICKS OF THE DAY -------------------------
st.markdown("<h2 id='top_picks_section' class='top-picks-title'>Top Picks of the Day</h2>", unsafe_allow_html=True)

# Get top picks (cached for the day)
top_picks = get_top_picks_of_the_day(10)

# Use columns for the top picks (matching the recommended movies layout)
top_picks_cols = st.columns(10)
for i, (movie_name, poster) in enumerate(top_picks):
    with top_picks_cols[i]:
        st.markdown(
            f"""
            <div class='movie-container' style='text-align: center;'>
                <a href='?movie={movie_name}' target='_self' style='text-decoration: none; color: inherit;'>
                    <img src='{poster}' width='150' style='border-radius: 5px;'>
                    <h6 style='color: white;'>{movie_name}</h6>
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown("<hr style='border:1px solid gray;'>", unsafe_allow_html=True)

# ------------------------- DISPLAY MAIN MOVIE & RECOMMENDATIONS -------------------------
if st.session_state.searched and st.session_state.selected_movie:
    main_movie = st.session_state.selected_movie

    if main_movie not in movies_list['title'].values:
        st.error(f"Movie '{main_movie}' not found in dataset.")
    else:
        movie_id = movies_list[movies_list['title'] == main_movie][movie_id_col].values[0]
        poster, genre, cast, director, release_date, overview = fetch_movie_details(movie_id)

        st.markdown(
            f"""
            <div class="searched-movie-container inline-container">
                <img src="{poster}" width="220">
                <div>
                    <div class="movie-title">{main_movie}</div>
                    <div class="movie-details"><strong>🎭 Genre:</strong> {genre}</div>
                    <div class="movie-details"><strong>🎭 Cast:</strong> {cast}</div>
                    <div class="movie-details"><strong>🎬 Director:</strong> {director}</div>
                    <div class="movie-details"><strong>📅 Release Date:</strong> {release_date}</div>
                    <div class="movie-details"><strong>📜 Overview:</strong> {overview}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<br><hr style='border:1px solid gray;'>", unsafe_allow_html=True)

        names, posters = recommend(main_movie)
        st.markdown(
            f"<h2 style='text-align: center;'>Movies Similar To {main_movie}</h2>",
            unsafe_allow_html=True
        )
        # Display 20 movies in 2 rows with 10 columns each
        for i in range(0, 20, 10):
            cols = st.columns(10)
            for j in range(10):
                with cols[j]:
                    st.markdown(
                        f"""
                        <div class='movie-container' style='text-align: center;'>
                            <a href='?movie={names[i+j]}' target='_self' style='text-decoration: none; color: inherit;'>
                                <img src='{posters[i+j]}' width='150' style='border-radius: 5px;'>
                                <h6 style='color: white;'>{names[i+j]}</h6>
                            </a>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
        st.markdown("<br><hr style='border:1px solid gray;'>", unsafe_allow_html=True)

# ------------------------- RANDOM MOVIES IF NOTHING SELECTED -------------------------
elif not st.session_state.searched:
    st.markdown("<h2 id='random_section' style='text-align: center;'>Random Movie Picks</h2>", unsafe_allow_html=True)
    random_movies = movies_list.sample(10)
    random_movie_names = random_movies['title'].tolist()
    random_movie_posters = [fetch_movie_details(mid)[0] for mid in random_movies[movie_id_col]]

    cols = st.columns(10)
    for i in range(10):
        with cols[i]:
            st.markdown(
                f"""
                <div class='random-movie-container'>
                    <a href='?movie={random_movie_names[i]}' target='_self' style='text-decoration: none; color: inherit;'>
                        <img src='{random_movie_posters[i]}' width='150' style='border-radius: 5px;'>
                        <h6 style='color: white;'>{random_movie_names[i]}</h6>
                    </a>
                </div>
                """,
                unsafe_allow_html=True
            )

# ------------------------- FOOTER -------------------------
st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">', unsafe_allow_html=True)

st.markdown(
    """
    <footer style="background-color: #1e1e1e; color: white; padding: 10px; text-align: center; margin-top: 20px;">
        <p>© 2025. All rights reserved.</p>
        <p>Connect with me on:</p>
        <div style="display: inline-block; border: 1px solid #fff; padding: 5px; margin-top: 0px; border-radius: 5px;">
            <a href="https://www.linkedin.com/in/informrohit1/" target="_blank" style="color: white; margin: 0 10px;">
                <i class="fa fa-linkedin"></i>
            </a>
            <a href="https://github.com/informrohit1" target="_blank" style="color: white; margin: 0 10px;">
                <i class="fa fa-github"></i>
            </a>
            <a href="https://www.kaggle.com/informrohit1" target="_blank" style="color: white; margin: 0 10px;">
                <img src="https://cdn4.iconfinder.com/data/icons/logos-and-brands/512/189_Kaggle_logo_logos-1024.png" style="width:20px; height:20px; vertical-align: middle;" alt="Kaggle">
            </a>
            <a href="mailto:imrohitkumar1205.com" target="_blank" style="color: white; margin: 0 10px;">
                <i class="fa fa-envelope"></i>
            </a>
        </div>
    </footer>
    """,
    unsafe_allow_html=True
)
