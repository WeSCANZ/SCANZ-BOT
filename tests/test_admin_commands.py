from cogs.general import General
from cogs.verification import RSIVerification


class TestAdminCommands:
    def test_set_staff_role_permissions(self):
        """set_staff_role must declare default_permissions and a runtime check."""
        cmd = RSIVerification.set_staff_role

        assert cmd.default_permissions is not None, "default_permissions is missing"
        assert cmd.default_permissions.administrator is True, "administrator=True is missing"

        # Check for runtime app_commands.check
        assert hasattr(cmd, "checks") and len(cmd.checks) > 0, (
            "No runtime check found. @app_commands.check missing."
        )

    def test_clear_staff_role_permissions(self):
        """clear_staff_role must declare default_permissions and a runtime check."""
        cmd = RSIVerification.clear_staff_role

        assert cmd.default_permissions is not None, "default_permissions is missing"
        assert cmd.default_permissions.administrator is True, "administrator=True is missing"

        # Check for runtime app_commands.check
        assert hasattr(cmd, "checks") and len(cmd.checks) > 0, (
            "No runtime check found. @app_commands.check missing."
        )

    def test_set_log_channel_permissions(self):
        """set_log_channel must declare default_permissions and a runtime check."""
        cmd = General.set_log_channel

        assert cmd.default_permissions is not None, "default_permissions is missing"
        assert cmd.default_permissions.administrator is True, "administrator=True is missing"

        # Check for runtime app_commands.check
        assert hasattr(cmd, "checks") and len(cmd.checks) > 0, (
            "No runtime check found. @app_commands.check missing."
        )
