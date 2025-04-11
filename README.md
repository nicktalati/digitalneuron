# DigitalNeuron

An interactive, open-source 3D visualization of a neuron, focusing on exploring the membrane surface and its components.

Before you begin, ensure you have the following installed and configured:

1.  **Git:** For cloning the repository.
2.  **Python:** Version **3.10.11**. We recommend using [`pyenv`](https://github.com/pyenv/pyenv) to manage Python versions. This repository includes a `.python-version` file.
3.  **Node.js:** Version **LTS/Jod (v22.x)**. We recommend using [`nvm`](https://github.com/nvm-sh/nvm) to manage Node.js versions. This repository includes a `.nvmrc` file.
4.  **NPM:** Version 10.x or higher (usually comes bundled with the correct Node.js version).
5.  **AWS CLI:** Installed and configured with AWS credentials that have permissions to deploy the necessary resources (S3, CloudFront, Lambda, API Gateway, IAM, etc.). ([Configure AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html))
6.  **AWS CDK Toolkit:** Install globally via npm: `npm install -g aws-cdk`

## Development Setup

1.  **Clone the repository:**
    ```bash
    git clone git@github.com:nicktalati/digitalneuron
    cd digitalneuron
    ```

2.  **Set up Python Environment:**
    *   If using `pyenv`, it should automatically pick up the version from `.python-version` when you `cd` into the directory (or run `pyenv install 3.10.11` if needed).
    *   Create and activate a virtual environment for the infrastructure code:
        ```bash
        cd infrastructure
        python -m venv .venv
        source .venv/bin/activate  # On Linux/macOS
        # .venv\Scripts\activate.bat # On Windows
        ```
    *   Install Python dependencies for CDK:
        ```bash
        pip install -r requirements.txt
        ```
    *   *(Note: Repeat venv setup for `backend` and `asset_pipeline` directories later)*
    *   `cd ..` # Return to root directory

3.  **Set up Node.js Environment:**
    *   If using `nvm`, run `nvm use` in the root directory. It will read the `.nvmrc` file and switch to the correct Node.js version (run `nvm install` first if needed).

## Infrastructure Deployment (Initial Frontend Stack)

This project uses AWS CDK (Python) to define and deploy cloud infrastructure.

**Warning:** Deploying AWS resources will incur costs. Remember to destroy stacks when not in use (`cdk destroy StackName`) and set up AWS Budget alerts.

1.  **Prerequisites:**
    *   Ensure you have configured AWS credentials.
    *   **Obtain an ACM Certificate:** You need a validated AWS Certificate Manager (ACM) certificate in the **`us-east-1`** region that covers both your root domain (e.g., `digitalneuron.org`) and the `www` subdomain (e.g., `www.digitalneuron.org`). Note down the ARN of this certificate.
    *   **Have your root domain name ready.**

2.  **Bootstrap CDK (If first time in account/region):**
    ```bash
    cd infrastructure
    cdk bootstrap --profile PROFILE
    ```

3.  **Deploy the Frontend Stack:**
    Deploy the `FrontendStack` which creates the S3 bucket for website assets and the CloudFront distribution. Pass your domain name and certificate ARN as context parameters:
    ```bash
    # Replace with your actual root domain and certificate ARN
    cdk deploy FrontendStack -c domain="yourdomain.org" -c cert_arn="arn:aws:acm:us-east-1:ACCOUNT-NUMBER:certificate/your-cert-id"
    ```
    *(Note: `DigitalNeuronFrontendStack` is the default name used in `app.py`, adjust if you changed it)*

4.  **Post-Deployment Steps:**
    *   **DNS Configuration:** After deployment, CDK will output the `DistributionDomainName` (e.g., `d123xyz.cloudfront.net`). Go to your DNS provider and create two records:
        *   An `A ALIAS` or `CNAME` record for your root domain (`yourdomain.org`) pointing to the `DistributionDomainName`.
        *   A `CNAME` record for your `www` domain (`www.yourdomain.org`) pointing to the `DistributionDomainName`.
    *   **Upload Frontend Assets:** Once you have built your frontend code (HTML, CSS, JS), upload the contents of your build directory to the S3 bucket created by CDK (the bucket name is also a CDK output). Example using AWS CLI:
        ```bash
        aws s3 sync path/to/your/frontend/build/ s3://YOUR-FRONTEND-BUCKET-NAME --delete
        ```
