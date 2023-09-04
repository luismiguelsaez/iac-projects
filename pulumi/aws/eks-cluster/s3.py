import pulumi
from pulumi_aws import s3

def elb_logs_bucket(name: str, acl: str = "private", force_destroy: bool = False) -> s3.Bucket:
  lb_logs_bucket = s3.Bucket(
    name,
    acl=acl,
    force_destroy=force_destroy,
    tags={
      "Name": name,
    }
  )

  lb_log_bucket_policy = s3.BucketPolicy(
    f"{name}-policy",
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

  return lb_logs_bucket
