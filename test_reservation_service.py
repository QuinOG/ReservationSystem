import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from reservation_service import OverlapError, ReservationService, ValidationError


class ReservationServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_reservations.db"
        self.service = ReservationService(db_path=self.db_path, open_hour=9, close_hour=21)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _next_valid_slot(self):
        start = datetime.now().replace(second=0, microsecond=0) + timedelta(days=1)
        start = start.replace(hour=10, minute=0)
        return start

    def test_create_reservation_success(self):
        start = self._next_valid_slot()
        reservation_id = self.service.create_reservation("Alice", "555-1111", start, 60)
        self.assertIsInstance(reservation_id, int)

        rows = self.service.list_reservations(include_past=True)
        self.assertEqual(1, len(rows))
        self.assertEqual("Alice", rows[0].customer_name)

    def test_reject_past_reservation(self):
        with self.assertRaises(ValidationError):
            self.service.create_reservation("Alice", "", datetime.now() - timedelta(hours=1), 60)

    def test_reject_outside_business_hours(self):
        start = self._next_valid_slot().replace(hour=8)
        with self.assertRaises(ValidationError):
            self.service.create_reservation("Alice", "", start, 60)

    def test_reject_reservation_ending_after_close(self):
        start = self._next_valid_slot().replace(hour=20, minute=30)
        with self.assertRaises(ValidationError):
            self.service.create_reservation("Alice", "", start, 60)

    def test_reject_overlap(self):
        start = self._next_valid_slot()
        self.service.create_reservation("Alice", "", start, 60)

        with self.assertRaises(OverlapError):
            self.service.create_reservation("Bob", "", start + timedelta(minutes=30), 60)

    def test_cancel_reservation(self):
        start = self._next_valid_slot()
        reservation_id = self.service.create_reservation("Alice", "", start, 60)
        cancelled = self.service.cancel_reservation(reservation_id)
        self.assertTrue(cancelled)

        rows = self.service.list_reservations(include_past=True)
        self.assertEqual(0, len(rows))


if __name__ == "__main__":
    unittest.main()
