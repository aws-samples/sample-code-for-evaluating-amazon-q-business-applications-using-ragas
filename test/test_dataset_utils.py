import unittest

from .constants import TEST_Q_CHAT_RESPONSE
from utils.dataset_utils import get_answers_from_q, get_contexts_from_q, create_evaluation_dataset


class TestDatasetUtils(unittest.TestCase):
    q_app_responses: dict = {"what is Q?": TEST_Q_CHAT_RESPONSE}

    def test_answers_is_extracted_successfully(self):
        expected_answers = ["test message"]
        answers = get_answers_from_q(self.q_app_responses)
        self.assertEqual(expected_answers, answers)

    def test_contexts_are_extracted_successfully(self):
        expected_contexts = [["data snippet"]]
        contexts = get_contexts_from_q(self.q_app_responses)
        self.assertEqual(expected_contexts, contexts)

    def test_dataset_is_created_correctly(self):
        questions = ["test question"]
        ground_truths = ["test ground thruth"]
        answers = ["test answer"]
        contexts = [["test contexts"]]

        dataset = create_evaluation_dataset(questions=questions,
                                            ground_truth=ground_truths,
                                            answers=answers,
                                            contexts=contexts)
        self.assertEqual(dataset.shape, (1, 4))
        self.assertEqual(dataset.column_names, ["question", "answer", "ground_truth", "contexts"])


