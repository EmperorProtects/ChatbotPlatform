from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Optional, List
import os
import asyncio
import asyncpg
from jose import JWTError, jwt
from passlib.context import CryptContext
import logging
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth_service")

app = FastAPI(
    title="Auth Service", 
    version="2.0.0",
    description="Authentication service with PostgreSQL backend"
)

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "chatbot_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "chatbot_pass_2024")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@postgres:5432/chatbot_db"
# Database configuration
# DATABASE_URL = os.getenv(
#     "DATABASE_URL", 
#     "postgresql://chatbot_user:chatbot_pass@postgres:5432/chatbot_db"
# )

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Global database pool
db_pool = None

# Pydantic models
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None

class User(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    roles: List[dict] = []

class UserInDB(User):
    hashed_password: str
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    password: str
    is_superuser: bool = False

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class Role(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    permissions: dict = {}

# Database functions
async def init_db():
    """Initialize database connection pool"""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=10,
            server_settings={
                'application_name': 'auth_service',
            }
        )
        logger.info("Database connection pool created successfully")
        
        # Test the connection
        async with db_pool.acquire() as connection:
            result = await connection.fetchval("SELECT 1")
            logger.info(f"Database connection test: {result}")
            
    except Exception as e:
        logger.error(f"Failed to create database pool: {e}")
        raise e
        # Fallback to fake database for development
        # logger.warning("Falling back to fake database")
        # global fake_users_db
        # fake_users_db = {
        #     "admin": {
        #         "id": 1,
        #         "username": "admin",
        #         "full_name": "Admin User",
        #         "email": "admin@example.com",
        #         "hashed_password": pwd_context.hash("admin123"),
        #         "is_active": True,
        #         "is_superuser": True,
        #         "roles": [{"id": 1, "name": "admin", "permissions": {}}]
        #     }
        # }

async def close_db():
    """Close database connection pool"""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed")

# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Token utilities
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Database operations with fallback to fake DB
async def get_user_by_username(username: str) -> Optional[UserInDB]:
    """Get user by username from database or fake DB"""
    if db_pool:
        try:
            async with db_pool.acquire() as connection:
                query = """
                    SELECT u.id, u.username, u.email, u.full_name, u.hashed_password, 
                           u.is_active, u.is_superuser, u.last_login, u.failed_login_attempts,
                           u.locked_until
                    FROM users u 
                    WHERE u.username = $1
                """
                row = await connection.fetchrow(query, username)
                if row:
                    return UserInDB(**dict(row))
        except Exception as e:
            logger.error(f"Database error, falling back to fake DB: {e}")
    
    # Fallback to fake database
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return UserInDB(**user_dict)
    return None

async def get_user_by_id(user_id: int) -> Optional[User]:
    """Get user by ID with roles"""
    if db_pool:
        try:
            async with db_pool.acquire() as connection:
                result = await connection.fetchrow(
                    "SELECT * FROM get_user_with_roles($1)", user_id
                )
                if result:
                    data = dict(result)
                    if isinstance(data.get("roles"), str):
                        data["roles"] = json.loads(data["roles"])
                    return User(**dict(data))
        except Exception as e:
            logger.error(f"Database error, falling back to fake DB: {e}")
    
    # Fallback to fake database
    for user_data in fake_users_db.values():
        if user_data["id"] == user_id:
            return User(**user_data)
    return None

async def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate user with username and password"""
    user = await get_user_by_username(username)
    if not user:
        return None
        
    # Check if user is locked (only for real DB)
    
    # if db_pool and user.locked_until and user.locked_until > datetime.utcnow():
    #     logger.warning(f"User {username} is currently locked until {user.locked_until}")
    #     return None
        
    if not user.is_active:
        return None

        
    if not verify_password(password, user.hashed_password):

        # Increment failed attempts (only for real DB)
        if db_pool:
            try:
                async with db_pool.acquire() as connection:
                    failed_attempts = user.failed_login_attempts + 1
                    locked_until = None
                    
                    # Lock user after 5 failed attempts for 30 minutes
                    if failed_attempts >= 5:
                        locked_until = datetime.utcnow() + timedelta(minutes=30)
                        
                    await connection.execute("""
                        UPDATE users 
                        SET failed_login_attempts = $1, locked_until = $2
                        WHERE id = $3
                    """, failed_attempts, locked_until, user.id)
            except Exception as e:
                logger.error(f"Failed to update login attempts: {e}")
        return None
        
    # Reset failed attempts on successful login (only for real DB)
    if db_pool:
        try:
            async with db_pool.acquire() as connection:
                await connection.execute("""
                    UPDATE users 
                    SET failed_login_attempts = 0, locked_until = NULL, last_login = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, user.id)
        except Exception as e:
            logger.error(f"Failed to reset login attempts: {e}")
    
    return user

