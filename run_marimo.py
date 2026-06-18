#!/usr/bin/env python3
import argparse
import subprocess
import time
import re
import socket

ERROR_LOG_PATH = "~/marimo/bsub.err"
OUT_LOG_PATH = "~/marimo/bsub.out"
MARIMO_START_SERVER_SCRIPT_PATH = "~/marimo/start_marimo_server.sh"

GREEN = "\033[32m"
RED = '\033[91m'
RESET = "\033[0m"

parser = argparse.ArgumentParser(
    "run_marimo",
    "Runs marimo on PMACS, forwards the ports, and outputs the appropriate URL to go to.",
)
parser.add_argument("directory")
args = parser.parse_args()


def shell(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, check=True)


jobname = f"run_marimo:{args.directory}"

# Check if server is already running to reconnect to it
res = shell(
    f"""ssh consign "bjobs -J \\"{jobname}\\"" """,
)
if "JOBID" in res.stdout.decode():
    job_id = res.stdout.decode().splitlines()[1].split()[0]
    print(f"Reconnecting to existing job {job_id}")
else:
    # Start the server
    print("Starting new server")
    # NOTE: hard-coded memory usage (36gb), cores (6), and paths are here
    res = shell(
        f"""ssh consign "bsub -J \\"{jobname}\\" -M 36000 -R \\"rusage [mem=36000] span[hosts=1]\\" -n 6 -eo {ERROR_LOG_PATH} -oo {OUT_LOG_PATH} {MARIMO_START_SERVER_SCRIPT_PATH} {args.directory}" """,
    )
    m = re.match(r"Job <([0-9]+)>", res.stdout.decode())
    job_id = m.groups()[0]

# Wait for it to start
for i in range(20):
    time.sleep(3)
    res = shell(
        f"""ssh consign "bjobs -w {job_id}" """,
    )
    out = res.stdout.decode()
    m = re.search("RUN", out)
    m_node = re.search("(node[0-9]+)", out)
    if m:
        break
else:
    raise Exception(f"{RED}Job still not running! Aborting\nThis is often caused by the job hanging in PEND status, try again later.{RESET}")

# Bpeek the output to find out access token, socket, and node
for i in range(20):
    time.sleep(2)
    try:
        res = shell(
            f"""ssh consign "bpeek {job_id}" """,
        )
    except subprocess.CalledProcessError:
        print(f"{RED}bpeek failed to find {job_id}.\nThis is often due to the start_marimo_server.sh script failing. Check {ERROR_LOG_PATH} and {OUT_LOG_PATH} on PMACS for details.{RESET}")
        raise
    print(res.stdout.decode())
    m_socket = re.search(
        r"URL: http://0.0.0.0:([0-9]+)\?access_token=([a-zA-Z0-9-_]+)",
        res.stdout.decode(),
    )
    if m_socket:
        break
else:
    raise Exception("Marimo has not output required information yet! Aborting")

node = m_node.groups()[0]

server_socket = m_socket.groups()[0]
access_token = m_socket.groups()[1]
print(node)
print(server_socket)
print(access_token)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as temp_sock:
    temp_sock.bind(("", 0))
    local_socket = temp_sock.getsockname()[1]

cmd = f"ssh -L {local_socket}:{node}:{server_socket} consign"
print(cmd)

print("-"*20)
print(f"{GREEN}Open link to access Marimo:")
link = f"http://localhost:{local_socket}?access_token={access_token}"
print(link + RESET)
print("-"*20)

# Start the port-forwarding
res = subprocess.run(
    cmd,
    shell=True,
    check=True,
)
