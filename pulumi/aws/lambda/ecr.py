from pulumi_aws import get_caller_identity

aws_account_id = get_caller_identity().account_id

repository_policy = {
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCrossAccountRO",
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Condition": {
        "StringLike": {
          "aws:PrincipalArn": [
            f"arn:aws:iam::{aws_account_id}:role/k8s-cluster-ecr-ro",
          ]
        }
      }
    },
    {
      "Sid": "AllowCrossAccountRW",
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:BatchGetImage",
        "ecr:CompleteLayerUpload",
        "ecr:GetDownloadUrlForLayer",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart"
      ],
      "Condition": {
        "StringLike": {
          "aws:PrincipalArn": [
            f"arn:aws:iam::{aws_account_id}:role/jenkins-ecr-rw",
            f"arn:aws:iam::{aws_account_id}:role/github-actions-ecr-rw",
          ]
        }
      }
    }
  ]
}

lifecycle_policy = {
  "rules": [
    {
      "rulePriority": 1,
      "description": "Expire images older than 14 days",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 14
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
