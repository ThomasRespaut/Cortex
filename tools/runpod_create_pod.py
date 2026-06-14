import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


API_URL = "https://rest.runpod.io/v1/pods"
DEFAULT_IMAGE = "runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04"
DEFAULT_GPUS = [
    "NVIDIA GeForce RTX 4090",
    "NVIDIA RTX A5000",
    "NVIDIA GeForce RTX 3090",
]


def request_json(method, url, api_key, payload=None):
    data = None
    headers = {"Authorization": f"Bearer {api_key}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"RunPod API error {error.code}: {details}") from error


def load_public_key(path):
    if not path:
        return None
    key_path = Path(path).expanduser()
    if not key_path.exists():
        raise SystemExit(f"Clé SSH publique introuvable: {key_path}")
    return key_path.read_text(encoding="utf-8").strip()


def pod_summary(pod):
    public_ip = pod.get("publicIp") or pod.get("machine", {}).get("podHostId")
    port_mappings = pod.get("portMappings") or {}
    ssh_port = port_mappings.get("22") or port_mappings.get(22)
    return {
        "id": pod.get("id"),
        "name": pod.get("name"),
        "desiredStatus": pod.get("desiredStatus"),
        "costPerHr": pod.get("costPerHr") or pod.get("adjustedCostPerHr"),
        "publicIp": public_ip,
        "sshPort": ssh_port,
        "portMappings": port_mappings,
    }


def main():
    parser = argparse.ArgumentParser(description="Crée un Pod RunPod pour fine-tuner Cortex.")
    parser.add_argument("--name", default=f"cortex-finetune-{int(time.time())}")
    parser.add_argument("--gpu", action="append", dest="gpus", help="GPU RunPod à essayer, dans l'ordre.")
    parser.add_argument("--cloud-type", choices=["COMMUNITY", "SECURE"], default="COMMUNITY")
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--volume-gb", type=int, default=80)
    parser.add_argument("--container-disk-gb", type=int, default=50)
    parser.add_argument("--ssh-public-key-file", help="Chemin vers une clé publique SSH à injecter.")
    parser.add_argument("--interruptible", action="store_true", help="Utilise une instance interruptible moins chère.")
    args = parser.parse_args()

    api_key = os.environ.get("RUNPOD_API_KEY")
    if not api_key:
        raise SystemExit("Définis RUNPOD_API_KEY avant de lancer ce script.")

    env = {}
    public_key = load_public_key(args.ssh_public_key_file)
    if public_key:
        env["SSH_PUBLIC_KEY"] = public_key

    payload = {
        "cloudType": args.cloud_type,
        "computeType": "GPU",
        "name": args.name,
        "imageName": args.image,
        "gpuTypeIds": args.gpus or DEFAULT_GPUS,
        "gpuTypePriority": "availability",
        "gpuCount": 1,
        "containerDiskInGb": args.container_disk_gb,
        "volumeInGb": args.volume_gb,
        "volumeMountPath": "/workspace",
        "ports": ["22/tcp", "8888/http"],
        "supportPublicIp": True,
        "minRAMPerGPU": 24,
        "minVCPUPerGPU": 4,
        "interruptible": args.interruptible,
        "env": env,
    }

    pod = request_json("POST", API_URL, api_key, payload)
    print(json.dumps(pod_summary(pod), indent=2, ensure_ascii=False))
    print("\nPod créé. Attends que le mapping SSH apparaisse dans la console RunPod.")


if __name__ == "__main__":
    main()
