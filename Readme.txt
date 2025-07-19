Movie Recommendation Telegram Bot

This is a Telegram bot that recommends movies based on user-specified language and country preferences, using the TMDb API. It fetches movie data for specific release periods, creates a poll for users to vote on their preferred movie, and visualizes the poll results with a bar chart.

Features

Movie Recommendations: Fetches movies from TMDb for June-July 2025 (or October 2024 onward as fallback) based on user-selected language and country.

-Interactive Polls: Creates a Telegram poll with the top 4 movies by TMDb rating, allowing users to vote.
-Vote Visualization: Generates and sends a bar chart of poll results to the chat.
-Caching: Stores fetched movie data in movies.csv to reduce API calls.
-Error Handling: Manages API errors, invalid inputs, and Telegram bot errors gracefully.

Prerequisites

Python

Telegram account and bot token (obtained via BotFather)

If using the bot in a group chat, ensure it is added as an administrator to allow poll creation and other features.

TMDb API key (sign up at TMDb)

Required Python packages:

requests
pandas
seaborn
matplotlib
python-telegram-bot
python-dotenv

Installation


Clone the repository
Set up a virtual environment
Install dependencies
Create a .env file in the project root with the following:
TMDB_API_KEY=your_tmdb_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

Usage

Run the bot
Interact with the bot on Telegram:

Start the bot by sending /recommend.

Specify the desired language (e.g., English, Spanish).

Specify the desired country (e.g., USA, UK).

The bot will fetch movies, display the top 4 by TMDb rating, and create a poll.

Cancel the process (if needed):

Send /cancel during the recommendation process to stop.

How It Works

Environment Setup: Loads TMDb API key and Telegram bot token from .env.

Movie Fetching: Queries the TMDb API for movies in the specified language and country, filtering by release date (June-July 2025 or October 2024 onward).

Caching: Checks for existing movies.csv to avoid redundant API calls. If insufficient data, fetches new data and saves it.

Conversation Flow:

/recommend: Starts the conversation, asking for language.

User inputs language, then country.

Bot fetches and displays top 4 movies, creates a poll, and stores the poll ID.

Poll Handling: When users vote, the bot generates a bar chart using seaborn and sends it to the chat.

Error Handling: Catches and reports API errors, invalid inputs, or Telegram issues.