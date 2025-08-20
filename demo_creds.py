"""RunPod inline credentials integration demo.

Creates a tiny RunPod cluster via SkyPilot with an API key passed inline.
This requires a valid RunPod API key.

Usage examples:
	# Using env var for the API key (launches a CPU-only RunPod VM)
	RUNPOD_API_KEY=... python demo_creds.py

	# Teardown the cluster (default name: rp-demo-test)
	RUNPOD_API_KEY=... python demo_creds.py --down

	# Or passing the key explicitly (avoids reading env var)
	python demo_creds.py --api-key ...

	# Optionally set a custom cluster name
	python demo_creds.py --api-key ... --name my-runpod-cluster
"""

from __future__ import annotations

import argparse
import os


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="RunPod inline credentials demo (integration)")
	parser.add_argument("--api-key", dest="api_key", default=None,
						help="RunPod API key. If not set, falls back to RUNPOD_API_KEY env var.")
	parser.add_argument("--name", dest="cluster_name", default="rp-demo-test",
						help="Cluster name (default: rp-demo-test).")
	parser.add_argument("--down", dest="down", action="store_true",
						help="Tear down the demo cluster (default: rp-demo-test).")
	parser.add_argument("--spot", dest="use_spot", action="store_true",
						help="Use spot if available.")
	parser.add_argument("--dryrun", dest="dryrun", action="store_true",
						help="Perform a dry run only (no provisioning).")
	parser.add_argument("--cpu-only", dest="cpu_only", action="store_true",
						help="Launch CPU-only instead of GPU.")
	parser.add_argument("--gpu", dest="gpu", default="L4",
						help="GPU accelerator name (default: L4).")
	parser.add_argument("--gpu-count", dest="gpu_count", type=int, default=1,
						help="Number of GPUs to request (default: 1).")
	parser.add_argument("--instance-type", dest="instance_type", default=None,
						help="Explicit RunPod instance type (e.g., cpu3c-2-4). Overrides --cpus.")
	parser.add_argument("--cpus", dest="cpus", default="2+",
						help="vCPUs requirement (e.g., 1+, 2, 4+). Ignored if --instance-type is set.")
	parser.add_argument("--disk-size", dest="disk_size", type=int, default=30,
						help="Container disk size in GB (RunPod containerDiskInGb).")
	parser.add_argument("--region", dest="region", default=None,
						help="Preferred country/region code (e.g., US, NL). Optional.")
	parser.add_argument("--zone", dest="zone", default=None,
						help="Preferred data center/zone ID in the region. Optional.")
	parser.add_argument("--retry-until-up", dest="retry_until_up", action="store_true",
						help="Keep retrying until capacity is found.")
	args = parser.parse_args()

	api_key = args.api_key or os.environ.get("RUNPOD_API_KEY")
	if not api_key:
		raise SystemExit("RUNPOD_API_KEY not set and --api-key not provided.")

	# Defer heavy imports until we actually run
	import sky
	from sky.adaptors import runpod_client as runpod

	# Hardcode the demo cluster name.
	cluster_name = args.cluster_name

	# Inline credentials ride along with the request to the API server.
	creds = {"runpod": {"api_key": api_key}}

	# Ensure the inline API key is honored for local CLI runs.
	with runpod.api_key_context(api_key):
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
			mode = "CPU-only" if args.cpu_only else f"GPU ({args.gpu} x{args.gpu_count})"
			print(f"[demo] Launching on RunPod as cluster: {cluster_name} [{mode}]")
			task = sky.Task(run='echo "hello from $(hostname)" && sleep 5')
			# Build resources: GPU by default (L4), or CPU-only if requested.
			res_kwargs = dict(
				cloud=sky.RunPod(),
				region=args.region,
				zone=args.zone,
				use_spot=args.use_spot,
			)
			if args.cpu_only:
				if args.instance_type:
					res_kwargs.update(instance_type=args.instance_type)
				else:
					res_kwargs.update(cpus=args.cpus)
				if args.disk_size:
					res_kwargs.update(disk_size=args.disk_size)
			else:
				# Request a specific accelerator (default: L4)
				res_kwargs.update(accelerators={args.gpu: args.gpu_count})

			task.set_resources(sky.Resources(**res_kwargs))

			try:
				request_id = sky.launch(
					task,
					cluster_name=cluster_name,
					dryrun=args.dryrun,
					retry_until_up=args.retry_until_up,
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

