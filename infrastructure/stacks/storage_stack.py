from aws_cdk import (
    Stack,
    aws_s3,
    CfnOutput,
    RemovalPolicy
)
from constructs import Construct
import os

class StorageStack(Stack):
    @property
    def tile_bucket(self) -> aws_s3.IBucket:
        return self._tile_bucket

    def __init__(self, scope: Construct, construct_id: str, root_domain_name, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        www_domain_name = f"www.{root_domain_name}"

        self._tile_bucket = aws_s3.Bucket(
            self, "TileBucket",
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            encryption=aws_s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=False,
            cors=[
                aws_s3.CorsRule(
                    allowed_origins=[
                        "http://localhost:8000",
                        "http://127.0.0.1:8000",
                        f"https://{root_domain_name}",
                        f"https://{www_domain_name}"
                    ],
                    allowed_methods=[aws_s3.HttpMethods.GET],
                    allowed_headers=["*"]
                )
            ]
        )

        CfnOutput(
            self, "TileBucketName",
            value=self._tile_bucket.bucket_name,
            description="Name of the S3 bucket storing processed mesh tiles (.glb)"
        )

        CfnOutput(
            self, "TileBucketArn",
            value=self._tile_bucket.bucket_arn,
            description="ARN of the S3 bucket storing processed mesh tiles"
        )
