"""Test validators module."""

import pytest
from src.validators import (
    validate_spotify_uri,
    validate_email,
    validate_username,
    validate_password_strength,
    DataValidationError
)


class TestValidators:
    """Test validation functions."""
    
    def test_validate_spotify_uri_valid(self):
        """Test valid Spotify URI validation."""
        # Use a valid 22-character Spotify ID
        assert validate_spotify_uri("spotify:track:4iV5W9uYEdYUVa79Axb7Rh", "track")
        assert validate_spotify_uri("spotify:artist:4iV5W9uYEdYUVa79Axb7Rh", "artist")
    
    def test_validate_spotify_uri_invalid(self):
        """Test invalid Spotify URI validation."""
        with pytest.raises(DataValidationError):
            validate_spotify_uri("invalid:uri", "track")
        
        with pytest.raises(DataValidationError):
            validate_spotify_uri("", "track")
    
    def test_validate_email_valid(self):
        """Test valid email validation."""
        assert validate_email("test@example.com")
        assert validate_email("user.name+tag@domain.co.uk")
    
    def test_validate_email_invalid(self):
        """Test invalid email validation."""
        with pytest.raises(DataValidationError):
            validate_email("invalid-email")
        
        with pytest.raises(DataValidationError):
            validate_email("")
    
    def test_validate_username_valid(self):
        """Test valid username validation."""
        assert validate_username("user123")
        assert validate_username("test_user")
    
    def test_validate_username_invalid(self):
        """Test invalid username validation."""
        with pytest.raises(DataValidationError):
            validate_username("ab")  # Too short
        
        with pytest.raises(DataValidationError):
            validate_username("a" * 31)  # Too long
        
        with pytest.raises(DataValidationError):
            validate_username("user@name")  # Invalid characters
    
    def test_validate_password_strength_valid(self):
        """Test valid password validation."""
        assert validate_password_strength("StrongPass123")
        assert validate_password_strength("MySecure@Password123")
    
    def test_validate_password_strength_invalid(self):
        """Test invalid password validation."""
        with pytest.raises(DataValidationError):
            validate_password_strength("weak")  # Too short
        
        with pytest.raises(DataValidationError):
            validate_password_strength("nouppercase123")  # No uppercase
        
        with pytest.raises(DataValidationError):
            validate_password_strength("NOLOWERCASE123")  # No lowercase
        
        with pytest.raises(DataValidationError):
            validate_password_strength("NoDigits!")  # No digits
