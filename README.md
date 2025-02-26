# GPU Cost Optimisation with CUDA MPS, and Knative Auto-Scaling

## **Overview**

This project demonstrates **cost-effective** ways to run GPU workloads on AWS without incurring excessive costs. By leveraging **CUDA Multi-Process Service (MPS), Knative auto-scaling, and Spot Instances**, we can efficiently share GPU resources across multiple workloads while **minimising expenses**.

## **Why This Project?**

High-performance GPUs like NVIDIA A100 or H100 can be **prohibitively expensive** when running AI workloads. This project shows how to:

- ✅ **Share a single GPU** between multiple AI models with **CUDA MPS**.
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
- **Auto-scale AI models to zero when idle using Knative Serving.**
- **Deploy two Ollama AI models that converse with each other on the same GPU.**

## **Setup Guide**

- divide this into 2

    - configure/setup gpu for workloads (watch v. again)
    - deploy ai

### **1️⃣ Set Environment Variables**

Before running the commands, set the required AWS environment variables:
```sh
export AWS_ACCOUNT_ID="966412459053"
export SUBNET_IDS="subnet-0bcd6d51,subnet-59f5923f"
export SECURITY_GROUP_IDS="sg-0643b1246dd531666"
export AWS_REGION="eu-west-1"
```

### **2️⃣ Deploy AWS EKS Cluster**

```sh
aws eks create-cluster --name ollama-cluster \
  --role-arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/EKSClusterRole \
  --resources-vpc-config subnetIds=${SUBNET_IDS},securityGroupIds=${SECURITY_GROUP_IDS} \
  --kubernetes-version 1.32 \
  --region ${AWS_REGION}
```

### **3️⃣ Deploy CPU Nodes for control plane**

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

### **4️⃣ Deploy GPU-enabled Spot Node Group**

#### was 
- ami-type BOTTLEROCKET_x86_64_NVIDIA     --> no nvidia-cuda-mps-control    
- ami-type AL2_x86_64_GPU       --> intermittent issues   
- ami-type AL2023_X86_64_NVIDIA  --> doesnt work with g4dn.xlarge



```sh
aws eks create-nodegroup \
  --cluster-name ollama-cluster \
  --nodegroup-name gpu-spot-nodes \
  --capacity-type SPOT \
  --instance-types g4dn.xlarge \
  --ami-type AL2_x86_64_GPU \
  --scaling-config minSize=0,maxSize=1,desiredSize=1 \
  --node-role arn:aws:iam::${AWS_ACCOUNT_ID}:role/EKSNodeRole \
  --subnets  ${SUBNET_IDS//,/ } \
  --region ${AWS_REGION} \
  --labels node-type=gpu \
  --taints key=nvidia.com/gpu,value=present,effect=NO_SCHEDULE
```

✅ **Spot Instances dramatically reduce GPU costs.**

1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣ 7️⃣ 8️⃣ 9️⃣ 🔟


### **5️⃣ Configure 

```sh
aws eks update-kubeconfig --region eu-west-1 --name ollama-cluster
```

### **5️⃣ Enable CUDA MPS for Shared GPU Usage**

- First, check if your GPU nodes support MPS by running:

```sh
nvidia-smi -q | grep "Compute Mode"
```

- If it returns "Default", you need to switch it to "Exclusive Process" for MPS to work:

```sh
sudo nvidia-smi -c EXCLUSIVE_PROCESS
```

- Enable the MPS Daemon in Your GPU Nodes

```sh
sudo nvidia-cuda-mps-control -d
```

To verify MPS is running:

```sh
sudo nvidia-cuda-mps-control -d
```

- it will return an  MPS daemon is running but no processes are using MPS yet.
- process list if processes are using MPS
- "Cannot find MPS control daemon process" if it is not running




```sh
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update

helm upgrade -i nvidia-device-plugin nvdp/nvidia-device-plugin \
  --namespace nvidia-device-plugin \
  --create-namespace \
  --version 0.17.0 \
  --set gfd.enabled=true \
  --values cuda-mps-values.yaml

# helm uninstall nvidia-device-plugin -n nvidia-device-plugin
```

### **5️⃣ Enable CUDA Time Slicing for Shared GPU Usage**

```sh
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update

helm upgrade -i nvidia-device-plugin nvdp/nvidia-device-plugin \
  --namespace nvidia-device-plugin \
  --create-namespace \
  --version 0.17.0 \
  --set gfd.enabled=true \
  --values cuda-time-slicing-values.yaml

# helm uninstall nvidia-device-plugin -n nvidia-device-plugin
```


✅ **Allows multiple AI models to share one GPU dynamically.**

### **6️⃣ Install Two separate Ollama instances**

```sh
helm repo add ollama-helm https://otwld.github.io/ollama-helm/
helm repo update

helm upgrade -i ollama-1 ollama-helm/ollama --namespace ollama --create-namespace --values ollama-1-values.yaml
helm upgrade -i ollama-2 ollama-helm/ollama --namespace ollama --create-namespace --values ollama-2-values.yaml

# helm uninstall ollama-1 --namespace ollama
# helm uninstall ollama-2 --namespace ollama
```

### **7️⃣ Confirm instances are using GPU**

- will do this during conversation
- exposed with lb


```sh
curl -X POST "http://aa98a66015f9741d28801c723d55e974-1392936248.eu-west-1.elb.amazonaws.com:11434/api/generate" \
     -H "Content-Type: application/json" \
     -d '{
           "model": "mistral",
           "prompt": "Tell me an interesting fact about space.",
           "stream": false
         }'
```


get instance idle

```sh
aws ssm describe-instance-information --region eu-west-1
```

jump to node

```sh
aws ssm start-session --target i-085380fe9f01932b9 --region eu-west-1
```

- can see processes on node

```sh
Every 2.0s: nvidia-smi                                                                                              Mon Feb 24 18:28:18 2025

Mon Feb 24 18:28:18 2025
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 550.144.03             Driver Version: 550.144.03     CUDA Version: 12.4     |
|-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  Tesla T4                       On  |   00000000:00:1E.0 Off |                    0 |
| N/A   36C    P0             32W /   70W |   13925MiB /  15360MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI        PID   Type   Process name                              GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|    0   N/A  N/A     36919      C   /usr/bin/ollama                              5562MiB |
|    0   N/A  N/A     37400      C   /usr/bin/ollama                              8360MiB |
+-----------------------------------------------------------------------------------------+
```






### **4️⃣ Deploy Two Ollama AI Models That Converse**

here are 2 ais chatting (plotting)

<!-- point `kubectl` at cluster

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
 -->

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

- ✅ Upgrade to **MIG on A100 GPUs (p4d.24xlarge)** for strict isolation (i.e. Partition a GPU into isolated instances using NVIDIA MIG).
- ✅ Optimise startup times with **Spot Instance auto-scaling**.
- 🔜 Introduce **real-time streaming responses**.
- 🔜 Deploy a third chatbot with a different AI model for more diversity.

## **Conclusion**

By leveraging **CUDA MPS, MIG, and Knative auto-scaling on Spot Instances**, this project successfully **runs AI workloads on AWS GPUs without causing bankruptcy**. This **minimises costs** while maintaining high performance, making GPU computing **accessible** and **efficient**.

---

Would you like **Terraform scripts** for automating deployment? 🚀

