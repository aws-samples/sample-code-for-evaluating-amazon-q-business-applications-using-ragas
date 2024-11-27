from unittest import TestCase
from unittest.mock import patch

from botocore.exceptions import ClientError

from .constants import TEST_Q_CHAT_RESPONSE, REGION, Q_APPLICATION_ID, TEST_CREDENTIALS, TEST_ERROR_RESPONSE
from adapters.qbusiness_adapter import QbusinessAdapter


class TestQbusinessAdapter(TestCase):
    @patch("adapters.qbusiness_adapter.boto3.client")
    def test_get_response_from_q_is_successful(self, boto3_client_mock):
        mock_qbusiness_client = boto3_client_mock.return_value
        mock_qbusiness_client.chat_sync.return_value = TEST_Q_CHAT_RESPONSE
        test_qbusiness_adapter = QbusinessAdapter(region=REGION, credentials=TEST_CREDENTIALS)

        sample_questions = ["what is qbusiness?"]
        expected_results = dict.fromkeys(sample_questions, TEST_Q_CHAT_RESPONSE)

        self.assertEqual(test_qbusiness_adapter.get_q_application_response(sample_questions, Q_APPLICATION_ID),
                         expected_results)

    @patch("adapters.qbusiness_adapter.boto3.client")
    def test_get_response_from_q_raises_exception(self, boto3_client_mock):
        mock_qbusiness_client = boto3_client_mock.return_value
        mock_qbusiness_client.chat_sync.side_effect = ClientError(TEST_ERROR_RESPONSE, "qbusiness")

        test_qbusiness_adapter = QbusinessAdapter(region=REGION, credentials=TEST_CREDENTIALS)
        sample_questions = ["what is qbusiness?"]

        with self.assertRaises(ClientError):
            test_qbusiness_adapter.get_q_application_response(sample_questions, Q_APPLICATION_ID)
