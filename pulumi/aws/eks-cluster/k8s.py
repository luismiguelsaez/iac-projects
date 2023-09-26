from pulumi_kubernetes.yaml import ConfigFile, ConfigGroup
from pulumi_kubernetes import Provider
from pulumi import ResourceOptions
import pulumi
from os import path
import glob

def create_resource_from_file(name: str, file: str, depends_on: list = [], provider: Provider = Provider("k8s_default"))->ConfigFile:

  resource_options = ResourceOptions(provider=provider, depends_on=depends_on)
  resource = ConfigFile(
    name,
    file=file,
    opts=resource_options
  )
  return resource

def karpenter_templates(name: str, provider: Provider, manifests_path: str, eks_cluster_name: str, depends_on: list = []):

    def transform_manifest(obj, opts):
      sg_selector={
        f"kubernetes.io/cluster/{eks_cluster_name}": "owned"
      }

      subnet_selector={
          "karpenter.sh/discovery/private": eks_cluster_name
      }

      obj['spec']['securityGroupSelector'] = sg_selector
      obj['spec']['subnetSelector'] = subnet_selector

    files = [
      path.join(path.dirname("__file__"), file) for file in glob.glob(path.join(path.dirname("__file__"), manifests_path, "*.yaml"))
    ]

    resource_options = ResourceOptions(provider=provider, depends_on=depends_on)

    config_files = []
    for file in files:
      config_files.append(
        ConfigFile(
          name=path.basename(file),
          file=file,
          transformations=[transform_manifest],
          opts=resource_options
        )
      )

    #config_group = ConfigGroup(
    #  name=name,
    #  files=files,
    #  transformations=[
    #    transform_manifest
    #  ],
    #  opts=resource_options
    #)

    return config_files
