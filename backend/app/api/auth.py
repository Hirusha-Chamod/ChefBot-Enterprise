from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from app.db.database import get_db_connection
from app.db.models import UserCreate, UserLogin, UserResponse, Token
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    """Dependency to retrieve current authenticated user from JWT token."""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

    conn = get_db_connection()
    user = conn.execute("SELECT id, username, email, dietary_profile FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        dietary_profile=user["dietary_profile"] or "Standard"
    )

@router.post("/register", response_model=Token)
def register(user_data: UserCreate):
    """Registers a new user with encrypted bcrypt password hashing."""
    conn = get_db_connection()
    cursor = conn.cursor()

    existing = cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (user_data.username, user_data.email)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already registered.")

    hashed_pw = get_password_hash(user_data.password)
    cursor.execute(
        "INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)",
        (user_data.username, user_data.email, hashed_pw)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    user_resp = UserResponse(id=user_id, username=user_data.username, email=user_data.email, dietary_profile="Standard")
    access_token = create_access_token({"sub": user_data.username})
    return Token(access_token=access_token, user=user_resp)

@router.post("/login", response_model=Token)
def login(login_data: UserLogin):
    """Authenticates a user and issues a JWT token."""
    conn = get_db_connection()
    user = conn.execute("SELECT id, username, email, hashed_password, dietary_profile FROM users WHERE username = ?", (login_data.username,)).fetchone()
    conn.close()

    if not user or not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password.")

    user_resp = UserResponse(id=user["id"], username=user["username"], email=user["email"], dietary_profile=user["dietary_profile"] or "Standard")
    access_token = create_access_token({"sub": user["username"]})
    return Token(access_token=access_token, user=user_resp)

@router.get("/me", response_model=UserResponse)
def get_me(current_user: UserResponse = Depends(get_current_user)):
    """Returns profile details of current logged-in user."""
    return current_user
