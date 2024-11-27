import json

import boto3
from botocore.exceptions import ClientError

from utils.logging_utils import setup_logging

logger = setup_logging(__name__)


class SecretManagerAdapter:
    def __init__(self, region: str):
        self.region = region
        self.secret_client = boto3.client("secretsmanager", region_name=region)

    def get_secret(self, secret_id: str):
        try:
            logger.info(f"Getting secret from secret {secret_id}")
            response = self.secret_client.get_secret_value(SecretId=secret_id)
            return json.loads(response['SecretString'])
        except ClientError as e:
            logger.error(f"failed to get secret {secret_id} due to {e}")
            raise e
