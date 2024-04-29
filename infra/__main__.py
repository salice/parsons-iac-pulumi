import pulumi 
import pulumi_aws as aws
import pulumi_awsx as awsx

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
##
## API Gateway REST API (API Gateway V1 / original)
##    /{proxy+} - passes all requests through to the lambda function
##
####################################################################

# Create a single Swagger spec route handler for a Lambda function.
def swagger_route_handler(arn):
    return ({
        "x-amazon-apigateway-any-method": {
            "x-amazon-apigateway-integration": {
                "uri": pulumi.Output.format('arn:aws:apigateway:{0}:lambda:path/2015-03-31/functions/{1}/invocations', "us-west-2", arn),
                "passthroughBehavior": "when_no_match",
                "httpMethod": "POST",
                "type": "aws_proxy",
            },
        },
    })

# Create the API Gateway Rest API, using a swagger spec.
rest_api = aws.apigateway.RestApi("api",
    body=pulumi.Output.json_dumps({
        "swagger": "2.0",
        "info": {"title": "api", "version": "1.0"},
        "paths": {
            "/{proxy+}": swagger_route_handler(lambda_fn.arn),
        },
    }))

# Create a deployment of the Rest API.
deployment = aws.apigateway.Deployment("api-deployment",
    rest_api=rest_api.id,
    # Note: Set to empty to avoid creating an implicit stage, we'll create it
    # explicitly below instead.
    stage_name="",
)

# Create a stage, which is an addressable instance of the Rest API. Set it to point at the latest deployment.
stage = aws.apigateway.Stage("api-stage",
    rest_api=rest_api.id,
    deployment=deployment.id,
    stage_name="wiki-random",
)

# Give permissions from API Gateway to invoke the Lambda
rest_invoke_permission = aws.lambda_.Permission("api-rest-lambda-permission",
    action="lambda:invokeFunction",
    function=lambda_fn.name,
    principal="apigateway.amazonaws.com",
    source_arn=deployment.execution_arn.apply(lambda arn: arn + "*/*"),
)

#########################################################################
# Create an HTTP API and attach the lambda function to it
##    /{proxy+} - passes all requests through to the lambda function
##
#########################################################################

http_endpoint = aws.apigatewayv2.Api("http-api-pulumi-wiki",
    protocol_type="HTTP"
)

http_lambda_backend = aws.apigatewayv2.Integration("wiki-integration",
    api_id=http_endpoint.id,
    integration_type="AWS_PROXY",
    connection_type="INTERNET",
    description="Lambda example",
    integration_method="POST",
    integration_uri=lambda_fn.arn,
    passthrough_behavior="WHEN_NO_MATCH"
)

url = http_lambda_backend.integration_uri

http_route = aws.apigatewayv2.Route("wiki-route",
    api_id=http_endpoint.id,
    route_key="ANY /{proxy+}",
    target=http_lambda_backend.id.apply(lambda targetUrl: "integrations/" + targetUrl)
)

http_stage = aws.apigatewayv2.Stage("wiki-stage",
    api_id=http_endpoint.id,
    route_settings= [
        {
            "route_key": http_route.route_key,
            "throttling_burst_limit": 1,
            "throttling_rate_limit": 0.5,
        }
    ],
    auto_deploy=True
)

# Give permissions from API Gateway to invoke the Lambda
http_invoke_permission = aws.lambda_.Permission("api-http-lambda-permission",
    action="lambda:invokeFunction",
    function=lambda_fn.name,
    principal="apigateway.amazonaws.com",
    source_arn=http_endpoint.execution_arn.apply(lambda arn: arn + "*/*"),
)

# Export the name of the bucket, lambda, rest endpoints
pulumi.export("bucket_name", bucket.id)
pulumi.export("lambda_name", lambda_fn.id)
pulumi.export("apigateway-rest-endpoint", deployment.invoke_url.apply(lambda url: url + "wiki-random" + '/{proxy+}'))
pulumi.export("apigatewayv2-http-endpoint", pulumi.Output.all(http_endpoint.api_endpoint, http_stage.name).apply(lambda values: values[0] + '/' + values[1] + '/'))
