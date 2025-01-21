#!/bin/bash

# Allow errors in pipes to be caught
set -eo pipefail

# Function to display usage
usage() {
    echo "Usage: $0 -s <stack-name>"
    echo "Options:"
    echo "  -s    Stack name (required)"
    echo "  -h    Display this help message"
    exit 1
}

# Parse command line arguments
while getopts ":s:h" opt; do
    case ${opt} in
        s )
            STACK_NAME=$OPTARG
            ;;
        h )
            usage
            ;;
        \? )
            echo "Invalid option: -$OPTARG" 1>&2
            usage
            ;;
        : )
            echo "Option -$OPTARG requires an argument" 1>&2
            usage
            ;;
    esac
done

# Check if stack name is provided
if [ -z "$STACK_NAME" ]; then
    echo "Error: Stack name is required"
    usage
fi

# Function to check if a bucket exists
check_bucket_exists() {
    local bucket_name=$1
    if aws s3api head-bucket --bucket "$bucket_name" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to empty and delete an S3 bucket
delete_bucket() {
    local bucket_name=$1
    echo "Checking bucket: $bucket_name"
    
    if check_bucket_exists "$bucket_name"; then
        echo "Emptying bucket: $bucket_name"
        
        # Get all versions and delete markers
        echo "Getting object versions..."
        local versions
        versions=$(aws s3api list-object-versions \
            --bucket "$bucket_name" \
            --query '{Objects: Versions[].{Key: Key, VersionId: VersionId}}' \
            --output json 2>/dev/null || echo '{"Objects": []}')

        if [ "$(echo "$versions" | jq -r '.Objects | length')" -gt 0 ]; then
            echo "Deleting object versions..."
            aws s3api delete-objects \
                --bucket "$bucket_name" \
                --delete "$versions" || true
        fi

        # Get and delete delete markers
        echo "Getting delete markers..."
        local markers
        markers=$(aws s3api list-object-versions \
            --bucket "$bucket_name" \
            --query '{Objects: DeleteMarkers[].{Key: Key, VersionId: VersionId}}' \
            --output json 2>/dev/null || echo '{"Objects": []}')

        if [ "$(echo "$markers" | jq -r '.Objects | length')" -gt 0 ]; then
            echo "Deleting delete markers..."
            aws s3api delete-objects \
                --bucket "$bucket_name" \
                --delete "$markers" || true
        fi

        # Delete any remaining non-versioned objects
        echo "Removing any remaining objects..."
        aws s3 rm "s3://${bucket_name}" --recursive || true

        # Final check
        echo "Checking if bucket is empty..."
        if ! aws s3api list-object-versions \
            --bucket "$bucket_name" \
            --query 'length(Versions[]) + length(DeleteMarkers[])' \
            --output text 2>/dev/null | grep -q '^0$'; then
            
            echo "Attempting one final deletion of all versions..."
            # One final attempt to delete all versions
            aws s3api list-object-versions \
                --bucket "$bucket_name" \
                --query '{Objects: [].{Key: Key, VersionId: VersionId}}' \
                --output json | \
            aws s3api delete-objects \
                --bucket "$bucket_name" \
                --delete file:///dev/stdin || true
        fi

        # Try to delete the bucket
        echo "Attempting to delete bucket: $bucket_name"
        if aws s3api delete-bucket --bucket "$bucket_name" 2>/dev/null; then
            echo "Successfully deleted bucket: $bucket_name"
        else
            echo "Warning: Failed to delete bucket. It might not be empty."
            echo "Remaining objects:"
            aws s3api list-object-versions --bucket "$bucket_name" --output json || true
        fi
    else
        echo "Bucket $bucket_name does not exist or you don't have access to it"
    fi
}


# Function to delete ECR repository and its images
delete_ecr_repository() {
    local repo_name=$1
    if aws ecr describe-repositories --repository-names "$repo_name" 2>/dev/null; then
        echo "Deleting ECR repository: $repo_name"
        # List images before deletion (optional)
        echo "Images to be deleted:"
        aws ecr list-images --repository-name "$repo_name" --query 'imageIds[*]' --output table || true
        
        # Delete repository and all images
        aws ecr delete-repository --repository-name "$repo_name" --force || true
        
        echo "Successfully deleted ECR repository: $repo_name"
        
    else
        echo "ECR repository $repo_name does not exist"
    fi
}

# Function to delete Q Business application
delete_q_business_app() {
    local app_id=$1
    if [ ! -z "$app_id" ] && [ "$app_id" != "None" ]; then
        echo "Deleting Q Business application: $app_id"
        aws qbusiness delete-application --application-id "$app_id" || true
        sleep 60  # Initial wait for deletion to start
    fi
}

# Function to delete service-linked role
delete_service_role() {
    sleep 60  # Initial wait for deletion to start
    if aws iam get-role --role-name "AWSServiceRoleForQBusiness" 2>/dev/null; then
        echo "Deleting AWSServiceRoleForQBusiness service-linked role"
        DELETION_TASK_ID=$(aws iam delete-service-linked-role --role-name "AWSServiceRoleForQBusiness" --query 'DeletionTaskId' --output text || true)
        if [ ! -z "$DELETION_TASK_ID" ]; then
            echo "Waiting for service role deletion to complete..."
            sleep 10  # Initial wait for deletion to start
        fi
    else
        echo "Service-linked role does not exist"
    fi
}

# Function to delete IAM Identity Center instance
delete_identity_center() {
    local instance_arn=$(aws sso-admin list-instances --query 'Instances[0].InstanceArn' --output text 2>/dev/null || echo "None")
    if [ "$instance_arn" != "None" ] && [ ! -z "$instance_arn" ]; then
        # Wait for service role deletion to complete
        local task_id=$(aws iam get-service-linked-role-deletion-status --deletion-task-id "${DELETION_TASK_ID}" --query 'Status' --output text 2>/dev/null || echo "")
        while [ "$task_id" == "IN_PROGRESS" ]; do
            echo "Waiting for service role deletion to complete..."
            sleep 10
            task_id=$(aws iam get-service-linked-role-deletion-status --deletion-task-id "${DELETION_TASK_ID}" --query 'Status' --output text 2>/dev/null || echo "")
        done

        echo "Deleting IAM Identity Center instance: $instance_arn"
        if [[ $instance_arn =~ ^arn:aws:sso:::instance/(sso)?ins-[a-zA-Z0-9-.]{16}$ ]]; then
            aws sso-admin delete-instance --instance-arn "$instance_arn" || true
        else
            echo "Invalid instance ARN format: $instance_arn"
        fi
    else
        echo "No IAM Identity Center instance found"
    fi
}

# Main cleanup process
echo "Starting cleanup process for stack: $STACK_NAME"


# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
echo "AWS Account ID: ${AWS_ACCOUNT_ID}"

AWS_REGION=$(aws configure get region)
echo "AWS Region: ${AWS_REGION}"

# Get bucket names from CloudFormation outputs
ASSETS_BUCKET_NAME="assets-${AWS_ACCOUNT_ID}-${STACK_NAME}-${AWS_REGION}"
RAGAS_BUCKET_NAME="ragas-${AWS_ACCOUNT_ID}-${STACK_NAME}-${AWS_REGION}"
PROMPT_SOURCE_BUCKET_NAME="riv2024-qb-prompt-source-${AWS_ACCOUNT_ID}"
DATA_SOURCE_BUCKET_NAME="riv2024-qb-data-source-${AWS_ACCOUNT_ID}"

# Delete S3 buckets
if [ ! -z "$ASSETS_BUCKET_NAME" ] && [ "$ASSETS_BUCKET_NAME" != "None" ]; then
    delete_bucket "$ASSETS_BUCKET_NAME"
fi

if [ ! -z "$RAGAS_BUCKET_NAME" ] && [ "$RAGAS_BUCKET_NAME" != "None" ]; then
    delete_bucket "$RAGAS_BUCKET_NAME"
fi

if [ ! -z "$PROMPT_SOURCE_BUCKET_NAME" ]; then
    delete_bucket "$PROMPT_SOURCE_BUCKET_NAME"
fi

if [ ! -z "$DATA_SOURCE_BUCKET_NAME" ]; then
    delete_bucket "$DATA_SOURCE_BUCKET_NAME"
fi

# Delete ECR repositories
delete_ecr_repository "q_evaluation_lambda"

# Get Q Business application ID and delete it
APP_ID=$(aws qbusiness list-applications --query 'Applications[0].ApplicationId' --output text 2>/dev/null || echo "None")
delete_q_business_app "$APP_ID"

# Delete CloudFormation stacks
echo "Deleting CloudFormation stacks..."

# Delete main stack
echo "Deleting main stack: $STACK_NAME"
aws cloudformation delete-stack --stack-name "$STACK_NAME" || true
aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" || true

# Delete service-linked role
delete_service_role

# Delete IAM Identity Center instance
delete_identity_center

echo "Cleanup process completed!"
