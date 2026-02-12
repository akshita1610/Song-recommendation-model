"""Authentication and authorization for the web interface."""

import os
from datetime import datetime, timedelta
from typing import Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field, validator

from ..exceptions import AuthenticationError, DataValidationError
from ..logging_config import get_logger

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Initialize password context and OAuth2 scheme
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

logger = get_logger(__name__)


class Token(BaseModel):
    """JWT token response model."""
    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseModel):
    """Token data model for validation."""
    username: Optional[str] = None
    scopes: list[str] = []


class User(BaseModel):
    """User model for authentication."""
    username: str = Field(..., min_length=3, max_length=30)
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    disabled: Optional[bool] = False


class UserInDB(User):
    """User model with hashed password."""
    hashed_password: str


class UserCreate(BaseModel):
    """User registration model."""
    username: str = Field(..., min_length=3, max_length=30)
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    password: str = Field(..., min_length=8, max_length=100)
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        
        return v


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing error: {e}")
        raise AuthenticationError("Failed to hash password")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        scopes: list[str] = payload.get("scopes", [])
        
        if username is None:
            raise credentials_exception
        
        token_data = TokenData(username=username, scopes=scopes)
        
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception
    
    # In a real application, you would fetch user from database
    # For now, we'll create a mock user
    user = get_user(token_data.username)
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    """Get current active user."""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return current_user


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate user with username and password."""
    # In a real application, you would verify against database
    user = get_user(username)
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


def get_user(username: str) -> Optional[UserInDB]:
    """Get user from database (mock implementation)."""
    # Mock user database - in real app, this would query your database
    mock_users = {
        "testuser": UserInDB(
            username="testuser",
            email="test@example.com",
            hashed_password=get_password_hash("TestPass123"),
            disabled=False
        ),
        "admin": UserInDB(
            username="admin",
            email="admin@example.com", 
            hashed_password=get_password_hash("AdminPass123"),
            disabled=False
        )
    }
    
    return mock_users.get(username)


class OAuth2PasswordRequestFormWithUsername(OAuth2PasswordRequestForm):
    """Extended OAuth2 form with username field."""
    username: str
    password: str
    grant_type: Optional[str] = None
    scope: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


async def login_for_access_token(
    form_data: OAuth2PasswordRequestFormWithUsername = Depends()
) -> Token:
    """Authenticate user and return access token."""
    try:
        user = authenticate_user(form_data.username, form_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if user.disabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "scopes": ["read"]},
            expires_delta=access_token_expires
        )
        
        logger.info(f"User {user.username} authenticated successfully")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication"
        )


async def get_current_active_user_info(
    current_user: UserInDB = Depends(get_current_active_user)
) -> dict:
    """Get current user information."""
    return {
        "username": current_user.username,
        "email": current_user.email,
        "disabled": current_user.disabled,
        "scopes": ["read"]
    }


# Role-based access control
def require_scope(required_scope: str):
    """Decorator to require specific scope."""
    def scope_checker(current_user: UserInDB = Depends(get_current_active_user)):
        # In a real application, you would check user's actual scopes
        # For now, we'll assume all authenticated users have read access
        if required_scope == "read":
            return current_user
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for scope: {required_scope}"
            )
    
    return scope_checker


# Rate limiting (simplified implementation)
class RateLimiter:
    """Simple rate limiter for API endpoints."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed."""
        now = datetime.utcnow()
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old requests outside the window
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if (now - req_time).total_seconds() < self.window_seconds
        ]
        
        # Check if under limit
        if len(self.requests[key]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


async def rate_limit_check(
    current_user: UserInDB = Depends(get_current_active_user)
) -> UserInDB:
    """Check rate limits for current user."""
    if not rate_limiter.is_allowed(current_user.username):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    return current_user
