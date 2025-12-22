import os
import streamlit as st
import google.generativeai as genai
import requests
from PIL import Image
from io import BytesIO
from movie_references import fetch_references
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ----------------------------
# CONFIG
# ----------------------------
# Get API keys from environment variables
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
OMDB_API_KEY = os.getenv('OMDB_API_KEY')  # OMDB API key for movie details and posters

# Validate API keys
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")
if not OMDB_API_KEY:
    raise ValueError("OMDB_API_KEY not found in environment variables")

# Configure the Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

# Create a Gemini model instance
model = genai.GenerativeModel('gemini-2.5-flash')
@st.cache_data(show_spinner=False)
def get_movie_references_cached(title):
    return fetch_references(title)

# ----------------------------
# UI
# ----------------------------
st.set_page_config(
    page_title="AI Movie Recommender", 
    layout="centered",
    page_icon="🎬"
)



# Apply custom CSS for dark theme
def get_movie_details(title, year=None):
    """Fetch movie details from OMDB API"""
    try:
        if not title or not title.strip():
            raise ValueError("Empty title provided")
            
        # Clean up the title
        title = ' '.join(title.strip().split())
        
        # If the title is too long, try to shorten it (OMDB has a limit)
        search_title = title[:100]  # Limit to 100 characters
        
        params = {
            'apikey': OMDB_API_KEY,
            't': search_title,
            'plot': 'short',
            'r': 'json',
            'type': 'movie',
            'y': year if (year and str(year).isdigit() and len(str(year)) == 4) else None
        }
        
        # Remove None values from params
        params = {k: v for k, v in params.items() if v is not None}
        
        # Only add year if it's provided and valid
        if year and str(year).isdigit() and len(str(year)) == 4:
            params['y'] = str(year)
        
        # Print debug info
        print(f"Fetching movie: {title} ({year if year else 'no year'})")
        
        response = requests.get('http://www.omdbapi.com/', params=params, timeout=10)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        data = response.json()
        
        print("OMDB API Response:", data)  # Debug log
        
        if data.get('Response') == 'True':
            # Clean up the poster URL
            poster_url = data.get('Poster', '')
            if poster_url == 'N/A':
                poster_url = ''
                
            return {
                'title': data.get('Title', title),
                'year': data.get('Year', year),
                'rating': data.get('imdbRating', 'N/A'),
                'poster': poster_url,
                'genre': data.get('Genre', 'N/A'),
                'response': data.get('Response', 'False')
            }
        else:
            print(f"OMDB API Error: {data.get('Error', 'Unknown error')}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except Exception as e:
        print(f"Error in get_movie_details: {str(e)}")
    
    # Return default values if API call fails
    return {
        'title': title,
        'year': year,
        'rating': 'N/A',
        'poster': '',
        'genre': 'N/A',
        'response': 'False'
    }

def extract_movie_info(rec_text):
    """Extract movie title and year from recommendation text"""
    try:
        # Remove numbering if present (e.g., "1. The Shawshank Redemption (1994)" -> "The Shawshank Redemption (1994)")
        title_year = re.sub(r'^\d+\.\s*', '', rec_text).strip()
        
        # Extract year if present in parentheses (must be 4 digits)
        year_match = re.search(r'\((\d{4})\)', title_year)
        year = int(year_match.group(1)) if year_match else None
        
        # Clean title - remove everything after special characters like -, [, or (
        title = re.split(r'\s*[-\[(]', title_year)[0].strip()
        
        # Remove any remaining parenthetical years
        title = re.sub(r'\s*\(\d{4}\)', '', title).strip()
        
        # Remove any remaining special characters
        title = re.sub(r'[^\w\s]', ' ', title).strip()
        
        # Remove extra spaces
        title = ' '.join(title.split())
        
        print(f"Extracted - Title: '{title}', Year: {year}")  # Debug log
        return title, year
        
    except Exception as e:
        print(f"Error in extract_movie_info: {e}")
        # Return the original text as title if parsing fails
        return rec_text, None

st.markdown("""
    <style>
    /* Main background */
    .stApp {
        background-color: #0e1117;
        color: #f0f2f6;
    }
    
    .movie-card {
        background-color: #1e2229;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        display: flex;
        gap: 15px;
        align-items: flex-start;
    }
    
    .movie-poster {
        width: 100px;
        height: 150px;
        object-fit: cover;
        border-radius: 5px;
    }
    
    .movie-info {
        flex: 1;
    }
    
    .movie-title {
        font-size: 1.2em;
        font-weight: bold;
        margin-bottom: 5px;
    }
    
    .movie-meta {
        color: #a0aec0;
        font-size: 0.9em;
        margin-bottom: 5px;
    }
    
    .movie-rating {
        display: inline-flex;
        align-items: center;
        background: #2d3748;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.8em;
    }
    
    /* Text color */
    .stTextInput>div>div>input, 
    .stTextInput>div>div>input:focus,
    .stTextInput>div>div>input:hover,
    .stTextInput>div>div>input:active {
        background-color: #1e2229 !important;
        color: #f0f2f6 !important;
        border-color: #2d3748 !important;
    }
    
    /* Button styling */
    .stButton>button {
        background-color: #1e2229;
        color: #f0f2f6;
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stButton>button:hover {
        background-color: #2d3748;
        border-color: #4a5568;
    }
    
    /* Recommendation cards */
    .recommendation {
        background-color: #1e2229 !important;
        color: #f0f2f6 !important;
        border: 1px solid #2d3748 !important;
        border-radius: 8px !important;
        padding: 15px !important;
        margin: 10px 0 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }
    
    .recommendation:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #f0f2f6 !important;
    }
    
    /* Text */
    p, div, span {
        color: #f0f2f6 !important;
    }
    
    /* Input labels */
    label {
        color: #f0f2f6 !important;
    }
    
    /* Warning and error messages */
    .stAlert {
        background-color: #2d3748 !important;
        border-left: 4px solid #4299e1 !important;
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1e2229;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #4a5568;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #718096;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎬 AI Movie Recommendation Agent")

st.write("Enter up to **3 movies you like**, and the AI will recommend similar movies.")

# Movie inputs
col1, col2, col3 = st.columns(3)
with col1:
    movie1 = st.text_input("Movie 1", key="movie1")
with col2:
    movie2 = st.text_input("Movie 2 (optional)", key="movie2")
with col3:
    movie3 = st.text_input("Movie 3 (optional)", key="movie3")

# Underrated movies option
underrated = st.checkbox("Show only underrated movies", 
                        help="Check this to see lesser-known or underappreciated movie recommendations")

movies = [m for m in [movie1, movie2, movie3] if m.strip()]

# Initialize session states
if 'show_more' not in st.session_state:
    st.session_state.show_more = False
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = []
if 'current_count' not in st.session_state:
    st.session_state.current_count = 8  # Initial number of recommendations to show

# ----------------------------
# Prompt builder
# ----------------------------
def build_prompt(movies, underrated=False):
    underrated_note = ""
    if underrated:
        underrated_note = """
IMPORTANT: Focus on recommending underrated, hidden gem, or lesser-known movies that are often overlooked.
Prioritize movies that are critically acclaimed but may not have received widespread recognition or box office success.
"""
    return f"""
You are an expert movie recommendation system. Your ONLY TASK is to recommend EXACTLY 16 movies similar to the ones the user likes.
{underrated_note}

CRITICAL INSTRUCTIONS - READ CAREFULLY:
1. You MUST provide EXACTLY 16 movie recommendations
2. Do NOT stop until you have listed all 16 movies
3. Do NOT include any other text before or after the list
4. Include movies from various languages and genres
5. For each movie, include the language in square brackets after the title
6. Make sure the first 8 recommendations are the most relevant
7. The remaining 8 can be slightly less relevant but still good matches

User's favorite movies: {', '.join(movies)}

REQUIRED FORMAT:
1. Movie Title (Year) [Language] - Brief reason (keep it to one line)
2. Movie Title (Year) [Language] - Brief reason
...
16. Movie Title (Year) [Language] - Brief reason

EXAMPLE:
1. The Shawshank Redemption (1994) [English] - A powerful story of hope and friendship
2. 3 Idiots (2009) [Hindi] - A heartwarming comedy about friendship and education
3. Parasite (2019) [Korean] - A masterful social satire with perfect pacing
4. Pather Panchali (1955) [Bengali] - A poetic portrayal of rural Indian life
5. Spirited Away (2001) [Japanese] - A magical animated journey through a spirit world
6. The Dark Knight (2008) [English] - Groundbreaking superhero film with an iconic villain
7. Dilwale Dulhania Le Jayenge (1995) [Hindi] - The ultimate Bollywood romance
8. Amélie (2001) [French] - A whimsical tale of a shy waitress in Paris

Now, please provide EXACTLY 16 movie recommendations following the format above:
"""

# ----------------------------
# LLM Call
# ----------------------------
def get_recommendations(movies, underrated=False, offset=0, count=8):
    try:
        prompt = build_prompt(movies, underrated=underrated)
        
        # Add system instruction as part of the prompt for Gemini
        full_prompt = """You are a helpful movie recommendation agent. Your ONLY TASK is to list EXACTLY 16 movies in the requested format.
        
        FORMAT REQUIREMENTS:
        1. Each recommendation must be on a new line
        2. Each line must start with a number followed by a dot (e.g., "1. ", "2. ", etc.)
        3. Each recommendation should follow this pattern: "[Number]. [Movie Title] ([Year]) [Language] - [Brief description]"
        4. Do not include any other text before or after the list
        
        Here's an example of the expected format:
        1. The Shawshank Redemption (1994) [English] - A powerful story of hope and friendship
        2. 3 Idiots (2009) [Hindi] - A heartwarming comedy about friendship and education
        
        Now, please provide 16 movie recommendations for: """ + ", ".join(movies) + "\n\n" + prompt
        
        # Generate content using Gemini with more specific parameters
        response = model.generate_content(
            full_prompt,
            generation_config={
                "temperature": 0.7,  # Lower temperature for more focused results
                "max_output_tokens": 4096,  # Increased to ensure we get all 16 recommendations
                "top_p": 0.8,  # More focused sampling
                "top_k": 40
            },
            safety_settings={
                'HARASSMENT': 'block_none',
                'HATE_SPEECH': 'block_none',
                'SEXUAL': 'block_none',
                'DANGEROUS': 'block_none'
            }
        )
        
        # Get and clean the response
        recommendations = response.text.strip()
        
        # Log the raw response for debugging
        print("\n=== RAW RESPONSE ===")
        print(recommendations)
        print("==================\n")
        
        # If no response, return error
        if not recommendations:
            return [], "Sorry, I couldn't generate any recommendations. Please try again."
        
        # Extract all numbered items using a more flexible approach
        import re
        
        # First, try to find all lines that start with a number followed by a dot
        lines = [line.strip() for line in recommendations.split('\n') if line.strip()]
        result = []
        
        # Pattern to match lines starting with a number followed by a dot
        pattern = re.compile(r'^\s*(\d+)\.\s*(.+)$')
        
        for line in lines:
            if len(result) >= 16:  # Stop if we have enough recommendations
                break
                
            match = pattern.match(line)
            if match:
                number = match.group(1)
                content = match.group(2).strip()
                # Only add if the line looks like a movie recommendation
                if '(' in content and ')' in content and '[' in content and ']' in content:
                    result.append(f"{len(result) + 1}. {content}")
        
        # If we have at least 8 recommendations, return them
        if len(result) >= 8:
            return result, None
            
        # If we still don't have enough, try a more permissive approach
        if len(result) < 8:
            # Try to find any line that looks like a movie title with year and language
            movie_pattern = re.compile(r'(.+?)\s*\(\d{4}\)\s*\[.+?\]')
            for line in lines:
                if len(result) >= 16:
                    break
                if movie_pattern.search(line) and line not in [r.split('. ', 1)[-1] for r in result]:
                    result.append(f"{len(result) + 1}. {line}")
        
        # If we still don't have enough, just return what we have with a note
        if result:
            return result, None
            
        return [], "Sorry, I couldn't generate any recommendations in the expected format. Please try again with different movies."
        
    except Exception as e:
        return f"An error occurred while generating recommendations: {str(e)}"

# ----------------------------
# Action
# ----------------------------
# Handle the recommend button click
if st.button("🎯 Recommend Movies"):
    if not movies:
        st.warning("Please enter at least one movie.")
    else:
        with st.spinner("Thinking like a cinephile..."):
            # Get all recommendations and store in session state
            all_recommendations, error = get_recommendations(movies, underrated=underrated)
            if not error and all_recommendations:
                st.session_state.recommendations = all_recommendations
                st.session_state.current_count = 8  # Show first 8 recommendations
                # Store the current search parameters to track changes
                st.session_state.last_search = {
                    'movies': tuple(sorted(movies)),
                    'underrated': underrated
                }

# Show recommendations if they exist in session state
if st.session_state.get('recommendations') and st.session_state.get('last_search'):
    # Check if the search parameters have changed
    current_search = {
        'movies': tuple(sorted(movies)),
        'underrated': underrated
    }
    
    # Only show if the search parameters match the last search
    if current_search == st.session_state.last_search:
        st.subheader("🍿 Recommended for you")
        
        # Get current recommendations to show
        current_recommendations = st.session_state.recommendations[:st.session_state.current_count]
        
        # Display the recommendations with posters and ratings
        for rec in current_recommendations:
            title, year = extract_movie_info(rec)
            movie_data = get_movie_details(title, year)
            references = get_movie_references_cached(title)

            # Create columns for poster and info
            col1, col2 = st.columns([1, 3])
            
            with col1:
                # Display poster or placeholder with error handling
                try:
                    if movie_data.get('poster') and movie_data['poster'] not in ('', 'N/A'):
                        st.image(
                            movie_data['poster'],
                            width=100,
                            use_container_width=False,
                            output_format='PNG'
                        )
                    else:
                        st.image(
                            'https://via.placeholder.com/100x150/1e2229/2d3748?text=No+Poster',
                            width=100,
                            use_container_width=False
                        )
                except Exception as e:
                    print(f"Error displaying poster for {title}: {e}")
                    st.image(
                        'https://via.placeholder.com/100x150/1e2229/2d3748?text=No+Poster',
                        width=100,
                        use_container_width=False
                    )
            
            with col2:
                # Display movie info
                st.markdown(f"""
                    <div class="movie-card">
                        <div class="movie-info">
                            <div class="movie-title">{movie_data['title']} ({movie_data.get('year', 'N/A')})</div>
                            <div class="movie-meta">{movie_data.get('genre', 'N/A')}</div>
                            <div class="movie-rating" title="IMDb Rating">
                                ⭐ {movie_data.get('rating', 'N/A')}/10 (IMDb)
                            </div>
                            <div class="movie-plot">
                                {rec}
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                # 🔗 NEW: Show recommendation sources
                if references:
                    with st.expander("🔗 Where this movie is recommended"):
                        for ref in references:
                            st.markdown(
                                f"- **{ref['platform']}** → [Link]({ref['url']})"
                            )

                st.write("")  # Add some spacing
        
        # Show view more/less buttons
        col1, col2 = st.columns([1, 1])
        
        # View More button - increases the count by 8
        if st.session_state.current_count < len(st.session_state.recommendations):
            if col1.button("View More"):
                st.session_state.current_count = min(
                    len(st.session_state.recommendations),
                    st.session_state.current_count + 8
                )
                st.rerun()
        
        # View Less button - resets to 8
        if st.session_state.current_count > 8:
            if col2.button("View Less"):
                st.session_state.current_count = 8
                st.rerun()

# Error handling
if 'error' in locals() and error:
    st.error(error)
elif not st.session_state.get('recommendations'):
    st.info("Enter some movies and click 'Recommend Movies' to get started.")

# Add CSS for the recommendations
st.markdown("""
<style>
.recommendation {
    margin: 12px 0 !important;
    padding: 15px !important;
    background: #1e2229 !important;
    color: #f0f2f6 !important;
    border: 1px solid #2d3748 !important;
    border-radius: 8px !important;
    font-size: 15px !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    transition: all 0.2s ease !important;
}
.recommendation:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
    border-color: #4a5568 !important;
}
.stButton>button {
    width: 100% !important;
    background-color: #1e2229 !important;
    color: #f0f2f6 !important;
    border: 1px solid #2d3748 !important;
    border-radius: 8px !important;
    padding: 0.5rem 1rem !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
    margin: 5px 0 !important;
}
.stButton>button:hover {
    background-color: #2d3748 !important;
    border-color: #4a5568 !important;
}
</style>
""", unsafe_allow_html=True)
