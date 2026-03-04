import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).with_name("reservations.db")


@dataclass(frozen=True)
class Reservation:
    id: int
    customer_name: str
    phone: str
    start_at: datetime
    duration_minutes: int

    @property
    def end_at(self) -> datetime:
        return self.start_at + timedelta(minutes=self.duration_minutes)


class ReservationError(Exception):
    pass


class ValidationError(ReservationError):
    pass


class OverlapError(ReservationError):
    pass


class ReservationService:
    def __init__(self, db_path=DEFAULT_DB_PATH, open_hour=9, close_hour=21):
        self.db_path = Path(db_path)
        self.open_hour = open_hour
        self.close_hour = close_hour
        self.initialize_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def initialize_db(self):
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    phone TEXT,
                    start_at TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def list_reservations(self, include_past=False):
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT id, customer_name, phone, start_at, duration_minutes
                FROM reservations
                ORDER BY start_at ASC
                """
            ).fetchall()
        finally:
            conn.close()

        reservations = [
            Reservation(
                id=row[0],
                customer_name=row[1],
                phone=row[2] or "",
                start_at=datetime.fromisoformat(row[3]),
                duration_minutes=row[4],
            )
            for row in rows
        ]

        if include_past:
            return reservations

        now = datetime.now()
        return [reservation for reservation in reservations if reservation.end_at >= now]

    def _validate_request(self, customer_name, start_at, duration_minutes):
        if not customer_name or not customer_name.strip():
            raise ValidationError("Please enter a customer name.")

        if duration_minutes <= 0:
            raise ValidationError("Duration must be greater than 0 minutes.")

        if start_at < datetime.now():
            raise ValidationError("Reservation time must be in the future.")

        if not (self.open_hour <= start_at.hour < self.close_hour):
            raise ValidationError(
                f"Reservations must start between {self.open_hour:02d}:00 and {self.close_hour - 1:02d}:59."
            )

        end_at = start_at + timedelta(minutes=duration_minutes)
        if end_at.hour > self.close_hour or (end_at.hour == self.close_hour and end_at.minute > 0):
            raise ValidationError(f"Reservation must end by {self.close_hour:02d}:00.")

    def validate_request(self, customer_name, start_at, duration_minutes):
        self._validate_request(customer_name, start_at, duration_minutes)

    def _overlaps_existing(self, start_at, end_at):
        for reservation in self.list_reservations(include_past=True):
            if reservation.start_at < end_at and reservation.end_at > start_at:
                return True
        return False

    def has_conflict(self, start_at, duration_minutes):
        end_at = start_at + timedelta(minutes=duration_minutes)
        return self._overlaps_existing(start_at, end_at)

    def create_reservation(self, customer_name, phone, start_at, duration_minutes):
        self._validate_request(customer_name, start_at, duration_minutes)
        end_at = start_at + timedelta(minutes=duration_minutes)

        if self._overlaps_existing(start_at, end_at):
            raise OverlapError("That time overlaps with an existing reservation.")

        conn = self._connect()
        try:
            cursor = conn.execute(
                """
                INSERT INTO reservations (customer_name, phone, start_at, duration_minutes)
                VALUES (?, ?, ?, ?)
                """,
                (
                    customer_name.strip(),
                    (phone or "").strip(),
                    start_at.isoformat(timespec="minutes"),
                    duration_minutes,
                ),
            )
            reservation_id = cursor.lastrowid
            conn.commit()
        finally:
            conn.close()

        return reservation_id

    def cancel_reservation(self, reservation_id):
        conn = self._connect()
        try:
            cursor = conn.execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
