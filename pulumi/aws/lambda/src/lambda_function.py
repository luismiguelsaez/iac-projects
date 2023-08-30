from email.mime import image
import boto3
import botocore.exceptions
import json
import os

def lambda_handler(event, context):
    """
    Lambda handler to create ECR repos automatically
    """
    ecr_client = boto3.client("ecr")
    ecr_repo_name = event["detail"]["requestParameters"]["repositoryName"]
    ecr_repo_lifecycle_policy = json.loads(os.environ["ECR_REPO_LIFECYCLE_POLICY"])
    ecr_repo_policy = json.loads(os.environ["ECR_REPO_POLICY"])

    try:
        ecr_client.create_repository(
            repositoryName=ecr_repo_name,
            imageScanningConfiguration={
                "scanOnPush": True
            },
            imageTagMutability="MUTABLE",
            encryptionConfiguration={
                "encryptionType": "AES256"
            },
            tags=[
                {
                    'Key':'auto-create',
                    'Value':'true'
                },
                {
                    'Key':'creation-date',
                    'Value': event["detail"]["eventTime"]
                },
                {
                    'Key':'creator-id',
                    'Value': event["detail"]["userIdentity"]["principalId"]
                },
            ],
        )
        ecr_client.put_lifecycle_policy(
            repositoryName=ecr_repo_name,
            lifecyclePolicyText=json.dumps(ecr_repo_lifecycle_policy)
        )
        ecr_client.set_repository_policy(
            repositoryName=ecr_repo_name,
            policyText=json.dumps(ecr_repo_policy)
        )
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "RepositoryAlreadyExistsException":
            print("Repository already exists")
        else:
            raise e

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Repository created successfully"
        })
    }
