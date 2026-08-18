import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from poweros_common.models.entities import User, Community
from poweros_common.database import get_engine, get_session_factory
from poweros_common.schemas.auth import (
    UserLogin,
    UserRegister,
    TokenResponse,
    UserResponse,
    UserRole,
)
from poweros_common.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from ..config import AuthDeviceConfig

logger = logging.getLogger("poweros-auth")
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
config = AuthDeviceConfig()


def get_db(request: Request):
    """Retrieves or lazily initializes db session."""
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        try:
            engine = get_engine(config.DATABASE_URL)
            session_factory = get_session_factory(engine)
            request.app.state.session_factory = session_factory
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database service temporarily unavailable: {str(e)}"
            )

    db = session_factory()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(req: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    comm_id = None
    if req.community_id:
        try:
            comm_uuid = uuid.UUID(req.community_id) if isinstance(req.community_id, str) else req.community_id
            comm = db.query(Community).filter(Community.id == comm_uuid).first()
            if not comm:
                raise HTTPException(status_code=404, detail="Community not found")
            comm_id = comm.id
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid community UUID format")

    hashed = hash_password(req.password)
    new_user = User(
        id=uuid.uuid4(),
        email=req.email,
        password_hash=hashed,
        full_name=req.full_name,
        role=req.role.value if hasattr(req.role, 'value') else req.role,
        community_id=comm_id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse(
        id=str(new_user.id),
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        community_id=str(new_user.community_id) if new_user.community_id else None,
        created_at=new_user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
def login(req: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_access_token(
        subject=str(user.id),
        role=user.role,
        community_id=str(user.community_id) if user.community_id else None,
        secret_key=config.JWT_SECRET,
        algorithm=config.JWT_ALGORITHM,
    )

    user_resp = UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        community_id=str(user.community_id) if user.community_id else None,
        created_at=user.created_at,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user_resp,
    )


@router.get("/me", response_model=UserResponse)
def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization.split(" ")[1]
    try:
        payload = decode_access_token(token, secret_key=config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {str(e)}")

    user_id = payload.get("sub")
    try:
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user UUID in token")

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        community_id=str(user.community_id) if user.community_id else None,
        created_at=user.created_at,
    )
