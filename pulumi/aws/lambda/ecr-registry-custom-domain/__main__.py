import iam
import pulumi
from pulumi_aws import lambda_, apigatewayv2, cloudwatch, route53, acm, get_caller_identity

aws_config = pulumi.Config("aws")
route53_config = pulumi.Config("route53")
aws_account_id = get_caller_identity().account_id
aws_region = aws_config.require("region")
dns_zone_name = route53_config.require("zone_name")
dns_record_name = route53_config.require("record_name")
dns_private_zone = route53_config.require_bool("private_zone")

ecr_registry = f"{aws_account_id}.dkr.ecr.{aws_region}.amazonaws.com"

"""
Create a Lambda function, using the IAM role and Python code in the 'src' folder
"""
lambda_function = lambda_.Function(
    "ecr-custom-domain-proxy",
    architectures=["arm64"],
    code=pulumi.AssetArchive({
        ".": pulumi.FileArchive("./src")
    }),
    environment={
        "variables": {
            "AWS_ECR_REGISTRY": ecr_registry
        }
    },
    description="Lambda function to act as a proxy for ECR",
    handler="index.handler",
    memory_size=128,
    publish=True,
    role=iam.lamba_role.arn,
    runtime="nodejs18.x",
    tracing_config=lambda_.FunctionTracingConfigArgs(
        mode="Active"
    ),
    tags={
        "Name": "ecr-custom-domain-proxy"
    }
)

"""
Create APIGateway resources
"""
acm_certificate = acm.get_certificate(
    domain=dns_zone_name,
    most_recent=True
)

apigateway_domain_name = apigatewayv2.DomainName(
    "ecr-custom-domain-proxy-domain-name",
    domain_name=f"{dns_record_name}.{dns_zone_name}",
    domain_name_configuration=apigatewayv2.DomainNameDomainNameConfigurationArgs(
        certificate_arn=acm_certificate.arn,
        endpoint_type="REGIONAL",
        security_policy="TLS_1_2"
    )
)

apigateway_api = apigatewayv2.Api(
    "ecr-custom-domain-proxy-api",
    disable_execute_api_endpoint=True,
    protocol_type="HTTP",
)

cloudwatch_log_group = cloudwatch.LogGroup(
    "ecr-custom-domain-proxy-apigateway",
    name=pulumi.Output.concat("/aws/apigateway2/", apigateway_api.id),
)

apigateway_stage_default = apigatewayv2.Stage(
    "ecr-custom-domain-proxy-default",
    api_id=apigateway_api.id,
    auto_deploy=True,
    name="$default",
    access_log_settings=apigatewayv2.StageAccessLogSettingsArgs(
        destination_arn=cloudwatch_log_group.arn,
        format='{"requestId":"$context.requestId","ip":"$context.identity.sourceIp","requestTime":"$context.requestTime","httpMethod":"$context.httpMethod","routeKey":"$context.routeKey","status":"$context.status","protocol":"$context.protocol","responseLength":"$context.responseLength"}'
    )
)

apigatewayv2.ApiMapping(
    "ecr-custom-domain-proxy-api-mapping",
    api_id=apigateway_api.id,
    domain_name=apigateway_domain_name.id,
    stage=apigateway_stage_default.name
)

apigateway_integration_proxy = apigatewayv2.Integration(
    resource_name="ecr-custom-domain-proxy-integration",
    api_id=apigateway_api.id,
    integration_method="POST",
    integration_type="AWS_PROXY",
    integration_uri=lambda_function.invoke_arn,
    payload_format_version="2.0"
)

apigateway_route_proxy = apigatewayv2.Route(
    "ecr-custom-domain-proxy-route-proxy",
    api_id=apigateway_api.id,
    route_key="ANY /{proxy+}",
    target=pulumi.Output.concat("integrations/", apigateway_integration_proxy.id),
    opts=pulumi.ResourceOptions(depends_on=[apigateway_integration_proxy])
)

"""
Route53 DNS record for the APIGateway
"""
route53_zone = route53.get_zone(
    name=dns_zone_name,
    private_zone=dns_private_zone
)

route53_apigateway_record = route53.Record(
    "ecr-custom-domain-proxy-apigateway-record",
    name=apigateway_domain_name.domain_name,
    type="A",
    zone_id=route53_zone.zone_id,
    aliases=[
        route53.RecordAliasArgs(
            evaluate_target_health=False,
            name=apigateway_domain_name.domain_name_configuration.target_domain_name,
            zone_id=apigateway_domain_name.domain_name_configuration.hosted_zone_id
        )
    ]
)

"""
Allow APIGateway to invoke the Lambda function
"""
lambda_permission_apigateway = lambda_.Permission(
    "ecr-custom-domain-proxy",
    statement_id="ecr-custom-domain-proxy",
    action="lambda:InvokeFunction",
    function=lambda_function.name,
    principal="apigateway.amazonaws.com",
    source_arn=apigateway_api.execution_arn.apply(lambda arn: arn)
)

pulumi.export("original_ecr_registry", ecr_registry)
pulumi.export("custom_ecr_registry", apigateway_domain_name.domain_name)
pulumi.export("route53_zone_id", route53_zone.zone_id)
pulumi.export("acm_certificate_domain_name", acm_certificate.domain)
pulumi.export("acm_certificate_arn", acm_certificate.arn)
