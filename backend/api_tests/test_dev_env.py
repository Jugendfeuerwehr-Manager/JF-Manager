import tempfile
from pathlib import Path
from unittest import mock

from cryptography.fernet import Fernet
from django.test import SimpleTestCase

import dev_env


class DevEnvTests(SimpleTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.env_file = Path(self.directory.name) / ".env"
        patcher = mock.patch.object(dev_env, "ENV_FILE", self.env_file)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_ensure_creates_missing_secrets_without_printing_them(self):
        with mock.patch("builtins.print") as printed:
            dev_env.ensure()
        values = dev_env.read_env(self.env_file)
        self.assertTrue(dev_env.valid_fernet(values["FIELD_ENCRYPTION_KEY"]))
        self.assertTrue(values["DJANGO_SECRET_KEY"])
        self.assertEqual(values["DEBUG"], "True")
        output = " ".join(str(call) for call in printed.call_args_list)
        self.assertNotIn(values["FIELD_ENCRYPTION_KEY"], output)
        self.assertNotIn(values["DJANGO_SECRET_KEY"], output)
        self.assertEqual(self.env_file.stat().st_mode & 0o777, 0o600)

    def test_ensure_never_replaces_a_valid_key_but_repairs_a_broken_one(self):
        key = Fernet.generate_key().decode()
        self.env_file.write_text(f"# Kommentar\nFIELD_ENCRYPTION_KEY={key}\nDJANGO_SECRET_KEY='abc'\n")
        with mock.patch("builtins.print"):
            dev_env.ensure()
        self.assertEqual(dev_env.read_env(self.env_file)["FIELD_ENCRYPTION_KEY"], key)
        self.assertEqual(dev_env.read_env(self.env_file)["DJANGO_SECRET_KEY"], "abc")
        self.assertIn("# Kommentar", self.env_file.read_text())
        dev_env.set_env_value("FIELD_ENCRYPTION_KEY", "kaputt", self.env_file)
        with mock.patch("builtins.print"):
            dev_env.ensure()
        repaired = dev_env.read_env(self.env_file)["FIELD_ENCRYPTION_KEY"]
        self.assertNotEqual(repaired, "kaputt")
        self.assertTrue(dev_env.valid_fernet(repaired))

    def test_env_file_takes_precedence_over_inherited_variables(self):
        key = Fernet.generate_key().decode()
        self.env_file.write_text(f"FIELD_ENCRYPTION_KEY={key}\n")
        with mock.patch.dict("os.environ", {"FIELD_ENCRYPTION_KEY": "geerbt", "DJANGO_SETTINGS_MODULE": "x"}):
            environment = dev_env.environment()
        self.assertEqual(environment["FIELD_ENCRYPTION_KEY"], key)
        self.assertEqual(environment["DJANGO_SETTINGS_MODULE"], dev_env.DEV_SETTINGS)
        self.assertEqual(environment["PIPENV_DONT_LOAD_ENV"], "1")

    def test_reset_requires_explicit_confirmation(self):
        with mock.patch.object(dev_env, "manage") as manage, mock.patch("builtins.print"):
            self.assertEqual(dev_env.reset(""), 1)
            self.assertEqual(dev_env.reset("yes"), 1)
        manage.assert_not_called()

    def test_check_reports_a_key_mismatch_with_the_reset_hint(self):
        failed = mock.Mock(returncode=1, stdout="", stderr="CommandError")
        with mock.patch.object(dev_env, "manage", return_value=failed), mock.patch("builtins.print") as printed:
            self.assertEqual(dev_env.check(), 3)
        self.assertIn("reset --confirm ja", str(printed.call_args))
