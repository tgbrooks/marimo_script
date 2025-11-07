import argparse
import subprocess
import time
import re
import socket

parser = argparse.ArgumentParser(
    "run_marimo",
    "Runs marimo on PMACS, forwards the ports, and outputs the appropriate URL to go to. Note: server job must be shut down manually at the end.",
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
else:
    # Start the server
    # marimo_command = f"""module load gcc/12.2.0 && cd {args.directory} && uv run marimo edit --host 0.0.0.0"""
    res = shell(
        f"""ssh consign "bsub -J \\"{jobname}\\" -M 36000 -R \\"rusage [mem=36000] span[hosts=1]\\" -n 6 -eo ~/marimo/bsub.err -oo ~/marimo/bsub.out ~/marimo/run_marimo.sh {args.directory}" """,
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
    raise Exception("Job still not running! Aborting")

# Bpeek the output to find out access token, socket, and node
for i in range(20):
    time.sleep(2)
    res = shell(
        f"""ssh consign "bpeek {job_id}" """,
    )
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

print(f"http://localhost:{local_socket}?access_token={access_token}")


# Start the port-forwarding
cmd = (f"ssh -L {local_socket}:{node}:{server_socket} consign",)
print(cmd)
res = subprocess.run(
    cmd,
    shell=True,
    check=True,
)