async def create_user_session(user_id: int, access_token: str, refresh_token: str, 
                            request: Request) -> str:
    """Create user session in database"""
    if db_pool:
        try:
            async with db_pool.acquire() as connection:
                expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                client_ip = request.client.host if request.client else None
                user_agent = request.headers.get("user-agent", "")
                await connection.execute("""
                INSERT INTO user_sessions (user_id, session_token, refresh_token, expires_at, ip_address, user_agent) VALUES ($1, $2, $3, $4, $5, $6)
                """, user_id, access_token, refresh_token, expires_at, client_ip, user_agent) 
                
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
        
    return access_token

async def cleanup_expired_sessions():
    """Clean up expired sessions"""
    if db_pool:
        try:
            async with db_pool.acquire() as connection:
                deleted = await connection.fetchval("SELECT cleanup_expired_sessions()")
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} expired sessions")
        except Exception as e:
            logger.error(f"Failed to cleanup sessions: {e}")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current user from token"""
    logger.info(f"RAW token len={len(token) if token else None}, head={token[:20] if token else None}")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        token_type: str = payload.get("type")
        
        if username is None or token_type != "access":
            raise credentials_exception
            
        token_data = TokenData(username=username, user_id=user_id)
    except JWTError:
        raise credentials_exception
        
    # Verify token exists in database (only for real DB)
    if db_pool:
        try:
            async with db_pool.acquire() as connection:
                session = await connection.fetchrow("""
                    SELECT * FROM user_sessions 
                    WHERE session_token = $1 AND expires_at > CURRENT_TIMESTAMP
                """, token)
                
                if not session:
                    raise credentials_exception
        except Exception as e:
            logger.error(f"Session verification failed: {e}")
    
    if user_id:
        user = await get_user_by_id(user_id)
    else:
        # Fallback for fake DB
        user_data = fake_users_db.get(username)
        if user_data:
            user = User(**user_data)
        else:
            user = None
            
    if user is None:
        raise credentials_exception
        
    return user

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    await init_db()
    # Start background task to cleanup expired sessions
    asyncio.create_task(periodic_cleanup())

@app.on_event("shutdown")
async def shutdown_event():
    await close_db()

async def periodic_cleanup():
    """Periodic cleanup of expired sessions"""
    while True:
        try:
            await cleanup_expired_sessions()
            # Run cleanup every hour
            await asyncio.sleep(3600)
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes on error

# API Routes
@app.get("/")
async def root():
    db_status = "PostgreSQL" if db_pool else "Fake Database (Fallback)"
    return {
        "message": "Auth Service", 
        "version": "2.0.0",
        "database": db_status,
        "features": ["JWT Authentication", "Role-based Access", "Session Management"]
    }

@app.get("/health")
async def health():
    if db_pool:
        try:
            async with db_pool.acquire() as connection:
                await connection.fetchval("SELECT 1")
            return {
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "degraded", 
                "database": "disconnected",
                "fallback": "fake_db_active",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    else:
        return {
            "status": "healthy",
            "database": "fake_db_active",
            "timestamp": datetime.utcnow().isoformat()
        }

@app.post("/token", response_model=Token)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    logger.info(user)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}, 
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "user_id": user.id}
    )
    
    # Store session in database
    await create_user_session(user.id, access_token, refresh_token, request)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_token": refresh_token
    }

@app.post("/refresh", response_model=Token)
async def refresh_token(request: Request, refresh_token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        token_type: str = payload.get("type")
        
        if username is None or token_type != "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Verify refresh token exists in database (only for real DB)
    if db_pool:
        try:
            async with db_pool.acquire() as connection:
                session = await connection.fetchrow("""
                    SELECT * FROM user_sessions 
                    WHERE refresh_token = $1 AND user_id = $2
                """, refresh_token, user_id)
                
                if not session:
                    raise credentials_exception
        except Exception as e:
            logger.error(f"Refresh token verification failed: {e}")
    
    user = await get_user_by_id(user_id) if user_id else None
    if not user or not user.is_active:
        # Fallback for fake DB
        if username in fake_users_db:
            user_data = fake_users_db[username]
            user = User(**user_data)
        else:
            raise credentials_exception
    
    # Create new tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    new_refresh_token = create_refresh_token(
        data={"sub": user.username, "user_id": user.id}
    )
    
    # Update session with new tokens (only for real DB)
    if db_pool:
        try:
            async with db_pool.acquire() as connection:
                expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                await connection.execute("""
                    UPDATE user_sessions 
                    SET session_token = $1, refresh_token = $2, expires_at = $3, last_accessed = CURRENT_TIMESTAMP
                    WHERE refresh_token = $4
                """, new_access_token, new_refresh_token, expires_at, refresh_token)
        except Exception as e:
            logger.error(f"Failed to update session: {e}")
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer", 
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_token": new_refresh_token
    }

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/users", response_model=List[User])
async def list_users(
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    # Check if user has admin permissions
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    if db_pool:
        try:
            async with db_pool.acquire() as connection:
                rows = await connection.fetch("""
                    SELECT * FROM get_user_with_roles(u.id)
                    FROM users u
                    ORDER BY u.id
                    LIMIT $1 OFFSET $2
                """, limit, skip)
                
                users = []
                for row in rows:
                    data = dict(result)
                    if isinstance(data.get("roles"), str):
                        data["roles"] = json.loads(data["roles"])
                    users.append(User(**dict(data)))
                return users
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
    
    # Fallback to fake database
    users = [User(**user_data) for user_data in fake_users_db.values()]
    return users[skip:skip+limit]

@app.post("/users", response_model=User)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    if db_pool:
        try:
            async with db_pool.acquire() as connection:
                # Check if username or email already exists
                existing = await connection.fetchrow("""
                    SELECT id FROM users WHERE username = $1 OR email = $2
                """, user_data.username, user_data.email)
                
                if existing:
                    raise HTTPException(
                        status_code=400,
                        detail="Username or email already registered"
                    )
                
                hashed_password = get_password_hash(user_data.password)
                
                user_id = await connection.fetchval("""
                    INSERT INTO users (username, email, full_name, hashed_password, is_superuser)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                """, user_data.username, user_data.email, user_data.full_name, 
                    hashed_password, user_data.is_superuser)
                
                # Get the created user with roles
                user = await get_user_by_id(user_id)
                return user
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise HTTPException(status_code=500, detail="Failed to create user")
    
    # Fallback for fake DB
    raise HTTPException(status_code=501, detail="User creation not implemented in fake DB mode")

@app.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    # Remove session from database (only for real DB)
    if db_pool:
        try:
            async with db_pool.acquire() as connection:
                await connection.execute("""
                    DELETE FROM user_sessions WHERE session_token = $1
                """, token)
        except Exception as e:
            logger.error(f"Failed to remove session: {e}")
    
    return {"message": "Successfully logged out"}

@app.get("/roles", response_model=List[Role])
async def list_roles(current_user: User = Depends(get_current_user)):
    if db_pool:
        try:
            async with db_pool.acquire() as connection:
                rows = await connection.fetch("SELECT * FROM roles ORDER BY name")
                return [Role(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to list roles: {e}")
    
    # Fallback roles for fake DB
    return [
        Role(id=1, name="admin", description="System Administrator", permissions={}),
        Role(id=2, name="manager", description="Content Manager", permissions={}),
        Role(id=3, name="operator", description="Chat Operator", permissions={})
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
