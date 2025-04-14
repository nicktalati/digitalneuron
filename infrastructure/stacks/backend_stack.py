from aws_cdk import (
    Stack,
    aws_lambda,
    aws_apigatewayv2,
    aws_apigatewayv2_integrations,
    aws_iam,
    aws_s3,
    aws_logs,
    Duration,
    CfnOutput,
    RemovalPolicy
)
from constructs import Construct
import os


class BackendStack(Stack):
    @property
    def api_gateway_url(self) -> str:
        return self._api_gateway_url

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        tile_bucket: aws_s3.IBucket,
        root_domain_name: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        if not tile_bucket:
            raise ValueError("tile_bucket must be provided to BackendStack.")

        self._tile_bucket = tile_bucket
        www_domain_name = f"www.{root_domain_name}"

        tile_api_function = aws_lambda.Function(
            self, "TileApiFunction",
            code=aws_lambda.Code.from_asset_image(
                directory=os.path.join(os.path.dirname(__file__), "../../backend")
            ),
            handler=aws_lambda.Handler.FROM_IMAGE,
            runtime=aws_lambda.Runtime.FROM_IMAGE,
            memory_size=256,
            timeout=Duration.seconds(30),
            environment={
                "TILE_BUCKET_NAME": self._tile_bucket.bucket_name
            },
            log_retention=aws_logs.RetentionDays.ONE_MONTH,
            description="Lambda function for Digital Neuron Tile API"
        )

        self._tile_bucket.grant_read(tile_api_function)

        http_api = aws_apigatewayv2.HttpApi(
            self, "TileHttpApi",
            description="HTTP API Gateway for Digital Neuron Tile API",
            default_integration=aws_apigatewayv2_integrations.HttpLambdaIntegration(
                "TileApiIntegration",
                handler=tile_api_function
            ),
            cors_preflight=aws_apigatewayv2.CorsPreflightOptions(
                allow_origins=[
                    "http://localhost:8000",
                    "http://127.0.0.1:8000",
                    f"https://{root_domain_name}",
                    f"https://{www_domain_name}"
                ],
                allow_methods=[aws_apigatewayv2.CorsHttpMethod.GET, aws_apigatewayv2.CorsHttpMethod.OPTIONS],
                allow_headers=[
                    "Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key",
                    "X-Amz-Security-Token", "Accept"
                ],
                max_age=Duration.days(1)
            )
        )

        self._api_gateway_url = http_api.api_endpoint

        CfnOutput(
            self, "ApiEndpointUrl",
            value=self._api_gateway_url,
            description="URL of the deployed API Gateway endpoint"
        )
