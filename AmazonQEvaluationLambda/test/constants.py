REGION = "us-east-1"
Q_APPLICATION_ID = "1345362547576588"
BEDROCK_EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v1"
BEDROCK_TEXT_MODEL_ID = "anthropic.claude-v2"
USER_POOL_ID = "userpoolid"
CLIENT_ID = "testClientId"
IDENTITY_POOL_ID = "testIdentityPool"
Q_APP_ROLE_ARN = "testQRoleArn"
USER_EMAIL = "test@test.com"
USER_SECRET_ID = "arn:aws:secretsmanager:us-west-2:111111111:secret:testSecretName"

TEST_Q_CHAT_RESPONSE = {
    'conversationId': '1111111',
    'systemMessage': 'test message',
    'sourceAttributions': [
        {
            'title': 'data source title',
            'snippet': 'data snippet',
            'url': 'test_url.com',
            'citationNumber': 123
        },
    ],
}

GET_SECRET_RESPONSE = {
    'ARN': 'arn:aws:secretsmanager:us-west-2:111111111:secret:testSecretName',
    'Name': 'testSecretName',
    'VersionId': 'version1g',
    'SecretString': '{\n "password":"sometestPassword"}\n',
}

TEST_ERROR_RESPONSE = {
    "Error": {
        "Code": "testeException",
        "Message": "call failed!",
    },
}

TEST_ASSUME_ROLE_WITH_WEB_IDENTITY_RESPONSE = {
    'AssumedRoleUser': {
        'Arn': 'arn:aws:sts::111111111:assumed-role/testRoleName/sessionnsme',
        'AssumedRoleId': 'AROACLKWSDQRAOEXAMPLE:app1',
    },
    'Audience': 'identitypoolId',
    'Credentials': {
        'AccessKeyId': 'testAccessKeyId',
        'SecretAccessKey': 'testSecretAccessKey',
        'SessionToken': 'testSessionToken',
    },
}

TEST_DESCRIBE_USER_POOL_CLIENT_RESPONSE = {
    'UserPoolClient': {
        'UserPoolId': 'testUserPoolId',
        'ClientName': 'testClientName',
        'ClientId': 'testClientId',
        'ClientSecret': 'testClientSecret'
    }
}

TEST_INITIATE_AUTH_RESPONSE = {
    'AuthenticationResult': {
        'AccessToken': 'testAccessToken',
        'ExpiresIn': 123,
        'TokenType': 'someType',
        'RefreshToken': 'testRefreshToken',
        'IdToken': 'testIdToken',

    }
}

TEST_GET_ID_RESPONSE = {
    'IdentityId': 'testIdentityId'
}

TEST_GET_OPEN_ID_TOKEN = {
    'IdentityId': 'testIdentityId',
    'Token': 'testToken'
}


TEST_CREDENTIALS = {'AccessKeyId': 'TestAccessId',
                    'SecretAccessKey': 'TestSecretKey',
                    'SessionToken': 'TestSessionToken',
                    }
