from pulumi_aws import acm, route53, Provider
import pulumi

def create_certificate(domain_name: str, route_53_zone_id: str)->acm.Certificate:

  global_region_provider = Provider("us-east-1", region="us-east-1")

  certificate = acm.Certificate(
      "cloudfrontCertificate",
      domain_name=domain_name,
      validation_method="DNS",
      opts=pulumi.ResourceOptions(provider=global_region_provider),
  )

  route53.Record(
      "cloudfrontCertificateValidationRecord",
      zone_id=route_53_zone_id,
      name=certificate.domain_validation_options[0].resource_record_name,
      type=certificate.domain_validation_options[0].resource_record_type,
      records=[certificate.domain_validation_options[0].resource_record_value],
      ttl=300,
  )

  return certificate
