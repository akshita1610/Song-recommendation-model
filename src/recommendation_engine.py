"""Modernized recommendation engine with vectorized operations and ML models."""

import asyncio
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import time

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity

from .exceptions import ModelLoadError, PlaylistGenerationError
from .data_models import Track, AudioFeatures, RecommendationResult, User
from .core.spotify import SpotifyClient
from .logging_config import get_logger

logger = get_logger(__name__)


class RecommendationEngine:
    """Modernized recommendation engine with multiple algorithms."""
    
    def __init__(
        self,
        spotify_client: SpotifyClient,
        model_dir: Path = Path("model"),
        cache_dir: Path = Path("cache/recommendations")
    ):
        """Initialize recommendation engine.
        
        Args:
            spotify_client: Spotify client instance
            model_dir: Directory containing ML models
            cache_dir: Directory for caching recommendations
        """
        self.spotify_client = spotify_client
        self.model_dir = model_dir
        self.cache_dir = cache_dir
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load ML models
        self.kmeans_model = self._load_kmeans_model()
        self.scaler = self._load_scaler()
        self.tsne_transformer = self._load_tsne_transformer()
        
        # Feature cache for performance
        self._feature_cache: Dict[str, np.ndarray] = {}
        
    def _load_kmeans_model(self) -> Optional[KMeans]:
        """Load K-means clustering model.
        
        Returns:
            KMeans model or None if not found
        """
        model_path = self.model_dir / "KMeans_K17_20000_sample_model.sav"
        
        if model_path.exists():
            try:
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
                logger.info("K-means model loaded successfully")
                return model
            except Exception as e:
                logger.error(f"Failed to load K-means model: {e}")
                raise ModelLoadError(f"Failed to load K-means model: {e}")
        
        logger.warning("K-means model not found")
        return None
    
    def _load_scaler(self) -> Optional[StandardScaler]:
        """Load StandardScaler model.
        
        Returns:
            StandardScaler model or None if not found
        """
        model_path = self.model_dir / "StdScaler.sav"
        
        if model_path.exists():
            try:
                with open(model_path, 'rb') as f:
                    scaler = pickle.load(f)
                logger.info("StandardScaler loaded successfully")
                return scaler
            except Exception as e:
                logger.error(f"Failed to load StandardScaler: {e}")
                raise ModelLoadError(f"Failed to load StandardScaler: {e}")
        
        logger.warning("StandardScaler not found")
        return None
    
    def _load_tsne_transformer(self) -> Optional[Any]:
        """Load t-SNE transformer model.
        
        Returns:
            t-SNE transformer or None if not found
        """
        model_path = self.model_dir / "openTSNETransformer.sav"
        
        if model_path.exists():
            try:
                with open(model_path, 'rb') as f:
                    transformer = pickle.load(f)
                logger.info("t-SNE transformer loaded successfully")
                return transformer
            except Exception as e:
                logger.warning(f"Failed to load t-SNE transformer: {e}")
                logger.info("Application will continue without t-SNE visualization")
                return None
        
        logger.warning("t-SNE transformer not found")
        return None
    
    def _extract_feature_vector(self, audio_features: AudioFeatures) -> np.ndarray:
        """Extract normalized feature vector from audio features.
        
        Args:
            audio_features: AudioFeatures object
            
        Returns:
            Normalized feature vector
        """
        features = np.array([
            audio_features.danceability,
            audio_features.energy,
            audio_features.key / 11.0,  # Normalize key to 0-1
            (audio_features.loudness + 60) / 60.0,  # Normalize loudness
            audio_features.mode,
            audio_features.speechiness,
            audio_features.acousticness,
            audio_features.instrumentalness,
            audio_features.liveness,
            audio_features.valence,
            audio_features.tempo / 200.0,  # Normalize tempo
            audio_features.time_signature / 4.0  # Normalize time signature
        ])
        
        return features
    
    def _get_cached_features(self, track_uri: str) -> Optional[np.ndarray]:
        """Get cached feature vector for a track.
        
        Args:
            track_uri: Spotify track URI
            
        Returns:
            Feature vector or None if not cached
        """
        return self._feature_cache.get(track_uri)
    
    def _cache_features(self, track_uri: str, features: np.ndarray) -> None:
        """Cache feature vector for a track.
        
        Args:
            track_uri: Spotify track URI
            features: Feature vector to cache
        """
        self._feature_cache[track_uri] = features
    
    async def get_user_preference_vector(self, user: User) -> np.ndarray:
        """Generate preference vector based on user's liked tracks.
        
        Args:
            user: User object
            
        Returns:
            User preference vector
        """
        # Combine all positive feedback tracks
        positive_tracks = (
            user.loved_it + user.like_it + user.okay + user.recently_searched
        )
        
        if not positive_tracks:
            # Return neutral vector if no preferences
            return np.zeros(12)
        
        # Get audio features for all tracks
        try:
            audio_features_list = await self.spotify_client.get_multiple_track_features(
                positive_tracks
            )
            
            # Extract feature vectors
            feature_vectors = []
            for features in audio_features_list:
                vector = self._extract_feature_vector(features)
                feature_vectors.append(vector)
            
            if not feature_vectors:
                return np.zeros(12)
            
            # Calculate weighted average based on preference strength
            weights = []
            for track in positive_tracks:
                if track in user.loved_it:
                    weights.append(1.0)
                elif track in user.like_it:
                    weights.append(0.7)
                elif track in user.okay:
                    weights.append(0.4)
                else:  # recently_searched
                    weights.append(0.3)
            
            # Calculate weighted average
            feature_matrix = np.array(feature_vectors)
            weight_array = np.array(weights).reshape(-1, 1)
            
            preference_vector = np.average(feature_matrix, axis=0, weights=weights.flatten())
            
            logger.info(f"Generated preference vector for user {user.username}")
            return preference_vector
            
        except Exception as e:
            logger.error(f"Failed to generate preference vector: {e}")
            raise PlaylistGenerationError(f"Failed to generate preference vector: {e}")
    
    def find_similar_tracks(
        self,
        seed_track_uri: str,
        candidate_tracks: List[str],
        n_recommendations: int = 10
    ) -> List[Tuple[str, float]]:
        """Find tracks similar to seed track using vectorized operations.
        
        Args:
            seed_track_uri: Seed track URI
            candidate_tracks: List of candidate track URIs
            n_recommendations: Number of recommendations to return
            
        Returns:
            List of (track_uri, similarity_score) tuples
        """
        if not candidate_tracks:
            return []
        
        try:
            # Get seed track features
            seed_features = self.spotify_client.get_track_features(seed_track_uri)
            seed_vector = self._extract_feature_vector(seed_features)
            
            # Get candidate track features (vectorized)
            candidate_vectors = []
            valid_candidates = []
            
            for track_uri in candidate_tracks:
                # Check cache first
                cached_vector = self._get_cached_features(track_uri)
                if cached_vector is not None:
                    candidate_vectors.append(cached_vector)
                    valid_candidates.append(track_uri)
                else:
                    try:
                        features = self.spotify_client.get_track_features(track_uri)
                        vector = self._extract_feature_vector(features)
                        candidate_vectors.append(vector)
                        valid_candidates.append(track_uri)
                        self._cache_features(track_uri, vector)
                    except Exception as e:
                        logger.warning(f"Failed to get features for {track_uri}: {e}")
                        continue
            
            if not candidate_vectors:
                return []
            
            # Calculate similarities using vectorized operations
            candidate_matrix = np.array(candidate_vectors)
            seed_matrix = np.array([seed_vector])
            
            # Use cosine similarity
            similarities = cosine_similarity(seed_matrix, candidate_matrix)[0]
            
            # Get top recommendations
            top_indices = np.argsort(similarities)[::-1][:n_recommendations]
            
            recommendations = []
            for idx in top_indices:
                if similarities[idx] > 0.1:  # Minimum similarity threshold
                    recommendations.append((valid_candidates[idx], similarities[idx]))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to find similar tracks: {e}")
            raise PlaylistGenerationError(f"Failed to find similar tracks: {e}")
    
    def cluster_based_recommendations(
        self,
        user_preference_vector: np.ndarray,
        candidate_tracks: List[str],
        n_recommendations: int = 10
    ) -> List[Tuple[str, float]]:
        """Generate recommendations using clustering model.
        
        Args:
            user_preference_vector: User's preference vector
            candidate_tracks: List of candidate track URIs
            n_recommendations: Number of recommendations to return
            
        Returns:
            List of (track_uri, confidence_score) tuples
        """
        if self.kmeans_model is None or self.scaler is None:
            logger.warning("Clustering models not available")
            return []
        
        if not candidate_tracks:
            return []
        
        try:
            # Get candidate track features
            candidate_vectors = []
            valid_candidates = []
            
            for track_uri in candidate_tracks:
                cached_vector = self._get_cached_features(track_uri)
                if cached_vector is not None:
                    candidate_vectors.append(cached_vector)
                    valid_candidates.append(track_uri)
                else:
                    try:
                        features = self.spotify_client.get_track_features(track_uri)
                        vector = self._extract_feature_vector(features)
                        candidate_vectors.append(vector)
                        valid_candidates.append(track_uri)
                        self._cache_features(track_uri, vector)
                    except Exception as e:
                        logger.warning(f"Failed to get features for {track_uri}: {e}")
                        continue
            
            if not candidate_vectors:
                return []
            
            # Scale features
            candidate_matrix = self.scaler.transform(np.array(candidate_vectors))
            user_vector_scaled = self.scaler.transform(user_preference_vector.reshape(1, -1))
            
            # Predict clusters
            candidate_clusters = self.kmeans_model.predict(candidate_matrix)
            user_cluster = self.kmeans_model.predict(user_vector_scaled)[0]
            
            # Find tracks in same cluster
            same_cluster_indices = np.where(candidate_clusters == user_cluster)[0]
            
            if len(same_cluster_indices) == 0:
                return []
            
            # Calculate distances within cluster
            cluster_candidates = candidate_matrix[same_cluster_indices]
            cluster_uris = [valid_candidates[i] for i in same_cluster_indices]
            
            distances = cdist(user_vector_scaled, cluster_candidates, metric='euclidean')[0]
            
            # Convert distances to confidence scores
            max_distance = np.max(distances) if np.max(distances) > 0 else 1
            confidence_scores = 1 - (distances / max_distance)
            
            # Get top recommendations
            top_indices = np.argsort(confidence_scores)[::-1][:n_recommendations]
            
            recommendations = []
            for idx in top_indices:
                if confidence_scores[idx] > 0.2:  # Minimum confidence threshold
                    recommendations.append((cluster_uris[idx], confidence_scores[idx]))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate cluster-based recommendations: {e}")
            raise PlaylistGenerationError(f"Failed to generate cluster-based recommendations: {e}")
    
    async def generate_recommendations(
        self,
        user: User,
        candidate_tracks: List[str],
        n_recommendations: int = 10,
        algorithm: str = "hybrid"
    ) -> RecommendationResult:
        """Generate song recommendations for a user.
        
        Args:
            user: User object
            candidate_tracks: List of candidate track URIs
            n_recommendations: Number of recommendations to generate
            algorithm: Recommendation algorithm ("similarity", "clustering", "hybrid")
            
        Returns:
            RecommendationResult object
        """
        start_time = time.time()
        
        try:
            # Get user preference vector
            user_preference_vector = await self.get_user_preference_vector(user)
            
            # Filter out tracks user already knows
            known_tracks = set(
                user.loved_it + user.like_it + user.okay + user.hate_it + user.recently_searched
            )
            filtered_candidates = [track for track in candidate_tracks if track not in known_tracks]
            
            if not filtered_candidates:
                raise PlaylistGenerationError("No new tracks available for recommendation")
            
            # Generate recommendations based on algorithm
            if algorithm == "similarity":
                recommendations = self._similarity_based_recommendations(
                    user_preference_vector, filtered_candidates, n_recommendations
                )
            elif algorithm == "clustering":
                recommendations = self.cluster_based_recommendations(
                    user_preference_vector, filtered_candidates, n_recommendations
                )
            else:  # hybrid
                recommendations = await self._hybrid_recommendations(
                    user_preference_vector, filtered_candidates, n_recommendations
                )
            
            # Create RecommendationResult
            processing_time = time.time() - start_time
            
            recommended_tracks = []
            confidence_scores = []
            
            for track_uri, confidence in recommendations:
                try:
                    track = self.spotify_client.get_track_info(track_uri)
                    recommended_tracks.append(track)
                    confidence_scores.append(confidence)
                except Exception as e:
                    logger.warning(f"Failed to get track info for {track_uri}: {e}")
            
            result = RecommendationResult(
                recommended_tracks=recommended_tracks,
                confidence_scores=confidence_scores,
                algorithm_used=algorithm,
                processing_time=processing_time
            )
            
            logger.info(f"Generated {len(recommended_tracks)} recommendations for {user.username}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            raise PlaylistGenerationError(f"Failed to generate recommendations: {e}")
    
    def _similarity_based_recommendations(
        self,
        user_preference_vector: np.ndarray,
        candidate_tracks: List[str],
        n_recommendations: int
    ) -> List[Tuple[str, float]]:
        """Generate recommendations based on user preference similarity."""
        if not user.recently_searched:
            return []
        
        # Use most recent search as seed
        seed_track = user.recently_searched[-1]
        return self.find_similar_tracks(seed_track, candidate_tracks, n_recommendations)
    
    async def _hybrid_recommendations(
        self,
        user_preference_vector: np.ndarray,
        candidate_tracks: List[str],
        n_recommendations: int
    ) -> List[Tuple[str, float]]:
        """Generate hybrid recommendations combining multiple algorithms."""
        # Get recommendations from different algorithms
        similarity_recs = self._similarity_based_recommendations(
            user_preference_vector, candidate_tracks, n_recommendations * 2
        )
        
        clustering_recs = self.cluster_based_recommendations(
            user_preference_vector, candidate_tracks, n_recommendations * 2
        )
        
        # Combine and weight recommendations
        combined_scores = {}
        
        # Weight similarity recommendations higher
        for track_uri, score in similarity_recs:
            combined_scores[track_uri] = combined_scores.get(track_uri, 0) + score * 0.6
        
        # Add clustering recommendations
        for track_uri, score in clustering_recs:
            combined_scores[track_uri] = combined_scores.get(track_uri, 0) + score * 0.4
        
        # Sort by combined score
        sorted_recommendations = sorted(
            combined_scores.items(), key=lambda x: x[1], reverse=True
        )
        
        return sorted_recommendations[:n_recommendations]
    
    def clear_feature_cache(self) -> None:
        """Clear the feature cache."""
        self._feature_cache.clear()
        logger.info("Feature cache cleared")
