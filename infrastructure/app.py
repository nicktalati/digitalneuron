import os
import aws_cdk as cdk
import dotenv

dotenv.load_dotenv()

from stacks.storage_stack import StorageStack
from stacks.backend_stack import BackendStack
from stacks.frontend_stack import FrontendStack


app = cdk.App()

aws_env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION")
)

root_domain_name = app.node.try_get_context("domain") or os.environ.get("ROOT_DOMAIN_NAME")
certificate_arn = app.node.try_get_context("cert_arn") or os.environ.get("CERTIFICATE_ARN")

if not root_domain_name:
    raise ValueError("root_domain_name must be provided.")
if not certificate_arn:
    raise ValueError("certificate_arn must be provided.")

storage_stack = StorageStack(
    app, "StorageStack",
    env=aws_env,
    root_domain_name=root_domain_name
)
backend_stack = BackendStack(
    app, "BackendStack",
    env=aws_env,
    tile_bucket=storage_stack.tile_bucket,
    root_domain_name=root_domain_name
)
frontend_stack = FrontendStack(
    app, "FrontendStack",
    env=aws_env,
    root_domain_name=root_domain_name,
    certificate_arn=certificate_arn
)

app.synth()
