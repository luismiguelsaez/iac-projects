"""An AWS Python Pulumi program"""

import pulumi
from pulumi_random import RandomString
from pulumi_aws import Provider, s3, cloudfront, route53, acm

from resources.s3 import create_logs_bucket
from resources.acm import create_certificate
from resources.cloudfront import cache_policies, origin_request_policies, create_distribution

route53_config = pulumi.Config("route53")
cloudfront_config = pulumi.Config("cloudfront")

cloudfront_s3_bucket_random_id = RandomString(
    "cloudfrontS3BucketRandomId",
    length=16,
    special=False,
    upper=False,
    numeric=False,
)

"""
Get the Route53 zone for the domain.
"""
route53_zone = route53.get_zone(
    name=route53_config.require("zone_name"),
    private_zone=route53_config.require_bool("private_zone"),
)

"""
ACM certificate in the global region, as required for CloudFront.
"""
cloudfront_certificate = create_certificate(
    domain_name=f"{cloudfront_config.require('subdomain')}.{route53_config.require('zone_name')}",
    route_53_zone_id=route53_zone.zone_id
)

"""
S3 bucket to store the static website content.
"""
cloudfront_s3_bucket = s3.BucketV2(
    "cloudfrontS3Bucket",
    bucket=pulumi.Output.concat("cloudfront-", cloudfront_config.require('subdomain'), "-", cloudfront_s3_bucket_random_id.result),
    acl="private",
    force_destroy=True,
)

"""
Cloudfront logs bucket
"""
cloudfront_s3_bucket_logs =  create_logs_bucket(name=pulumi.Output.concat("cloudfront-", cloudfront_config.require('subdomain'), "-", cloudfront_s3_bucket_random_id.result, "-logs"))

"""
Create Cloudfront distribution
"""
cloudfront_distribution = create_distribution(
    aliases=[f"{cloudfront_config.require('subdomain')}.{route53_config.require('zone_name')}"],
    origin_domain_name=cloudfront_s3_bucket.bucket_regional_domain_name,
    acm_certificate=cloudfront_certificate.arn,
    logging_bucket=cloudfront_s3_bucket_logs.bucket_regional_domain_name
)

"""
Access control for the S3 bucket, needed for Cloudfront origin access identity.
"""
#cloudfront_s3_origin_access_control = cloudfront.OriginAccessControl(
#    "cloudfrontS3OriginAccessControl",
#    origin_access_control_origin_type="s3",
#    signing_behavior="always",
#    signing_protocol="sigv4"
#)

"""
Cloudfront distribution with S3 bucket as only origin.
"""
#cloudfront_distribution = cloudfront.Distribution(
#    "cloudfrontDistribution",
#    aliases=[f"{cloudfront_config.require('subdomain')}.{route53_config.require('zone_name')}"],
#    default_root_object="index.html",
#    enabled=True,
#    is_ipv6_enabled=True,
#    origins=[
#        cloudfront.DistributionOriginArgs(
#            domain_name=cloudfront_s3_bucket.bucket_regional_domain_name,
#            origin_id="s3Origin",
#            origin_access_control_id=cloudfront_s3_origin_access_control.id,
#        ),
#        #cloudfront.DistributionOriginArgs(
#        #    domain_name="",
#        #    origin_id="k8sNLBOrigin",
#        #    custom_headers=[],
#        #    custom_origin_config=cloudfront.DistributionOriginCustomOriginConfigArgs(
#        #        http_port=80,
#        #        https_port=443,
#        #        origin_protocol_policy="https-only",
#        #        origin_ssl_protocols=["TLSv1.2"],
#        #    ),
#        #)
#    ],
#    default_cache_behavior=cloudfront.DistributionDefaultCacheBehaviorArgs(
#        allowed_methods=["GET", "HEAD", "OPTIONS"],
#        cached_methods=["GET", "HEAD", "OPTIONS"],
#        target_origin_id="s3Origin",
#        viewer_protocol_policy="redirect-to-https",
#        # Configure managed policies
#        cache_policy_id=cache_policies["CachingOptimized"],
#        origin_request_policy_id=origin_request_policies["CORS-S3Origin"],
#        #response_headers_policy_id=response_header_policies["CORS-and-SecurityHeadersPolicy"],
#    ),
#    #ordered_cache_behaviors=[
#    #    cloudfront.DistributionOrderedCacheBehaviorArgs(
#    #        allowed_methods=["GET", "HEAD", "OPTIONS"],
#    #        cached_methods=["GET", "HEAD", "OPTIONS"],
#    #        target_origin_id="k8sNLBOrigin",
#    #        viewer_protocol_policy="redirect-to-https",
#    #        path_pattern="/v2/*",
#    #        cache_policy_id=cache_policies["CachingDisabled"],
#    #        origin_request_policy_id=origin_request_policies["AllViewer"],
#    #    ),
#    #],
#    custom_error_responses=[
#        cloudfront.DistributionCustomErrorResponseArgs(
#            error_code=404,
#            response_code=200,
#            response_page_path="/index.html",
#            error_caching_min_ttl=300,
#        )
#    ],
#    restrictions=cloudfront.DistributionRestrictionsArgs(
#        geo_restriction=cloudfront.DistributionRestrictionsGeoRestrictionArgs(
#            restriction_type="none",
#        ),
#    ),
#    viewer_certificate=cloudfront.DistributionViewerCertificateArgs(
#        acm_certificate_arn=cloudfront_certificate.arn,
#        ssl_support_method="sni-only",
#    ),
#    logging_config=cloudfront.DistributionLoggingConfigArgs(
#        bucket=cloudfront_s3_bucket_logs.bucket_regional_domain_name,
#        include_cookies=False,
#        prefix="",
#    )
#)

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
