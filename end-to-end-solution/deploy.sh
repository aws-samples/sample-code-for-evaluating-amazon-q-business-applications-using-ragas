#!/bin/bash

# Exit on error
set -e

# Function to display usage
usage() {
    echo "Usage: $0 -s STACK_NAME -r REGION [-b BUCKET_NAME] [-a ASSETS_DIR] [-g RAGAS_DIR]"
    echo "  -s STACK_NAME : Name of the CloudFormation stack"
    echo "  -r REGION    : AWS region (e.g., us-east-1)"
    echo "  -b BUCKET_NAME : (Optional) S3 bucket name for deployment artifacts"
    echo "  -a ASSETS_DIR : (Optional) Directory containing assets to upload"
    echo "  -g RAGAS_DIR : (Optional) Directory containing RAGAS content to upload"
    echo "  -v VPC_CIDR : (Optional) CIDR block for VPC (default: 10.0.0.0/16)"
    echo "  -pa PUB_SUB_A_CIDR : (Optional) CIDR for public subnet A (default: 10.0.0.0/24)"
    echo "  -pb PUB_SUB_B_CIDR : (Optional) CIDR for public subnet B (default: 10.0.1.0/24)"
    echo "  -ra PRIV_SUB_A_CIDR : (Optional) CIDR for private subnet A (default: 10.0.2.0/24)"
    echo "  -rb PRIV_SUB_B_CIDR : (Optional) CIDR for private subnet B (default: 10.0.3.0/24)"
    exit 1
}

# Function to check if AWS CLI is installed
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        echo "AWS CLI is not installed. Please install it first."
        exit 1
    fi
}

# Function to check if AWS credentials are configured and get account ID
check_aws_credentials() {
    local account_info
    if ! account_info=$(aws sts get-caller-identity --query 'Account' --output text 2>/dev/null); then
        echo "AWS credentials are not configured. Please configure them first."
        exit 1
    fi
    echo "${account_info}"
}

# Function to create S3 bucket with enhanced settings
create_s3_bucket() {
    local bucket_name=$1
    local region=$2
    local bucket_type=$3
    
    if ! aws s3 ls "s3://${bucket_name}" 2>&1 > /dev/null; then
        echo "Creating ${bucket_type} bucket: ${bucket_name}..."
        if [[ "${region}" == "us-east-1" ]]; then
            aws s3 mb "s3://${bucket_name}"
        else
            aws s3 mb "s3://${bucket_name}" --region ${region}
        fi
        
        # Enable versioning on the bucket
        aws s3api put-bucket-versioning \
            --bucket "${bucket_name}" \
            --versioning-configuration Status=Enabled

        # Block public access
        aws s3api put-public-access-block \
            --bucket "${bucket_name}" \
            --public-access-block-configuration \
                "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
        
        echo "${bucket_type} bucket created successfully."
    else
        echo "${bucket_type} bucket already exists."
    fi
}

# Function to upload content to S3
upload_content() {
    local source_dir=$1
    local bucket_name=$2
    local content_type=$3

    if [ -d "$source_dir" ]; then
        echo "Uploading ${content_type} content from ${source_dir} to s3://${bucket_name}..."
        aws s3 sync "${source_dir}" "s3://${bucket_name}" --delete
        echo "${content_type} content uploaded successfully."
    else
        echo "Warning: ${content_type} directory ${source_dir} does not exist. Skipping upload."
    fi
}

# Main deployment function
deploy_solution() {
    local stack_name=$1
    local region=$2
    local bucket_name=$3
    local assets_bucket_name=$4
    local ragas_bucket_name=$5
    local vpc_cidr=${6:-"10.0.0.0/16"}  # Default value if not provided
    local public_subnet_a_cidr=${7:-"10.0.0.0/24"}
    local public_subnet_b_cidr=${8:-"10.0.1.0/24"}
    local private_subnet_a_cidr=${9:-"10.0.2.0/24"}
    local private_subnet_b_cidr=${10:-"10.0.3.0/24"}

    # Package the CloudFormation template
    echo "Packaging CloudFormation template..."
    aws cloudformation package \
        --template-file template.yaml \
        --s3-bucket ${bucket_name} \
        --output-template-file packaged-template.yaml

    # Deploy the CloudFormation stack
    echo "Deploying CloudFormation stack..."
    aws cloudformation deploy \
        --template-file packaged-template.yaml \
        --stack-name ${stack_name} \
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
        --region ${region} \
        --parameter-overrides \
            AssetsBucketName=${assets_bucket_name} \
            RagasBucketName=${ragas_bucket_name} \
            VpcCidr=${vpc_cidr} \
            PublicSubnetAcidr=${public_subnet_a_cidr} \
            PublicSubnetBcidr=${public_subnet_b_cidr} \
            PrivateSubnetAcidr=${private_subnet_a_cidr} \
            PrivateSubnetBcidr=${private_subnet_b_cidr}
}

