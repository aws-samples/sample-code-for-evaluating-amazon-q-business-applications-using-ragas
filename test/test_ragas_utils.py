from unittest import TestCase
from unittest.mock import patch

from datasets import Dataset
from langchain_aws import BedrockEmbeddings
from ragas.evaluation import Result
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    answer_relevancy,
    faithfulness
)

from utils.ragas_utils import RagasUtils
from .constants import REGION, BEDROCK_EMBEDDING_MODEL_ID, BEDROCK_TEXT_MODEL_ID


class TestRagasUtils(TestCase):
    test_ragas_utils = RagasUtils(REGION, BEDROCK_EMBEDDING_MODEL_ID, BEDROCK_TEXT_MODEL_ID)
    metrics = [answer_relevancy, faithfulness,]

    def test_metric_configuration_is_set_correctly(self):
        self.test_ragas_utils.configure_metrics_to_use_bedrock(self.metrics)

        for metric in self.metrics:
            self.assertIsInstance(metric.embeddings, BedrockEmbeddings)
            self.assertEqual(metric.embeddings.model_id, BEDROCK_EMBEDDING_MODEL_ID)
            self.assertIsInstance(metric.llm, LangchainLLMWrapper)
            self.assertEqual(metric.llm.langchain_llm.model_id, BEDROCK_TEXT_MODEL_ID)

    @patch("utils.ragas_utils.evaluate")
    def test_evaluate_metrics_is_successful(self, ragas_eval_mock):
        test_scores = Dataset.from_dict(
            {
                'answer_relevancy': [0.9],
                'faithfulness': [0.8],
            }
        )

        mock_results = Result(test_scores)
        ragas_eval_mock.return_value = mock_results

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
        results = self.test_ragas_utils.evaluate_dataset(dataset, self.metrics)
        self.assertEqual(results, mock_results)
        evaluate_call_args = ragas_eval_mock.call_args

        self.assertEqual(evaluate_call_args[0][0], dataset)
        self.assertEqual(evaluate_call_args[1]["metrics"], self.metrics)
