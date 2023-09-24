import pulumi
from pulumi_aws import athena

def create_database(name: str,bucket: pulumi.Output[str])->athena.Database:

    database = athena.Database(
        resource_name=name,
        bucket=bucket,
    )

    return database
