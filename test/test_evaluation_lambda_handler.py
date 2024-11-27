import unittest
from unittest.mock import patch

from datasets import Dataset
from ragas.evaluation import Result

from ragas.metrics import answer_relevancy, faithfulness, context_recall, context_precision

from .constants import TEST_Q_CHAT_RESPONSE, REGION, Q_APPLICATION_ID, BEDROCK_EMBEDDING_MODEL_ID, \
    BEDROCK_TEXT_MODEL_ID, IDENTITY_POOL_ID, USER_POOL_ID, CLIENT_ID, Q_APP_ROLE_ARN, USER_EMAIL, USER_SECRET_ID


class TestEvaluationLambdaHandler(unittest.TestCase):
    @patch.dict("os.environ", {"Region": REGION,
                               "QBusinessApplicationId": Q_APPLICATION_ID,
                               "BedrockEmbeddingModelId": BEDROCK_EMBEDDING_MODEL_ID,
                               "BedrockTextModelId": BEDROCK_TEXT_MODEL_ID,
                               "USER_POOL_ID": USER_POOL_ID,
                               "CLIENT_ID": CLIENT_ID,
                               "IDENTITY_POOL_ID": IDENTITY_POOL_ID,
                               "Q_APP_ROLE_ARN": Q_APP_ROLE_ARN,
                               "USER_EMAIL": USER_EMAIL,
                               "USER_SECRET_ID": USER_SECRET_ID})
    @patch("handlers.q_evaluation_lambda_handler.QbusinessAdapter")
    @patch("handlers.q_evaluation_lambda_handler.RagasUtils")
    @patch("handlers.q_evaluation_lambda_handler.SecretManagerAdapter")
    @patch("handlers.q_evaluation_lambda_handler.AuthenticationUtils")
    @patch("handlers.q_evaluation_lambda_handler.StsAdapter")
    def test_evaluation_lambda_handler_is_successful(self,
                                                     mock_sts_adapter,
                                                     mock_auth_utils,
                                                     mock_secret_manager_adapter,
                                                     mock_ragas_utils, mock_qbusiness_adapter):
        qbusiness_adapter_mock = mock_qbusiness_adapter.return_value
        qbusiness_adapter_mock.get_q_application_response.return_value = {"what is Q?": TEST_Q_CHAT_RESPONSE}
        sts_adapter_mock = mock_sts_adapter.return_value
        auth_utils_mock = mock_auth_utils.return_value
        secret_manager_adapter_mock = mock_secret_manager_adapter.return_value
        secret_manager_adapter_mock.get_secret.return_value = {"password": "some_test_password"}

        test_scores = Dataset.from_dict(
            {
                'answer_relevancy': [0.9],
                'faithfulness': [0.8],
                'context_recall': [0.9],
                'context_precision': [0.8],
            }
        )

        questions = ["test question"]
        ground_truths = ["test ground truth"]
        answers = ["test answer"]
        contexts = [["test contexts"]]
        dataset = Dataset.from_dict(
            {
                'question': questions,
                'answer': answers,
                'ground_truth': ground_truths,
                'contexts': contexts,
            }
        )
        mock_results = Result(scores=test_scores, dataset=dataset)
        ragas_utils_mock = mock_ragas_utils.return_value
        ragas_utils_mock.evaluate_dataset.return_value = mock_results
        ragas_utils_mock.configure_metrics_to_use_bedrock.return_value = None

        expected_evaluation_metrics = [answer_relevancy,
                                       faithfulness,
                                       context_recall,
                                       context_precision]
        testset = [{
            "question": "what is Q?",
            "ground_truth": "Q is an AWS service"
        }]

        from handlers import q_evaluation_lambda_handler
        q_evaluation_lambda_handler.lambda_handler({"testset": testset}, None)

        qbusiness_adapter_mock.get_q_application_response.assert_called_with(['what is Q?'], Q_APPLICATION_ID)
        ragas_utils_mock.configure_metrics_to_use_bedrock.assert_called_with(expected_evaluation_metrics)
        ragas_utils_mock.evaluate_dataset.assert_called_once()
        sts_adapter_mock.assume_role_with_oidc_provider.assert_called_once()
        auth_utils_mock.get_token_id_for_cognito_user.assert_called_once()
        auth_utils_mock.get_open_id_from_token_id.assert_called_once()
        secret_manager_adapter_mock.get_secret.assert_called_once()

        evaluate_call_args = ragas_utils_mock.evaluate_dataset.call_args
        self.assertIsInstance(evaluate_call_args[0][0], Dataset)
        self.assertEqual(evaluate_call_args[0][1], expected_evaluation_metrics)

    def test_when_testset_exceeds_limits_handler_raises_exception(self):
        testset = [{
            "question": "what is Q?",
            "ground_truth": "Q is an AWS service"
        } for i in range(20)]
        with self.assertRaises(Exception):
            from handlers import q_evaluation_lambda_handler
            q_evaluation_lambda_handler.lambda_handler({"testset": testset}, None)
