import pulumi
import json
import pulumi_aws as aws

example_role = aws.iam.Role("pulumi-pipe-execution-role",
    path="/",
    assume_role_policy=json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "pipes.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
            # "Condition": {
            #     "StringEquals": {
            #         "aws:SourceArn": "arn:aws:pipes:us-east-1:588025306866:pipe/*",
            #         "aws:SourceAccount": "588025306866"
            #     }
            # }
        }
    ]
})
)

policy1 = aws.iam.Policy("policy1-lambda",
    path="/",
    policy=json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": [
                "arn:aws:lambda:us-east-1:588025306866:function:*"
            ]
        }
    ]
}))

policy2 = aws.iam.Policy("policy2-sqs",
    path="/",
    policy=json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage",
                "sqs:GetQueueAttributes"
            ],
            "Resource": [
                "arn:aws:sqs:us-east-1:588025306866:*"
            ]
        }
    ]
}))

cloudformation_role_policy_attachment = aws.iam.RolePolicyAttachment('pulumi-cloudformation-full-access',
    role=example_role.id,
    policy_arn='arn:aws:iam::aws:policy/AWSCloudFormationFullAccess')

role_policy_attachment = aws.iam.RolePolicyAttachment('policy1-attachment',
    role=example_role.id,
    policy_arn=policy1.arn,
)
role_policy_attachment = aws.iam.RolePolicyAttachment('policy2-attachment',
    role=example_role.id,
    policy_arn=policy2.arn,
)
role_policy_attachment = aws.iam.RolePolicyAttachment('policy3-attachment',
    role=example_role.id,
    policy_arn="arn:aws:iam::aws:policy/AdministratorAccess",)
####creatung SQS

queue = aws.sqs.Queue("sqs-7april-pulumi",
    content_based_deduplication=True,
    fifo_queue= True)

###### Role and policy for lambda function

lambda_role = aws.iam.Role("pulumi-lambda-role",
    path="/",
    assume_role_policy=json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
})
)

sqs_role_policy_attachment = aws.iam.RolePolicyAttachment('pulumi-sqs-full-access',
    role=lambda_role.id,
    policy_arn='arn:aws:iam::aws:policy/AmazonSQSFullAccess')

cloudwatch_role_policy_attachment = aws.iam.RolePolicyAttachment('pulumi-cloudwatch-full-access',
    role=lambda_role.id,
    policy_arn='arn:aws:iam::aws:policy/CloudWatchFullAccess')

eventbridge_role_policy_attachment = aws.iam.RolePolicyAttachment('pulumi-eventbridge-full-access',
    role=lambda_role.id,
    policy_arn='arn:aws:iam::aws:policy/AmazonEventBridgePipesFullAccess')

##### Lambda Layer version creation

lambda_layer = aws.lambda_.LayerVersion("lambdaLayer",
    compatible_runtimes=["python3.9"],
    compatible_architectures=["x86_64"],
    code=pulumi.FileArchive("requirement.zip"),
    layer_name="lambda_layer_name")

##### Lambda Function Creation

test_lambda = aws.lambda_.Function("testLambda",role=lambda_role.arn , code='lambda_code.zip', handler='lambda_code.lambda_handler', runtime='python3.9', layers= [lambda_layer.arn] , opts=pulumi.ResourceOptions(depends_on=[
        sqs_role_policy_attachment,
        cloudwatch_role_policy_attachment,
        eventbridge_role_policy_attachment,
        lambda_role
    ]))

### role for cloudformation to access eventbridge pipe

stack_pipe_role = aws.iam.Role("pulumi-stack_pipe-execution-role",
    path="/",
    assume_role_policy=json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudformation.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
})
)

pipe_role_policy_attachment = aws.iam.RolePolicyAttachment('pulumi-eventbridge_pipe-full-access',
    role=stack_pipe_role.id,
    policy_arn='arn:aws:iam::aws:policy/AmazonEventBridgeFullAccess')
role_policy_attachment = aws.iam.RolePolicyAttachment('policy4-attachment',
    role=stack_pipe_role.id,
    policy_arn="arn:aws:iam::aws:policy/AdministratorAccess",)

### cloudformation code ####

network = aws.cloudformation.Stack (resource_name = "network", iam_role_arn= stack_pipe_role.arn,
   parameters = {
    'RoleArn'   : example_role.arn,
    'SourceArn' : queue.arn,
    'TargetArn' : test_lambda.arn,
  },

  template_body = json.dumps({
    "Parameters" : {
      "SourceArn" : {
        "Type" : "String",
      },
      "TargetArn" : {
        "Type" : "String",
      },
      "RoleArn" : {
        "Type" : "String"
      },
    },
    "Resources" : {
      "TestPipe" : {
        "Type" : "AWS::Pipes::Pipe",
        "Properties" : {
          "Name" : "Pipe",
          "RoleArn" : { "Ref" : "RoleArn" },
          "Source" : { "Ref" : "SourceArn" },
          "Target" : { "Ref" : "TargetArn" },
        }
      }
    }
  }
  ))
