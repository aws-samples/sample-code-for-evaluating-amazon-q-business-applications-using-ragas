import unittest
from unittest.mock import patch

from botocore.exceptions import ClientError
from adapters.sts_adapter import StsAdapter
from .constants import TEST_ASSUME_ROLE_WITH_WEB_IDENTITY_RESPONSE, REGION, Q_APP_ROLE_ARN, USER_EMAIL, \
    TEST_ERROR_RESPONSE


class TestStsAdapter(unittest.TestCase):
    @patch("adapters.sts_adapter.boto3.client")
    def test_assume_role_with_oidc_provider_is_successful(self, boto3_client_mock):
        mock_sts_client = boto3_client_mock.return_value
        mock_sts_client.assume_role_with_web_identity.return_value = TEST_ASSUME_ROLE_WITH_WEB_IDENTITY_RESPONSE

        test_sts_adapter = StsAdapter(region=REGION)
        results = test_sts_adapter.assume_role_with_oidc_provider(roleArn=Q_APP_ROLE_ARN,
                                                                  username=USER_EMAIL,
                                                                  open_id_token="testToken")
        self.assertTrue("AccessKeyId" in results)
        self.assertTrue("SecretAccessKey" in results)
        self.assertTrue("SessionToken" in results)

    @patch("adapters.sts_adapter.boto3.client")
    def test_assume_role_with_oidc_provider_raises_exception(self, boto3_client_mock):

        mock_sts_client = boto3_client_mock.return_value
        mock_sts_client.assume_role_with_web_identity.side_effect = ClientError(TEST_ERROR_RESPONSE, "sts")

        test_sts_adapter = StsAdapter(region=REGION)

        with self.assertRaises(ClientError):
            test_sts_adapter.assume_role_with_oidc_provider(roleArn=Q_APP_ROLE_ARN,
                                                            username=USER_EMAIL,
                                                            open_id_token="testToken")