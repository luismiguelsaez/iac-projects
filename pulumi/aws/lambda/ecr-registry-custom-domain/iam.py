import pulumi
from pulumi_aws import iam

"""
Create an IAM policy for the Lambda function, with permissions to write logs to CloudWatch
"""
lambda_policy = iam.Policy(
  resource_name="ecr-custom-domain",
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
        }
      ]
    }
  ),
  tags={
    "Name": "lambda-ecr-custom-domain"
  }
)

"""
Create an IAM role for the Lambda function, using the policy created above
"""
lamba_role = iam.Role(
  name="ecr-custom-domain",
  resource_name="ecr-custom-domain",
  assume_role_policy=pulumi.Output.json_dumps(
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Action": "sts:AssumeRole",
          "Principal": {
            "Service": [
              "edgelambda.amazonaws.com",
              "lambda.amazonaws.com",
            ]
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
    "Name": "lambda-ecr-custom-domain"
  }
)

iam.RolePolicyAttachment(
  resource_name="ecr-custom-domain",
  policy_arn=lambda_policy.arn,
  role=lamba_role.name
)
