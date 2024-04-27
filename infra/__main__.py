import pulumi 
import pulumi_aws as aws
import pulumi_awsx as awsx
import json

# Create an AWS resource (S3 Bucket)
bucket = aws.s3.Bucket("parsons")

# create ECR image repo and resource
ecr_repo = aws.ecr.Repository("ecr_repo",
    name="parsons",
    image_tag_mutability="MUTABLE",
    image_scanning_configuration=aws.ecr.RepositoryImageScanningConfigurationArgs(
        scan_on_push=True,
    ))
image_resource = awsx.ecr.Image("image_resource",
    repository_url=ecr_repo.url,
    builder_version=awsx.ecr.BuilderVersion.BUILDER_V1,
    context="../app")

# create IAM role
assume_role = aws.iam.get_policy_document(statements=[aws.iam.GetPolicyDocumentStatementArgs(
    effect="Allow",
    principals=[aws.iam.GetPolicyDocumentStatementPrincipalArgs(
        type="Service",
        identifiers=["lambda.amazonaws.com"],
    )],
    actions=["sts:AssumeRole"],
)])
lambda_role = aws.iam.Role("parsons_lambda_role",
    name="parsons_lambda_role",
    assume_role_policy=assume_role.json
    )
lambda_policy = aws.iam.get_policy_document(statements=[aws.iam.GetPolicyDocumentStatementArgs(
    effect="Allow",
    actions=["s3:*"],
    resources=[f"arn:aws:s3:::{bucket.id}",
               f"arn:aws:s3:::{bucket.id}/*"],
)])
lambda_policy_policy = aws.iam.Policy("policy",
    name="test-policy",
    description="A test policy",
    policy=lambda_policy.json)
lambda_attach = aws.iam.RolePolicyAttachment("lambda-attach",
                                           role=lambda_role.name,
                                           policy_arn=lambda_policy.arn)
lambda_fn = aws.lambda_.Function("parsons-lambda", 
                                 role=lambda_role.arn,
                                 image_uri=image_resource.uri,
                                 handler="main.handler")
# add api gateway

# Export the name of the bucket
pulumi.export("bucket_name", bucket.id)
pulumi.export("lambda_name", lambda_fn.id)
