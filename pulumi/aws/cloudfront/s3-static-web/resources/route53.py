import pulumi
from pulumi_aws import route53

def create_dns_record(
        name: str,
        route53_zone_id: str,
        cloudfront_distribution_domain_name: pulumi.Output[str],
        cloudfront_distribution_hosted_zone: pulumi.Output[str]
    )->route53.Record:

    dns_record = route53.Record(
        "cloudfrontDnsRecord",
        zone_id=route53_zone_id,
        name=name,
        type="A",
        aliases=[
            route53.RecordAliasArgs(
                name=cloudfront_distribution_domain_name,
                zone_id=cloudfront_distribution_hosted_zone,
                evaluate_target_health=False,
            )
        ],
    )
    
    return dns_record
