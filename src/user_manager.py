"""Modernized user management system with proper error handling and validation."""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import sqlite3

import pandas as pd

from .exceptions import DatabaseError, AuthenticationError, DataValidationError
from .data_models import User
from .validators import validate_username, validate_email, validate_password_strength, sanitize_string
from .logging_config import get_logger

logger = get_logger(__name__)


class UserManager:
    """Modernized user management system."""
    
    def __init__(self, db_path: Path = Path("data/users.db")):
        """Initialize user manager.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize the database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        username TEXT PRIMARY KEY,
                        password_hash TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        count INTEGER DEFAULT 10,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP,
                        loved_it TEXT DEFAULT '[]',
                        like_it TEXT DEFAULT '[]',
                        okay TEXT DEFAULT '[]',
                        hate_it TEXT DEFAULT '[]',
                        recently_searched TEXT DEFAULT '[]'
                    )
                """)
                
                # Create user_sessions table for tracking active sessions
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        session_id TEXT PRIMARY KEY,
                        username TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        FOREIGN KEY (username) REFERENCES users (username)
                    )
                """)
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Failed to initialize database: {e}")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _serialize_list(self, data_list: List[str]) -> str:
        """Serialize list to JSON string.
        
        Args:
            data_list: List to serialize
            
        Returns:
            JSON string
        """
        return json.dumps(data_list)
    
    def _deserialize_list(self, json_string: str) -> List[str]:
        """Deserialize JSON string to list.
        
        Args:
            json_string: JSON string to deserialize
            
        Returns:
            List of strings
        """
        try:
            return json.loads(json_string)
        except json.JSONDecodeError:
            return []
    
    def create_user(
        self,
        username: str,
        password: str,
        email: str,
        initial_count: int = 10
    ) -> User:
        """Create a new user account.
        
        Args:
            username: Username
            password: Plain text password
            email: Email address
            initial_count: Initial recommendation count
            
        Returns:
            Created User object
        """
        # Validate inputs
        validate_username(username)
        validate_email(email)
        validate_password_strength(password)
        
        # Sanitize inputs
        username = sanitize_string(username)
        email = sanitize_string(email)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if user already exists
                cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
                if cursor.fetchone():
                    raise DataValidationError(f"Username '{username}' already exists")
                
                # Check if email already exists
                cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
                if cursor.fetchone():
                    raise DataValidationError(f"Email '{email}' already registered")
                
                # Create user
                password_hash = self._hash_password(password)
                created_at = datetime.now().isoformat()
                
                cursor.execute("""
                    INSERT INTO users (
                        username, password_hash, email, count, created_at,
                        loved_it, like_it, okay, hate_it, recently_searched
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    username, password_hash, email, initial_count, created_at,
                    self._serialize_list([]), self._serialize_list([]),
                    self._serialize_list([]), self._serialize_list([]),
                    self._serialize_list([])
                ))
                
                conn.commit()
                
                user = User(
                    username=username,
                    password_hash=password_hash,
                    email=email,
                    count=initial_count,
                    created_at=datetime.fromisoformat(created_at)
                )
                
                logger.info(f"User created successfully: {username}")
                return user
                
        except sqlite3.Error as e:
            logger.error(f"Database error creating user: {e}")
            raise DatabaseError(f"Failed to create user: {e}")
    
    def authenticate_user(self, username: str, password: str) -> User:
        """Authenticate user credentials.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            Authenticated User object
        """
        validate_username(username)
        
        if not password:
            raise DataValidationError("Password cannot be empty")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get user data
                cursor.execute("""
                    SELECT username, password_hash, email, count, created_at, last_login,
                           loved_it, like_it, okay, hate_it, recently_searched
                    FROM users WHERE username = ?
                """, (username,))
                
                row = cursor.fetchone()
                if not row:
                    raise AuthenticationError("Invalid username or password")
                
                (db_username, password_hash, email, count, created_at, last_login,
                 loved_it, like_it, okay, hate_it, recently_searched) = row
                
                # Verify password
                if self._hash_password(password) != password_hash:
                    raise AuthenticationError("Invalid username or password")
                
                # Update last login
                now = datetime.now().isoformat()
                cursor.execute(
                    "UPDATE users SET last_login = ? WHERE username = ?",
                    (now, username)
                )
                conn.commit()
                
                # Create User object
                user = User(
                    username=db_username,
                    password_hash=password_hash,
                    email=email,
                    count=count,
                    created_at=datetime.fromisoformat(created_at) if created_at else None,
                    last_login=datetime.fromisoformat(last_login) if last_login else None,
                    loved_it=self._deserialize_list(loved_it),
                    like_it=self._deserialize_list(like_it),
                    okay=self._deserialize_list(okay),
                    hate_it=self._deserialize_list(hate_it),
                    recently_searched=self._deserialize_list(recently_searched)
                )
                
                logger.info(f"User authenticated successfully: {username}")
                return user
                
        except sqlite3.Error as e:
            logger.error(f"Database error during authentication: {e}")
            raise DatabaseError(f"Authentication failed: {e}")
    
    def get_user(self, username: str) -> Optional[User]:
        """Get user by username.
        
        Args:
            username: Username
            
        Returns:
            User object or None if not found
        """
        validate_username(username)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT username, password_hash, email, count, created_at, last_login,
                           loved_it, like_it, okay, hate_it, recently_searched
                    FROM users WHERE username = ?
                """, (username,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                (db_username, password_hash, email, count, created_at, last_login,
                 loved_it, like_it, okay, hate_it, recently_searched) = row
                
                return User(
                    username=db_username,
                    password_hash=password_hash,
                    email=email,
                    count=count,
                    created_at=datetime.fromisoformat(created_at) if created_at else None,
                    last_login=datetime.fromisoformat(last_login) if last_login else None,
                    loved_it=self._deserialize_list(loved_it),
                    like_it=self._deserialize_list(like_it),
                    okay=self._deserialize_list(okay),
                    hate_it=self._deserialize_list(hate_it),
                    recently_searched=self._deserialize_list(recently_searched)
                )
                
        except sqlite3.Error as e:
            logger.error(f"Database error getting user: {e}")
            raise DatabaseError(f"Failed to get user: {e}")
    
    def update_user_preferences(
        self,
        username: str,
        loved_it: Optional[List[str]] = None,
        like_it: Optional[List[str]] = None,
        okay: Optional[List[str]] = None,
        hate_it: Optional[List[str]] = None,
        recently_searched: Optional[List[str]] = None
    ) -> bool:
        """Update user preferences.
        
        Args:
            username: Username
            loved_it: List of loved tracks
            like_it: List of liked tracks
            okay: List of okay tracks
            hate_it: List of hated tracks
            recently_searched: List of recently searched tracks
            
        Returns:
            True if successful
        """
        validate_username(username)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if user exists
                cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
                if not cursor.fetchone():
                    raise DataValidationError(f"User '{username}' not found")
                
                # Update preferences
                updates = []
                params = []
                
                if loved_it is not None:
                    updates.append("loved_it = ?")
                    params.append(self._serialize_list(loved_it))
                
                if like_it is not None:
                    updates.append("like_it = ?")
                    params.append(self._serialize_list(like_it))
                
                if okay is not None:
                    updates.append("okay = ?")
                    params.append(self._serialize_list(okay))
                
                if hate_it is not None:
                    updates.append("hate_it = ?")
                    params.append(self._serialize_list(hate_it))
                
                if recently_searched is not None:
                    updates.append("recently_searched = ?")
                    params.append(self._serialize_list(recently_searched))
                
                if updates:
                    params.append(username)
                    query = f"UPDATE users SET {', '.join(updates)} WHERE username = ?"
                    cursor.execute(query, params)
                    conn.commit()
                    
                    logger.info(f"User preferences updated: {username}")
                    return True
                
                return False
                
        except sqlite3.Error as e:
            logger.error(f"Database error updating preferences: {e}")
            raise DatabaseError(f"Failed to update preferences: {e}")
    
    def decrement_user_count(self, username: str) -> bool:
        """Decrement user's recommendation count.
        
        Args:
            username: Username
            
        Returns:
            True if successful, False if count is already 0
        """
        validate_username(username)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current count
                cursor.execute("SELECT count FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                
                if not row:
                    raise DataValidationError(f"User '{username}' not found")
                
                current_count = row[0]
                
                if current_count <= 0:
                    return False
                
                # Decrement count
                cursor.execute(
                    "UPDATE users SET count = ? WHERE username = ?",
                    (current_count - 1, username)
                )
                conn.commit()
                
                logger.info(f"Count decremented for user: {username}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Database error decrementing count: {e}")
            raise DatabaseError(f"Failed to decrement count: {e}")
    
    def get_all_users(self) -> List[User]:
        """Get all users.
        
        Returns:
            List of all users
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT username, password_hash, email, count, created_at, last_login,
                           loved_it, like_it, okay, hate_it, recently_searched
                    FROM users ORDER BY created_at DESC
                """)
                
                users = []
                for row in cursor.fetchall():
                    (username, password_hash, email, count, created_at, last_login,
                     loved_it, like_it, okay, hate_it, recently_searched) = row
                    
                    users.append(User(
                        username=username,
                        password_hash=password_hash,
                        email=email,
                        count=count,
                        created_at=datetime.fromisoformat(created_at) if created_at else None,
                        last_login=datetime.fromisoformat(last_login) if last_login else None,
                        loved_it=self._deserialize_list(loved_it),
                        like_it=self._deserialize_list(like_it),
                        okay=self._deserialize_list(okay),
                        hate_it=self._deserialize_list(hate_it),
                        recently_searched=self._deserialize_list(recently_searched)
                    ))
                
                return users
                
        except sqlite3.Error as e:
            logger.error(f"Database error getting all users: {e}")
            raise DatabaseError(f"Failed to get all users: {e}")
    
    def export_to_dataframe(self) -> pd.DataFrame:
        """Export all users to pandas DataFrame.
        
        Returns:
            DataFrame with user data
        """
        users = self.get_all_users()
        
        data = []
        for user in users:
            data.append({
                'Username': user.username,
                'Email': user.email,
                'Count': user.count,
                'Created At': user.created_at,
                'Last Login': user.last_login,
                'Loved It': len(user.loved_it),
                'Like It': len(user.like_it),
                'Okay': len(user.okay),
                'Hate It': len(user.hate_it),
                'Recently Searched': len(user.recently_searched)
            })
        
        return pd.DataFrame(data)
