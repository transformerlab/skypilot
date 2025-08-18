"""RunPod inline credentials integration demo.

Creates a tiny RunPod cluster via SkyPilot with an API key passed inline.
This requires a valid RunPod API key.

Usage examples:
	# Using env var for the API key (launches a CPU-only RunPod VM)
	RUNPOD_API_KEY=... python demo_creds.py

	# Teardown the hardcoded cluster
	RUNPOD_API_KEY=... python demo_creds.py --down

	# Or passing the key explicitly (avoids reading env var)
	python demo_creds.py --api-key ...
"""

from __future__ import annotations

import argparse
import os


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="RunPod inline credentials demo (integration)")
	parser.add_argument("--api-key", dest="api_key", default=None,
						help="RunPod API key. If not set, falls back to RUNPOD_API_KEY env var.")
	parser.add_argument("--down", dest="down", action="store_true",
						help="Tear down the demo cluster (rp-demo-test).")
	parser.add_argument("--spot", dest="use_spot", action="store_true",
						help="Use spot if available.")
	parser.add_argument("--dryrun", dest="dryrun", action="store_true",
						help="Perform a dry run only (no provisioning).")
	args = parser.parse_args()

	api_key = args.api_key or os.environ.get("RUNPOD_API_KEY")
	if not api_key:
		raise SystemExit("RUNPOD_API_KEY not set and --api-key not provided.")

	# Defer heavy imports until we actually run
	import sky

	# Hardcode the demo cluster name.
	cluster_name = "rp-demo-test"

	# Inline credentials ride along with the request to the API server.
	creds = {"runpod": {"api_key": api_key}}

	if args.down:
		print(f"[demo] Tearing down cluster: {cluster_name}")
		try:
			request_id = sky.down(cluster_name=cluster_name, credentials=creds)
			sky.stream_and_get(request_id)
			print(f"[demo] Down completed. Cluster: {cluster_name} removed")
		except Exception as e:
			print(f"[demo] Down FAILED: {e}")
			raise
	else:
		print(f"[demo] Launching on RunPod as cluster: {cluster_name} (CPU-only)")
		task = sky.Task(run='echo "hello from $(hostname)" && sleep 5')
		# CPU-only: do not set accelerators; request 2 vCPUs as a default.
		task.set_resources(
			sky.Resources(
				cloud=sky.RunPod(),
				cpus='2',
				use_spot=args.use_spot,
			)
		)

		try:
			request_id = sky.launch(
				task,
				cluster_name=cluster_name,
				dryrun=args.dryrun,
				credentials=creds,
			)
			if args.dryrun:
				print("[demo] Dry run submitted.")
			else:
				# Stream until the task finishes; the cluster will remain up.
				sky.stream_and_get(request_id)
				print(f"[demo] Launch completed. Cluster: {cluster_name}")
				print("         You can inspect it with: sky status -a")
		except Exception as e:
			print(f"[demo] Launch FAILED: {e}")
			raise

