from pulumi_aws import cloudfront
import pulumi

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

def create_distribution(
        aliases: list[str],
        origin_domain_name: pulumi.Output[str],
        acm_certificate: pulumi.Output[str],
        logging_bucket: pulumi.Output[str],
        origin_type: str = "s3",
    )->cloudfront.Distribution:

    origin_list = []

    if origin_type == "s3":
        s3_origin_access_control = cloudfront.OriginAccessControl(
            "cloudfrontS3OriginAccessControl",
            origin_access_control_origin_type="s3",
            signing_behavior="always",
            signing_protocol="sigv4"
        )
        origin_list = [
            cloudfront.DistributionOriginArgs(
                domain_name=origin_domain_name,
                origin_id="s3Origin",
                origin_access_control_id=s3_origin_access_control.id,
            )
        ]
    else:
        origin_list = [
            cloudfront.DistributionOriginArgs(
                domain_name=origin_domain_name,
                origin_id="NLBOrigin",
                custom_headers=[],
                custom_origin_config=cloudfront.DistributionOriginCustomOriginConfigArgs(
                    http_port=80,
                    https_port=443,
                    origin_protocol_policy="https-only",
                    origin_ssl_protocols=["TLSv1.2"],
                ),
            )
        ]

    distribution = cloudfront.Distribution(
        "cloudfrontDistribution",
        comment="CloudFront distribution for static site",
        aliases=aliases,
        default_root_object="index.html",
        enabled=True,
        is_ipv6_enabled=True,
        origins=origin_list,
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
        #        target_origin_id="NLBOrigin",
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
            acm_certificate_arn=acm_certificate,
            ssl_support_method="sni-only",
            minimum_protocol_version="TLSv1.2_2021"
        ),
        logging_config=cloudfront.DistributionLoggingConfigArgs(
            bucket=logging_bucket,
            include_cookies=False,
            prefix="",
        )
    )

    return distribution
