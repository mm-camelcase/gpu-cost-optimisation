# GPU Cost Optimisation with CUDA MPS

## **Overview**

**Kubernetes** has become the **de facto standard** for managing all types of workloads, providing scalability, automation, and efficient resource management.

**AI workloads** perform significantly better on **GPUs** compared to CPUs, as GPUs are optimized for parallel processing, which is essential for deep learning and inference tasks.

To effectively utilize **GPUs** in **Kubernetes**, we need to perform three key tasks:

- 1️⃣ **Provision GPU nodes**: Create nodes or node groups with **GPU support** in our **K8S Cluster**.
- 2️⃣ **Enable GPU access**: Install device plugins that allow pods to use specialized hardware features like GPUs.
- 3️⃣ **Configure GPU usage in pods**: Ensure that workloads explicitly request and leverage GPU resources.

This project demonstrates cost-effective ways to run GPU workloads, using AWS in this case, but these methods can be applied to any cloud provider. By leveraging **NVIDIA device plugin** for **Kubernetes's GPU sharing features**, we can efficiently share GPU resources across multiple workloads while **minimising expenses**.

## **Why This Project?**

High-performance GPUs like **NVIDIA A100** or **H100** can be **prohibitively expensive** when running AI workloads. This project shows how to:

- ✅ **Share a single GPU** between multiple AI models with **CUDA**(Compute Unified Device Architecture).
- ✅ Compare **CUDA MPS** and **CUDA Time Slicing** for shared GPU usage.
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

- Deploy **GPU workloads** on **AWS EKS** using **Spot Instances**.
- Use **NVEDIA CUDA** to run **multiple AI models** on a **single GPU** dynamically.
- Real-time **monitoring** of GPU usage with **NVIDIA-SMI**.
- Compare **CUDA MPS vs. Time Slicing** and observe performance differences.


![Infrastructure](gpu-time-slicing.gif)
**Figure 1:** Two Ollama AI models ~~plotting~~ conversing with each other on the same GPU.



## **Setup Guide**

### **1️⃣ Provision GPU Nodes**

#### **Step 1: Set Up Required Environment Variables**

Before deploying the cluster, set the following environment variables:

```sh
export AWS_ACCOUNT_ID="<aws-acccount-id>"
export SUBNET_IDS="subnet-0bcd6d51,subnet-59f5923f"
export SECURITY_GROUP_IDS="sg-0643b1246dd531666"
export AWS_REGION="eu-west-1"
```

- **SUBNET_IDS**: Specifies the AWS subnets where the EKS cluster will be deployed. Ensure that these subnets are in a VPC with internet connectivity or the necessary private network access.
- **SECURITY_GROUP_IDS**: Defines the security groups that control inbound and outbound traffic to the EKS cluster. These should allow necessary Kubernetes communication and node access.

#### **Step 2: Deploy an AWS EKS Cluster**

Create the EKS cluster that will host GPU workloads:

```sh
aws eks create-cluster --name ollama-cluster \
  --role-arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/EKSClusterRole \
  --resources-vpc-config subnetIds=${SUBNET_IDS},securityGroupIds=${SECURITY_GROUP_IDS} \
  --kubernetes-version 1.32 \
  --region ${AWS_REGION}
```

#### **Step 3: Deploy CPU Nodes for the Control Plane**

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

- **`--labels node-type=cpu,system=true`**: Labels are metadata tags that help Kubernetes schedule workloads effectively. In this case:
  - `node-type=cpu` ensures the node group is identified as a CPU-based system.
  - `system=true` may be used to indicate nodes dedicated for system-level workloads, such as control plane operations or background services.

#### **Step 4: Deploy GPU-enabled Spot Node Group**

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

- **Spot Instances (`--capacity-type SPOT`)**: AWS Spot Instances allow you to run workloads at a significantly reduced cost compared to on-demand pricing. However, they can be interrupted if AWS reclaims the capacity.
- **GPU Instance Type (`--instance-types g4dn.xlarge`)**: The `g4dn.xlarge` instance provides a single NVIDIA T4 GPU, making it cost-effective for AI inference and smaller training workloads.
- **AMI Type (`--ami-type AL2_x86_64_GPU`)**: Specifies an Amazon Linux 2 AMI that comes with NVIDIA drivers pre-installed.
- **Labels (`--labels node-type=gpu`)**: Helps Kubernetes identify that this node group is GPU-based, so it can be scheduled appropriately.
- **Taints (`--taints key=nvidia.com/gpu,value=present,effect=NO_SCHEDULE`)**: Ensures that only workloads requesting GPUs are scheduled on these nodes.

✅ **Spot Instances reduce GPU costs significantly but may not be suitable for workloads requiring guaranteed availability.**

## **2️⃣ Enable GPU Access**

### **Install NVIDIA K8s Device Plugin**

To enable **GPU access** in Kubernetes, install the **NVIDIA K8s Device Plugin** from:

