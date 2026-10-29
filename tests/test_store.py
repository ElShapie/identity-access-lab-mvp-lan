import tempfile
import unittest
from pathlib import Path

from app.store import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.store = Store(Path(self.temp.name) / "lab.sqlite")
        self.user = self.store.save({"userName": "ingeniero@example.test", "title": "mantenimiento"})

    def tearDown(self):
        self.temp.cleanup()

    def test_role_permissions_are_least_privilege(self):
        self.assertTrue(self.store.permitted(self.user["id"], "mantenimiento"))
        self.assertFalse(self.store.permitted(self.user["id"], "admin"))

    def test_role_change_applies_to_existing_session_id(self):
        self.store.save({"title": "auditor"}, self.user["id"])
        self.assertFalse(self.store.permitted(self.user["id"], "mantenimiento"))
        self.assertTrue(self.store.permitted(self.user["id"], "registros"))

    def test_deactivation_blocks_existing_session_id(self):
        self.store.save({"active": False}, self.user["id"])
        self.assertFalse(self.store.permitted(self.user["id"], "consulta"))

    def test_unknown_role_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.save({"title": "superuser"}, self.user["id"])

    def test_identity_cannot_be_rebound(self):
        self.assertTrue(self.store.bind_identity(self.user["id"], "subject-a"))
        self.assertFalse(self.store.bind_identity(self.user["id"], "subject-b"))

    def test_delete_deactivates_instead_of_erasing_audit_identity(self):
        self.assertTrue(self.store.deactivate(self.user["id"]))
        self.assertFalse(self.store.permitted(self.user["id"], "consulta"))
        self.assertEqual(self.store.get(self.user["id"])["active"], False)

    def test_card_is_registered_with_normalized_uid(self):
        card = self.store.register_card("0f:c7:28:c9", "ingeniero@example.test", "Tarjeta de prueba")
        self.assertEqual(card["uid"], "0FC728C9")
        self.assertEqual(card["username"], "ingeniero@example.test")
        self.assertEqual(len(self.store.cards()), 1)

    def test_card_is_found_in_both_byte_orders(self):
        self.store.register_card("0FC728C9", "ingeniero@example.test")
        self.assertIsNotNone(self.store.card("0FC728C9"))
        self.assertIsNotNone(self.store.card("C928C70F"))

    def test_invalid_card_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.register_card("no-es-hex", "ingeniero@example.test")
        with self.assertRaises(ValueError):
            self.store.register_card("0FC728C9", "sin-correo")

    def test_tap_is_claimed_only_once(self):
        self.store.record_tap("0FC728C9", "ingeniero@example.test")
        tap = self.store.claim_tap(15)
        self.assertIsNotNone(tap)
        self.assertEqual(tap["username"], "ingeniero@example.test")
        self.assertIsNone(self.store.claim_tap(15))

    def test_tap_outside_the_window_is_ignored(self):
        self.store.record_tap("0FC728C9", "ingeniero@example.test")
        self.assertIsNone(self.store.claim_tap(0))

    def test_removed_card_no_longer_matches(self):
        self.store.register_card("0FC728C9", "ingeniero@example.test")
        self.assertTrue(self.store.remove_card("0FC728C9"))
        self.assertIsNone(self.store.card("0FC728C9"))

    def test_superadmin_is_reserved_for_the_three_roster_owners(self):
        owner = self.store.save({"userName": "emp-001@securityteam.com", "title": "superadmin"})
        self.assertTrue(self.store.permitted(owner["id"], "usuarios"))
        with self.assertRaises(ValueError):
            self.store.save({"userName": "other@example.test", "title": "superadmin"})
        with self.assertRaises(ValueError):
            self.store.save({"title": "auditor"}, owner["id"])

    def test_role_permission_changes_apply_to_existing_users(self):
        self.store.set_role_permissions("mantenimiento", ["consulta"])
        self.assertTrue(self.store.permitted(self.user["id"], "consulta"))
        self.assertFalse(self.store.permitted(self.user["id"], "mantenimiento"))

    def test_admin_role_cannot_manage_users_or_role_permissions_by_default(self):
        admin = self.store.save({"userName": "admin@example.test", "title": "admin"})
        self.assertTrue(self.store.permitted(admin["id"], "admin"))
        self.assertFalse(self.store.permitted(admin["id"], "usuarios"))
        self.assertFalse(self.store.permitted(admin["id"], "roles"))

    def test_superadmin_must_keep_user_and_role_management(self):
        self.store.save({"userName": "emp-010@securityteam.com", "title": "superadmin"})
        with self.assertRaises(ValueError):
            self.store.set_role_permissions("superadmin", ["consulta", "admin"])


if __name__ == "__main__":
    unittest.main()

