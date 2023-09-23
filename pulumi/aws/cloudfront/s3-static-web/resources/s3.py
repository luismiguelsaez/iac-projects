from pulumi_aws import s3, cloudfront
import pulumi

def create_logs_bucket(name)->s3.BucketV2:

    current_user = s3.get_canonical_user_id()
    log_delivery_user = cloudfront.get_log_delivery_canonical_user_id()

    bucket = s3.BucketV2(
        "cloudfrontS3BucketLogs",
        bucket=name,
        force_destroy=True,
    )

    bucket_ownership = s3.BucketOwnershipControls(
        "cloudfrontS3BucketLogsOwnership",
        bucket=bucket.id,
        rule=s3.BucketOwnershipControlsRuleArgs(
            object_ownership="ObjectWriter",
        )
    )

    s3.BucketAclV2(
        "cloudfrontS3BucketAcl",
        bucket=bucket.id,
        access_control_policy=s3.BucketAclV2AccessControlPolicyArgs(
            grants=[
                s3.BucketAclV2AccessControlPolicyGrantArgs(
                    grantee=s3.BucketAclV2AccessControlPolicyGrantGranteeArgs(
                        id=current_user.id,
                        type="CanonicalUser",
                    ),
                    permission="FULL_CONTROL",
                ),
                s3.BucketAclV2AccessControlPolicyGrantArgs(
                    grantee=s3.BucketAclV2AccessControlPolicyGrantGranteeArgs(
                        id=log_delivery_user.id,
                        type="CanonicalUser",
                    ),
                    permission="FULL_CONTROL",
                ),
            ],
            owner=s3.BucketAclV2AccessControlPolicyOwnerArgs(
                id=current_user.id,
            ),
        ),
        opts=pulumi.ResourceOptions(depends_on=[bucket_ownership]),
    )

    cloudfront.DistributionLoggingConfigArgs(
        bucket=bucket.bucket_regional_domain_name,
        include_cookies=False,
        prefix="",
    )

    return bucket
