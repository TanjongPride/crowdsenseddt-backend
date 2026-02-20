import uuid
import enum
from sqlalchemy import Column, String, DateTime, Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from app.db.base import Base


class UserRole(str, enum.Enum):
    admin       = "admin"
    contributor = "contributor"
    tester      = "tester"


class User(Base):
    __tablename__ = "users"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email      = Column(String(255), unique=True, nullable=False)
    password   = Column(String(255), nullable=False)
    role       = Column(PgEnum(UserRole), nullable=False, default=UserRole.contributor)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
