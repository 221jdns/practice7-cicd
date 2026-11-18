import json, os, subprocess

def aws(*args):
    return json.loads(subprocess.check_output(['aws', *args, '--output', 'json']))

region=os.environ['AWS_REGION']
subject=os.environ['OIDC_SUB']
if ':environment:production' not in subject or not subject.startswith('repo:'):
    raise SystemExit('Use exact production environment sub from OIDC check')
account=aws('sts','get-caller-identity')['Account']
stack=aws('cloudformation','describe-stacks','--stack-name','p7-lab')['Stacks'][0]
o={x['OutputKey']:x['OutputValue'] for x in stack['Outputs']}
provider=f'arn:aws:iam::{account}:oidc-provider/token.actions.githubusercontent.com'
existing=aws('iam','list-open-id-connect-providers')['OpenIDConnectProviderList']
if not any(x['Arn']==provider for x in existing):
    aws('iam','create-open-id-connect-provider','--url','https://token.actions.githubusercontent.com','--client-id-list','sts.amazonaws.com')
else:
    detail=aws('iam','get-open-id-connect-provider','--open-id-connect-provider-arn',provider)
    if 'sts.amazonaws.com' not in detail['ClientIDList']:
        aws('iam','add-client-id-to-open-id-connect-provider','--open-id-connect-provider-arn',provider,'--client-id','sts.amazonaws.com')
trust={'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Federated':provider},'Action':'sts:AssumeRoleWithWebIdentity','Condition':{'StringEquals':{'token.actions.githubusercontent.com:aud':'sts.amazonaws.com','token.actions.githubusercontent.com:sub':subject}}}]}
role='p7-github-deploy'
roles=aws('iam','list-roles')['Roles']
if any(r['RoleName']==role for r in roles):
    raise SystemExit('Role p7-github-deploy exists. Review it in IAM; do not overwrite blindly.')
r=aws('iam','create-role','--role-name',role,'--assume-role-policy-document',json.dumps(trust))
def allow(actions,resource,condition=None):
    s={'Effect':'Allow','Action':actions,'Resource':resource}
    if condition: s['Condition']=condition
    return s
policy={'Version':'2012-10-17','Statement':[
    allow(['ecr:GetAuthorizationToken'],'*'),
    allow(['ecr:ListImages','ecr:BatchCheckLayerAvailability','ecr:InitiateLayerUpload','ecr:UploadLayerPart','ecr:CompleteLayerUpload','ecr:PutImage','ecr:BatchGetImage','ecr:GetDownloadUrlForLayer'],o['RepoArn']),
    allow(['cloudformation:DescribeStacks','cloudformation:CreateChangeSet','cloudformation:DescribeChangeSet','cloudformation:ExecuteChangeSet','cloudformation:DeleteChangeSet','cloudformation:GetTemplate','cloudformation:GetTemplateSummary','cloudformation:DescribeStackEvents'],stack['StackId']),
    allow(['ecs:RegisterTaskDefinition','ecs:DeregisterTaskDefinition','ecs:DescribeTaskDefinition','ecs:TagResource','ecs:UntagResource','ecs:ListTagsForResource'],'*'),
    allow(['ecs:UpdateService','ecs:DescribeServices'],o['ServiceArn']),
    allow(['iam:PassRole'],[o['TaskRoleArn'],o['ExecutionRoleArn']],{'StringEquals':{'iam:PassedToService':'ecs-tasks.amazonaws.com'}})
]}
aws('iam','put-role-policy','--role-name',role,'--policy-name','p7-update-app','--policy-document',json.dumps(policy))
open('github-trust.json','w').write(json.dumps(trust,indent=2))
open('github-permissions.json','w').write(json.dumps(policy,indent=2))
print('DEPLOY_ROLE_ARN='+r['Role']['Arn'])
print('Trust and permission policies saved locally for review/submission.')
