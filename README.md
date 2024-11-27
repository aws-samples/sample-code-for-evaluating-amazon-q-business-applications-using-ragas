# AmazonQEvaluationLambda

**Sample Code for Q Business Application Response Evaluation using RAGAS**


[Amazon Q Business](https://aws.amazon.com/q/business/) is a generative AI-powered application that helps users get work done. 
Amazon Q Business can become your tailored business expert and let you discover content, brainstorm ideas, or gain further insight using your company’s data safely and securely. 
For more information see: [Introducing Amazon Q, a new generative AI-powered assistant (preview)](https://aws.amazon.com/blogs/aws/introducing-amazon-q-a-new-generative-ai-powered-assistant-preview)

In this project we share a solution that lets you evaluate your Q Business application responses using RAGAS against a test-set of questions and ground-truth.
The sample code solution provided in this repo allows the user to:
- evaluate the Q Business application responses against a test-set of questions & ground truths
- Visualize the metrics in Cloudwatch

Based on the input test-set and the responses from the Q Busieness application, RAGAS evaluates 4 different metrics:
- Answer Relevancy
- Faithfulness
- Context Recall
- Context Precision

For more information about the RAGAS evaluation metrics see: [RAGAS Metrics](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/)

## How to deploy the solution

### Prerequisites

1. You need to have an AWS account and an IAM Role/User with permissions to create and manage the necessary resources and components for this application.*(If you do not have an AWS account, please see [How do I create and activate a new Amazon Web Services account?](https://aws.amazon.com/premiumsupport/knowledge-center/create-and-activate-aws-account/))*
2. You also need to have an existing, working Amazon Q business application integrated with IdC or Cognito as an IdP. If you haven't set one up yet, see [Creating an Amazon Q application](https://docs.aws.amazon.com/amazonq/latest/business-use-dg/create-app.html)
3. You have the latest version of aws cli  installed on your system. If you haven't installed yet, see [Installing the AWS CLI version 2](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
4. You have `sam` installed on your system, see [Install SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
5. You have `Docker` installed on your system, see [Install Docker](https://docs.docker.com/engine/install/)


### Setup

#### 1. Create the Cognito Authentication Infrastructure 

##### 1.1 Create the Cognito Authentication Infrastructure
**If you already have a Q Business application that uses Cognito as IdP, you can skip this step**
    
The QEval lambda solution uses AWS Congito as an OIDC provider, in this step a cloudformation stack is deploy to create all the required resources needed.
To deploy the Cognito infrastructure run `aws configure` to configure your aws credentials,
then run the following command:
```
aws cloudformation deploy --template-file authentication_infra_template.yml --stack-name QEvalAuthInfra \
--parameter-overrides CreateOIDCProvider=false \
--capabilities CAPABILITY_NAMED_IAM --region=THE_REGION_OF_YOUR_Q_BUSINESS_APPLICATION
```

Please note that only a single instance of OIDCProvider for Cognito using `"https://cognito-identity.amazonaws.com"` can be created for an account globally
if you already have one deploy you just need to add the identity pool Id to the `audience list`

##### 1.2 Create a user in your Cognito UserPool

run this to create a Cognito user

`aws cognito-idp admin-create-user \ --user-pool-id $UserPoolId \ --username $UserEmail`

Reset the user password

`aws cognito-idp admin-set-user-password --user-pool-id $UserPoolId --username $UserEmail --password $SOME_PASSWORD --permanent`

Verify the user email
```
aws cognito-idp admin-update-user-attributes \
--user-pool-id $UserPoolId \
--username $UserEmail \
--user-attributes Name=email_verified,Value=true
```

Create a secret in AWS Secret Manager
```
aws secretsmanager create-secret --name qevalsecret \
 --secret-string '{"password": "$SOME_PASSWORD" }'
```


Create an IAM Role with Permissions to your Q Business application

Role Policy

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "QBusinessAdmin",
            "Effect": "Allow",
            "Action": [
                "qbusiness:*",
                "qapps:*",
                "user-subscriptions:*",
                "kms:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "QBusinessKMSDecryptPermissions",
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt"
            ],
            "Resource": "*"
        }
    ]
}
```

Trust Policy
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/cognito-identity.amazonaws.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "cognito-identity.amazonaws.com:aud": "YOUR_OIDCCLIENTID"
                }
            }
        },
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/cognito-identity.amazonaws.com"
            },
            "Action": "sts:TagSession",
            "Condition": {
                "StringLike": {
                    "aws:RequestTag/Email": "*"
                }
            }
        }
    ]
}
```

Copy the Arn of your IAM role, you will need it in step 3

#### 2. Enable Bedrock models in Your Region
RAGAS uses LLM models to process the input testset and responses in the evaluation.

To run the evaluation we need 2 LLM models:
- 1 Embedding model such as `amazon.titan-embed-text-v1`
- 1 Text model such as `anthropic.claude-v2`

Steps:
- Go to Amazon Bedrock in console.
- Go to `Base Models`.
- request access to your models of choice.
- Copy the `Model ID` for each one, you'll need them in the next step.

#### 3. Deploy the QEvaluation Lambda
 - Build your code using `sam build`
 - deploy your resources using `sam deploy --guided`

While deploying the stack you will need to provide the following parameters:
- `Stack Name`: the stack name for the Q Evaluation lambda
- `AWS Region`: the AWS region where you want to deploy your solution
- `QBusinessApplicationId`: the ID of your Q Application
- `BedrockEmbeddingModelId`: The embedding model ID that you copied in step 2
- `BedrockTextModelId`: The text model ID that you copied in step 2
- `UserPoolId`: Your Cognito UserPool Id that was deployed in step 1
- `ClientId`: Your Cognito Client Id
- `UserEmail`: The cognito user email that you created in step 1.2
- `UserSecretId`: The user secret Id that you created in step 1.2
- `IdentityPoolId`: The Cognito Identity Pool Id
- `QAppRoleArn`: The IAM role arn that you created in step 1.2

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

