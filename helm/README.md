# helm

kubectl get svc -n  kourier-system
NAME               TYPE           CLUSTER-IP       EXTERNAL-IP                                                              PORT(S)                      AGE
kourier            LoadBalancer   10.100.40.98     a714d2d3e91ac41a0a598c84fb65e4e9-837919173.eu-west-1.elb.amazonaws.com   80:31782/TCP,443:32230/TCP   4h
kourier-internal   ClusterIP      10.100.153.172   <none>          


nslookup a714d2d3e91ac41a0a598c84fb65e4e9-837919173.eu-west-1.elb.amazonaws.com
Server:         10.255.255.254
Address:        10.255.255.254#53

Non-authoritative answer:
Name:   a714d2d3e91ac41a0a598c84fb65e4e9-837919173.eu-west-1.elb.amazonaws.com
Address: 54.76.105.151
Name:   a714d2d3e91ac41a0a598c84fb65e4e9-837919173.eu-west-1.elb.amazonaws.com
Address: 3.248.93.23


Since nip.io works with a single IP, you can choose either of these for your hostname.

----

kubectl get nodes
NAME                                         STATUS   ROLES    AGE   VERSION
ip-172-31-33-99.eu-west-1.compute.internal   Ready    <none>   86m   v1.32.0-eks-aeac579
mmitchell@SurfacePro:~$ kubectl taint nodes ip-172-31-33-99.eu-west-1.compute.internal nvidia.com/gpu=present:NoSchedule
node/ip-172-31-33-99.eu-west-1.compute.internal tainted
mmitchell@SurfacePro:~$ kubectl get nodes -o jsonpath="{.items[*].spec.taints}" | jq .
[
  {
    "effect": "NoSchedule",
    "key": "nvidia.com/gpu",
    "value": "present"
  }
]
mmitchell@SurfacePro:~$

==========================================================

- setup cluster

- cpu node group for system pods

aws eks create-nodegroup \
  --cluster-name ollama-cluster \
  --nodegroup-name cpu-system-nodes \
  --capacity-type ON_DEMAND \
  --instance-types t3.medium \
  --ami-type AL2_x86_64 \
  --scaling-config minSize=1,maxSize=3,desiredSize=1 \
  --node-role arn:aws:iam::${AWS_ACCOUNT_ID}:role/EKSNodeRole \
  --subnets ${SUBNET_IDS//,/ } \
  --region ${AWS_REGION}

- gpu node group


- kubectl taint nodes --selector node.kubernetes.io/instance-type=g4dn.xlarge nvidia.com/gpu=present:NoSchedule

