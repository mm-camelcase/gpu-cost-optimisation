# GPU Cost Optimisation with CUDA MPS

## **Overview**

Kubernetes has become the de facto standard for managing all types of workloads, providing scalability, automation, and efficient resource management.

AI workloads perform significantly better on GPUs compared to CPUs, as GPUs are optimized for parallel processing, which is essential for deep learning and inference tasks.

To effectively utilize GPUs in Kubernetes, we need to perform three key tasks:

- **Provision GPU nodes**: Create nodes or node groups with GPU support in our EKS cluster.
- **Enable GPU access**: Install device plugins that allow pods to use specialized hardware features like GPUs.
- **Configure GPU usage in pods**: Ensure that workloads explicitly request and leverage GPU resources.

This project demonstrates **cost-effective** ways to run GPU workloads on AWS without incurring excessive costs. By leveraging **CUDA Multi-Process Service (MPS) and Spot Instances**, we can efficiently share GPU resources across multiple workloads while **minimising expenses**.

## **Why This Project?**

High-performance GPUs like NVIDIA A100 or H100 can be **prohibitively expensive** when running AI workloads. This project shows how to:

- ✅ **Share a single GPU** between multiple AI models with **CUDA**(Compute Unified Device Architecture).
- ✅ **Compare CUDA MPS and CUDA time slicing** for shared GPU usage.
- ✅ **Use Spot Instances** to save up to **90% on GPU costs**.

## **Project Structure**
```
/gpu-cost-optimisation
  ├── /cuda            # CUDA configs for dynamic GPU sharing
  ├── /olama           # Ollama AI model values configuration
  ├── /results         # Benchmark results and performance comparisons
  ├── /README.md       # Documentation and setup guide
```

## **Key Features**

- **Deploy GPU workloads on AWS EKS using Spot Instances.**
- **Use NVEDIA CUDA to run multiple AI models on a single GPU dynamically.**
- **Real-time monitoring of GPU usage with NVIDIA-SMI.**
- **Compare CUDA MPS vs. Time Slicing and observe performance differences.**


![Infrastructure](gpu-time-slicing.gif)
**Figure 1:** Two Ollama AI models ~~plotting~~ conversing with each other on the same GPU.



## **Setup Guide**

### **1️⃣ Provision GPU Nodes**

Ensure your environment is correctly set up before deployment:

todo: prec

```sh
export AWS_ACCOUNT_ID="<aws-acccount-id>"
export SUBNET_IDS="subnet-0bcd6d51,subnet-59f5923f"
export SECURITY_GROUP_IDS="sg-0643b1246dd531666"
export AWS_REGION="eu-west-1"
```

Deploy a standard AWS EKS Cluster:
```sh
aws eks create-cluster --name ollama-cluster \
  --role-arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/EKSClusterRole \
  --resources-vpc-config subnetIds=${SUBNET_IDS},securityGroupIds=${SECURITY_GROUP_IDS} \
  --kubernetes-version 1.32 \
  --region ${AWS_REGION}
```

Deploy CPU Nodes for Control Plane:

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
   

Deploy GPU-enabled Spot Node Group:
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

todo explain taints, lables, AL2_x86_64_GPU, g4dn.xlarge, spot (add/diss)

✅ **Spot Instances dramatically reduce GPU costs.**

### **2️⃣ Enable GPU Access**

To enable GPU access in Kubernetes, you need to install the NVIDIA K8s Device Plugin from:

👉 NVIDIA/k8s-device-plugin

**Why Do You Need This?**
- The NVIDIA GPU device plugin allows Kubernetes to detect and allocate GPUs to your workloads.
- Without this plugin, Kubernetes won’t recognize GPUs, even if your node has an NVIDIA GPU.
- Required for both CUDA MPS and Time-Slicing configurations.

There are two flavors of sharing available: Time-Slicing and MPS. Time-slicing and MPS are mutually exclusive.

#### **Enable CUDA Time Slicing for Shared GPU Usage**

```sh
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update

helm upgrade -i nvidia-device-plugin nvdp/nvidia.github.io/k8s-device-plugin \
  --namespace nvidia-device-plugin \
  --create-namespace \
  --version 0.17.0 \
  --set gfd.enabled=true \
  --values cuda/cuda-time-slicing-values.yaml
```

