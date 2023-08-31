import pulumi
from pulumi_aws import cloudwatch

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
