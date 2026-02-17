import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { CloudForgeInfrastructureStack } from '../lib/cloudforge-infrastructure-stack';

describe('CloudForgeInfrastructureStack', () => {
  test('Stack creates successfully', () => {
    const app = new cdk.App();
    const stack = new CloudForgeInfrastructureStack(app, 'TestStack');
    const template = Template.fromStack(stack);

    // Basic smoke test - will be expanded in task 18
    expect(template).toBeDefined();
  });
});
