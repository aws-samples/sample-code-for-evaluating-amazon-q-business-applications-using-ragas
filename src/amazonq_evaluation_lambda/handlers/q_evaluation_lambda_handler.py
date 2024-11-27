from enum import Enum
import os
import jwt
from typing import Dict, Any

from adapters.ssooidc_adapter import SSOOIDCAdapter
from aws_embedded_metrics import metric_scope, MetricsLogger
from ragas.metrics import (answer_relevancy, faithfulness, context_recall, context_precision)

from adapters.qbusiness_adapter import QbusinessAdapter
from adapters.secret_manager_adapter import SecretManagerAdapter
from adapters.sts_adapter import StsAdapter
from utils.authentication_utils import AuthenticationUtils
from utils.dataset_utils import get_answers_from_q, create_evaluation_dataset, get_contexts_from_q
from utils.logging_utils import setup_logging
from utils.ragas_utils import RagasUtils

from aws_embedded_metrics.config import get_config

Config = get_config()
Config.namespace = "QEvaluationLambda"

logger = setup_logging(__name__)

IdentitySource = Enum('IdentitySource', ['COGNITO', 'IDC'])

REGION = os.environ.get("Region")
ACCOUNT_ID = os.environ.get("AccountId")
APPLICATION_ID = os.environ.get("QBusinessApplicationId")
BEDROCK_EMBEDDING_MODEL_ID = os.environ.get("BedrockEmbeddingModelId")
BEDROCK_TEXT_MODEL_ID = os.environ.get("BedrockTextModelId")

USER_POOL_ID = os.environ.get("UserPoolId")
CLIENT_ID = os.environ.get("ClientId")
IDENTITY_POOL_ID = os.environ.get("IdentityPoolId")
Q_APP_ROLE_ARN = os.environ.get("QAppRoleArn")
USER_EMAIL = os.environ.get("UserEmail")
USER_SECRET_ID = os.environ.get("UserSecretId")

# Set to IDC for Q App that use Identity Center as identity source
Q_APP_IDENTITY_SOURCE = IdentitySource[
    os.environ.get(
        "QAppIdentitySource",
        default=IdentitySource.COGNITO.name)]
IDC_APP_TRUSTED_IDENTITY_PROPAGATION_ARN = os.environ.get("IdcAppTrustedIdentityPropagationArn")

MAX_ALLOWED_ENTRIES = 10


def parse_field_from_event(field_name: str, event: Dict):
    if field_name not in event:
        raise Exception(f"expected field {field_name} was not found in the event")
    return event[field_name]


@metric_scope
def lambda_handler(event: Dict, context: Any, metrics: MetricsLogger):
    testset = parse_field_from_event("testset", event)
    if len(testset) > MAX_ALLOWED_ENTRIES:
        raise Exception("Maximum allowed entries exceeded!")

    questions: list[str] = [entry["question"] for entry in testset]
    ground_truths: list[str] = [entry["ground_truth"] for entry in testset]

    logger.info(f"Starting the QBusiness client authentication for the application {APPLICATION_ID}")
    secret_manager_adapter = SecretManagerAdapter(REGION)
    user_secret_dict = secret_manager_adapter.get_secret(USER_SECRET_ID)
    if "password" not in user_secret_dict:
        raise Exception("No 'password' key found in secret value!")
    user_secret_value = user_secret_dict["password"]

    auth_utils = AuthenticationUtils(REGION,
                                     ACCOUNT_ID,
                                     USER_POOL_ID,
                                     CLIENT_ID,
                                     IDENTITY_POOL_ID)

    id_token = auth_utils.get_token_id_for_cognito_user(USER_EMAIL, user_secret_value)
    ssooidc_adapter = SSOOIDCAdapter(REGION)
    sts_adapter = StsAdapter(REGION)

    if Q_APP_IDENTITY_SOURCE == IdentitySource.IDC:
        identity_context = ssooidc_adapter.create_token_with_iam(
            id_token, IDC_APP_TRUSTED_IDENTITY_PROPAGATION_ARN)["sts:identity_context"]
        credentials = sts_adapter.assume_role(Q_APP_ROLE_ARN, USER_EMAIL, identity_context)
    elif Q_APP_IDENTITY_SOURCE == IdentitySource.COGNITO:
        open_id_token = auth_utils.get_open_id_from_token_id(id_token)
        credentials = sts_adapter.assume_role_with_oidc_provider(Q_APP_ROLE_ARN, USER_EMAIL, open_id_token)
    else:
        raise Exception(f"Invalid identity source {Q_APP_IDENTITY_SOURCE}. Valid values are {IdentitySource.list()}")

    qbusiness_adapter = QbusinessAdapter(REGION, credentials)
    logger.info(f"Finished the QBusiness client authentication for the application {APPLICATION_ID}")

    logger.info(f"Getting answers and contexts from q application {APPLICATION_ID}")
    q_app_responses = qbusiness_adapter.get_q_application_response(questions, APPLICATION_ID)
    logger.info(f"Done getting answers and contexts from q application {APPLICATION_ID}")

    q_app_answers: list[str] = get_answers_from_q(q_app_responses)
    q_app_contexts: list[str] = get_contexts_from_q(q_app_responses)

    evaluation_dataset = create_evaluation_dataset(questions=questions,
                                                   ground_truth=ground_truths,
                                                   answers=q_app_answers,
                                                   contexts=q_app_contexts)

    evaluations_metrics = [answer_relevancy,
                           faithfulness,
                           context_recall,
                           context_precision]
    ragas_utils = RagasUtils(region=REGION,
                             bedrock_embedding_model_id=BEDROCK_EMBEDDING_MODEL_ID,
                             bedrock_llm_model_id=BEDROCK_TEXT_MODEL_ID)

    logger.info(f"Using metrics {str(evaluations_metrics)} to use {BEDROCK_EMBEDDING_MODEL_ID} embedding"
                + f" and {BEDROCK_TEXT_MODEL_ID} llm models")
    ragas_utils.configure_metrics_to_use_bedrock(evaluations_metrics)

    logger.info("Starting dataset evaluation with ragas")
    evaluations_results = ragas_utils.evaluate_dataset(evaluation_dataset, evaluations_metrics)
    logger.info("Evaluation Complete!")

    evaluations_results_json = evaluations_results.to_pandas().to_json(orient="records")

    metrics.put_dimensions({"QApplicationId": APPLICATION_ID})
    for metric in evaluations_metrics:
        metric_name = metric.name
        metrics_score = evaluations_results.get(metric_name)
        metrics.put_metric(metric_name, metrics_score)
    return evaluations_results_json
