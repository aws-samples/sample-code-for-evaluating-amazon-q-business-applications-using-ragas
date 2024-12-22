import nest_asyncio
from datasets import Dataset
from langchain_aws import BedrockEmbeddings
from langchain_aws import ChatBedrock
from ragas.evaluation import Result
from ragas.llms import LangchainLLMWrapper
from ragas import evaluate, RunConfig
from ragas.metrics.base import Metric

from typing import List


class RagasUtils:
    MAX_WORKERS_COUNT = 2

    def __init__(self, region: str, bedrock_embedding_model_id: str, bedrock_llm_model_id: str):
        self.region = region
        self.bedrock_embedding_model_id = bedrock_embedding_model_id
        self.bedrock_llm_model_id = bedrock_llm_model_id

    # turning test into numerical vector
    def _get_bedrock_embeddings(self):
        return BedrockEmbeddings(
            model_id=self.bedrock_embedding_model_id,
            region_name=self.region)

    # used for metrics evaluation
    def _get_bedrock_llm_model_wrapper(self):
        bedrock_model = ChatBedrock(
            region_name=self.region,
            endpoint_url=f"https://bedrock-runtime.{self.region}.amazonaws.com",
            model_id=self.bedrock_llm_model_id)
        return LangchainLLMWrapper(bedrock_model)

    def configure_metrics_to_use_bedrock(self, metrics: List[Metric]):
        bedrock_llm_wrapper = self._get_bedrock_llm_model_wrapper()
        bedrock_embeddings = self._get_bedrock_embeddings()
        for m in metrics:
            m.__setattr__("llm", bedrock_llm_wrapper)
            m.__setattr__("embeddings", bedrock_embeddings)

    def evaluate_dataset(self, evaluation_dataset: Dataset, metrics: List[Metric]) -> Result:
        nest_asyncio.apply()
        evaluation_results = evaluate(
            evaluation_dataset,
            metrics=metrics,
            run_config=RunConfig(max_workers=self.MAX_WORKERS_COUNT),
        )
        return evaluation_results
