from pulumi_aws import ec2, get_availability_zones
import pulumi
import tools

aws_config = pulumi.Config("aws-eks-cluster")
vpc_cidr = aws_config.require("vpc_cidr")
eks_name_prefix = aws_config.require("name_prefix")

"""
VPC
"""
vpc = ec2.Vpc(
  eks_name_prefix,
  cidr_block=vpc_cidr,
  enable_dns_hostnames=True,
  enable_dns_support=True,
  tags={
    "Name": eks_name_prefix,
    f"kubernetes.io/cluster/{eks_name_prefix}": "shared",
    f"karpenter.sh/discovery": eks_name_prefix,
  },
)

"""
IGW for the public subnets
"""
igw = ec2.InternetGateway(
  eks_name_prefix,
  vpc_id=vpc.id,
  tags={
    "Name": eks_name_prefix,
  },
)

"""
Route table for the public subnets
"""
public_route_table = ec2.RouteTable(
  f"{eks_name_prefix}-public",
  vpc_id=vpc.id,
  routes=[
    ec2.RouteTableRouteArgs(
      cidr_block="0.0.0.0/0",
      gateway_id=igw.id,
    ),
  ],
  tags={
    "Name": f"{eks_name_prefix}-public",
  },
)

azs = get_availability_zones(state="available")

"""
Create public subnets
"""
public_subnets = []

for i in range(0, len(azs.names)):

  public_subnets.append(
    ec2.Subnet(
      f"{eks_name_prefix}-public-{i}",
      vpc_id=vpc.id,
      assign_ipv6_address_on_creation=False,
      availability_zone=azs.names[i],
      #cidr_block=f"10.0.{i}.0/24",
      cidr_block=tools.subnet_calc(vpc_cidr, 24, i),
      map_public_ip_on_launch=True,
      tags={
        "Name": f"{eks_name_prefix}-public-{i}",
        f"kubernetes.io/cluster/{eks_name_prefix}": "shared",
        "kubernetes.io/role/elb": "1",
        "karpenter.sh/discovery": eks_name_prefix,
      },
    )
  )
  
  ec2.route_table_association.RouteTableAssociation(
    f"{eks_name_prefix}-public-{i}",
    route_table_id=public_route_table.id,
    subnet_id=public_subnets[i].id,
  )

"""
NAT Gateway for the private subnets
"""
ngw_eip = ec2.Eip(
  eks_name_prefix,
  tags={
    "Name": eks_name_prefix,
  },
)

ngw = ec2.NatGateway(
  eks_name_prefix,
  allocation_id=ngw_eip.id,
  subnet_id=public_subnets[0].id,
  tags={
    "Name": eks_name_prefix,
  },
)

"""
Route table for the private subnets
"""
private_route_table = ec2.RouteTable(
  f"{eks_name_prefix}-private",
  vpc_id=vpc.id,
  routes=[
    ec2.RouteTableRouteArgs(
      cidr_block="0.0.0.0/0",
      nat_gateway_id=ngw.id,
    ),
  ],
  tags={
    "Name": f"{eks_name_prefix}-private",
  },
)

"""
Create private subnets
"""
private_subnets = []
start_idx = len(public_subnets)

for i in range(0, len(azs.names)):
  
  private_subnets.append(
    ec2.Subnet(
      f"{eks_name_prefix}-private-{i}",
      vpc_id=vpc.id,
      assign_ipv6_address_on_creation=False,
      availability_zone=azs.names[i - start_idx],
      #cidr_block=f"10.0.{i + start_idx}.0/24",
      cidr_block=tools.subnet_calc(vpc_cidr, 24, i + start_idx),
      map_public_ip_on_launch=False,
      tags={
        "Name": f"{eks_name_prefix}-private-{i}",
        f"kubernetes.io/cluster/{eks_name_prefix}": "owned",
        "kubernetes.io/role/internal-elb": "1",
        "karpenter.sh/discovery": eks_name_prefix,
      },
    )
  )

  ec2.route_table_association.RouteTableAssociation(
    f"{eks_name_prefix}-private-{i}",
    route_table_id=private_route_table.id,
    subnet_id=private_subnets[i].id,
  )

"""
Cluster additional security group
"""
#security_group = ec2.SecurityGroup(
#  eks_name_prefix,
#  description="Allow all HTTP(s) traffic",
#  vpc_id=vpc.id,
#  ingress=[
#    ec2.SecurityGroupIngressArgs(
#      cidr_blocks=["0.0.0.0/0"],
#      from_port=443,
#      to_port=443,
#      protocol="tcp",
#    ),
#    ec2.SecurityGroupIngressArgs(
#      cidr_blocks=["0.0.0.0/0"],
#      from_port=80,
#      to_port=80,
#      protocol="tcp",
#    ),
#  ],
#  egress=[
#    ec2.SecurityGroupEgressArgs(
#      cidr_blocks=["0.0.0.0/0"],
#      from_port=0,
#      to_port=0,
#      protocol="-1",
#    )
#  ],
#  tags={
#    "Name": eks_name_prefix,
#    #f"kubernetes.io/cluster/{eks_name_prefix}": "owned",
#    #"karpenter.sh/discovery": eks_name_prefix,
#  },
#)