#### **Enable CUDA MPS for Shared GPU Usage**

- Jump to GPU Node using SSM:

```sh
aws ssm start-session --target $(aws ec2 describe-instances --region eu-west-1 \
  --filters "Name=instance-type,Values=g4dn.xlarge" "Name=instance-state-name,Values=running" \
  --query "Reservations[0].Instances[0].InstanceId" --output text) --region eu-west-1
```
- First, check if your GPU nodes support MPS by running:

```sh
nvidia-smi -q | grep "Compute Mode"
```

- If it returns ``Default``, you need to switch it to ``Exclusive Process`` for MPS to work:

```sh
sudo nvidia-smi -c EXCLUSIVE_PROCESS
sudo nvidia-cuda-mps-control -d
```

- Enable the MPS Daemon in Your GPU Nodes (todo: why)

```sh
sudo nvidia-cuda-mps-control -d
```

```sh
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update

helm upgrade -i nvidia-device-plugin nvdp/nvidia.github.io/k8s-device-plugin \
  --namespace nvidia-device-plugin \
  --create-namespace \
  --version 0.17.0 \
  --set gfd.enabled=true \
  --values cuda/cuda-mps-values.yaml
```

### **3️⃣ Configure GPU Usage in Pods**

Install Two Ollama AI Instances:
```sh
helm upgrade -i ollama-1 ollama-helm/ollama --namespace ollama --create-namespace --values olama/ollama-1-values.yaml
helm upgrade -i ollama-2 ollama-helm/ollama --namespace ollama --create-namespace --values olama/ollama-2-values.yaml
```

✅ **Allows multiple AI models to share one GPU dynamically.**
  - todo explain how  ollama pods request vGPUs

## **CUDA MPS vs. Time Slicing**

| Feature               | Time-Slicing                                 | MPS                                          |
|---------------------- |------------------------------------------- |--------------------------------------------- |
| **Process Switching** | Alternates (one at a time)                 | Runs concurrently                            |
| **GPU Utilization**   | Spikes (100% → 0%)                         | Steady (e.g., 50%)                          |
| **Total Utilization** | ~100% but fluctuates                       | ~100% and stable                            |
| **Latency**          | Higher (switching overhead)                 | Lower                                       |
| **Best For**         | Large independent workloads                 | Smaller, parallel workloads                 |
| **Memory Sharing**   | ❌ No                                        | ✅ Yes (some overlap)                        |
| **Memory Efficiency**| 🟡 Medium                                   | 🟢 High                                     |
| **Total Memory Usage** | Sum of all processes                     | Slightly less than the sum                  |
| **Risk of Starvation** | ❌ No                                      | ⚠️ Possible if not managed                  |

## **Visual Demonstrations**

We have included **animated GIFs** showcasing the performance of both CUDA MPS and time slicing.

- **CUDA MPS in Action**: Two Ollama AI models interacting with **real-time GPU utilization shown via NVIDIA-SMI.**
- **Time Slicing in Action**: The same AI models, but scheduled sequentially, demonstrating latency differences.

## **Teardown Guide**

To delete all resources:
```sh
aws eks delete-nodegroup --cluster-name ollama-cluster --nodegroup-name gpu-spot-nodes --region ${AWS_REGION}
aws eks delete-cluster --name ollama-cluster --region ${AWS_REGION}
```

✅ **All resources should be removed successfully!**

## **Future Enhancements**

- ✅ **Introduce MIG on A100 GPUs** for strict isolation.
  - todo mention CUDA is a software solution , MIG is a hardware solotion
- ✅ **Enhance auto-scaling with Knative** (moved from core implementation).
- ✅ **Compare additional GPU-sharing strategies**.
- 🔜 **Integrate cost monitoring tools**.

## **Conclusion**

This project successfully demonstrates **how CUDA MPS and time slicing impact GPU cost optimization** without relying on expensive deployments. By using Spot Instances and efficient GPU-sharing techniques, AI workloads can run **at a fraction of the cost**.

---

🚀 Would you like to see more benchmarks? Let us know!


## **TODO**
-  mention in this case weuse aws but...
- links to https://github.com/NVIDIA/k8s-device-plugin

