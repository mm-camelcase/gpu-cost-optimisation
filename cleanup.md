# 🚀 Cleanup Leftover AWS Resources After Deleting an EKS Cluster

When you delete an AWS EKS cluster, some resources may remain, such as **Classic Load Balancers (CLB), Security Groups, Elastic IPs, and Route53 records**. This guide helps you remove those leftover resources to avoid unnecessary charges.

---

## **🔥 Step 1: Delete the Leftover Load Balancer**
The **Classic Load Balancer (CLB)** was left behind because Kubernetes services (like **Knative Kourier**) created it, but it wasn’t deleted with the cluster.

Run the following command to delete it:
```sh
aws elb delete-load-balancer --load-balancer-name a714d2d3e91ac41a0a598c84fb65e4e9 --region ${AWS_REGION}
```

Confirm deletion:
```sh
aws elb describe-load-balancers --region ${AWS_REGION} | grep a714d2d3e91ac41a0a598c84fb65e4e9
```
If nothing is returned, it’s successfully deleted.

---

## **🔥 Step 2: Delete the Leftover Security Group**
AWS won’t allow you to delete a security group **if it’s still in use**. First, find the security group ID:
```sh
aws ec2 describe-security-groups --filters Name=group-name,Values="Security group for Kubernetes ELB a714d2d3e91ac41a0a598c84fb65e4e9*" --query "SecurityGroups[*].GroupId" --region ${AWS_REGION}
```

If it returns something like:
```json
["sg-0abcd1234ef56789"]
```
Delete the security group:
```sh
aws ec2 delete-security-group --group-id sg-0abcd1234ef56789 --region ${AWS_REGION}
```

Confirm deletion:
```sh
aws ec2 describe-security-groups --region ${AWS_REGION} | grep sg-0abcd1234ef56789
```
If nothing is returned, it’s successfully deleted.

---

## **🔥 Step 3: Check for Leftover Elastic IPs (Optional)**
If an **Elastic IP (EIP)** was assigned to this Load Balancer, you might be getting billed for it. Run:
```sh
aws ec2 describe-addresses --region ${AWS_REGION}
```
If any **Elastic IPs** are listed but not in use, **release them**:
```sh
aws ec2 release-address --allocation-id eipalloc-1234567890abcdef0 --region ${AWS_REGION}
```

---

## **🔥 Step 4: Check for Leftover Route53 Records (Optional)**
If you used **a custom domain** with Knative, check if **Route53 still has records pointing to the old Load Balancer**:
```sh
aws route53 list-hosted-zones --query "HostedZones[*].Name"
```
Find the hosted zone ID and delete the records manually.

---

## **✅ Final Cleanup Confirmation**
Run these commands to confirm everything is removed:
```sh
aws elb describe-load-balancers --region ${AWS_REGION}  # Should return nothing
aws ec2 describe-security-groups --region ${AWS_REGION}  # Should not list the ELB security group
aws ec2 describe-addresses --region ${AWS_REGION}  # Should not list unused Elastic IPs
```

---

🚀 **Now your AWS environment is fully cleaned up!** 🚀 If any resources are still stuck, verify dependencies using AWS Console or CLI logs.

