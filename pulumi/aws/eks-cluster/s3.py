import pulumi
from pulumi_aws import s3

aws_eks_config = pulumi.Config("aws-eks-cluster")
eks_name_prefix = aws_eks_config.require("name_prefix")

lb_logs_bucket = s3.Bucket(
  f"{eks_name_prefix}-lb-logs",
  acl="private",
  force_destroy=True,
  tags={
    "Name": f"{eks_name_prefix}-lb-logs",
  }
)

lb_log_bucket_policy = s3.BucketPolicy(
  f"{eks_name_prefix}-lb-logs-policy",
  bucket=lb_logs_bucket.id,
  policy=pulumi.Output.json_dumps(
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "AWSElasticLoadBalancingLogManagement",
          "Effect": "Allow",
          "Principal": {
            "Service": "delivery.logs.amazonaws.com"
          },
          "Action": "s3:GetBucketAcl",
          "Resource": lb_logs_bucket.arn,
        },
        {
          "Sid": "AWSElasticLoadBalancingLogDelivery",
          "Effect": "Allow",
          "Principal": {
            "Service": "delivery.logs.amazonaws.com"
          },
          "Action": "s3:PutObject",
          "Resource": f"{lb_logs_bucket.arn}/*",
        }
      ]
    }
  )
)
