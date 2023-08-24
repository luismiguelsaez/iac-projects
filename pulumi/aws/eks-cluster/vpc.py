from pulumi_aws import ec2, get_availability_zones
import pulumi

aws_config = pulumi.Config("aws-eks-cluster")
vpc_cidr = aws_config.require("vpc_cidr")

vpc = ec2.Vpc(
  "eks-main",
  cidr_block=vpc_cidr,
  enable_dns_hostnames=True,
  enable_dns_support=True,
  tags={
    "Name": "eks-main",
    "kubernetes.io/cluster/eks-main": "shared",
  },
)

igw = ec2.InternetGateway(
  "eks-main",
  vpc_id=vpc.id,
  tags={
    "Name": "eks-main",
  },
)

public_route_table = ec2.RouteTable(
  "eks-main-public",
  vpc_id=vpc.id,
  routes=[
    ec2.RouteTableRouteArgs(
      cidr_block="0.0.0.0/0",
      gateway_id=igw.id,
    ),
  ],
  tags={
    "Name": "eks-main-public",
  },
)

azs = get_availability_zones(state="available")

public_subnets = []

for i in range(0, len(azs.names)):

  public_subnets.append(
    ec2.Subnet(
      f"eks-main-public-{i}",
      vpc_id=vpc.id,
      assign_ipv6_address_on_creation=False,
      availability_zone=azs.names[i],
      cidr_block=f"10.0.{i}.0/24",
      map_public_ip_on_launch=True,
      tags={
        "Name": f"eks-main-public-{i}",
        "kubernetes.io/cluster/eks-main": "shared",
        "kubernetes.io/role/elb": "1",
      },
    )
  )
  
  ec2.route_table_association.RouteTableAssociation(
    f"eks-main-public-{i}",
    route_table_id=public_route_table.id,
    subnet_id=public_subnets[i].id,
  )

ngw_eip = ec2.Eip(
  "eks-main",
  tags={
    "Name": "eks-main",
  },
)

ngw = ec2.NatGateway(
  "eks-main",
  allocation_id=ngw_eip.id,
  subnet_id=public_subnets[0].id,
  tags={
    "Name": "eks-main",
  },
)

private_route_table = ec2.RouteTable(
  "eks-main-private",
  vpc_id=vpc.id,
  routes=[
    ec2.RouteTableRouteArgs(
      cidr_block="0.0.0.0/0",
      nat_gateway_id=ngw.id,
    ),
  ],
  tags={
    "Name": "eks-main-private",
  },
)

private_subnets = []
start_idx = len(public_subnets)

for i in range(0, len(azs.names)):
  
  private_subnets.append(
    ec2.Subnet(
      f"eks-main-private-{i}",
      vpc_id=vpc.id,
      assign_ipv6_address_on_creation=False,
      availability_zone=azs.names[i - start_idx],
      cidr_block=f"10.0.{i + start_idx}.0/24",
      map_public_ip_on_launch=False,
      tags={
        "Name": f"eks-main-private-{i}",
        "kubernetes.io/cluster/eks-main": "shared",
        "kubernetes.io/role/internal-elb": "1",
      },
    )
  )

  ec2.route_table_association.RouteTableAssociation(
    f"eks-main-private-{i}",
    route_table_id=private_route_table.id,
    subnet_id=private_subnets[i].id,
  )

security_group = ec2.SecurityGroup(
  "eks-main",
  description="Allow all HTTP(s) traffic",
  vpc_id=vpc.id,
  ingress=[
    ec2.SecurityGroupIngressArgs(
      cidr_blocks=["0.0.0.0/0"],
      from_port=443,
      to_port=443,
      protocol="tcp",
    ),
    ec2.SecurityGroupIngressArgs(
      cidr_blocks=["0.0.0.0/0"],
      from_port=80,
      to_port=80,
      protocol="tcp",
    ),
  ],
)
