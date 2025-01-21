import boto3
from botocore.exceptions import ClientError

from utils.logging_utils import setup_logging

logger = setup_logging(__name__)


class StsAdapter:
    def __init__(self, region: str):
        self.region = region
        self.sts_client = boto3.client("sts", region_name=region)

    def assume_role_with_oidc_provider(self, roleArn: str, username: str, open_id_token: str):
        try:
            logger.info(f"Assuming role {roleArn} with web identity")
            response = self.sts_client.assume_role_with_web_identity(
                RoleArn=roleArn,
                RoleSessionName=username + "OIDC",
                WebIdentityToken=open_id_token,
            )
            return response["Credentials"]
        except ClientError as e:
            logger.error(f"failed to assume role {roleArn} due to {e}")
            raise e

    def assume_role(self, role_arn: str, username: str, sts_context: str):
        try:
            logger.info(f"Assuming role {role_arn} with context assertion")
            response = self.sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName=username + "OIDC",
                ProvidedContexts=[{
                    "ProviderArn": "arn:aws:iam::aws:contextProvider/IdentityCenter",
                    "ContextAssertion": sts_context
                }]            )
            return response["Credentials"]
        except ClientError as e:
            logger.error(f"failed to assume role {role_arn} due to {e}")
            raise e