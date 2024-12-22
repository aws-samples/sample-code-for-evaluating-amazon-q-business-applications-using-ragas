from typing import List, Dict

import boto3
from botocore.exceptions import ClientError
from utils.logging_utils import setup_logging

logger = setup_logging(__name__)


class QbusinessAdapter:
    def __init__(self, region: str, credentials: Dict):
        self.region = region
        self.q_client = boto3.client('qbusiness',
                                     aws_access_key_id=credentials["AccessKeyId"],
                                     aws_secret_access_key=credentials["SecretAccessKey"],
                                     aws_session_token=credentials["SessionToken"],
                                     region_name=region)

    def get_q_application_response(self, questions: List[str], application_id: str) -> dict:
        questions_response = {}
        try:
            logger.info(f"Getting response from the Q Business application with Id={application_id}")
            for q in questions:
                response = self.q_client.chat_sync(
                    applicationId=application_id,
                    userMessage=q)
                questions_response[q] = response
        except ClientError as e:
            logger.exception(f"Failed to get responses from QBusiness app {application_id} due to {e}")
            raise e
        return questions_response
