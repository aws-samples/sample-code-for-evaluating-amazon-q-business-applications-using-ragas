import unittest
from unittest.mock import patch

from botocore.exceptions import ClientError

from adapters.secret_manager_adapter import SecretManagerAdapter
from .constants import GET_SECRET_RESPONSE, REGION, USER_SECRET_ID, TEST_ERROR_RESPONSE


class TestSecretManagerAdapter(unittest.TestCase):
    @patch("adapters.secret_manager_adapter.boto3.client")
    def test_get_secret_value_is_successful(self, boto3_client_mock):
        mock_secret_manager_client = boto3_client_mock.return_value
        mock_secret_manager_client.get_secret_value.return_value = GET_SECRET_RESPONSE

        test_secret_manager_adapter = SecretManagerAdapter(region=REGION)
        results = test_secret_manager_adapter.get_secret(USER_SECRET_ID)

        expected_password_value = "sometestPassword"
        self.assertEqual(results.get("password"), expected_password_value)

    @patch("adapters.secret_manager_adapter.boto3.client")
    def test_get_secret_value_raises_exception(self, boto3_client_mock):
        mock_secret_manager_client = boto3_client_mock.return_value
        mock_secret_manager_client.get_secret_value.side_effect = ClientError(TEST_ERROR_RESPONSE, "secretsmanager")

        test_secret_manager_adapter = SecretManagerAdapter(region=REGION)

        with self.assertRaises(ClientError):
            test_secret_manager_adapter.get_secret(USER_SECRET_ID)

