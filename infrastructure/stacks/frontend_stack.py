from aws_cdk import (
    Stack,
    aws_s3,
    aws_iam,
    aws_cloudfront,
    aws_cloudfront_origins,
    aws_certificatemanager,
    CfnOutput,
    RemovalPolicy,
    Duration
)
from constructs import Construct
import os

class FrontendStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, root_domain_name: str, certificate_arn: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        www_domain_name = f"www.{root_domain_name}"

        frontend_bucket = aws_s3.Bucket(
            self, "FrontendBucket",
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            encryption=aws_s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True
        )

        cfn_origin_access_control = aws_cloudfront.CfnOriginAccessControl(
            self, "FrontendOAC",
            origin_access_control_config=aws_cloudfront.CfnOriginAccessControl.OriginAccessControlConfigProperty(
                name=f"OAC-{construct_id}",
                origin_access_control_origin_type="s3",
                signing_behavior="always",
                signing_protocol="sigv4",
                description="Origin Access Control for Frontend S3 Bucket"
            )
        )

        certificate = aws_certificatemanager.Certificate.from_certificate_arn(
            self, "SiteCertificate", certificate_arn=certificate_arn
        )

        distribution = aws_cloudfront.Distribution(
            self, "FrontendDistribution",
            default_behavior=aws_cloudfront.BehaviorOptions(
                origin=aws_cloudfront_origins.S3BucketOrigin(
                    frontend_bucket,
                    origin_access_control_id=cfn_origin_access_control.attr_id
                ),
                viewer_protocol_policy=aws_cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=aws_cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS
            ),
            domain_names=[root_domain_name, www_domain_name],
            certificate=certificate,
            minimum_protocol_version=aws_cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
            default_root_object="index.html",
            error_responses=[
                aws_cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(10)
                ),
                aws_cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(10)
                )
            ],
            comment=f"CloudFront distribution for {root_domain_name} and {www_domain_name}"
        )

        frontend_bucket.add_to_resource_policy(
            aws_iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[frontend_bucket.arn_for_objects("*")],
                principals=[aws_iam.ServicePrincipal("cloudfront.amazonaws.com")],
                conditions={
                    "StringEquals": {
                        "AWS:SourceArn": distribution.distribution_arn
                    }
                }
            )
        )

        CfnOutput(
            self, "FrontendBucketName",
            value=frontend_bucket.bucket_name,
            description="Name of the S3 bucket storing frontend assets"
        )

        CfnOutput(
            self, "DistributionId",
            value=distribution.distribution_id,
            description="ID of the CloudFront distribution"
        )

        CfnOutput(
            self, "DistributionDomainName",
            value=distribution.distribution_domain_name,
            description="Domain name of the CloudFront distribution (use for A records)"
        )
