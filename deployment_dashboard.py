#!/usr/bin/env python3
"""
Simple Deployment Dashboard
Executes deployment steps with visual feedback
"""

import streamlit as st
import subprocess
import time
import os
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Deployment Dashboard",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 Deployment Dashboard")
st.markdown("---")

# Configuration from environment or defaults
REGISTRY = os.getenv("DOCKER_REGISTRY", "your-registry")
TAG = os.getenv("DOCKER_TAG", "latest")
NAMESPACE = os.getenv("K8S_NAMESPACE", "essorcloud")

# Show current configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    st.text(f"Registry: {REGISTRY}")
    st.text(f"Tag: {TAG}")
    st.text(f"Namespace: {NAMESPACE}")
    st.markdown("---")
    st.caption("Set via environment variables:\n- DOCKER_REGISTRY\n- DOCKER_TAG\n- K8S_NAMESPACE")

def run_command(command, description):
    """Run a shell command and stream output"""
    st.write(f"**{description}**")
    output_placeholder = st.empty()
    
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        output_lines = []
        for line in process.stdout:
            output_lines.append(line)
            output_placeholder.code("".join(output_lines[-20:]))  # Show last 20 lines
        
        process.wait()
        
        if process.returncode == 0:
            st.success(f"✅ {description} - Complete")
            return True
        else:
            st.error(f"❌ {description} - Failed (exit code: {process.returncode})")
            return False
            
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return False

def wait_for_deployment():
    """Wait for deployment to be ready"""
    st.write("**⏳ Waiting for deployment to be ready...**")
    progress_bar = st.progress(0)
    status_placeholder = st.empty()
    
    max_wait = 180  # 3 minutes
    interval = 5
    elapsed = 0
    
    while elapsed < max_wait:
        try:
            # Check pod status
            result = subprocess.run(
                f"kubectl get pods -n {NAMESPACE} -l app=lego-apps -o json",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                import json
                pods_data = json.loads(result.stdout)
                
                if pods_data.get('items'):
                    pod = pods_data['items'][0]
                    status = pod.get('status', {})
                    phase = status.get('phase', 'Unknown')
                    
                    # Check container statuses
                    container_statuses = status.get('containerStatuses', [])
                    if container_statuses:
                        all_ready = all(cs.get('ready', False) for cs in container_statuses)
                        if phase == 'Running' and all_ready:
                            progress_bar.progress(100)
                            status_placeholder.success("✅ All pods are running and ready!")
                            return True
                    
                    status_placeholder.info(f"Pod status: {phase}")
                else:
                    status_placeholder.warning("No pods found yet...")
        
        except Exception as e:
            status_placeholder.warning(f"Checking status: {str(e)}")
        
        elapsed += interval
        progress_bar.progress(min(int((elapsed / max_wait) * 100), 99))
        time.sleep(interval)
    
    status_placeholder.error("⚠️ Timeout waiting for deployment")
    return False

# Main deployment flow
col1, col2, col3 = st.columns([2, 1, 2])

with col2:
    if st.button("🚀 START DEPLOYMENT", type="primary", use_container_width=True):
        st.session_state.deploying = True
        st.session_state.deployment_start = datetime.now()

if st.session_state.get('deploying'):
    st.markdown("---")
    
    # Step 1: Build Docker app
    st.header("Step 1/6: Building Docker Image")
    if run_command(
        f"docker build -t lego-apps:{TAG} .",
        "Building Docker image"
    ):
        
        # Step 2: Push to repository
        st.markdown("---")
        st.header("Step 2/6: Pushing to Repository")
        if run_command(
            f"docker tag lego-apps:{TAG} {REGISTRY}/lego-apps:{TAG} && docker push {REGISTRY}/lego-apps:{TAG}",
            f"Pushing image to {REGISTRY}"
        ):
            
            # Step 3: Delete existing deployments
            st.markdown("---")
            st.header("Step 3/6: Deleting Existing Deployments")
            run_command(
                f"kubectl delete deployment lego-apps -n {NAMESPACE} --ignore-not-found=true",
                "Deleting existing deployment"
            )
            time.sleep(2)
            
            # Step 4: Restart deployments
            st.markdown("---")
            st.header("Step 4/6: Creating New Deployment")
            if run_command(
                f"kubectl apply -f k8s/ -n {NAMESPACE}",
                "Applying Kubernetes configurations"
            ):
                
                # Step 5: Wait for deployments to be finished
                st.markdown("---")
                st.header("Step 5/6: Waiting for Deployment")
                deployment_ready = wait_for_deployment()
                
                # Step 6: Final message
                st.markdown("---")
                st.header("Step 6/6: Deployment Complete")
                
                if deployment_ready:
                    duration = (datetime.now() - st.session_state.deployment_start).seconds
                    
                    st.balloons()
                    st.success(f"""
                    ### 🎉 Deployment Successful!
                    
                    **Duration:** {duration} seconds
                    
                    **Services:**
                    - Streamlit Dashboard: Port 8501
                    - Flask Admin: Port 5003
                    """)
                    
                    # Show service info
                    st.subheader("Service Information")
                    result = subprocess.run(
                        f"kubectl get services -n {NAMESPACE}",
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        st.code(result.stdout)
                    
                    # Show pod status
                    st.subheader("Pod Status")
                    result = subprocess.run(
                        f"kubectl get pods -n {NAMESPACE} -l app=lego-apps",
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        st.code(result.stdout)
                    
                else:
                    st.warning("""
                    ### ⚠️ Deployment Created but Not Fully Ready
                    
                    The deployment has been created but pods may still be starting.
                    
                    Check status manually with:
                    ```
                    kubectl get pods -n essorcloud
                    kubectl logs -n essorcloud -l app=lego-apps -f
                    ```
                    """)
                
                # Reset button
                if st.button("Deploy Again", use_container_width=True):
                    st.session_state.deploying = False
                    st.rerun()
        
        st.session_state.deploying = False

# Quick actions sidebar
with st.sidebar:
    st.markdown("---")
    st.header("🔧 Quick Actions")
    
    if st.button("View Logs", use_container_width=True):
        with st.expander("Recent Logs", expanded=True):
            result = subprocess.run(
                f"kubectl logs -n {NAMESPACE} -l app=lego-apps --tail=50 --all-containers=true",
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                st.code(result.stdout)
            else:
                st.error("Could not fetch logs")
    
    if st.button("Check Status", use_container_width=True):
        with st.expander("Current Status", expanded=True):
            st.write("**Pods:**")
            result = subprocess.run(
                f"kubectl get pods -n {NAMESPACE} -l app=lego-apps",
                shell=True,
                capture_output=True,
                text=True
            )
            st.code(result.stdout if result.returncode == 0 else "Error fetching pods")
            
            st.write("**Services:**")
            result = subprocess.run(
                f"kubectl get services -n {NAMESPACE}",
                shell=True,
                capture_output=True,
                text=True
            )
            st.code(result.stdout if result.returncode == 0 else "Error fetching services")

