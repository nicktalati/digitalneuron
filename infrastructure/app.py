import os
import aws_cdk as cdk
import dotenv

dotenv.load_dotenv()

from stacks.frontend_stack import FrontendStack


app = cdk.App()
stack_name = app.node.try_get_context("stack_name") or "DigitalNeuronFrontendStack"
aws_env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION")
)

FrontendStack(app, "FrontendStack", env=aws_env)

app.synth()
