#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { CloudForgeInfrastructureStack } from '../lib/cloudforge-infrastructure-stack';

const app = new cdk.App();

new CloudForgeInfrastructureStack(app, 'CloudForgeInfrastructureStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  description: 'CloudForge Bug Intelligence - Core Infrastructure',
});

app.synth();