# Parse command line arguments
while getopts ":s:r:b:a:g:" opt; do
    case $opt in
        s)
            STACK_NAME="$OPTARG"
            ;;
        r)
            REGION="$OPTARG"
            ;;
        b)
            BUCKET_NAME="$OPTARG"
            ;;
        a)
            ASSETS_DIR="$OPTARG"
            ;;
        g)
            RAGAS_DIR="$OPTARG"
            ;;
        v)
            VPC_CIDR="$OPTARG"
            ;;
        pa)
            PUBLIC_SUBNET_A_CIDR="$OPTARG"
            ;;
        pb)
            PUBLIC_SUBNET_B_CIDR="$OPTARG"
            ;;
        ra)
            PRIVATE_SUBNET_A_CIDR="$OPTARG"
            ;;
        rb)
            PRIVATE_SUBNET_B_CIDR="$OPTARG"
            ;;
        \?)
            echo "Invalid option: -$OPTARG"
            usage
            ;;
        :)
            echo "Option -$OPTARG requires an argument."
            usage
            ;;
    esac
done

# Validate required parameters
if [ -z "$STACK_NAME" ] || [ -z "$REGION" ]; then
    echo "Error: Stack name and region are required parameters."
    usage
fi

# Main script execution
main() {
    # Check prerequisites
    echo "Checking prerequisites..."
    check_aws_cli
    
    # Get AWS account ID
    AWS_ACCOUNT_ID=$(check_aws_credentials)
    echo "Using AWS Account ID: ${AWS_ACCOUNT_ID}"

    # Generate bucket names
    if [ -z "$BUCKET_NAME" ]; then
        BUCKET_NAME="deployment-${AWS_ACCOUNT_ID}-${STACK_NAME}-${REGION}"
    fi
    ASSETS_BUCKET_NAME="assets-${AWS_ACCOUNT_ID}-${STACK_NAME}-${REGION}"
    RAGAS_BUCKET_NAME="ragas-${AWS_ACCOUNT_ID}-${STACK_NAME}-${REGION}"

    # Convert bucket names to lowercase
    BUCKET_NAME=$(echo "$BUCKET_NAME" | tr '[:upper:]' '[:lower:]')
    ASSETS_BUCKET_NAME=$(echo "$ASSETS_BUCKET_NAME" | tr '[:upper:]' '[:lower:]')
    RAGAS_BUCKET_NAME=$(echo "$RAGAS_BUCKET_NAME" | tr '[:upper:]' '[:lower:]')

    echo "Using deployment bucket: ${BUCKET_NAME}"
    echo "Using assets bucket: ${ASSETS_BUCKET_NAME}"
    echo "Using RAGAS bucket: ${RAGAS_BUCKET_NAME}"

    # Create all required buckets
    create_s3_bucket "${BUCKET_NAME}" "${REGION}" "Deployment"
    create_s3_bucket "${ASSETS_BUCKET_NAME}" "${REGION}" "Assets"
    create_s3_bucket "${RAGAS_BUCKET_NAME}" "${REGION}" "RAGAS"

    # Upload content before CloudFormation deployment
    if [ -z "$ASSETS_DIR" ]; then
        ASSETS_DIR=${ASSETS_DIR:-"./assets"}
    fi

    if [ -z "$RAGAS_DIR" ]; then
        RAGAS_DIR=${RAGAS_DIR:-"./ragas"}   
    fi

    upload_content "${ASSETS_DIR}" "${ASSETS_BUCKET_NAME}" "Assets"
    upload_content "${RAGAS_DIR}" "${RAGAS_BUCKET_NAME}" "RAGAS"


    # Deploy the solution
    deploy_solution \
        "${STACK_NAME}" \
        "${REGION}" \
        "${BUCKET_NAME}" \
        "${ASSETS_BUCKET_NAME}" \
        "${RAGAS_BUCKET_NAME}" \
        "${VPC_CIDR:-"10.0.0.0/16"}" \
        "${PUBLIC_SUBNET_A_CIDR:-"10.0.0.0/24"}" \
        "${PUBLIC_SUBNET_B_CIDR:-"10.0.1.0/24"}" \
        "${PRIVATE_SUBNET_A_CIDR:-"10.0.2.0/24"}" \
        "${PRIVATE_SUBNET_B_CIDR:-"10.0.3.0/24"}"

    echo "Deployment completed successfully!"
}

# Execute main function
main
