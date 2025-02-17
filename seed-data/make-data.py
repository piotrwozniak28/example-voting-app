import os
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv, find_dotenv

#########################################################################################


def is_running_in_container() -> bool:
    """
    Detect whether the Python process is running inside a container.
    Common signals include:
      • The existence of the file "/.dockerenv"
      • Docker control groups in "/proc/1/cgroup" (may also contain hints like "docker", "containerd", or "kubepods")
    """
    # Check for the env variable
    if os.environ.get("IS_RUNNING_IN_CONTAINER:"):
        return True

    # Check for the presence of the Docker-specific file
    if os.path.exists("/.dockerenv"):
        return True

    # Check the process control groups for hints of containerization
    try:
        with open("/proc/1/cgroup", "rt") as f:
            contents = f.read()
            if any(
                keyword in contents for keyword in ("docker", "containerd", "kubepods")
            ):
                return True
    except Exception:
        pass

    return False


if is_running_in_container():
    print("Running in container")
    EXECUTION_ENVIRONMENT = "container"
    VOTE_URL = "http://vote/"
else:
    print("Running locally")
    EXECUTION_ENVIRONMENT = "local"
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=find_dotenv(), verbose=True, override=True)
    VOTE_URL = f"http://localhost:{os.environ.get("VOTE_HOST_PORT")}/"

#########################################################################################


def send_requests(url, data, total_requests, concurrency):
    def worker():
        try:
            req = urllib.request.Request(
                url,
                data=data.encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urllib.request.urlopen(req) as response:
                return response.status
        except Exception as e:
            print(f"Request failed: {e}")
            return None

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        # Submit all requests
        futures = [executor.submit(worker) for _ in range(total_requests)]

        # Wait for completion (optional: add progress tracking)
        for future in futures:
            future.result()


if __name__ == "__main__":
    # Create encoded payloads directly in memory
    payload_b = urllib.parse.urlencode({"vote": "b"})
    payload_a = urllib.parse.urlencode({"vote": "a"})

    # Maintain original test sequence
    send_requests(VOTE_URL, payload_b, 100, 50)
    send_requests(VOTE_URL, payload_a, 100, 50)
    send_requests(VOTE_URL, payload_b, 100, 50)
