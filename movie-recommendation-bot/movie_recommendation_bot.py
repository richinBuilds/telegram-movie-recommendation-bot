import os
import requests
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
    PollHandler
)
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TMDB_API_KEY or not TELEGRAM_BOT_TOKEN:
    raise ValueError("TMDB_API_KEY or TELEGRAM_BOT_TOKEN not found in .env file")

# Set up TMDb API
def get_current_and_next_month():
    """Return list of current and next month in YYYY-MM format."""
    today = datetime.now()
    current_month = today.strftime('%Y-%m')
    next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1).strftime('%Y-%m')
    return [current_month, next_month]

def get_fallback_months(months_back=6):
    """Return list of months from `months_back` ago to next month in YYYY-MM format."""
    today = datetime.now()
    months = []
    for i in range(-months_back, 2):  # From `months_back` ago to next month
        month = (today.replace(day=1) + timedelta(days=32 * i)).replace(day=1).strftime('%Y-%m')
        months.append(month)
    return months

INITIAL_MONTHS = get_current_and_next_month()
FALLBACK_MONTHS = get_fallback_months(months_back=6)

# Language and country mappings
LANGUAGE_MAP = {
    'english': 'en', 'spanish': 'es', 'french': 'fr', 'german': 'de', 'italian': 'it',
    'japanese': 'ja', 'korean': 'ko', 'chinese': 'zh', 'hindi': 'hi'
}
COUNTRY_MAP = {
    'usa': 'US', 'uk': 'GB', 'canada': 'CA', 'france': 'FR', 'germany': 'DE',
    'italy': 'IT', 'japan': 'JP', 'korea': 'KR', 'china': 'CN', 'india': 'IN',
    'united states': 'US', 'united states of america': 'US'
}

# Conversation states
LANGUAGE, COUNTRY = range(2)

# Global poll-to-chat mapping
poll_id_to_chat_id = {}

def is_target_month(released_date, target_months):
    """Check if released_date is in target months (YYYY-MM format)."""
    try:
        release = datetime.strptime(released_date, '%Y-%m-%d')
        return release.strftime('%Y-%m') in target_months
    except (ValueError, TypeError):
        return False

def fetch_movie_data(language=None, country=None, use_fallback=False):
    """Fetch movies from TMDb with filters and save to movies.csv."""
    print("Fetching movie data...")
    target_months = FALLBACK_MONTHS if use_fallback else INITIAL_MONTHS
    cache_file = 'movies.csv'

    # Check cached data
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file)
        if not df.empty and all(col in df.columns for col in ['title', 'rating', 'language', 'country', 'released']):
            print(f"Using cached movies.csv with {len(df)} movies")
            if language:
                df = df[df['language'].str.lower().str.contains(language.lower(), na=False)]
            if country:
                df = df[df['country'].str.lower().str.contains(country.lower(), na=False)]
            df = df[df['released'].apply(lambda x: is_target_month(x, target_months))]
            if len(df) >= 4:
                return df

    data = []
    page = 1
    max_pages = 2  # Limit to 40 movies
    language_code = LANGUAGE_MAP.get(language.lower() if language else '', 'en')
    region_code = COUNTRY_MAP.get(country.lower() if country else '', 'US')
    
    # Dynamic date range for API query
    if use_fallback:
        start_date = (datetime.now().replace(day=1) - timedelta(days=30 * 6)).replace(day=1).strftime('%Y-%m-%d')
        # Last day of next month
        end_date = (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1)
        end_date = (end_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)
        end_date = end_date.strftime('%Y-%m-%d')
    else:
        start_date = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        # Last day of next month
        end_date = (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1)
        end_date = (end_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)
        end_date = end_date.strftime('%Y-%m-%d')

    while len(data) < 20 and page <= max_pages:
        url = f'https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&language={language_code}®ion={region_code}&primary_release_date.gte={start_date}&primary_release_date.lte={end_date}&with_original_language={language_code}&page={page}'
        try:
            response = requests.get(url).json()
            print(f"Page {page} response: {'success' if 'results' in response else response.get('status_message', 'error')}")
            movies = response.get('results', [])
            print(f"Found {len(movies)} movies on page {page}")
            for movie in movies:
                try:
                    released = movie.get('release_date', '')
                    if is_target_month(released, target_months):
                        detail_url = f'https://api.themoviedb.org/3/movie/{movie["id"]}?api_key={TMDB_API_KEY}&language={language_code}'
                        detail_response = requests.get(detail_url).json()
                        time.sleep(0.25)  # Avoid TMDb rate limit (40 requests/10s)
                        genres = ', '.join(g['name'] for g in detail_response.get('genres', []))
                        countries = ', '.join(c['name'] for c in detail_response.get('production_countries', []))
                        movie_language = detail_response.get('original_language', language_code).upper()
                        country_codes = [c['iso_3166_1'] for c in detail_response.get('production_countries', [])]
                        if ((not language or language_code == detail_response.get('original_language', '')) and
                            (not country or region_code in country_codes)):
                            data.append({
                                'title': movie['title'],
                                'year': released[:4] if released else datetime.now().strftime('%Y'),
                                'rating': float(movie.get('vote_average', 0)),
                                'genre': genres,
                                'released': released,
                                'language': movie_language,
                                'country': countries
                            })
                            print(f"Added {movie['title']} ({released})")
                        else:
                            print(f"Skipped {movie['title']}: Language or country mismatch")
                    else:
                        print(f"Skipped {movie['title']}: Invalid release date")
                except Exception as e:
                    print(f"Error fetching details for {movie['title']}: {e}")
            total_pages = response.get('total_pages', 1)
            print(f"Total pages: {total_pages}")
            if page >= total_pages:
                break
            page += 1
        except Exception as e:
            print(f"Error fetching /discover/movie: {e}")
            break

    df = pd.DataFrame(data)
    if not df.empty:
        df = df.dropna(subset=['title', 'rating'])
        df['rating'] = df['rating'].astype(float)
        df = df.drop_duplicates(subset=['title'])
        print(f"Fetched {len(df)} movies")
        df.to_csv(cache_file, index=False)
        print("Saved to movies.csv")
    else:
        print("No valid movies found")
    return df

