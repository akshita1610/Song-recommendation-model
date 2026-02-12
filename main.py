"""Modernized main application entry point."""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import streamlit as st
from dotenv import load_dotenv
from streamlit_option_menu import option_menu

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src import (
    setup_logging, get_logger,
    SpotifyAPIError, DatabaseError, AuthenticationError
)
from src.core.spotify import SpotifyClient
from src.user_manager import UserManager
from src.recommendation_engine import RecommendationEngine

# Load environment variables
load_dotenv()

# Setup logging
log_file = Path("logs/app.log")
log_file.parent.mkdir(exist_ok=True)
setup_logging(log_level="INFO", log_file=log_file)
logger = get_logger(__name__)


class SongRecommendationApp:
    """Main application class."""
    
    def __init__(self):
        """Initialize the application."""
        self.spotify_client: Optional[SpotifyClient] = None
        self.user_manager: Optional[UserManager] = None
        self.recommendation_engine: Optional[RecommendationEngine] = None
        self.current_user: Optional[object] = None
        
        # Initialize components
        self._init_components()
    
    def _init_components(self) -> None:
        """Initialize application components."""
        try:
            # Get Spotify credentials from environment
            client_id = os.getenv("SPOTIPY_CLIENT_ID")
            client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
            redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8501")
            
            if not all([client_id, client_secret]):
                st.error("Spotify credentials not found in environment variables")
                st.stop()
            
            # Initialize components
            self.spotify_client = SpotifyClient(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri
            )
            
            self.user_manager = UserManager()
            self.recommendation_engine = RecommendationEngine(self.spotify_client)
            
            logger.info("Application components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            st.error(f"Failed to initialize application: {e}")
            st.stop()
    
    def run(self) -> None:
        """Run the Streamlit application."""
        st.set_page_config(
            page_title="Song Recommendation System",
            page_icon="🎵",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Main navigation
        page = self._render_navigation()
        
        # Render selected page
        if page == "Login":
            self._render_login_page()
        elif page == "Register":
            self._render_register_page()
        elif page == "Recommendations":
            self._render_recommendations_page()
        elif page == "Profile":
            self._render_profile_page()
        elif page == "About":
            self._render_about_page()
    
    def _render_navigation(self) -> str:
        """Render navigation menu."""
        st.title("🎵 Song Recommendation System")
        
        # Check if user is logged in
        if 'user' not in st.session_state:
            page = option_menu(
                "Main Menu",
                ["Login", "Register", "About"],
                icons=["box-arrow-in-right", "person-plus", "info-circle"],
                menu_icon="music-note-beamed",
                default_index=0,
                orientation="horizontal"
            )
        else:
            page = option_menu(
                "Main Menu",
                ["Recommendations", "Profile", "Logout", "About"],
                icons=["stars", "person", "box-arrow-right", "info-circle"],
                menu_icon="music-note-beamed",
                default_index=0,
                orientation="horizontal"
            )
            
            if page == "Logout":
                del st.session_state.user
                st.rerun()
        
        return page
    
    def _render_login_page(self) -> None:
        """Render login page."""
        st.header("🔐 Login")
        
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                try:
                    user = self.user_manager.authenticate_user(username, password)
                    st.session_state.user = user
                    st.success(f"Welcome back, {user.username}!")
                    st.rerun()
                    
                except AuthenticationError as e:
                    st.error(f"Login failed: {e}")
                except Exception as e:
                    st.error(f"An error occurred: {e}")
    
    def _render_register_page(self) -> None:
        """Render registration page."""
        st.header("📝 Register")
        
        with st.form("register_form"):
            username = st.text_input("Username", key="reg_username")
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm_password")
            submit_button = st.form_submit_button("Register")
            
            if submit_button:
                if password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    try:
                        user = self.user_manager.create_user(
                            username=username,
                            password=password,
                            email=email
                        )
                        st.success(f"Account created successfully! Please login, {user.username}.")
                        
                    except Exception as e:
                        st.error(f"Registration failed: {e}")
    
    def _render_recommendations_page(self) -> None:
        """Render recommendations page."""
        if 'user' not in st.session_state:
            st.error("Please login first")
            return
        
        user = st.session_state.user
        st.header(f"🎵 Recommendations for {user.username}")
        
        # Show remaining count
        st.info(f"Remaining recommendations: {user.count}")
        
        if user.count <= 0:
            st.warning("You have no remaining recommendations. Please upgrade your plan.")
            return
        
        # Search for songs
        search_query = st.text_input("Search for a song you like:")
        
        if search_query:
            try:
                # Search for tracks
                results = self.spotify_client.sp.search(
                    q=search_query, type='track', limit=10
                )
                
                if results['tracks']['items']:
                    st.write("Search Results:")
                    
                    for track in results['tracks']['items']:
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            track_name = f"{track['name']} - {track['artists'][0]['name']}"
                            st.write(track_name)
                        
                        with col2:
                            if st.button("Like", key=f"like_{track['uri']}"):
                                # Add to user preferences
                                user.recently_searched.append(track['uri'])
                                self.user_manager.update_user_preferences(
                                    username=user.username,
                                    recently_searched=user.recently_searched
                                )
                                st.success("Added to your preferences!")
                                st.rerun()
                
                # Generate recommendations
                if st.button("Get Recommendations"):
                    with st.spinner("Generating personalized recommendations..."):
                        try:
                            # Get candidate tracks (simplified - in real app, this would be from a database)
                            candidate_tracks = [
                                track['uri'] for track in results['tracks']['items']
                            ]
                            
                            # Generate recommendations
                            result = asyncio.run(
                                self.recommendation_engine.generate_recommendations(
                                    user=user,
                                    candidate_tracks=candidate_tracks,
                                    n_recommendations=5
                                )
                            )
                            
                            # Display recommendations
                            st.write("🎯 Your Personalized Recommendations:")
                            
                            for i, (track, confidence) in enumerate(
                                zip(result.recommended_tracks, result.confidence_scores), 1
                            ):
                                st.write(f"{i}. {track.track_name} - {track.artist_name}")
                                st.progress(confidence)
                            
                            # Update user count
                            self.user_manager.decrement_user_count(user.username)
                            user.count -= 1
                            st.session_state.user = user
                            
                            st.success(f"Recommendations generated in {result.processing_time:.2f} seconds")
                            
                        except Exception as e:
                            st.error(f"Failed to generate recommendations: {e}")
                
            except Exception as e:
                st.error(f"Search failed: {e}")
    
    def _render_profile_page(self) -> None:
        """Render user profile page."""
        if 'user' not in st.session_state:
            st.error("Please login first")
            return
        
        user = st.session_state.user
        st.header(f"👤 Profile - {user.username}")
        
        # User information
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Email:**", user.email)
            st.write("**Remaining Recommendations:**", user.count)
            st.write("**Member Since:**", user.created_at.strftime("%Y-%m-%d") if user.created_at else "Unknown")
        
        with col2:
            st.write("**Preferences:**")
            st.write(f"❤️ Loved: {len(user.loved_it)}")
            st.write(f"👍 Liked: {len(user.like_it)}")
            st.write(f"😐 Okay: {len(user.okay)}")
            st.write(f"👎 Hated: {len(user.hate_it)}")
        
        # Recent activity
        if user.recently_searched:
            st.write("**Recently Searched:**")
            for track_uri in user.recently_searched[-5:]:
                try:
                    track = self.spotify_client.get_track_info(track_uri)
                    st.write(f"• {track.track_name} - {track.artist_name}")
                except:
                    st.write("• Track information unavailable")
    
    def _render_about_page(self) -> None:
        """Render about page."""
        st.header("ℹ️ About")
        
        st.write("""
        ## 🎵 Song Recommendation System
        
        This modern song recommendation system uses machine learning to provide personalized music recommendations based on your preferences.
        
        ### Features:
        - **Personalized Recommendations**: Get song suggestions based on your taste
        - **Multiple Algorithms**: Hybrid approach using similarity and clustering
        - **Audio Feature Analysis**: Analyzes danceability, energy, valence, and more
        - **User Preferences**: Learn from your feedback to improve recommendations
        - **Modern Architecture**: Built with async operations, caching, and type safety
        
        ### How it works:
        1. Search for songs you like
        2. The system analyzes audio features
        3. Machine learning models find similar tracks
        4. Get personalized recommendations
        
        ### Technologies Used:
        - **Python 3.9+** with modern features
        - **Streamlit** for the web interface
        - **Spotify API** for music data
        - **scikit-learn** for machine learning
        - **pandas/numpy** for data processing
        - **asyncio** for concurrent operations
        """)


def main():
    """Main entry point."""
    try:
        app = SongRecommendationApp()
        app.run()
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error(f"Application error: {e}")


if __name__ == "__main__":
    main()
