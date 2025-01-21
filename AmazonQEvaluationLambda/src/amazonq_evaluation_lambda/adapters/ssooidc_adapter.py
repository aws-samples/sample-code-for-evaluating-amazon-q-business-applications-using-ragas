import boto3
import jwt
from botocore.exceptions import ClientError

from utils.logging_utils import setup_logging

logger = setup_logging(__name__)


class SSOOIDCAdapter:
    def __init__(self, region: str):
        self.region = region
        self.ssooidc_client = boto3.client("sso-oidc", region_name=region)

    def create_token_with_iam(self, id_token: str, client_id: str):
        try:
            logger.info(f"Exchanging token")
            response = self.ssooidc_client.create_token_with_iam(
                clientId=client_id,
                grantType="urn:ietf:params:oauth:grant-type:jwt-bearer",
                assertion=id_token
            )
            return jwt.decode(
                response["idToken"],
                algorithms=["RS256"],
                options={"verify_signature": False}
            )
        except ClientError as e:
            logger.error(f"failed to create token due to {e}")
            raise e
