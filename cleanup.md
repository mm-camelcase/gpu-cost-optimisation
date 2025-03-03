## Teardown Guide

To delete all resources follow these steps:

### 1️⃣ Delete the GPU Node Groups

```sh
aws eks delete-nodegroup \
  --cluster-name ollama-cluster \
  --nodegroup-name gpu-spot-nodes \
  --region ${AWS_REGION}
```

```sh
aws eks delete-nodegroup \
  --cluster-name ollama-cluster \
  --nodegroup-name cpu-system-nodes \
  --region ${AWS_REGION}
```

### 2️⃣ Delete the EKS Cluster

```sh
aws eks delete-cluster \
  --name ollama-cluster \
  --region ${AWS_REGION}
```

### 3️⃣ Verify Deletion

Ensure all resources have been deleted:

```sh
aws eks list-clusters --region ${AWS_REGION}
aws eks list-nodegroups --cluster-name ollama-cluster --region ${AWS_REGION}
```

---

## 🚀 Cleanup Remaining AWS Resources After Deleting an EKS Cluster

When you delete an AWS EKS cluster, some resources may remain, such as **Classic Load Balancers (CLB), Security Groups, Elastic IPs, and Route53 records**. This guide helps you remove those remaining resources to avoid unnecessary charges.

---

### 🔥 Step 1: Delete the Classic Load Balancer

**Find the Load Balancer Name:**
```sh
aws elb describe-load-balancers --region ${AWS_REGION} --query "LoadBalancerDescriptions[*].LoadBalancerName"
```

**Delete the Load Balancer:**
```sh
aws elb delete-load-balancer --load-balancer-name a714d2d3e91ac41a0a598c84fb65e4e9 --region ${AWS_REGION}
```

**Verify Deletion:**
```sh
aws elb describe-load-balancers --region ${AWS_REGION} --query "LoadBalancerDescriptions[*].LoadBalancerName"
```
**Expected Output:** `[]` (empty array)

---

### 🔥 Step 2: Delete the Security Group

AWS won’t allow you to delete a security group **if it’s still in use**. First, find the security group ID:
```sh
aws ec2 describe-security-groups --filters Name=group-name,Values="Security group for Kubernetes ELB a714d2d3e91ac41a0a598c84fb65e4e9*" --query "SecurityGroups[*].GroupId" --region ${AWS_REGION}
```

If it returns something like:
```json
["sg-0abcd1234ef56789"]
```
First, check if any **Elastic Network Interfaces (ENI)** are using it:
```sh
aws ec2 describe-network-interfaces --filters Name=group-id,Values=sg-0abcd1234ef56789 --region ${AWS_REGION}
```
If no ENIs are using it, delete the security group:
```sh
aws ec2 delete-security-group --group-id sg-0abcd1234ef56789 --region ${AWS_REGION}
```

**Verify Deletion:**
```sh
aws ec2 describe-security-groups --region ${AWS_REGION} --query "SecurityGroups[*].GroupId"
```
**Expected Output:** Security group ID should not be listed.

---

### 🔥 Step 3: Check for Remaining Elastic IPs (Optional)

If an **Elastic IP (EIP)** was assigned to this Load Balancer, you might be getting billed for it. Run:
```sh
aws ec2 describe-addresses --region ${AWS_REGION}
```
If any **Elastic IPs** are listed but not in use, **release them**:
```sh
aws ec2 release-address --allocation-id eipalloc-1234567890abcdef0 --region ${AWS_REGION}
```

---

### 🔥 Step 4: Check for Route53 Records (Optional)

If you used **a custom domain** with Knative, check if **Route53 still has records pointing to the old Load Balancer**:
```sh
aws route53 list-hosted-zones --query "HostedZones[*].Name"
```
Find the hosted zone ID and delete the records manually.

---

### ✅ Final Cleanup Confirmation

Run these commands to confirm everything is removed:
```sh
aws elb describe-load-balancers --region ${AWS_REGION}  # Expected Output: []
aws ec2 describe-security-groups --region ${AWS_REGION}  # Security group should not be listed
aws ec2 describe-addresses --region ${AWS_REGION}  # Should not list unused Elastic IPs
```

---

🚀 **Now your AWS environment is fully cleaned up!** 🚀 If any resources are still stuck, verify dependencies using AWS Console or CLI logs.

