import unittest
from unittest.mock import patch

from handlers.q_evaluation_lambda_handler import ACCOUNT_ID
from utils.authentication_utils import AuthenticationUtils
from .constants import TEST_INITIATE_AUTH_RESPONSE, TEST_DESCRIBE_USER_POOL_CLIENT_RESPONSE, REGION, IDENTITY_POOL_ID, \
    CLIENT_ID, USER_POOL_ID, TEST_GET_ID_RESPONSE, TEST_GET_OPEN_ID_TOKEN


class TestAuthenticationUtils(unittest.TestCase):
    @patch("utils.authentication_utils.boto3.client")
    def test_get_token_id_for_cognito_user_is_successful(self, boto3_client_mock):
        mock_cognito_idp_client = boto3_client_mock.return_value
        mock_cognito_idp_client.initiate_auth.return_value = TEST_INITIATE_AUTH_RESPONSE
        mock_cognito_idp_client.describe_user_pool_client.return_value = TEST_DESCRIBE_USER_POOL_CLIENT_RESPONSE

        test_auth_utils = AuthenticationUtils(region=REGION,
                                              account_id=ACCOUNT_ID,
                                              user_pool_id=USER_POOL_ID,
                                              client_id=CLIENT_ID,
                                              identity_pool_id=IDENTITY_POOL_ID)
        self.assertEqual("testIdToken",
                         test_auth_utils.get_token_id_for_cognito_user("username", "somecredentials"))
        mock_cognito_idp_client.describe_user_pool_client.assert_called_once()
        mock_cognito_idp_client.initiate_auth.assert_called_once()

    @patch("utils.authentication_utils.boto3.client")
    def test_get_open_id_from_token_id_is_successful(self, boto3_client_mock):
        mock_cognito_identity_client = boto3_client_mock.return_value
        mock_cognito_identity_client.get_id.return_value = TEST_GET_ID_RESPONSE
        mock_cognito_identity_client.get_open_id_token.return_value = TEST_GET_OPEN_ID_TOKEN

        test_auth_utils = AuthenticationUtils(region=REGION,
                                              account_id=ACCOUNT_ID,
                                              user_pool_id=USER_POOL_ID,
                                              client_id=CLIENT_ID,
                                              identity_pool_id=IDENTITY_POOL_ID)

        self.assertEqual("testToken",
                         test_auth_utils.get_open_id_from_token_id("someIdToken"))
        mock_cognito_identity_client.get_id.assert_called_once()
        mock_cognito_identity_client.get_open_id_token.assert_called_once()
