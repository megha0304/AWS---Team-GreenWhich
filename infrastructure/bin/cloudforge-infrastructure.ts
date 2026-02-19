#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { CloudForgeInfrastructureStack } from '../lib/cloudforge-infrastructure-stack';
import { CloudForgeComputeStack } from '../lib/cloudforge-compute-stack';
import { CloudForgeMonitoringStack } from '../lib/cloudforge-monitoring-stack';

const app = new cdk.App();

// Core infrastructure stack (DynamoDB, S3, IAM, Secrets Manager)
const infraStack = new CloudForgeInfrastructureStack(app, 'CloudForgeInfrastructureStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  description: 'CloudForge Bug Intelligence - Core Infrastructure',
});

// Compute resources stack (Lambda, ECS, VPC)
const computeStack = new CloudForgeComputeStack(app, 'CloudForgeComputeStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  description: 'CloudForge Bug Intelligence - Compute Resources',
  workflowsTableName: infraStack.workflowsTable.tableName,
  bugsTableName: infraStack.bugsTable.tableName,
  artifactsBucketName: infraStack.artifactsBucket.bucketName,
  apiSecretArn: infraStack.apiSecret.secretArn,
  apiLambdaRoleArn: infraStack.apiLambdaRole.roleArn,
  orchestratorTaskRoleArn: infraStack.orchestratorTaskRole.roleArn,
  testExecutionLambdaRoleArn: infraStack.testExecutionLambdaRole.roleArn,
  testExecutionTaskRoleArn: infraStack.testExecutionTaskRole.roleArn,
});

// Monitoring and alerting stack (CloudWatch, SNS)
new CloudForgeMonitoringStack(app, 'CloudForgeMonitoringStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  description: 'CloudForge Bug Intelligence - Monitoring and Alerting',
  workflowsTableName: infraStack.workflowsTable.tableName,
  bugsTableName: infraStack.bugsTable.tableName,
  apiFunctionName: computeStack.apiFunction.functionName,
  ecsClusterName: computeStack.ecsCluster.clusterName,
  alertEmail: process.env.ALERT_EMAIL, // Optional: set via environment variable
});

app.synth();
