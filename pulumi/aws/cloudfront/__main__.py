"""An AWS Python Pulumi program"""

import pulumi
from pulumi_random import RandomString
from pulumi_aws import Provider, s3, cloudfront, route53, acm

route53_config = pulumi.Config("route53")
cloudfront_config = pulumi.Config("cloudfront")

global_region_provider = Provider("aws", region="us-east-1")

route53_zone = route53.get_zone(
    name=route53_config.require("zone_name"),
    private_zone=False,
)

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

cloudfront_s3_origin_access_control = cloudfront.OriginAccessControl(
    "cloudfrontS3OriginAccessControl",
    origin_access_control_origin_type="s3",
    signing_behavior="always",
    signing_protocol="sigv4"
)

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
        )
    ],
    default_cache_behavior=cloudfront.DistributionDefaultCacheBehaviorArgs(
        allowed_methods=["GET", "HEAD", "OPTIONS"],
        cached_methods=["GET", "HEAD", "OPTIONS"],
        target_origin_id="s3Origin",
        viewer_protocol_policy="redirect-to-https",
        cache_policy_id="658327ea-f89d-4fab-a63d-7e88639e58f6",
    ),
    restrictions=cloudfront.DistributionRestrictionsArgs(
        geo_restriction=cloudfront.DistributionRestrictionsGeoRestrictionArgs(
            restriction_type="none",
        ),
    ),
    viewer_certificate=cloudfront.DistributionViewerCertificateArgs(
        acm_certificate_arn=cloudfront_certificate.arn,
        ssl_support_method="sni-only",
    ),
)

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