👉 [NVIDIA/k8s-device-plugin](https://github.com/NVIDIA/k8s-device-plugin)

#### **Why Do You Need This?**
- The **NVIDIA GPU device plugin** allows Kubernetes to **detect and allocate GPUs** to workloads.
- Without this plugin, Kubernetes won’t recognize GPUs, even if a node has an **NVIDIA GPU**.
- Required for both **GPU sharing** features.
- There are two mutually exclusive modes of GPU sharing: **Time-Slicing** and **Multi-Process Service (MPS)**.

---

#### **Option 1: Enable CUDA Time Slicing**

CUDA **Time Slicing** allows multiple workloads to share a single GPU by allocating usage time slots.

##### **Step 1: Deploy NVIDIA Device Plugin with Time Slicing**
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

##### **Step 2: Configure Time Slicing**
The configuration file **cuda/cuda-time-slicing-values.yaml** enables GPU sharing by defining how many workloads can run simultaneously on the same GPU.

#### **Configuration Example**
```yaml
config:
  map:
    default: |-
      {
        "version": "v1",
        "sharing": {
          "timeSlicing": {
            "resources": [
              {
                "name": "nvidia.com/gpu",
                "replicas": 4
              }
            ]
          }
        }
      }
  default: "default"
```

#### **Explanation**
- **`"name": "nvidia.com/gpu"`** → Defines the GPU resource type recognized by Kubernetes.
- **`"replicas": 4`** → Allows up to **4 workloads** to share the same physical GPU by assigning time slices.
- **`"timeSlicing"`** → Enables GPU time-sharing rather than exclusive access per workload.

✅ **Use Case:** Suitable for large independent workloads that don't require concurrent GPU execution.

---

#### **Option 2: Enable CUDA MPS (Multi-Process Service)**

CUDA **MPS** allows multiple workloads to share a GPU **concurrently**, optimizing memory and compute utilization.

##### **Step 1: Connect to GPU Node**
Before enabling MPS, access a GPU node using **AWS Systems Manager (SSM)**:
```sh
aws ssm start-session --target $(aws ec2 describe-instances --region eu-west-1 \
  --filters "Name=instance-type,Values=g4dn.xlarge" "Name=instance-state-name,Values=running" \
  --query "Reservations[0].Instances[0].InstanceId" --output text) --region eu-west-1
```

##### **Step 2: Check GPU Compute Mode**
Verify the current GPU compute mode:
```sh
nvidia-smi -q | grep "Compute Mode"
```
If it returns `Default`, switch to `Exclusive Process` mode for MPS:

By default, most GPUs operate in **Default Compute Mode**, which allows multiple processes to use the GPU but prevents true concurrent execution. **Exclusive Process Mode** ensures that each CUDA application has exclusive access to a GPU partition, which is necessary for **MPS** to function efficiently.

- **Why is this needed?**
  - **Default Mode** does not allow efficient GPU sharing under MPS.
  - **Exclusive Process Mode** enables multiple processes to share GPU resources dynamically without blocking each other.
  - MPS **reduces context switching overhead** and **improves overall performance** when multiple workloads run simultaneously.  

```sh
sudo nvidia-smi -c EXCLUSIVE_PROCESS
```

##### **Step 3: Enable the MPS Daemon**

The **MPS Daemon** (Multi-Process Service Daemon) is a background process that enables multiple CUDA applications to share a GPU concurrently. It helps optimize GPU utilization by allowing multiple workloads to execute in parallel instead of time-slicing between them.

**Why is this needed?**
- Without the MPS daemon, CUDA workloads execute sequentially when running on a shared GPU.
- MPS enables **lower-latency, parallel execution** of multiple workloads, improving GPU efficiency.
- It allows AI models and inference tasks to share GPU memory and compute resources dynamically.

```sh
sudo nvidia-cuda-mps-control -d
```

##### **Step 4: Deploy NVIDIA Device Plugin with MPS**
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

### **Step 5: Configure MPS**
The configuration file **cuda/cuda-mps-values.yaml** enables **multi-process service**, allowing concurrent execution of multiple workloads on a single GPU.

#### **Configuration Example**
```yaml
config:
  map:
    default: |-
      {
        "version": "v1",
        "sharing": {
          "mps": {
            "resources": [
              {
                "name": "nvidia.com/gpu",
                "replicas": 4
              }
            ]
          }
        }
      }
  default: "default"
```

#### **Explanation**
- **`"mps"`** → Enables CUDA Multi-Process Service (MPS).
- **`"replicas": 2`** → Allows **two workloads** to run **concurrently** on the same GPU.
- **More efficient memory utilization** compared to time-slicing.

✅ **Use Case:** Ideal for AI inference and workloads that benefit from concurrent execution.

---

### **Choosing Between Time Slicing and MPS**
| Feature              | Time-Slicing                           | MPS                                      |
|---------------------|-------------------------------------|-----------------------------------------|
| Process Execution  | Alternates workloads sequentially  | Runs multiple workloads in parallel    |
| GPU Utilization    | Varies between 0% and 100%         | Maintains steady utilization           |
| Memory Efficiency  | Medium                              | High                                   |
| Best For           | Large, independent workloads       | Smaller, parallel workloads            |
| Latency            | Higher due to context switching    | Lower due to concurrent execution      |

🔹 **Choose Time-Slicing** if workloads are independent and don’t need parallel execution.
🔹 **Choose MPS** if workloads require efficient GPU sharing with lower latency.


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

