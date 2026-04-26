import boto3
import os

ec2 = boto3.client('ec2')
elbv2 = boto3.client('elbv2')

def lambda_handler(event, context):
    # --- PASTE YOUR SPECIFIC IDs HERE ---
    AMI_ID = '' #Get your configured AMI ID
    TARGET_GROUP_ARN = '' #Get from the ALB being used
    SECURITY_GROUP = '' # Get this from your EC2 instance details
    SUBNET_ID = ''          # Get this from your EC2 instance details

    try:
        print("Threat detected! Launching backup EC2 instance...")
        
        # 1. Boot the new clone server
        run_response = ec2.run_instances(
            ImageId=AMI_ID,
            InstanceType='t3.micro', 
            MinCount=1, MaxCount=1,
            SubnetId=SUBNET_ID,
            SecurityGroupIds=[SECURITY_GROUP],
            IamInstanceProfile={'Name': 'EC2-SSM-Role'},
            TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': 'ML-Auto-Scaled-Backup'}]}]
        )
        
        new_instance_id = run_response['Instances'][0]['InstanceId']
        print(f"Successfully launched clone: {new_instance_id}")
        
        # --- THE FIX: WAIT FOR SERVER TO BOOT ---
        print("Waiting for the server hardware to turn on...")
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[new_instance_id])
        print("Server is now running! Wiring to Load Balancer...")
        
        # 2. Wire it into the Load Balancer
        elbv2.register_targets(
            TargetGroupArn=TARGET_GROUP_ARN,
            Targets=[{'Id': new_instance_id}]
        )
        
        return {'statusCode': 200, 'body': f"Success! Launched and registered {new_instance_id}"}
        
    except Exception as e:
        return {'statusCode': 500, 'body': str(e)}
   