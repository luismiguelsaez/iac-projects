from pulumi_aws import iam

eks_cluster_role = iam.Role(
  "eks-main",
  assume_role_policy="""{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": "sts:AssumeRole",
        "Principal": {
          "Service": "eks.amazonaws.com"
        },
        "Effect": "Allow",
        "Sid": ""
      }
    ]
  }""",
  tags={
    "Name": "eks-main",
  },
)

iam.RolePolicyAttachment(
  "eks-main-AmazonEKSClusterPolicy",
  policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
  role=eks_cluster_role.name,
)

iam.RolePolicyAttachment(
  "eks-main-AmazonEKSServicePolicy",
  policy_arn="arn:aws:iam::aws:policy/AmazonEKSServicePolicy",
  role=eks_cluster_role.name,
)

ec2_role = iam.Role(
  "eks-main-nodegroup",
  assume_role_policy="""{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": "sts:AssumeRole",
        "Principal": {
          "Service": "ec2.amazonaws.com"
        },
        "Effect": "Allow",
        "Sid": ""
      }
    ]
  }""",
  tags={
    "Name": "eks-main-nodegroup",
  },
)

iam.RolePolicyAttachment(
  "eks-main-nodegroup-AmazonEKSWorkerNodePolicy",
  policy_arn="arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
  role=ec2_role.name,
)

iam.RolePolicyAttachment(
  "eks-main-nodegroup-AmazonEKS_CNI_Policy",
  policy_arn="arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
  role=ec2_role.name,
)

iam.RolePolicyAttachment(
  "eks-main-nodegroup-AmazonEC2ContainerRegistryReadOnly",
  policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
  role=ec2_role.name,
)
