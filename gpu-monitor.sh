#!/bin/bash

# Set AWS region and instance type
AWS_REGION="eu-west-1"
INSTANCE_TYPE="g4dn.xlarge"

# Function to handle Ctrl + C
cleanup() {
    echo -e "\nDetected Ctrl + C. Exiting session..."
    exit 0
}
trap cleanup SIGINT  # Trap Ctrl + C and call cleanup()

# Find the GPU instance of the specified type that is running
INSTANCE_ID=$(aws ec2 describe-instances --region "$AWS_REGION" \
  --filters "Name=instance-type,Values=$INSTANCE_TYPE" "Name=instance-state-name,Values=running" \
  --query "Reservations[].Instances[].InstanceId" --output text)

# Check if an instance was found
if [ -n "$INSTANCE_ID" ]; then
  echo "Starting session on GPU instance ($INSTANCE_TYPE): $INSTANCE_ID"
  
  # Start the SSM session and run 'watch nvidia-smi' every second
  aws ssm start-session --target "$INSTANCE_ID" --region "$AWS_REGION" --document-name AWS-StartInteractiveCommand --parameters 'command=["watch -n 1 nvidia-smi"]'
else
  echo "No GPU instance of type $INSTANCE_TYPE found!"
  exit 1
fi
