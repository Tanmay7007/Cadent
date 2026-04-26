# Cadent
Cadent is a ML-based load balancing system. Here, we have Network Bytes and CPU Utilization as inputs and then we perform a bivariate analysis using Random Forest Model. The model then classifies the system as "Normal", "Warning" or "Threat" Level. 

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![AWS](https://img.shields.io/badge/AWS-EC2%20%7C%20Lambda%20%7C%20ALB-FF9900.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B.svg)
![Machine Learning](https://img.shields.io/badge/Scikit--Learn-Random%20Forest-F7931E.svg)

Traditional auto-scalers are "blind"—they scale infrastructure based purely on static thresholds (e.g., CPU > 80%), leaving enterprise environments vulnerable to expensive "scale-out" billing attacks. 

CADENT replaces this blind logic with an AI-driven **Split Architecture**. By leveraging a Random Forest Machine Learning model, CADENT continuously analyzes bivariate AWS telemetry (CPU Utilization and Network Traffic) to differentiate legitimate viral web surges from malicious, CPU-bound insider threats, triggering serverless mitigation only when mathematically justified.

## System Architecture

CADENT utilizes a **Split Architecture** to decouple heavy Machine Learning orchestration from the live cloud environment:
1. **Local Command Center:** A Streamlit dashboard that ingests live AWS CloudWatch metrics, runs the Random Forest `.pkl` model, and provides a UI for attack team simulations.
2. **Dual-Vector Simulation:** Uses `Locust` to generate benign web traffic and `stress-ng` to simulate internal CPU-stress malware.
3. **Serverless Cloud Mitigation:** When the local AI detects a Critical Threat, it fires an authenticated API payload to an **AWS Lambda** function. Lambda utilizes `boto3` to clone a Golden AMI, boot a backup EC2 instance, and seamlessly register it to the Application Load Balancer (ALB).

## Repository Structure

* `app.py`: The Streamlit Command Center and ML inference engine.
* `lambda_function.py`: The serverless `boto3` mitigation script deployed to AWS Lambda.
* `model.pkl`: The serialized Random Forest Classifier.
* `locustfile.py`: The traffic generation script for simulating benign public web load.

## Prerequisites

**Local Environment:**
* Python 3.8+
* AWS CLI installed and configured (`aws configure` with appropriate IAM access keys)

**AWS Environment Requirements:**
To run this project, you must have the following pre-configured in your AWS account:
1. **Golden AMI:** A pre-configured EC2 Amazon Machine Image containing your web application and dependencies (like `stress-ng`).
2. **Application Load Balancer (ALB):** An active ALB connected to a Target Group.
3. **Master EC2 Instance:** An instance running your application, registered to the ALB Target Group.
4. **IAM Role for Lambda:** An execution role with permissions for:
   * `ec2:RunInstances`
   * `ec2:CreateTags`
   * `elasticloadbalancing:RegisterTargets`
   * `iam:PassRole` (Critical for attaching an instance profile to the new clone).

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Tanmay7007/Cadent.git]
   cd CADENT
   
2. **Install dependencies:**
   ```bash
   pip install streamlit boto3 scikit-learn pandas locust

3. **Configure AWS Variables:**

   * Open lambda_function.py and update the AMI_ID, SUBNET_ID, SECURITY_GROUP_ID, and TARGET_GROUP_ARN with your specific AWS environment values.
   * Update app.py with your Master EC2 INSTANCE_ID for CloudWatch metric ingestion.

4. **Deploy the Lambda Function:**
   * Zip the lambda_function.py file.
   * Upload it to the AWS Lambda console.
   * Ensure the Lambda function's execution role has the required IAM permissions listed in the prerequisites.

## Usage Instructions
Step 1: **Start Benign Traffic Simulation**
   * Open a terminal and start Locust to simulate normal user traffic hitting your ALB:

   ```bash
   locust -f locustfile.py --host=http://YOUR_ALB_DNS_NAME.com
```
   * Navigate to http://localhost:8089 to start the swarm.


Step 2: **Launch the Command Center**
   * Open a second terminal and start the Streamlit dashboard:

```bash
streamlit run app.py
```
or
```bash
python -m streamlit run app.py
```

Step 3: **Simulate an Attack & Observe Mitigation**
   * From the Streamlit dashboard, monitor the live CPU and Network graphs.
   * Initiate a stress test (e.g., executing stress-ng --cpu 4 on the Master EC2 instance).
   * Watch as the Random Forest model detects the "High CPU + Low Network" anomaly (State 2: Critical Threat).
   * The dashboard will automatically trigger the AWS Lambda function.
   * Verify in your AWS Console that a new EC2 clone has been provisioned and registered to your ALB Target Group seamlessly.

## Disclaimer
This project is designed for educational and architectural demonstration purposes. Running automated load generation (Locust) and infrastructure scaling scripts in an active AWS environment will incur real AWS billing charges. Always ensure you destroy your EC2 instances and ALBs after testing to prevent runaway costs.
