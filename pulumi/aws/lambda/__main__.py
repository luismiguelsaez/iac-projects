import ecr, iam, cloudwatch

import pulumi
from pulumi_aws import lambda_
from pulumi_aws import cloudwatch as aws_cloudwatch

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
      "ECR_REPO_LIFECYCLE_POLICY": pulumi.Output.json_dumps(ecr.lifecycle_policy),
      "ECR_REPO_POLICY": pulumi.Output.json_dumps(ecr.repository_policy),
    }
  },
  description="Lambda function to create ECR repos automatically",
  handler="lambda_function.lambda_handler",
  memory_size=128,
  publish=True,
  role=iam.lamba_role.arn,
  runtime="python3.8",
  tracing_config=lambda_.FunctionTracingConfigArgs(
    mode="Active"
  ),
  tags={
    "Name": "lambda-ecr-repo-creation"
  },
)

eventbridge_target = aws_cloudwatch.EventTarget(
  resource_name="lambda-ecr-repo-creation",
  arn=lambda_function.arn,
  rule=cloudwatch.eventbridge_rule.name,
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
  source_arn=cloudwatch.eventbridge_rule.arn,
)
