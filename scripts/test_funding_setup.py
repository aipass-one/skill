import base64
import contextlib
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch

skill_dir = Path(__file__).resolve().parent.parent / "skills/aipass-app-credit"
spec = importlib.util.spec_from_file_location("funding_setup", skill_dir / "scripts/setup_funding_key.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)

TARGET = {"clientId": "owned-app", "projectId": "test-project", "secretName": "APP_KEY", "retireKeyId": 17}
DEVICE = {"userCode": "ABCD-EFGH", "deviceCode": "private-device-code", "expiresIn": 600, "interval": 5}
AUTHORIZATION = {"scopes": [setup.SCOPE], "accessToken": "private-setup-bearer"}
CREDENTIAL = "afk_" + "x" * 43
ISSUED = {"target": TARGET, "credential": {"key": {"id": 18}, "token": CREDENTIAL}}


class FundingSetupTest(unittest.TestCase):
    def test_one_approval_delivers_key_directly_before_confirmation(self):
        output = io.StringIO()
        with patch.object(setup, "post", side_effect=[DEVICE, AUTHORIZATION, ISSUED, None]) as post, \
                patch.object(setup.time, "sleep"), patch.object(setup, "request_json") as google, \
                patch.object(setup.subprocess, "run") as run, contextlib.redirect_stdout(output):
            run.return_value.returncode = 0
            run.return_value.stdout = "private-google-bearer"
            setup.provision("/test/gcloud", TARGET, "authorized@example.test")

        self.assertEqual(run.call_args.args[0], ["/test/gcloud", "auth", "print-access-token",
                                                "--quiet", "--no-log-http", "--account", "authorized@example.test"])
        google.assert_called_once_with(
            setup.SECRET_MANAGER + "/projects/test-project/secrets/APP_KEY:addVersion",
            {"payload": {"data": base64.b64encode(CREDENTIAL.encode()).decode()}}, "private-google-bearer")
        self.assertEqual([call.args[0] for call in post.call_args_list],
                         [setup.DEVICE, setup.TOKEN, setup.ISSUE, setup.CONFIRM])
        self.assertNotIn(CREDENTIAL, output.getvalue())
        self.assertNotIn(DEVICE["deviceCode"], output.getvalue())
        self.assertNotIn("private-google-bearer", output.getvalue())
        self.assertIn("Retired funding key #17.", output.getvalue())

    def test_creates_only_the_approved_missing_secret(self):
        with patch.object(setup, "request_json", side_effect=[setup.ApiError(404, None), None, None]) as google:
            setup.save_to_secret_manager(TARGET, CREDENTIAL, "private-google-bearer")
        self.assertEqual(google.call_args_list[1].args[:2], (
            setup.SECRET_MANAGER + "/projects/test-project/secrets?secretId=APP_KEY",
            {"replication": {"automatic": {}}}))
        self.assertEqual(google.call_args_list[0], google.call_args_list[2])

    def test_decline_never_issues_or_stores_a_key(self):
        with patch.object(setup, "post", side_effect=[DEVICE, setup.ApiError(400, "access_denied")]) as post, \
                patch.object(setup.time, "sleep"), patch.object(setup, "google_access_token", return_value="google-token"), \
                patch.object(setup, "save_to_secret_manager") as save, \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "declined"):
                setup.provision("/test/gcloud", TARGET, None)
        save.assert_not_called()
        self.assertEqual(post.call_count, 2)

    def test_failed_or_mismatched_storage_never_confirms_retirement(self):
        mismatch = {**ISSUED, "target": {**TARGET, "projectId": "different-project"}}
        for response, expected_calls in ((mismatch, 0), (ISSUED, 1)):
            with self.subTest(expected_calls=expected_calls):
                with patch.object(setup, "post", side_effect=[DEVICE, AUTHORIZATION, response]) as post, \
                        patch.object(setup.time, "sleep"), patch.object(setup, "google_access_token", return_value="google-token"), \
                        patch.object(setup, "save_to_secret_manager", side_effect=setup.ApiError(403, None)) as save, \
                        contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(RuntimeError, "#18"):
                        setup.provision("/test/gcloud", TARGET, None)
                self.assertEqual(save.call_count, expected_calls)
                self.assertEqual([call.args[0] for call in post.call_args_list],
                                 [setup.DEVICE, setup.TOKEN, setup.ISSUE])

    def test_confirmation_retries_only_the_confirmation(self):
        with patch.object(setup, "post", side_effect=[setup.ApiError(503, None), None]) as post, \
                patch.object(setup.time, "sleep"):
            self.assertTrue(setup.confirm("synthetic-setup"))
        self.assertEqual([call.args[0] for call in post.call_args_list], [setup.CONFIRM, setup.CONFIRM])


if __name__ == "__main__":
    unittest.main()
