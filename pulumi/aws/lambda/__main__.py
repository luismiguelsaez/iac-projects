"""An AWS Python Pulumi program"""

from os import name
import pulumi
from pulumi_aws import iam, lambda_, cloudwatch

"""
Create an IAM policy for the Lambda function, with permissions to write logs to CloudWatch
"""
lambda_iam_policy = iam.Policy(
  resource_name="lambda-ecr-repo-cration",
  description="IAM policy for lambda",
  policy=pulumi.Output.json_dumps(
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Action": [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents"
          ],
          "Resource": "arn:aws:logs:*:*:*",
          "Effect": "Allow"
        },
        {
          "Action": [
            "ecr:CreateRepository",
            "ecr:SetRepositoryPolicy",
            "ecr:PutLifecyclePolicy",
            "ecr:TagResource"
          ],
          "Resource": "*",
          "Effect": "Allow"
        }
      ]
    }
  ),
  tags={
    "Name": "lambda-ecr-repo-creation"
  }
)

"""
Create an IAM role for the Lambda function, using the policy created above
"""
lamba_iam_role = iam.Role(
  name="lambda-ecr-repo-creation",
  resource_name="lambda-ecr-repo-creation",
  assume_role_policy=pulumi.Output.json_dumps(
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Action": "sts:AssumeRole",
          "Principal": {
            "Service": "lambda.amazonaws.com"
          },
          "Effect": "Allow",
          "Sid": ""
        }
      ]
    }
  ),
  description="IAM role for lambda",
  force_detach_policies=True,
  path="/",
  permissions_boundary=None,
  tags={
    "Name": "lambda-ecr-repo-creation"
  }
)

iam.RolePolicyAttachment(
  resource_name="lambda-ecr-repo-creation",
  policy_arn=lambda_iam_policy.arn,
  role=lamba_iam_role.name
)

ecr_repository_policy = {
  "Version": "2008-10-17",
  "Statement": [
    {
      "Sid": "AllowPushPull",
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "arn:aws:iam::123456789012:root",
          "arn:aws:iam::123456789012:user/MyUser"
        ]
      },
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ]
    }
  ]
}

ecr_lifecycle_policy = {
  "rules": [
    {
      "rulePriority": 1,
      "description": "Expire images older than 14 days",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 14
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}

"""
Create a Lambda function, using the IAM role and Python code in the 'src' folder
"""
lambda_function = lambda_.Function(
  resource_name="lambda-ecr-repo-creation",
  code=pulumi.AssetArchive({
    ".": pulumi.FileArchive("./src")
  }),
  environment={
    "variables": {
      "ECR_REPO_NAME": "test-repo",
      "ECR_REPO_LIFECYCLE_POLICY": pulumi.Output.json_dumps(ecr_lifecycle_policy),
      "ECR_REPO_POLICY": pulumi.Output.json_dumps(ecr_repository_policy),
    }
  },
  description="Lambda function to create ECR repos automatically",
  handler="lambda_function.lambda_handler",
  memory_size=128,
  publish=True,
  role=lamba_iam_role.arn,
  runtime="python3.8",
  tracing_config=lambda_.FunctionTracingConfigArgs(
    mode="Active"
  ),
  tags={
    "Name": "lambda-ecr-repo-creation"
  },
)

"""
Create an EventBridge rule to trigger the Lambda function from a CloudTrail event
"""
eventbridge_rule = cloudwatch.EventRule(
  name="lambda-ecr-repo-creation",
  resource_name="lambda-ecr-repo-creation",
  description="EventBridge rule to trigger the Lambda function from a CloudTrail event",
  event_pattern=pulumi.Output.json_dumps(
    {
      "source": [
        "aws.ecr"
      ],
      "detail-type": [
        "AWS API Call via CloudTrail"
      ],
      "detail": {
        "eventSource": [
          "ecr.amazonaws.com"
        ],
        "eventName": [
          "InitiateLayerUpload"
        ],
        "errorCode": [
          "RepositoryNotFoundException"
        ]
      }
    }
  ),
  is_enabled=True,
)

eventbridge_target = cloudwatch.EventTarget(
  resource_name="lambda-ecr-repo-creation",
  arn=lambda_function.arn,
  rule=eventbridge_rule.name,
  target_id="lambda-ecr-repo-creation",
)

"""
Allow EventBridge rule to invoke the Lambda function
"""
lambda_permission_eventbridge = lambda_.Permission(
  resource_name="lambda-ecr-repo-creation",
  statement_id="lambda-ecr-repo-creation",
  action="lambda:InvokeFunction",
  function=lambda_function.name,
  principal="events.amazonaws.com",
  source_arn=eventbridge_rule.arn,
)
