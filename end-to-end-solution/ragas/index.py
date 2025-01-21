import os
import json
import logging
import boto3
import jwt
from botocore.exceptions import ClientError

import nest_asyncio
from langchain_aws import BedrockEmbeddings, ChatBedrock
from ragas.evaluation import Result
#from ragas_lambda.index import evaluate, RunConfig
from ragas import evaluate, RunConfig
from ragas.llms import LangchainLLMWrapper
from ragas.metrics.base import Metric
from ragas.metrics import (answer_relevancy, faithfulness, context_recall, context_precision)  # Import necessary metrics
from datasets import Dataset
from typing import List
from decimal import Decimal
import time
import random

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global variables to be populated
IAM_ROLE = os.environ.get('IamRoleArn')
REGION = os.environ.get('AwsRegion')
BEDROCK_REGION = os.environ.get('AwsRegion')
IDC_APPLICATION_ID = os.environ.get('IDC_APPLICATION_ID')
AMAZON_Q_APP_ID = os.environ.get('AMAZON_Q_APP_ID')

UserPoolId = os.environ.get('UserPoolId')
ClientId = os.environ.get('ClientId')
OAUTH_CONFIG = {
    "UserPoolId": UserPoolId,
    "ClientId": ClientId
}


# Authenticate user using AdminInitiateAuth
def authenticate_user(username, password):
    client = boto3.client('cognito-idp', region_name=REGION)
    try:
        response = client.admin_initiate_auth(
            UserPoolId=OAUTH_CONFIG["UserPoolId"],
            ClientId=OAUTH_CONFIG["ClientId"],
            AuthFlow='ADMIN_USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        auth_result = response.get('AuthenticationResult')
        if auth_result:
            return auth_result  # Contains AccessToken, IdToken, RefreshToken, etc.
        else:
            logger.error("Authentication result returned is empty")
            return None
    except ClientError as e:
        logger.error(f"Authentication failed: {e.response['Error']['Message']}")
        return None
        
# Get IAM OIDC token using the ID token retrieved from Cognito
def get_iam_oidc_token(id_token):
    client = boto3.client("sso-oidc", region_name=REGION)
    try:
        response = client.create_token_with_iam(
            clientId=IDC_APPLICATION_ID,
            grantType="urn:ietf:params:oauth:grant-type:jwt-bearer",
            assertion=id_token,
        )
        return response
    except ClientError as e:
        logger.error(f"Failed to get IAM OIDC token: {e.response['Error']['Message']}")
        return None
    
# Assume IAM role with the IAM OIDC idToken
def assume_role_with_token(iam_token):
    decoded_token = jwt.decode(iam_token, options={"verify_signature": False})
    sts_client = boto3.client("sts", region_name=REGION)
    try:
        response = sts_client.assume_role(
            RoleArn=IAM_ROLE,
            RoleSessionName="qapp",
            ProvidedContexts=[
                {
                    "ProviderArn": "arn:aws:iam::aws:contextProvider/IdentityCenter",
                    "ContextAssertion": decoded_token["sts:identity_context"],
                }
            ],
            DurationSeconds=3600
        )
        credentials = response["Credentials"]
        return credentials
    except ClientError as e:
        logger.error(f"Failed to assume role: {e.response['Error']['Message']}")
        return None
    
# Create the Q client using the assumed role credentials
def get_qclient(credentials):
    session = boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    amazon_q = session.client("qbusiness", region_name=REGION)
    return amazon_q

# Create the DynamoDB client using the assumed role credentials
def get_DynamodbCli(credentials):
    session = boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    DynamodbCli = session.client("dynamodb", region_name=REGION)
    DynamodbRes = session.resource("dynamodb", region_name=REGION)
    return DynamodbCli, DynamodbRes

# Process the prompt and get the answer from Amazon Q
def process_prompt(prompt_input, conversation_id, parent_message_id, qclient):
    if conversation_id:
        answer = qclient.chat_sync(
            applicationId=AMAZON_Q_APP_ID,
            userMessage=prompt_input,
            conversationId=conversation_id,
            parentMessageId=parent_message_id,
        )
    else:
        answer = qclient.chat_sync(
            applicationId=AMAZON_Q_APP_ID,
            userMessage=prompt_input
        )
    # Process the answer as needed
    logger.info(answer)
    return answer

# Formatting functions using Dataset.from_dict
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
    print(testcases)
    return Dataset.from_dict(testcases)

def get_answers_from_q(q_app_responses):
    answers = []
    if 'systemMessage' in q_app_responses:
        answers.append(q_app_responses['systemMessage'])
    else:
        # Handle the case where 'systemMessage' is missing
        answers.append(None)

    return answers

def extract_text_snippets_from_sources_attributes(q_app_response):
    contexts = []
    if isinstance(q_app_response, dict):
        if "sourceAttributions" in q_app_response and q_app_response['sourceAttributions']:
            # Extract snippets from sourceAttributions
            snippets = []
            for attribution in q_app_response['sourceAttributions']:
                snippet = attribution.get('snippet', '')
                if snippet:
                    snippets.append(snippet)
            # Append the list of snippets to contexts
            contexts.append(snippets)
        else:
            # Handle the case where 'sourceAttributions' is missing or empty
            contexts.append([])
            logger.warning("sourceAttributions key is missing or empty in q_app_response. Appending empty list.")
    else:
        contexts.append([])
        logger.error("q_app_response is not a dictionary. Appending empty list.")
    return contexts
class RagasUtils:
    MAX_WORKERS_COUNT = 4
    def __init__(self, region: str, bedrock_embedding_model_id: str, bedrock_llm_model_id: str):
        self.region = region
        self.bedrock_embedding_model_id = bedrock_embedding_model_id
        self.bedrock_llm_model_id = bedrock_llm_model_id
    
    def _get_bedrock_embeddings(self):

        retry_delay = 1
        i = 1
        for i in range(25):  # Retries
            try:
                result= BedrockEmbeddings(
                    model_id=self.bedrock_embedding_model_id,
                    region_name=self.region)
                break  # If successful, break the loop
            except Exception as e:
                logger.error(f"Error processing BedrockEmbeddings: {e}")
                time.sleep(retry_delay)  # Wait before retrying
                retry_delay *= 3  # Exponential backoff
                retry_delay += random.uniform(0,10)
        return result
    
    def _get_bedrock_llm_model_wrapper(self):
        bedrock_model = ChatBedrock(
            region_name=self.region,
            endpoint_url=f"https://bedrock-runtime.{self.region}.amazonaws.com",
            model_id=self.bedrock_llm_model_id)
        
        retry_delay = 1
        i = 1
        for i in range(25):  # Retries
            try:
                result= LangchainLLMWrapper(bedrock_model)
                break  # If successful, break the loop
            except Exception as e:
                logger.error(f"Error processing LangchainLLMWrapper: {e}")
                time.sleep(retry_delay)  # Wait before retrying
                retry_delay *= 3  # Exponential backoff
                retry_delay += random.uniform(0,10)
        return result

    def configure_metrics_to_use_bedrock(self, metrics):
        bedrock_llm_wrapper = self._get_bedrock_llm_model_wrapper()
        bedrock_embeddings = self._get_bedrock_embeddings()
        for m in metrics:
            setattr(m, 'llm', bedrock_llm_wrapper)
            setattr(m, 'embeddings', bedrock_embeddings)
    def evaluate_dataset(self, evaluation_dataset:Dataset, metrics:List[Metric]) -> Result:
        nest_asyncio.apply()

        delay = 30 
        delay += random.uniform(1,10)
        time.sleep(delay)  # Wait before eval
        runconfig = RunConfig(max_workers=self.MAX_WORKERS_COUNT, max_retries=25, max_wait=60, timeout=600)

        evaluation_results = evaluate(
            evaluation_dataset,
            metrics=metrics,
            run_config=runconfig,
        )
        return evaluation_results
    
# Main Lambda handler
def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    # Get secret
    # Extract username and password from the environment variables
    UserCredentialsSecret = os.environ.get('UserCredentialsSecret')
    
    secrets_manager = boto3.client('secretsmanager')
    secret = secrets_manager.get_secret_value(SecretId=UserCredentialsSecret)
    secret_dict = json.loads(secret['SecretString'])

    username = secret_dict['username']
    password = secret_dict['password']
    
    if not username or not password:
        logger.error("Username or password not provided.")
        return {
            'statusCode': 400,
            'body': json.dumps('Username or password not provided.')
        }
    # Authenticate user
    auth_tokens = authenticate_user(username, password)
    if not auth_tokens:
        return {
            'statusCode': 401,
            'body': json.dumps('Authentication failed.')
        }
    id_token = auth_tokens['IdToken']
    # Get IAM OIDC token
    iam_oidc_response = get_iam_oidc_token(id_token)
    if not iam_oidc_response:
        return {
            'statusCode': 500,
            'body': json.dumps('Failed to get IAM OIDC token.')
        }
    iam_token = iam_oidc_response["idToken"] 
    # Assume role with the IAM OIDC token
    credentials = assume_role_with_token(iam_token)
    if not credentials:
        return {
            'statusCode': 500,
            'body': json.dumps('Failed to assume role.')
        }
    # Create Amazon Q client
    qclient = get_qclient(credentials)
    
    # Initialize DynamoDB client
    dynamodb, dynamodbRes = get_DynamodbCli(credentials)
    
    table_name = os.environ.get('TABLE_NAME')
    table_name_results = os.environ.get('PromptEvalResultsTable')

          
    for record in event['Records']:
        questions = []
        answers = []
        answer_text_list = []
        ground_truth = []  # Assuming you have ground truth data
        contexts = []
        context_list = []

        try:
            message = json.loads(record['body'])
            # Process the message (the original DynamoDB event)
            print(f"Processing DynamoDB event: {message}")
            
            new_image = message
            item_id = new_image['id']['S']
            prompt_input = new_image['prompt']['S']
            # Check if 'Response' attribute already exists
            if 'Response' in new_image:
                logger.info(f"Item with id {item_id} already processed. Skipping.")
                continue
            # Process the prompt and get the answer

            retry_delay = 60
            i = 1
            for i in range(20):  # Retries
                try:
                    answer = process_prompt(prompt_input, None, None, qclient)
                    print(f"Q prompt exec successfully! after {i} retries..")
                    break  # If successful, break the loop
                except Exception as e:
                    logger.error(f"Error processing record: {e} . Trying again.. retry = {i} .")
                    retry_delay += random.uniform(0,10)
                    time.sleep(retry_delay)  # Wait before retrying
                    retry_delay *= 2  # Exponential backoff
                    
                    
                    
            #answer = process_prompt(prompt_input, None, None, qclient)
            
            # Collect data for formatting
            questions.append(prompt_input)
            logger.info(questions)

            # Get the answer and append
            answer_text_list: list[str] = get_answers_from_q(answer)
            answers.extend(answer_text_list)  # Extend the answers list
            logger.info(answers)

            # Get contexts and append
            context_list = extract_text_snippets_from_sources_attributes(answer)
            contexts.extend(context_list)  # Extend the contexts list
            logger.info(contexts)
            
            # If ground truth is available, retrieve it; else, use placeholder
            if 'ground_truth' in new_image:
                ground_truth_value = new_image['ground_truth']['S']
            else:
                logger.warning(f"No ground truth found for item id {item_id}. Skipping this item.")
                ground_truth_value = ''
            
            ground_truth.append(ground_truth_value)
            logger.info(ground_truth)

            
        except Exception as e:
            logger.error(f"Error processing record: {e}")
            continue

        # Verify that all lists have the same length
        if not (len(questions) == len(answers) == len(ground_truth) == len(contexts)):
            logger.error("Mismatch in lengths of data lists.")
           
            return {
                'statusCode': 500,
                'body': json.dumps('Mismatch in lengths of data lists.')
            }

        # After processing all records, create the evaluation dataset
        evaluation_dataset = create_evaluation_dataset(questions, answers, ground_truth, contexts)
        logger.info(f"Evaluation Dataset: {evaluation_dataset}")

        # Initialize RagasUtils with environment variables
        bedrock_embedding_model_id = os.environ.get('BedrockEmbeddingModelId')
        bedrock_llm_model_id = os.environ.get('BedrockTextModelId')
        ragas_utils = RagasUtils(BEDROCK_REGION, bedrock_embedding_model_id, bedrock_llm_model_id)
        # Define metrics
        metrics = [answer_relevancy,
                faithfulness,
                context_recall,
                context_precision]

        # Configure metrics
        ragas_utils.configure_metrics_to_use_bedrock(metrics)
        # Evaluate the dataset
        
        evaluation_results = ragas_utils.evaluate_dataset(evaluation_dataset, metrics)
        evaluations_results_json = evaluation_results.to_pandas().to_json(orient="records")
        logger.info(f"Evaluation Results: {evaluations_results_json}")

        # Update the item in DynamoDB with the response        
        data = json.loads(evaluations_results_json)
        
        item = { 
            'id': f"{item_id}", 
            'question': f"{data[0]['question']}",
            'answer': f"{data[0]['answer']}",
            'ground_truth': f"{data[0]['ground_truth']}",
            'contexts': f"{data[0]['contexts']}",           
            'answer_relevancy': f"{data[0]['answer_relevancy']}",
            'truthfulness': f"{data[0]['faithfulness']}",
            'context_recall': f"{data[0]['context_recall']}",
            'context_precision': f"{data[0]['context_precision']}"
        }

        table = dynamodbRes.Table(table_name_results)
        table.put_item(Item=item)

        
    return {
        'statusCode': 200,
        'body': json.dumps('Successfully processed the DynamoDB stream.')
    }