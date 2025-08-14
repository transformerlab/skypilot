import os
import sys
import argparse
from contextlib import contextmanager
from typing import Optional
import dotenv
import sky
dotenv.load_dotenv()

parser = argparse.ArgumentParser(description='Manage RunPod cluster')
parser.add_argument('command', choices=['up', 'down', 'status'], 
                    help='Command to execute: up (launch), down (terminate), or status')
parser.add_argument('--cluster-name', default='my-runpod',
                    help='Name of the cluster (default: my-runpod)')
parser.add_argument('--profile', default=None,
                    help='Optional profile name to source RUNPOD_AI_API_KEY from {profile}.env')
args = parser.parse_args()

cluster_name = args.cluster_name

@contextmanager
def profile(name: Optional[str] = None):
    key = 'RUNPOD_AI_API_KEY'
    prev = os.environ.get(key)
    candidate = None
    print(f"Load profile {name}")
    if name:
        profile_env_path = f'{name}.env'
        if os.path.exists(profile_env_path):
            values = dotenv.dotenv_values(profile_env_path)
            candidate = values.get(key)
    else:
        if os.path.exists('.env'):
            values = dotenv.dotenv_values('.env')
            candidate = values.get(key)
    try:
        if candidate is not None:
            os.environ[key] = candidate
        yield
    finally:
        if prev is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = prev

def ensure_api_key():
    api_key = os.getenv('RUNPOD_AI_API_KEY')
    if not api_key:
        print('RUNPOD_AI_API_KEY is not set. Use --profile (looks for {profile}.env) or set it in your environment/.env file.')
        sys.exit(1)

def launch_cluster():
    print(f"Launching cluster '{cluster_name}'...")
    task = sky.Task(run='echo "Hello, RunPod!"')
    task.set_resources(sky.Resources(cloud='runpod', accelerators='A100-80GB:1'))
    try:
        req_id = sky.launch(task, cluster_name=cluster_name)
        sky.stream_and_get(req_id)
        print(f"Cluster '{cluster_name}' launched successfully!")
    except Exception as e:
        print(f"Error launching cluster: {e}")
        sys.exit(1)

def terminate_cluster():
    print(f"Terminating cluster '{cluster_name}'...")
    try:
        req_id = sky.down(cluster_name)
        sky.stream_and_get(req_id)
        print(f"Cluster '{cluster_name}' terminated successfully!")
    except Exception as e:
        print(f"Error terminating cluster: {e}")

def show_status():
    print(f"Checking status of cluster '{cluster_name}'...")
    try:
        req_id = sky.status([cluster_name])
        clusters = sky.get(req_id)
        print('Status for cluster', cluster_name, ':', clusters)
    except Exception as e:
        print(f"Error checking status: {e}")
        try:
            req_id = sky.status([cluster_name])
            clusters = sky.get(req_id)
            print('Status for cluster', cluster_name, ':', clusters)
        except Exception as e2:
            print(f"Failed to check status: {e2}")
            sys.exit(1)

with profile(args.profile):
    ensure_api_key()
    if args.command == 'up':
        launch_cluster()
    elif args.command == 'down':
        terminate_cluster()
    elif args.command == 'status':
        show_status()