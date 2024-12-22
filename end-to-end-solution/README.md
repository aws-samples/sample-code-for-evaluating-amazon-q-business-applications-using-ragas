# Evaluation Framework for Amazon Q Business Applications

In this project we share a solution that an evaluation framework for the Amazon Q application, allowing you to assess its accuracy and effectiveness based on data and information in your enterprise systems. This solution can be deployed using your own AWS account, following step-by-step instructions provided here.

## How to deploy the solution

### Prerequisites

1. You need to have an AWS account and an IAM Role/User with permissions to create and manage the necessary resources and components for this application.*(If you do not have an AWS account, please see [How do I create and activate a new Amazon Web Services account?](https://aws.amazon.com/premiumsupport/knowledge-center/create-and-activate-aws-account/))*
2. You have the latest version of aws cli  installed on your system. If you haven't installed yet, see [Installing the AWS CLI version 2](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)


### Setup

#### 1. Enable Bedrock models in Your Region
RAGAS uses LLM models to process the input testset and responses in the evaluation.

To run the evaluation we need 2 LLM models:
- 1 Embedding model `amazon.titan-embed-text-v1`
- 1 Text model `anthropic.claude-v3-sonnet`

Steps:
- Go to Amazon Bedrock in console.
- Go to `Base Models`.
- request access to your models of choice.
- Copy the `Model ID` for each one, you'll need them in the next step.

#### 2. Clone this repo into your laptop and go to ./end-to-end-solution

#### 3. Run deploy script providing cloudformation stack name and aws region where to deploy the stack
  - ./deploy -s < Cfn Stack Name > -r < AWS REGION >
  - This script deploys all solution into your account using Cloudformation. Once the deployment is finish, you get the message 'Deployment completed successfully!'

#### 4. Open AWS Console and go to the Amazon Q Business console.
  - Next, click on the Manage User Access under User Access.
  - On the Add groups and users screen you will configure user subscription and access for the application.
  - Next click on Add Groups and users, select Assign existing users and groups, click Next and click Get Started.
  - In the Assign users and groups window use the search box to find users and groups by name. For the workshop users, type "qbusiness" in the search box and select "qbusiness" user from the drop down.
  - Click Assign to add the user to the application.
  - From the Users tab select the newly added user qbusiness, click the Current subscription, select Q Business Pro and click on the Confirm button.

#### 5. Open AWS Console and go to Cloudformation service. Click on the new deployed stack and go to 'Outputs'
  - Take note of the 'UserName' and 'Password' values. Default values are:
    UserName: qbusiness
    Password: Riv2024!

  - Take note webapp endpoint 'StreamlitUrl'

#### 6. Open streamlit application and login using the credentials from last step

#### 7. Once you login the custom UI used for Amazon Q Evaluation, click on "Upload Dataset" button, and then upload the file 'prompt.csv'

#### 8. Once the file is uploaded, the evaluation framework will start to send the prompt to Amazon Q Business to generate the answer, then send prompt, ground truth and answer to Ragas to evaluate.

#### 9. After about 7 minutes, the workflow will finish, and you should see the evaluation results.

### Key Evaluation Metrics
 - Context Recall: Ensures all relevant content is retrieved.
 - Context Precision: Focuses on the relevance and conciseness of retrieved information.
 - Answer Relevancy: Assesses if responses fully address the query without extraneous details.
 - Truthfulness: Confirms factual accuracy by comparing responses to verified sources.

This streamlined evaluation architecture and metric-based approach ensure Amazon Q Business delivers accurate, relevant, and trustworthy answers for enterprise use.

### Perform HITL evaluation

In this section you will review metric scores generated via RAGAS (an LLM aided evaluation method), and you will provide human feedback as an evaluator to provide further calibration. This HITL (Human-in-the-Loop) calibration will further improve the evaluation accuracy.

HITL is a process or system that involves human interaction or intervention as part of its operation or decision-making process. HITL process are particularly valuable in fields where human judgment, expertise, or ethical considerations are crucial. In this case, the HITL will further improve the evaluation accuracy.

There are a few pros and cons related with RAGAS and HITL evaluation methods.

#### Pros for RAGAS:
1. A fully automated evaluation that leverages the latest Generative AI technology.
2. Higher consistency.

#### Cons for RAGAS:
1. RAGAS presents certain limitations, especially for RAG solutions using enterprise-specific proprietary data. These metrics often fail to capture the full complexity of human-like language generation, lacking the ability to assess semantic understanding and the contextual nuances unique to a specific domain.
2. such automated metrics don’t align well with qualitative human judgment, which is crucial when the evaluation must consider the intricate details and specialized knowledge inherent to enterprise data.

#### Pros for HITL:
1. It is suitable for tasks with a deep understanding of the domain because humans can understand context, subtleties, and nuances better than the automated metrics.
2. HITL can bring qualitative assessments and human judgement that automated evaluation metrics lack

#### Cons for HITL:
1. Resource intensive
2. Lower consistency between different evaluators



## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

