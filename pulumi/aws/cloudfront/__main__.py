"""An AWS Python Pulumi program"""

import pulumi
from pulumi_random import RandomString
from pulumi_aws import Provider, s3, cloudfront, route53, acm

route53_config = pulumi.Config("route53")
cloudfront_config = pulumi.Config("cloudfront")

# https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-cache-policies.html
cache_policies = {
  "CachingDisabled": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
  "CachingOptimized": "658327ea-f89d-4fab-a63d-7e88639e58f6",
  "CachingOptimizedForUncompressedObjects": "b2884449-e4de-46a7-ac36-70bc7f1ddd6d"
}

# https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-origin-request-policies.html
origin_request_policies = {
  "AllViewer": "216adef6-5c7f-47e4-b989-5492eafa07d3",
  "AllViewerExceptHostHeader": "b689b0a8-53d0-40ab-baf2-68738e2966ac",
  "AllViewerAndCloudFrontHeaders-2022-06": "33f36d7e-f396-46d9-90e0-52428a34d9dc",
  "CORS-S3Origin": "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf"
}

# https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-response-headers-policies.html
response_header_policies = {
  "CORS-and-SecurityHeadersPolicy": "e61eb60c-9c35-4d20-a928-2b84e02af89c",
  "SecurityHeadersPolicy": "67f7725c-6f97-4210-82d7-5512b31e9d03"
}

"""
Create an additional provider for the global region. This is required for the ACM certificate
"""
global_region_provider = Provider("aws", region="us-east-1")

route53_zone = route53.get_zone(
    name=route53_config.require("zone_name"),
    private_zone=route53_config.require_bool("private_zone"),
)

"""
ACM certificate in the global region, as required for CloudFront.
"""
cloudfront_certificate = acm.Certificate(
    "cloudfrontCertificate",
    domain_name=f"{cloudfront_config.require('subdomain')}.{route53_config.require('zone_name')}",
    validation_method="DNS",
    opts=pulumi.ResourceOptions(provider=global_region_provider),
)

cloudfront_certificate_validation_record = route53.Record(
    "cloudfrontCertificateValidationRecord",
    zone_id=route53_zone.zone_id,
    name=cloudfront_certificate.domain_validation_options[0].resource_record_name,
    type=cloudfront_certificate.domain_validation_options[0].resource_record_type,
    records=[cloudfront_certificate.domain_validation_options[0].resource_record_value],
    ttl=300,
)

"""
S3 bucket to store the static website content.
"""
cloudfront_s3_bucket_random_id = RandomString(
    "cloudfrontS3BucketRandomId",
    length=16,
    special=False,
    upper=False,
    numeric=False,
)

cloudfront_s3_bucket = s3.Bucket(
    "cloudfrontS3Bucket",
    bucket=pulumi.Output.concat("cloudfront-", cloudfront_config.require('subdomain'), "-", cloudfront_s3_bucket_random_id.result),
    acl="private",
    force_destroy=True,
)

"""
Cloudfront logs bucket
"""
if cloudfront_config.get_bool("enable_logs"):
  cloudfront_s3_bucket_logs = s3.Bucket(
      "cloudfrontS3BucketLogs",
      bucket=pulumi.Output.concat("cloudfront-", cloudfront_config.require('subdomain'), "-", cloudfront_s3_bucket_random_id.result, "-logs"),
      acl="private",
      force_destroy=True,
  )

  cloudfront_s3_bucket_ownership = s3.BucketOwnershipControls(
      "cloudfrontS3BucketLogsOwnership",
      bucket=cloudfront_s3_bucket.id,
      rule=s3.BucketOwnershipControlsRuleArgs(
          object_ownership="BucketOwnerPreferred",
      )
  )
  
  cloudfront_distribution_logging_config=cloudfront.DistributionLoggingConfigArgs(
      bucket=cloudfront_s3_bucket_logs.bucket_regional_domain_name,
      include_cookies=False,
      prefix="",
  ),

"""
Access control for the S3 bucket, needed for Cloudfront origin access identity.
"""
cloudfront_s3_origin_access_control = cloudfront.OriginAccessControl(
    "cloudfrontS3OriginAccessControl",
    origin_access_control_origin_type="s3",
    signing_behavior="always",
    signing_protocol="sigv4"
)

