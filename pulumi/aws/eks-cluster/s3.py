import pulumi
from pulumi_aws import s3

def bucket_with_allowed_roles(name: str, acl: str = "private", force_destroy: bool = False, roles: list = []) -> s3.Bucket:
  bucket = s3.Bucket(
    resource_name=name,
    bucket=name,
    acl=acl,
    force_destroy=force_destroy,
    tags={
      "Name": name,
    }
  )

  s3.BucketPolicy(
    resource_name=name,
    bucket=bucket.id,
    policy=pulumi.Output.json_dumps(
      {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Sid": "AllowS3ObjectManagement",
            "Effect": "Allow",
            "Principal": {
              "AWS": roles
            },
            "Action": [
                "s3:PutObjectAcl",
                "s3:PutObject",
                "s3:GetObjectAcl",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": pulumi.Output.concat(bucket.arn, "/*"),
          },
          {
            "Sid": "AllowS3ObjectList",
            "Effect": "Allow",
            "Principal": {
              "AWS": roles
            },
            "Action": "s3:ListBucket",
            "Resource": bucket.arn.apply(lambda arn: arn),
          }
        ]
      }
    )
  )

  return bucket

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
