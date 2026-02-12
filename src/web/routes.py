"""Modern FastAPI routes for song recommendation system."""

from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator

from ..core.spotify import SpotifyClient, SpotifyTrack
from ..exceptions import SpotifyAPIError, DataValidationError
from ..logging_config import get_logger

# Initialize router and templates
router = APIRouter(prefix="/api/v1", tags=["recommendations"])
templates = Jinja2Templates(directory="templates")
logger = get_logger(__name__)


class RecommendationRequest(BaseModel):
    """Request model for track recommendations."""
    track_ids: List[str] = Field(
        ..., 
        min_items=1, 
        max_items=5,
        description="List of Spotify track IDs for recommendations (max 5)"
    )
    limit: int = Field(
        default=20, 
        ge=1, 
        le=100,
        description="Number of recommendations to return (1-100)"
    )
    target_energy: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0,
        description="Target energy level (0.0-1.0)"
    )
    target_danceability: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0,
        description="Target danceability (0.0-1.0)"
    )
    target_valence: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0,
        description="Target valence/mood (0.0-1.0)"
    )
    
    @validator('track_ids')
    def validate_track_ids(cls, v):
        """Validate track IDs format."""
        for track_id in v:
            if not track_id or len(track_id) < 10:
                raise ValueError(f"Invalid track ID: {track_id}")
        return v


class SearchRequest(BaseModel):
    """Request model for track search."""
    query: str = Field(..., min_length=1, max_length=100)
    limit: int = Field(default=20, ge=1, le=50)
    market: str = Field(default="US", pattern="^[A-Z]{2}$")


class RecommendationResponse(BaseModel):
    """Response model for recommendations."""
    recommendations: List[Dict[str, Any]]
    count: int
    processing_time_ms: float
    algorithm_used: str = "spotify_recommendations"


class PlaylistResponse(BaseModel):
    """Response model for playlist data."""
    playlist_id: str
    name: str
    description: Optional[str]
    tracks: List[Dict[str, Any]]
    track_count: int


# Dependency to get Spotify client
async def get_spotify_client() -> SpotifyClient:
    """Get Spotify client instance."""
    try:
        return await SpotifyClient.from_env()
    except Exception as e:
        logger.error(f"Failed to create Spotify client: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to initialize Spotify client"
        )


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Render home page."""
    try:
        return templates.TemplateResponse(
            "index.html", 
            {
                "request": request,
                "title": "Song Recommendation System"
            }
        )
    except Exception as e:
        logger.error(f"Error rendering home page: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to render home page"
        )


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "song-recommendation-api",
        "version": "2.0.0"
    }


@router.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    spotify: SpotifyClient = Depends(get_spotify_client)
) -> RecommendationResponse:
    """Get song recommendations based on track IDs."""
    import time
    start_time = time.time()
    
    try:
        # Prepare target features
        target_features = {}
        if request.target_energy is not None:
            target_features["target_energy"] = request.target_energy
        if request.target_danceability is not None:
            target_features["target_danceability"] = request.target_danceability
        if request.target_valence is not None:
            target_features["target_valence"] = request.target_valence
        
        # Get recommendations
        tracks = await spotify.get_recommendations(
            seed_tracks=request.track_ids,
            limit=request.limit,
            target_features=target_features if target_features else None
        )
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000
        
        # Convert to response format
        recommendations = [track.dict() for track in tracks]
        
        logger.info(f"Generated {len(recommendations)} recommendations in {processing_time:.2f}ms")
        
        return RecommendationResponse(
            recommendations=recommendations,
            count=len(recommendations),
            processing_time_ms=processing_time,
            algorithm_used="spotify_recommendations"
        )
        
    except SpotifyAPIError as e:
        logger.error(f"Spotify API error in recommendations: {e}")
        raise HTTPException(
            status_code=503,
            detail="Spotify API temporarily unavailable"
        )
    except DataValidationError as e:
        logger.error(f"Validation error in recommendations: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in recommendations: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/playlist/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(
    playlist_id: str,
    spotify: SpotifyClient = Depends(get_spotify_client)
) -> PlaylistResponse:
    """Get tracks from a playlist."""
    try:
        # Get playlist tracks
        tracks = await spotify.get_playlist_tracks(playlist_id)
        
        # Get playlist info (simplified - in real app, would fetch playlist metadata)
        playlist_info = {
            "id": playlist_id,
            "name": f"Playlist {playlist_id[:8]}...",
            "description": "Generated playlist",
        }
        
        # Convert to response format
        track_dicts = [track.dict() for track in tracks]
        
        logger.info(f"Fetched {len(track_dicts)} tracks from playlist {playlist_id}")
        
        return PlaylistResponse(
            playlist_id=playlist_id,
            name=playlist_info["name"],
            description=playlist_info["description"],
            tracks=track_dicts,
            track_count=len(track_dicts)
        )
        
    except SpotifyAPIError as e:
        logger.error(f"Spotify API error getting playlist: {e}")
        raise HTTPException(
            status_code=503,
            detail="Spotify API temporarily unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting playlist: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/search")
async def search_tracks(
    query: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=50),
    market: str = Query(default="US", regex="^[A-Z]{2}$"),
    spotify: SpotifyClient = Depends(get_spotify_client)
) -> List[Dict[str, Any]]:
    """Search for tracks."""
    try:
        tracks = await spotify.search_tracks(
            query=query,
            limit=limit,
            market=market
        )
        
        # Convert to response format
        track_dicts = [track.dict() for track in tracks]
        
        logger.info(f"Found {len(track_dicts)} tracks for query: {query}")
        
        return track_dicts
        
    except SpotifyAPIError as e:
        logger.error(f"Spotify API error in search: {e}")
        raise HTTPException(
            status_code=503,
            detail="Spotify API temporarily unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in search: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/track/{track_id}")
async def get_track_details(
    track_id: str,
    spotify: SpotifyClient = Depends(get_spotify_client)
) -> Dict[str, Any]:
    """Get detailed track information."""
    try:
        track = await spotify.get_track(track_id)
        
        if not track:
            raise HTTPException(
                status_code=404,
                detail="Track not found"
            )
        
        logger.debug(f"Fetched track details for: {track_id}")
        
        return track.dict()
        
    except SpotifyAPIError as e:
        logger.error(f"Spotify API error getting track: {e}")
        raise HTTPException(
            status_code=503,
            detail="Spotify API temporarily unavailable"
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Unexpected error getting track: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/track/{track_id}/features")
async def get_track_features(
    track_id: str,
    spotify: SpotifyClient = Depends(get_spotify_client)
) -> Dict[str, Any]:
    """Get audio features for a track."""
    try:
        features = await spotify.get_audio_features(track_id)
        
        if not features:
            raise HTTPException(
                status_code=404,
                detail="Audio features not found for this track"
            )
        
        logger.debug(f"Fetched audio features for: {track_id}")
        
        return features.dict()
        
    except SpotifyAPIError as e:
        logger.error(f"Spotify API error getting features: {e}")
        raise HTTPException(
            status_code=503,
            detail="Spotify API temporarily unavailable"
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Unexpected error getting features: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/stats")
async def get_api_stats(
    spotify: SpotifyClient = Depends(get_spotify_client)
) -> Dict[str, Any]:
    """Get API statistics and cache information."""
    try:
        # Get cache stats (simplified)
        cache_stats = {
            "track_cache_size": len(spotify._track_cache),
            "features_cache_size": len(spotify._features_cache),
        }
        
        return {
            "api_version": "2.0.0",
            "cache_stats": cache_stats,
            "spotify_client_initialized": True,
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get statistics"
        )