"""
Cloudfront distribution with S3 bucket as only origin.
"""
cloudfront_distribution = cloudfront.Distribution(
    "cloudfrontDistribution",
    aliases=[f"{cloudfront_config.require('subdomain')}.{route53_config.require('zone_name')}"],
    default_root_object="index.html",
    enabled=True,
    is_ipv6_enabled=True,
    origins=[
        cloudfront.DistributionOriginArgs(
            domain_name=cloudfront_s3_bucket.bucket_regional_domain_name,
            origin_id="s3Origin",
            origin_access_control_id=cloudfront_s3_origin_access_control.id,
        ),
        #cloudfront.DistributionOriginArgs(
        #    domain_name="",
        #    origin_id="k8sNLBOrigin",
        #    custom_headers=[],
        #    custom_origin_config=cloudfront.DistributionOriginCustomOriginConfigArgs(
        #        http_port=80,
        #        https_port=443,
        #        origin_protocol_policy="https-only",
        #        origin_ssl_protocols=["TLSv1.2"],
        #    ),
        #)
    ],
    default_cache_behavior=cloudfront.DistributionDefaultCacheBehaviorArgs(
        allowed_methods=["GET", "HEAD", "OPTIONS"],
        cached_methods=["GET", "HEAD", "OPTIONS"],
        target_origin_id="s3Origin",
        viewer_protocol_policy="redirect-to-https",
        # Configure managed policies
        cache_policy_id=cache_policies["CachingOptimized"],
        origin_request_policy_id=origin_request_policies["CORS-S3Origin"],
        #response_headers_policy_id=response_header_policies["CORS-and-SecurityHeadersPolicy"],
    ),
    #ordered_cache_behaviors=[
    #    cloudfront.DistributionOrderedCacheBehaviorArgs(
    #        allowed_methods=["GET", "HEAD", "OPTIONS"],
    #        cached_methods=["GET", "HEAD", "OPTIONS"],
    #        target_origin_id="k8sNLBOrigin",
    #        viewer_protocol_policy="redirect-to-https",
    #        path_pattern="/v2/*",
    #        cache_policy_id=cache_policies["CachingDisabled"],
    #        origin_request_policy_id=origin_request_policies["AllViewer"],
    #    ),
    #],
    custom_error_responses=[
        cloudfront.DistributionCustomErrorResponseArgs(
            error_code=404,
            response_code=200,
            response_page_path="/index.html",
            error_caching_min_ttl=300,
        )
    ],
    restrictions=cloudfront.DistributionRestrictionsArgs(
        geo_restriction=cloudfront.DistributionRestrictionsGeoRestrictionArgs(
            restriction_type="none",
        ),
    ),
    viewer_certificate=cloudfront.DistributionViewerCertificateArgs(
        acm_certificate_arn=cloudfront_certificate.arn,
        ssl_support_method="sni-only",
    ),
    #logging_config=cloudfront_distribution_logging_config if cloudfront_config.get_bool("enable_logs") else None,
)

"""
DNS record pointing to the Cloudfront distribution.
"""
cloudfront_dns_record = route53.Record(
    "cloudfrontDnsRecord",
    zone_id=route53_zone.zone_id,
    name=f"{cloudfront_config.require('subdomain')}.{route53_config.require('zone_name')}",
    type="A",
    aliases=[
        route53.RecordAliasArgs(
            name=cloudfront_distribution.domain_name,
            zone_id=cloudfront_distribution.hosted_zone_id,
            evaluate_target_health=False,
        )
    ],
)

"""
S3 bucket policy to allow Cloudfront to access the bucket.
"""
cloudfront_s3_bucket_policy = s3.BucketPolicy(
    "cloudfrontS3BucketPolicy",
    bucket=cloudfront_s3_bucket.id,
    policy=pulumi.Output.json_dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "CloudfrontReadObject",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "cloudfront.amazonaws.com"
                    },
                    "Action": ["s3:GetObject"],
                    "Resource": [cloudfront_s3_bucket.arn.apply(lambda arn: f"{arn}/*")],
                    "Condition": {
                        "StringEquals": {
                          "AWS:SourceArn": cloudfront_distribution.arn.apply(lambda arn: arn)
                        }
                    }
                },
                {
                    "Sid": "CloudfrontListBucket",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "cloudfront.amazonaws.com"
                    },
                    "Action": ["s3:ListBucket"],
                    "Resource": [cloudfront_s3_bucket.arn.apply(lambda arn: arn)],
                    "Condition": {
                        "StringEquals": {
                          "AWS:SourceArn": cloudfront_distribution.arn.apply(lambda arn: arn)
                        }
                    }
                }
            ],
        }
    ),
)

"""
Index object for the S3 bucket.
"""
cloudfront_s3_bucket_index_object = s3.BucketObject(
    "cloudfrontS3BucketIndexObject",
    bucket=cloudfront_s3_bucket.id,
    key="index.html",
    acl="private",
    content_type="text/html",
    content="""
<html>
<body>
<h1>Hello, world!</h1>
<p>This is a test of CloudFront.</p>
</body>
</html>
""",
)

pulumi.export("cloudfront_distribution_dns_name", cloudfront_dns_record.fqdn)
