import pulumi
from pulumi_aws import iam

"""
Create an IAM policy for the Lambda function, with permissions to write logs to CloudWatch
"""
lambda_policy = iam.Policy(
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
lamba_role = iam.Role(
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
  policy_arn=lambda_policy.arn,
  role=lamba_role.name
)
