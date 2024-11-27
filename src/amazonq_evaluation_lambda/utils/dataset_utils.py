from datasets import Dataset
from typing import List, Dict


def create_evaluation_dataset(questions: List[str],
                              answers: List[str],
                              ground_truth: List[str],
                              contexts: List[List[str]]) -> Dataset:
    testcases = {
        'question': questions,
        'answer': answers,
        'ground_truth': ground_truth,
        'contexts': contexts,
    }
    return Dataset.from_dict(testcases)


def get_answers_from_q(q_app_responses: Dict) -> List[str]:
    answers = []
    for q, resp in q_app_responses.items():
        answers.append(resp["systemMessage"])
    return answers


def get_contexts_from_q(q_app_responses: Dict) -> List[List[str]]:
    contexts = []
    for q, resp in q_app_responses.items():
        contexts.append(extract_text_snippets_from_sources_attributes(resp["sourceAttributions"]))
    return contexts


def extract_text_snippets_from_sources_attributes(source_attributions: Dict) -> List[str]:
    snippets = []
    for snippet in source_attributions:
        snippets.append(snippet["snippet"])
    return snippets
