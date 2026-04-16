from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from app.core.config import get_settings


UserStatus = Literal["pending", "approved"]
UserRole = Literal["owner", "admin", "member"]
PBKDF2_ITERATIONS = 100_000


@dataclass(frozen=True)
class AuthUser:
    id: int
    email: str
    full_name: str | None
    access_reason: str | None
    status: UserStatus
    role: UserRole
    created_at: str
    approved_at: str | None


class QueryLimitExceededError(RuntimeError):
    """Raised when a user exceeds the configured daily query quota."""


class AuthService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.db_path = Path(self.settings.auth_db_path).expanduser()

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    access_reason TEXT,
                    status TEXT NOT NULL CHECK(status IN ('pending', 'approved')),
                    role TEXT NOT NULL DEFAULT 'member',
                    created_at TEXT NOT NULL,
                    approved_at TEXT
                );

                CREATE TABLE IF NOT EXISTS auth_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS daily_query_usage (
                    user_id INTEGER NOT NULL,
                    usage_date TEXT NOT NULL,
                    query_count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (user_id, usage_date),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )
            user_columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(users)").fetchall()
            }
            if "role" not in user_columns:
                connection.execute(
                    "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'member'"
                )
            self._bootstrap_owner_account(connection)

    def create_user(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None = None,
        access_reason: str | None = None,
    ) -> AuthUser:
        self.initialize()
        normalized_email = self._normalize_email(email)
        normalized_name = self._normalize_optional_text(full_name)
        normalized_reason = self._normalize_optional_text(access_reason)
        password_hash = self._hash_password(password)
        created_at = self._utcnow().isoformat()
        approved_at = created_at

        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO users (
                        email,
                        password_hash,
                        full_name,
                        access_reason,
                        status,
                        created_at,
                        approved_at
                    )
                    VALUES (?, ?, ?, ?, 'approved', ?, ?)
                    """,
                    (
                        normalized_email,
                        password_hash,
                        normalized_name,
                        normalized_reason,
                        created_at,
                        approved_at,
                    ),
                )
                user_id = int(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise ValueError("An account with this email already exists.") from exc

        return AuthUser(
            id=user_id,
            email=normalized_email,
            full_name=normalized_name,
            access_reason=normalized_reason,
            status="approved",
            role="member",
            created_at=created_at,
            approved_at=approved_at,
        )

    def authenticate_user(self, *, email: str, password: str) -> tuple[str, AuthUser]:
        self.initialize()
        normalized_email = self._normalize_email(email)

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, email, password_hash, full_name, access_reason, status, role, created_at, approved_at
                FROM users
                WHERE email = ?
                """,
                (normalized_email,),
            ).fetchone()

            if row is None or not self._verify_password(password, row["password_hash"]):
                raise ValueError("Invalid email or password.")

            user = self._row_to_user(row)
            self._delete_expired_tokens(connection)
            raw_token = secrets.token_urlsafe(32)
            connection.execute(
                """
                INSERT INTO auth_tokens (user_id, token_hash, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    user.id,
                    self._hash_token(raw_token),
                    self._utcnow().isoformat(),
                    (self._utcnow() + timedelta(days=self.settings.auth_token_ttl_days)).isoformat(),
                ),
            )

        return raw_token, user

    def consume_daily_query(self, *, user_id: int) -> int:
        self.initialize()
        usage_date = self._utcnow().date().isoformat()
        daily_limit = max(int(self.settings.daily_query_limit), 1)

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT query_count
                FROM daily_query_usage
                WHERE user_id = ? AND usage_date = ?
                """,
                (user_id, usage_date),
            ).fetchone()
            current_count = int(row["query_count"]) if row is not None else 0

            if current_count >= daily_limit:
                raise QueryLimitExceededError("Today's GPT explanation quota is exhausted. Please try again tomorrow.")

            if row is None:
                connection.execute(
                    """
                    INSERT INTO daily_query_usage (user_id, usage_date, query_count)
                    VALUES (?, ?, 1)
                    """,
                    (user_id, usage_date),
                )
            else:
                connection.execute(
                    """
                    UPDATE daily_query_usage
                    SET query_count = query_count + 1
                    WHERE user_id = ? AND usage_date = ?
                    """,
                    (user_id, usage_date),
                )

        return daily_limit - current_count - 1

    def get_user_by_token(self, token: str) -> AuthUser | None:
        self.initialize()
        if not token.strip():
            return None

        with self._connect() as connection:
            self._delete_expired_tokens(connection)
            row = connection.execute(
                """
                SELECT u.id, u.email, u.full_name, u.access_reason, u.status, u.role, u.created_at, u.approved_at
                FROM auth_tokens t
                JOIN users u ON u.id = t.user_id
                WHERE t.token_hash = ?
                """,
                (self._hash_token(token.strip()),),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_user(row)

    def list_users(self, *, status: UserStatus | None = None) -> list[AuthUser]:
        self.initialize()
        query = """
            SELECT id, email, full_name, access_reason, status, role, created_at, approved_at
            FROM users
        """
        parameters: tuple[str, ...] = ()
        if status:
            query += " WHERE status = ?"
            parameters = (status,)
        query += " ORDER BY created_at ASC"

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

        return [self._row_to_user(row) for row in rows]

    def approve_user(self, *, email: str) -> AuthUser:
        self.initialize()
        normalized_email = self._normalize_email(email)
        approved_at = self._utcnow().isoformat()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE users
                SET status = 'approved', approved_at = ?
                WHERE email = ?
                """,
                (approved_at, normalized_email),
            )
            if cursor.rowcount == 0:
                raise LookupError("No account exists for that email.")

            row = connection.execute(
                """
                SELECT id, email, full_name, access_reason, status, role, created_at, approved_at
                FROM users
                WHERE email = ?
                """,
                (normalized_email,),
            ).fetchone()

        if row is None:
            raise LookupError("No account exists for that email.")

        return self._row_to_user(row)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _bootstrap_owner_account(self, connection: sqlite3.Connection) -> None:
        if not self.settings.owner_email or not self.settings.owner_password:
            return

        owner_email = self._normalize_email(self.settings.owner_email)
        owner_name = self._normalize_optional_text(self.settings.owner_full_name)
        now = self._utcnow().isoformat()
        existing_user = connection.execute(
            """
            SELECT id, email, password_hash, full_name, access_reason, status, role, created_at, approved_at
            FROM users
            WHERE email = ?
            """,
            (owner_email,),
        ).fetchone()

        if existing_user is None:
            connection.execute(
                """
                INSERT INTO users (
                    email,
                    password_hash,
                    full_name,
                    access_reason,
                    status,
                    role,
                    created_at,
                    approved_at
                )
                VALUES (?, ?, ?, ?, 'approved', 'owner', ?, ?)
                """,
                (
                    owner_email,
                    self._hash_password(self.settings.owner_password),
                    owner_name,
                    "Bootstrap owner account.",
                    now,
                    now,
                ),
            )
            return

        connection.execute(
            """
            UPDATE users
            SET full_name = COALESCE(full_name, ?),
                status = 'approved',
                role = 'owner',
                approved_at = COALESCE(approved_at, ?)
            WHERE email = ?
            """,
            (owner_name, now, owner_email),
        )

    def _delete_expired_tokens(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            "DELETE FROM auth_tokens WHERE expires_at <= ?",
            (self._utcnow().isoformat(),),
        )

    def _row_to_user(self, row: sqlite3.Row) -> AuthUser:
        return AuthUser(
            id=int(row["id"]),
            email=str(row["email"]),
            full_name=str(row["full_name"]) if row["full_name"] is not None else None,
            access_reason=str(row["access_reason"]) if row["access_reason"] is not None else None,
            status=row["status"],
            role=row["role"],
            created_at=str(row["created_at"]),
            approved_at=str(row["approved_at"]) if row["approved_at"] is not None else None,
        )

    def _normalize_email(self, email: str) -> str:
        normalized = email.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("A valid email address is required.")
        return normalized

    def _normalize_optional_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _hash_password(self, password: str) -> str:
        normalized_password = password.strip()
        if len(normalized_password) < 8:
            raise ValueError("Password must be at least 8 characters long.")

        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            normalized_password.encode("utf-8"),
            salt,
            PBKDF2_ITERATIONS,
        )
        return f"{PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        try:
            iterations_text, salt_hex, digest_hex = stored_hash.split("$", 2)
            iterations = int(iterations_text)
            salt = bytes.fromhex(salt_hex)
            expected_digest = bytes.fromhex(digest_hex)
        except (TypeError, ValueError):
            return False

        candidate_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.strip().encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(candidate_digest, expected_digest)

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _utcnow(self) -> datetime:
        return datetime.now(UTC)


auth_service = AuthService()