def get_recommendations(df, n=4):
    """Return top n movies by rating."""
    print(f"Selecting top {n} movies")
    if df.empty or not all(col in df.columns for col in ['title', 'rating']):
        print("Invalid DataFrame: Empty or missing title/rating columns")
        return []
    return df.sort_values('rating', ascending=False).head(n)[['title', 'rating']].to_dict('records')

async def recommend_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the /recommend conversation, ask for language."""
    print(f"Received /recommend command from chat {update.effective_chat.id}")
    await update.effective_chat.send_message(
        "Which language would you like for the movies? (e.g., English, Spanish)"
    )
    return LANGUAGE

async def recommend_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store language and ask for country."""
    context.user_data['language'] = update.message.text.strip()
    print(f"User selected language: {context.user_data['language']}")
    await update.effective_chat.send_message(
        "Which country would you like the movies to be from? (e.g., USA, UK)"
    )
    return COUNTRY

async def recommend_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch movies based on language and country, display recommendations."""
    context.user_data['country'] = update.message.text.strip()
    print(f"User selected country: {context.user_data['country']}")
    language = context.user_data.get('language')
    country = context.user_data.get('country')

    # Try current and next month
    df = fetch_movie_data(language, country, use_fallback=False)
    month_range = INITIAL_MONTHS
    if len(df) < 4:
        print(f"Insufficient movies for {', '.join(month_range)}: {len(df)}")
        await update.effective_chat.send_message(
            f"Only {len(df)} movies found for {', '.join(month_range)} in {language} from {country}. "
            f"Searching movies from {FALLBACK_MONTHS[0]} onward..."
        )
        df = fetch_movie_data(language, country, use_fallback=True)
        month_range = FALLBACK_MONTHS
        if len(df) < 4:
            await update.effective_chat.send_message(
                f"Only {len(df)} movies found for {', '.join(month_range)} in {language} from {country}. "
                "Need at least 4 for a poll. Try again later."
            )
            return ConversationHandler.END

    top_movies = get_recommendations(df)
    if not top_movies:
        print("No recommendations due to invalid DataFrame")
        await update.effective_chat.send_message(
            "Error processing movie data. Try again later."
        )
        return ConversationHandler.END

    # Format message with movie titles and ratings
    message_text = f"Top Movies Released in {', '.join(month_range)}:\n"
    for i, movie in enumerate(top_movies, 1):
        message_text += f"{i}. {movie['title']} (TMDb Rating: {movie['rating']})\n"
    print(f"Sending recommendations: {message_text}")

    # Send message with ratings
    await update.effective_chat.send_message(message_text)
    # Create poll with movie titles
    message = await update.effective_chat.send_poll(
        question="Which movie to watch in theaters?",
        options=[movie['title'] for movie in top_movies],
        is_anonymous=False,
        allows_multiple_answers=False
    )
    # Store poll ID and chat ID
    poll_id_to_chat_id[message.poll.id] = update.effective_chat.id
    print(f"Created poll with ID {message.poll.id}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation."""
    await update.effective_chat.send_message("Recommendation process cancelled.")
    return ConversationHandler.END

async def poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle poll votes and send bar chart."""
    poll = update.poll
    chat_id = poll_id_to_chat_id.get(poll.id)
    if chat_id is None:
        print("Chat ID not found for this poll.")
        return

    # Collect vote data
    votes = {option.text: option.voter_count for option in poll.options}
    df_votes = pd.DataFrame(list(votes.items()), columns=['Movie', 'Votes'])
    print(f"Poll results: {votes}")

    # Generate and save bar chart
    plt.figure(figsize=(8, 5))
    sns.barplot(x='Votes', y='Movie', data=df_votes, hue='Movie', palette='viridis', legend=False)
    plt.title('Movie Poll Results')
    plt.xlabel('Number of Votes')
    plt.ylabel('Movie')
    plt.tight_layout()
    os.makedirs('images', exist_ok=True)
    plt.savefig('images/poll_results.png')
    plt.close()
    print("Saved poll_results.png")

    # Send the image
    with open('images/poll_results.png', 'rb') as image_file:
        await context.bot.send_photo(chat_id=chat_id, photo=image_file)
        print(f"Sent poll results to chat {chat_id}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    print(f"Error: {context.error}")
    if update and update.effective_chat:
        await update.effective_chat.send_message("An error occurred. Please try again.")

def main():
    """Run the bot."""
    print("Starting bot...")
    try:
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('recommend', recommend_start)],
            states={
                LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recommend_language)],
                COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, recommend_country)]
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )
        app.add_handler(conv_handler)
        app.add_handler(PollHandler(poll_answer))
        app.add_error_handler(error_handler)
        print("Bot initialized, starting polling...")
        app.run_polling()
    except Exception as e:
        print(f"Error starting bot: {e}")

if __name__ == '__main__':
    main()