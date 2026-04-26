"""
Cadent is a ML-based Load Balancing System using AWS. Here we have Network Bytes and CPU Utilization as the inputs.
We perform a Bi-variate Analysis using Random Forest Model.
It classifies the System as"Normal", "Warning" or "Threat" level.
If it's Threat Level, it enables a AWS Lambda Function to create a new EC2 serve under the same ALB and redirect the new Network traffic over there.   
For further information read the Github Readme file.
~Tanmay7007
"""

import os
from dotenv import load_dotenv
import streamlit as st
import boto3
import pandas as pd
import datetime
import time
import pickle 

# --- SAFETY LOCK ---
if 'scaler_triggered' not in st.session_state:
    st.session_state.scaler_triggered = False

# 1. Securely load the AWS keys from your .env file
load_dotenv()

# --- CONFIGURATION ---
st.set_page_config(page_title="Cadent", layout="wide")

# 2. Inject Custom CSS for the Iceberg Font
st.markdown("""
<style>
/* IMPORT FONT: Imports Iceberg from Google Fonts */

@import url('https://fonts.googleapis.com/css2?family=Iceberg&display=swap');

/* Force all standard headers to use it as a backup */
h1 {
    font-family: 'Iceberg', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

# 3. The Layout (Using the inline-style override like you did in QUANTA)
st.markdown(
    """
    <div style="display: flex; align-items: baseline; margin-top: -20px;">
        <h1 style="font-family: 'Iceberg', sans-serif !important; font-size: 4rem; margin-right: 20px; margin-bottom: 0;">CADENT</h1>
        <p style="font-size: 1.5rem; color: #808495; margin-bottom: 0;">ML-based Load Balancing</p>
    </div>
    <hr style="margin-top: 5px; margin-bottom: 30px; border: 1px solid #384A5C;">
    """, 
    unsafe_allow_html=True
)


REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

st.sidebar.header("Dashboard Controls")
auto_refresh = st.sidebar.checkbox("🔴 Enable Live Auto-Refresh")
fetch_clicked = st.sidebar.button("Refresh 🔄")

# --- AWS CLIENTS ---
@st.cache_resource
def get_aws_clients(region):
    ec2 = boto3.client('ec2', region_name=region)
    cw = boto3.client('cloudwatch', region_name=region)
    ssm = boto3.client('ssm', region_name=region)
    # Added the Lambda client for when you are ready to connect the Auto-Scaler
    lmbda = boto3.client('lambda', region_name=region) 
    return ec2, cw, ssm, lmbda

ec2_client, cw_client, ssm_client, lambda_client = get_aws_clients(REGION)

# --- LOAD AI MODEL ---
@st.cache_resource
def load_ai_brain():
    """Silently loads the trained Machine Learning brain into memory."""
    try:
        return pickle.load(open('model.pkl', 'rb'))
    except Exception as e:
        return None

ai_model = load_ai_brain()

# --- CORE LOGIC FUNCTIONS ---
def get_running_instances():
    filters = [{'Name': 'instance-state-name', 'Values': ['running', 'pending']}]
    try:
        response = ec2_client.describe_instances(Filters=filters)
        instance_ids = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_ids.append(instance['InstanceId'])
        return instance_ids
    except Exception as e:
        st.error(f"Failed to connect to AWS EC2: {e}")
        return []

def get_ec2_traffic(instance_id, minutes=30):
    end_time = datetime.datetime.now(datetime.timezone.utc)
    start_time = end_time - datetime.timedelta(minutes=minutes)
    try:
        response = cw_client.get_metric_statistics(
            Namespace='AWS/EC2', MetricName='NetworkIn',
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=start_time, EndTime=end_time, Period=60, Statistics=['Sum']
        )
        datapoints = response.get('Datapoints', [])
        if not datapoints: return pd.DataFrame()
        df = pd.DataFrame(datapoints).sort_values(by='Timestamp')
        df.set_index('Timestamp', inplace=True)
        df = df[['Sum']].rename(columns={'Sum': 'Incoming Traffic (Bytes)'})
        return df
    except Exception: return pd.DataFrame()

def get_ec2_cpu(instance_id, minutes=30):
    end_time = datetime.datetime.now(datetime.timezone.utc)
    start_time = end_time - datetime.timedelta(minutes=minutes)
    try:
        response = cw_client.get_metric_statistics(
            Namespace='AWS/EC2', MetricName='CPUUtilization',
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=start_time, EndTime=end_time, Period=60, Statistics=['Average']
        )
        datapoints = response.get('Datapoints', [])
        if not datapoints: return pd.DataFrame()
        df = pd.DataFrame(datapoints).sort_values(by='Timestamp')
        df.set_index('Timestamp', inplace=True)
        df = df[['Average']].rename(columns={'Average': 'CPU Utilization (%)'})
        return df
    except Exception: return pd.DataFrame()

def trigger_cpu_spike(target_instance, command):
    try:
        response = ssm_client.send_command(
            InstanceIds=[target_instance], DocumentName="AWS-RunShellScript",
            Parameters={'commands': [command]}
        )
        st.sidebar.success(f"Attack payload delivered to {target_instance[:8]}...")
    except Exception as e:
        st.sidebar.error(f"Attack failed. Error: {e}")

# --- ATTACK CONTROLS (SIDEBAR) ---
st.sidebar.divider()
st.sidebar.header("Attack Controls")

attack_targets = get_running_instances()

if attack_targets:
    target_id = st.sidebar.selectbox("Select Target Server", attack_targets)
    if st.sidebar.button("🟢 Baseline Testing "):
        trigger_cpu_spike(target_id, "stress-ng --cpu 1 --cpu-load 50 --timeout 120")
    
    if st.sidebar.button("🔴 Peak Testing "):
        trigger_cpu_spike(target_id, "stress-ng --cpu 1 --cpu-load 70 --timeout 60")
else:
    st.sidebar.warning("Turn on an EC2 server to enable attack controls.")

# --- MAIN UI ---
master_cpu_df = pd.DataFrame()
master_traffic_df = pd.DataFrame()

if fetch_clicked or auto_refresh:
    st.markdown("Scanning for AWS EC2 servers...")
    if not attack_targets:
        st.warning("No active EC2 servers found. Your environment is currently empty.")
    else:
        st.success(f"Found {len(attack_targets)} active server(s) running.")
        
        for server_id in attack_targets:
            st.divider()
            st.subheader(f"🖥️ Server ID: `{server_id}`")
            
            # Fetch both metrics
            traffic_df = get_ec2_traffic(server_id)
            cpu_df = get_ec2_cpu(server_id)
            
            # Save the data from the FIRST server for our ML Download button
            if master_cpu_df.empty and master_traffic_df.empty:
                master_traffic_df = traffic_df
                master_cpu_df = cpu_df
            
            # Draw the graphs side-by-side
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**CPU Utilization (%)**")
                if not cpu_df.empty: st.line_chart(cpu_df, color="#FF4B4B")
                else: st.info("Waiting for CPU data...")
                    
            with col2:
                st.markdown("**Network Traffic (Bytes)**")
                if not traffic_df.empty: st.line_chart(traffic_df, color="#0068C9")
                else: st.info("Waiting for Traffic data...")
            
            # --- NEW: AI PREDICTION ENGINE ---
            st.markdown("### 🧠 Live AI Threat Analysis")
            if ai_model is None:
                st.warning("⚠️ model.pkl not found. Please ensure your ML brain is in the same folder.")
            elif not cpu_df.empty and not traffic_df.empty:
                # 1. Grab the absolute latest data point
                latest_cpu = cpu_df['CPU Utilization (%)'].iloc[-1]
                latest_traffic = traffic_df['Incoming Traffic (Bytes)'].iloc[-1]
                
                # 2. Package it exactly how the model was trained
                live_data = pd.DataFrame({
                    'CPU Utilization (%)': [latest_cpu],
                    'Incoming Traffic (Bytes)': [latest_traffic]
                })
                
                # 3. Ask the Brain
                prediction = ai_model.predict(live_data)[0]
                
                # 4. React to the Prediction
                if prediction == 0:
                    st.success(f"🟢 **Status: NORMAL** (CPU: {latest_cpu:.1f}%)")
                    
                elif prediction == 1:
                    st.warning(f"🟡 **Status: WARNING - Elevated Load Detected** (CPU: {latest_cpu:.1f}%)")

                elif prediction == 2:
                    st.error(f"🔴 **STATUS: CRITICAL - INSIDER THREAT DETECTED!** (CPU: {latest_cpu:.1f}%)")
                    
                    # Check if the lock is FALSE (we haven't fired it yet)
                    if not st.session_state.scaler_triggered:
                        st.markdown("> 🚀 *Triggering AWS Lambda Auto-Scaler...*")
                        try:
                            lambda_client.invoke(
                                FunctionName='ML-Trigger-Backup',
                                InvocationType='Event' 
                            )
                            st.success("✅ Backup Server is currently booting up!")
                            # ENGAGE THE LOCK so it never fires again
                            st.session_state.scaler_triggered = True 
                        except Exception as e:
                            st.error(f"Failed to trigger Lambda: {e}")
                    else:
                        st.info("🛡️ Auto-Scaler already deployed a backup server. Waiting for system to stabilize.")
                else:
                    # --- THE SAFETY NET ---
                    st.error(f"⚠️ **SYSTEM ANOMALY:** The AI returned an unknown threat level ({prediction}). Manual inspection required.")
            else:
                st.info("Waiting for enough telemetry data to run AI analysis...")


# --- AUTO-REFRESH LOOP ---
if auto_refresh:
    time.sleep(60)
    st.rerun()