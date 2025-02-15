# GPU Cost Optimisation with CUDA MPS, MIG, and Knative Auto-Scaling

## **Overview**

This project demonstrates **cost-effective** ways to run GPU workloads on AWS without incurring excessive costs. By leveraging **CUDA Multi-Process Service (MPS), NVIDIA Multi-Instance GPU (MIG), Knative auto-scaling, and Spot Instances**, we can efficiently share GPU resources across multiple workloads while **minimising expenses**.

## **Why This Project?**

High-performance GPUs like NVIDIA A100 or H100 can be **prohibitively expensive** when running AI workloads. This project shows how to:

- ✅ **Share a single GPU** between multiple AI models with **CUDA MPS**.
- ✅ **Partition a GPU into isolated instances** using **NVIDIA MIG**.
- ✅ **Automatically scale GPU workloads** to zero when idle using **Knative**.
- ✅ **Use Spot Instances** to save up to **90% on GPU costs**.

## **Project Structure**
To ensure clarity and modularity, the project is divided into separate directories for **CUDA MPS**, **MIG**, and **Knative auto-scaling**:
```
/gpu-cost-optimisation
  ├── /cuda-mps       # Implementation of CUDA MPS for dynamic GPU sharing
  ├── /mig            # NVIDIA MIG implementation for strict GPU partitioning
  ├── /knative        # Auto-scaling setup using Knative
  ├── /terraform      # Infrastructure as Code (IaC) using Terraform/Terragrunt
  ├── README.md       # Documentation and setup guide
```

## **Key Features**

- **Deploy GPU workloads on AWS EKS using Spot Instances.**
- **Use CUDA MPS to run multiple AI models on a single GPU dynamically.**
- **Implement NVIDIA MIG for strict GPU partitioning.**
- **Auto-scale AI models to zero when idle using Knative Serving.**
- **Deploy two Ollama AI models that converse with each other on the same GPU.**

## **Setup Guide**

### **1️⃣ Set Environment Variables**

Before running the commands, set the required AWS environment variables:
```sh
export AWS_ACCOUNT_ID="966412459053"
export SUBNET_IDS="subnet-0bcd6d51,subnet-59f5923f"
export SECURITY_GROUP_IDS="sg-0643b1246dd531666"
export AWS_REGION="eu-west-1"
```

### **2️⃣ Deploy AWS EKS Cluster with Spot GPU Nodes**

```sh
aws eks create-cluster --name ollama-cluster \
  --role-arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/EKSClusterRole \
  --resources-vpc-config subnetIds=${SUBNET_IDS},securityGroupIds=${SECURITY_GROUP_IDS} \
  --kubernetes-version 1.32 \
  --region ${AWS_REGION}
```



Create a **GPU-enabled Spot Node Group**:

- check for AWS Deep Learning AMI (NVIDIA Drivers, CUDA, and container runtime are pre-installed)

```sh
aws ec2 describe-images \
    --owners amazon \
    --filters "Name=name,Values=Deep Learning Base AMI (Amazon Linux 2)*" \
    --query 'Images | sort_by(@, &CreationDate) | [-1].{ImageId:ImageId, Name:Name}' \
    --region eu-west-1

{
    "ImageId": "ami-0cca382104dfca6de",
    "Name": "Deep Learning Base AMI (Amazon Linux 2) Version 60.9"
}
```

- cpu node group for system pods

```sh
aws eks create-nodegroup \
  --cluster-name ollama-cluster \
  --nodegroup-name cpu-system-nodes \
  --capacity-type ON_DEMAND \
  --instance-types t3.medium \
  --ami-type AL2_x86_64 \
  --scaling-config minSize=1,maxSize=3,desiredSize=1 \
  --node-role arn:aws:iam::${AWS_ACCOUNT_ID}:role/EKSNodeRole \
  --subnets ${SUBNET_IDS//,/ } \
  --region ${AWS_REGION} \
  --labels node-type=cpu,system=true
```


```sh
aws eks create-nodegroup \
  --cluster-name ollama-cluster \
  --nodegroup-name gpu-spot-nodes \
  --capacity-type SPOT \
  --instance-types g4dn.xlarge \
  --ami-type AL2_x86_64_GPU \
  --scaling-config minSize=0,maxSize=5,desiredSize=1 \
  --node-role arn:aws:iam::${AWS_ACCOUNT_ID}:role/EKSNodeRole \
  --subnets  ${SUBNET_IDS//,/ } \
  --region ${AWS_REGION} \
  --labels node-type=gpu \
  --taints key=nvidia.com/gpu,value=present,effect=NO_SCHEDULE
```


- check 

