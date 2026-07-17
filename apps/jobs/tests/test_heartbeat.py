from django.test import TestCase

from apps.authentication.services.user_profile import UserProfileService
from apps.jobs.tasks.heartbeat import heartbeat_deactivate_stale_users


class HeartbeatTaskTests(TestCase):
    def test_runs_without_error_against_service_layer(self) -> None:
        UserProfileService().create(email="active@example.com", password="password123")
        heartbeat_deactivate_stale_users.call_local()

    def test_runs_with_no_users(self) -> None:
        heartbeat_deactivate_stale_users.call_local()
