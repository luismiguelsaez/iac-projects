"""An AWS Python Pulumi program"""

import pulumi
from pulumi_random import RandomString
from pulumi_aws import s3, route53

from resources.s3 import create_content_bucket, create_logs_bucket, create_bucket_policy_cloudfront
from resources.acm import create_certificate
from resources.cloudfront import create_distribution
from resources.route53 import create_dns_record
from resources.athena import create_database

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
cloudfront_s3_bucket = create_content_bucket(pulumi.Output.concat("cloudfront-", cloudfront_config.require('subdomain'), "-", cloudfront_s3_bucket_random_id.result))

"""
Cloudfront logs bucket
"""
cloudfront_s3_bucket_logs = create_logs_bucket(name=pulumi.Output.concat("cloudfront-", cloudfront_config.require('subdomain'), "-", cloudfront_s3_bucket_random_id.result, "-logs"))
cloudfront_s3_athena_db = create_database(name=f"cloudfront_{cloudfront_config.require('subdomain')}_logs".replace("-", "_").lower(), bucket=cloudfront_s3_bucket_logs.id)

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
DNS record pointing to the Cloudfront distribution.
"""

cloudfront_dns_record = create_dns_record(
    name=f"{cloudfront_config.require('subdomain')}.{route53_config.require('zone_name')}",
    route53_zone_id=route53_zone.zone_id,
    cloudfront_distribution_domain_name=cloudfront_distribution.domain_name,
    cloudfront_distribution_hosted_zone=cloudfront_distribution.hosted_zone_id
)

"""
S3 bucket policy to allow Cloudfront to access the bucket.
"""

cloudfront_s3_bucket_policy = create_bucket_policy_cloudfront(
    bucket_id=cloudfront_s3_bucket.id,
    bucket_arn=cloudfront_s3_bucket.arn,
    cloudfront_distribution_arn=cloudfront_distribution.arn
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
