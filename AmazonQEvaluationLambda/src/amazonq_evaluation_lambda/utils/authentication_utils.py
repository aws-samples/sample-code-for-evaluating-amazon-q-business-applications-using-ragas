import base64
import hashlib
import hmac

import boto3
from botocore.exceptions import ClientError

from utils.logging_utils import setup_logging

logger = setup_logging(__name__)


class AuthenticationUtils:
    def __init__(self, region: str,
                 account_id: str,
                 user_pool_id: str,
                 client_id: str,
                 identity_pool_id: str, ):
        self.region = region
        self.account_id = account_id
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.identity_pool_id = identity_pool_id

        self.cognito_idp_client = boto3.client('cognito-idp', region_name=region)
        self.cognito_identity_client = boto3.client("cognito-identity", region_name=region)

    def get_token_id_for_cognito_user(self, username: str, password: str):
        response = self._sign_in_cognito_user(username, password)
        if "IdToken" in response:
            return response["IdToken"]
        raise Exception("Failed to get IdToken!")

    def _sign_in_cognito_user(self, username: str, password: str):
        try:
            logger.info(f"Started signing-in user {username}")
            kwargs = {
                "ClientId": self.client_id,
                "AuthFlow": "USER_PASSWORD_AUTH",
                "AuthParameters": {"USERNAME": username, "PASSWORD": password},
            }

            kwargs["AuthParameters"]["SECRET_HASH"] = self._get_secret_hash(username)
            response = self.cognito_idp_client.initiate_auth(**kwargs)
            return response["AuthenticationResult"]
        except ClientError as e:
            logger.error(
                f"Failed to sign in user {username} due to {e}")
            raise e

    def get_open_id_from_token_id(self, id_token: str):
        login_url = f"cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
        try:
            logger.info(f"Getting identity id for identity pool {self.identity_pool_id}")
            get_id_response = self.cognito_identity_client.get_id(
                AccountId=self.account_id,
                IdentityPoolId=self.identity_pool_id,
                Logins={
                    login_url: id_token
                }
            )
        except ClientError as e:
            logger.error("Failed to get identity id {e}!")
            raise e

        identity_id = get_id_response["IdentityId"]
        try:
            logger.info(f"Getting open id for identity pool {self.identity_pool_id}")
            get_open_id_response = self.cognito_identity_client.get_open_id_token(
                IdentityId=identity_id,
                Logins={
                    login_url: id_token
                })
        except ClientError as e:
            logger.error("Failed to get open id token!", e)
            raise e
        return get_open_id_response["Token"]

    def _get_client_secret(self):
        try:
            response = self.cognito_idp_client.describe_user_pool_client(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id
            )
            user_pool_client = response["UserPoolClient"]
            return user_pool_client["ClientSecret"] if "ClientSecret" in user_pool_client else None
        except ClientError as e:
            logger.error("Failed to read user pool client {e}!")
            raise e

    def _get_secret_hash(self, username):
        key = self._get_client_secret().encode()

        msg = bytes(f"{username}{self.client_id}", "utf-8")
        secret_hash = base64.b64encode(
            hmac.new(key, msg, digestmod=hashlib.sha256).digest()
        ).decode()
        return secret_hash