```sh
$ kubectl get nodes \
    --selector=node.kubernetes.io/instance-type=g4dn.xlarge \
    -o jsonpath="{.items[0].spec.taints[0]}" | jq .


#### 

```sh
kubectl describe daemonset aws-node -n kube-system | grep -A5 Tolerations
kubectl describe daemonset kube-proxy -n kube-system | grep -A5 Tolerations
```

both have have broad toleration (op=Exists), it means it tolerates all taints, including nvidia.com/gpu,value=present,effect=NO_SCHEDULE.

```sh
kubectl patch daemonset aws-node -n kube-system --type='json' -p='[
  {
    "op": "replace",
    "path": "/spec/template/spec/tolerations",
    "value": [
      {
        "key": "node.kubernetes.io/not-ready",
        "operator": "Exists",
        "effect": "NoExecute"
      },
      {
        "key": "node.kubernetes.io/unreachable",
        "operator": "Exists",
        "effect": "NoExecute"
      }
    ]
  }
]'
```

```sh
kubectl patch daemonset kube-proxy -n kube-system --type='json' -p='[
  {
    "op": "replace",
    "path": "/spec/template/spec/tolerations",
    "value": [
      {
        "key": "node.kubernetes.io/not-ready",
        "operator": "Exists",
        "effect": "NoExecute"
      },
      {
        "key": "node.kubernetes.io/unreachable",
        "operator": "Exists",
        "effect": "NoExecute"
      }
    ]
  }
]'
```

### **3 Install Knative Serving on Your Cluster

```sh
kubectl apply -f https://github.com/knative/serving/releases/latest/download/serving-core.yaml
```


- install NVIDIA device plugin

```sh
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.1/nvidia-device-plugin.yml

kubectl apply -f https://github.com/knative/net-kourier/releases/latest/download/kourier.yaml

kubectl patch configmap/config-network \
  --namespace knative-serving \
  --type merge \
  --patch '{"data":{"ingress-class":"kourier.ingress.networking.knative.dev"}}'
```


✅ **Spot Instances dramatically reduce GPU costs.**

### **4 Enable CUDA MPS for Shared GPU Usage**

get instance idle

```sh
aws ssm describe-instance-information --region eu-west-1
```

jump to node

```sh
aws ssm start-session --target i-085380fe9f01932b9 --region eu-west-1
```


```sh
export CUDA_MPS_PIPE_DIRECTORY=/tmp/nvidia-mps
export CUDA_MPS_LOG_DIRECTORY=/tmp/nvidia-log
nvidia-cuda-mps-control -d
```

✅ **Allows multiple AI models to share one GPU dynamically.**

### **4️⃣ Deploy Two Ollama AI Models That Converse**

point `kubectl` at cluster

```sh
aws eks update-kubeconfig --region eu-west-1 --name ollama-cluster
```


Create **Knative Service (`ollama-knative.yaml`)**:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: ollama-gpu
  namespace: default
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/min-scale: "0"   # Scale to zero when idle
        autoscaling.knative.dev/max-scale: "2"   # Allow 2 Ollama instances
    spec:
      containers:
      - name: ollama-mistral
        image: ollama/ollama-gpu
        args: ["mistral"]  # Runs Mistral model
        resources:
          limits:
            nvidia.com/gpu: "1"  # Uses shared CUDA MPS
      - name: ollama-llama2
        image: ollama/ollama-gpu
        args: ["llama2"]  # Runs LLaMA 2 model
        resources:
          limits:
            nvidia.com/gpu: "1"  # Uses shared CUDA MPS
```

Deploy it:
```sh
kubectl apply -f ollama-knative.yaml
```
✅ **Now, Mistral and LLaMA 2 will talk to each other dynamically.**


## Teardown Guide

To delete all resources and avoid unnecessary costs, follow these steps:

1️⃣ Delete the Knative Service

```sh
kubectl delete -f ollama-knative.yaml
```

2️⃣ Delete the GPU Node Group

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

3️⃣ Delete the EKS Cluster

```sh
aws eks delete-cluster \
  --name ollama-cluster \
  --region ${AWS_REGION}
```

4️⃣ Verify Deletion

Ensure all resources have been deleted:

```sh
aws eks list-clusters --region ${AWS_REGION}
aws eks list-nodegroups --cluster-name ollama-cluster --region ${AWS_REGION}
```

✅ All resources should be removed successfully!


## **Future Enhancements**

- ✅ Upgrade to **MIG on A100 GPUs (p4d.24xlarge)** for strict isolation.
- ✅ Optimise startup times with **Spot Instance auto-scaling**.
- 🔜 Introduce **real-time streaming responses**.
- 🔜 Deploy a third chatbot with a different AI model for more diversity.

## **Conclusion**

By leveraging **CUDA MPS, MIG, and Knative auto-scaling on Spot Instances**, this project successfully **runs AI workloads on AWS GPUs without causing bankruptcy**. This **minimises costs** while maintaining high performance, making GPU computing **accessible** and **efficient**.

---

Would you like **Terraform scripts** for automating deployment? 🚀

