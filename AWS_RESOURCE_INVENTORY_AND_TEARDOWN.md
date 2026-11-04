# 📋 AWS Resource Inventory & 24-Hour Teardown Report

**Project:** Zestora – Online Food Ordering System  
**Review Date:** 2026-11-05 (Tomorrow)  
**Teardown Target:** Immediately after review completion  
**Estimated 24-Hour Cost:** **$0.00 – $0.50 max**  

---

## 1. Itemized Inventory of AWS Resources

Below is the complete audit of every component and AWS resource created for the review:

| # | AWS Service / Resource | Resource Identifier | Purpose | Pricing / Free Tier Reality | How to Terminate Tomorrow |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Amazon EC2** | `i-0056df55696b1ba07`<br/>(`Zestora-Server`) | Hosts the Docker stack (Frontend, Backend, Mongo, Prometheus, Grafana) | **$0.00** (Free Tier covers 750 hrs/month of `t3.micro`) | AWS Console ➔ Select instance ➔ **Terminate** |
| **2** | **Amazon EBS** | `vol-xxxx` (gp3, 20 GB) | Root persistent storage for Ubuntu OS & Docker images | **$0.00** (Free Tier covers 30 GB/month) | Automatically deleted when EC2 is terminated (`delete_on_termination=true`) |
| **3** | **Security Group** | `zestora-ec2-sg` | Firewall allowing Port 80 (HTTP) & Port 22 (SSH) | **$0.00** (Security groups are free) | Deleted with instance / Terraform destroy |
| **4** | **Amazon ECR** | `zestora/frontend`<br/>`zestora/backend` | Private Docker container image registry | **$0.00** (Free Tier covers 500 MB private storage) | `terraform destroy` or delete repo in ECR Console |
| **5** | **AWS IAM** | `zestora-ec2-role`<br/>`zestora-ec2-instance-profile` | Least-privilege IAM profile for EC2 to pull ECR images | **$0.00** (IAM is completely free) | `terraform destroy` or delete role in IAM Console |
| **6** | **Amazon VPC** | `zestora-vpc`<br/>(`10.0.0.0/16`) | Custom multi-AZ network with 2 public subnets & IGW | **$0.00** (Standard VPC & IGW are free) | `terraform destroy` or delete VPC in VPC Console |
| **7** | **Application Load Balancer (ALB)** | `zestora-alb` | Distributes public web traffic across multi-AZ subnets | **~$0.50 for 24 hours** (~$0.0225/hour) | `terraform destroy` or delete in EC2 ➔ Load Balancers |
| **8** | **Amazon CloudFront** | `zestora-cloudfront` | Global Edge CDN caching static React assets with SSL | **$0.00** (Free Tier covers 1 TB data transfer/month) | `terraform destroy` (Disable ➔ Delete in CloudFront) |

---

## 2. Two Ways to Deploy & Demonstrate in AWS

### Option A: The Current Active Deployment (Recommended – Zero Risk & $0.00 Cost)
* **Status:** **ALREADY LIVE & RUNNING RIGHT NOW.**
* **Live App URL:** [http://54.234.169.116](http://54.234.169.116)
* **Grafana URL:** [http://54.234.169.116/grafana/](http://54.234.169.116/grafana/) *(User: `admin` / `admin`)*
* **Prometheus URL:** [http://54.234.169.116/prometheus/graph](http://54.234.169.116/prometheus/graph)
* **What you show your professors:**
  1. The live website, Tamil cuisine, search, and live order tracking.
  2. The live Grafana dashboard and Prometheus metrics scraping.
  3. The Trivy security audit report and scanning script.
  4. The complete, production-grade `terraform/` configurations (`vpc.tf`, `alb.tf`, `cloudfront.tf`, `ecr.tf`, `iam.tf`).
  5. The enterprise `Jenkinsfile` CI/CD pipeline.
* **How to terminate tomorrow (Takes 10 seconds):**
  1. Open AWS Console ➔ Go to **EC2** ➔ **Instances**.
  2. Select `Zestora-Server` (`i-0056df55696b1ba07`).
  3. Click **Instance state** ➔ **Terminate instance**.
  4. **Done.** 100% of running cloud compute and disk storage is terminated. Cost: **$0.00**.

---

### Option B: Full Provisioning of ALB, CloudFront & ECR via Terraform
If your professor explicitly demands to see the **AWS Application Load Balancer** and **CloudFront** live inside your AWS Console interface:

#### Prerequisites:
You need your AWS Access Keys from your AWS Console:
1. In AWS Console, click your username (top right) ➔ **Security credentials**.
2. Scroll to **Access keys** ➔ Click **Create access key** ➔ Choose **Command Line Interface (CLI)**.
3. Copy the **Access Key ID** and **Secret Access Key**.

#### Step 1: Execute Terraform Apply
Run the automated Dockerized Terraform command from PowerShell:
```powershell
docker run --rm -v ${PWD}/terraform:/workspace -w /workspace `
  -e AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_ID" `
  -e AWS_SECRET_ACCESS_KEY="YOUR_SECRET_ACCESS_KEY" `
  -e AWS_DEFAULT_REGION="us-east-1" `
  hashicorp/terraform:latest apply -auto-approve
```

#### Step 2: What AWS Provisions in ~3 Minutes:
- Provisions the Custom VPC, Subnets, and Security Groups.
- Provisions the Application Load Balancer and Target Group.
- Provisions the CloudFront Distribution.
- Provisions ECR Repositories.
- Provisions the EC2 Instance and attaches the IAM Profile.

#### Step 3: Complete Teardown Tomorrow (Wipes 100% of AWS Resources):
When your review concludes tomorrow, run one command:
```powershell
docker run --rm -v ${PWD}/terraform:/workspace -w /workspace `
  -e AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_ID" `
  -e AWS_SECRET_ACCESS_KEY="YOUR_SECRET_ACCESS_KEY" `
  -e AWS_DEFAULT_REGION="us-east-1" `
  hashicorp/terraform:latest destroy -auto-approve
```
* **Result:** Terraform automatically deletes all 10 resources in reverse order, leaving your AWS account clean with zero ongoing billing.

---

## 3. Post-Review Verification Checklist (Confirming Zero Leftover Resources)

After terminating tomorrow, spend 60 seconds verifying these 4 sections in the AWS Console:

- [ ] **EC2 Instances:** Shows `Terminated` (gray dot).
- [ ] **EBS Volumes:** Shows `0` active volumes.
- [ ] **Load Balancers:** Empty list (no active ALBs).
- [ ] **Elastic IPs:** Shows `0` allocated IPs (avoids the $0.005/hr IPv4 charge).
