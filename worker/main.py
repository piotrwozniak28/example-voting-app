import os
import json
import socket
import sys
import time
from typing import Optional

import psycopg2
import psycopg2.extensions
import redis
from psycopg2 import errors
from redis import RedisError

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
    # EXECUTION_ENVIRONMENT = "container"
    # APP_ENV_INFO = "Running in container"
else:
    print("Running locally")
    # EXECUTION_ENVIRONMENT = "local"
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=".env", verbose=True, override=True)
    # APP_ENV_INFO = "Running locally"

POSTGRES_HOST = os.environ.get("POSTGRES_HOST")
POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASS = os.environ.get("POSTGRES_PASS")
POSTGRES_NAME = os.environ.get("POSTGRES_NAME")

REDIS_HOST = os.environ.get("REDIS_HOST")

#########################################################################################


def open_db_connection() -> psycopg2.extensions.connection:
    """Connect to PostgreSQL with retries and create table if needed"""
    while True:
        try:
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                user=POSTGRES_USER,
                password=POSTGRES_PASS,
                dbname=POSTGRES_NAME,
            )
            print("Connected to PostgreSQL", file=sys.stderr)
            break
        except (socket.error, psycopg2.OperationalError):
            print("Waiting for PostgreSQL...", file=sys.stderr)
            time.sleep(1)

    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS votes (
                id VARCHAR(255) NOT NULL UNIQUE,
                vote VARCHAR(255) NOT NULL
            )
        """
        )
        conn.commit()

    return conn


def get_redis_ip(hostname: str) -> str:
    """Resolve hostname to IPv4 address"""
    while True:
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for addr in addr_info:
                if addr[0] == socket.AF_INET:
                    ip = addr[4][0]
                    print(f"Found Redis at {ip}", file=sys.stderr)
                    return ip
            raise ValueError(f"No IPv4 address for {hostname}")
        except socket.gaierror:
            print("Waiting for Redis DNS...", file=sys.stderr)
            time.sleep(1)


def open_redis_connection(hostname: str) -> redis.Redis:
    """Connect to Redis with retries"""
    ip = get_redis_ip(hostname)
    while True:
        try:
            client = redis.Redis(host=ip, port=6379)
            if client.ping():
                print("Connected to Redis", file=sys.stderr)
                return client
        except RedisError:
            print("Waiting for Redis...", file=sys.stderr)
            time.sleep(1)


def update_vote(conn: psycopg2.extensions.connection, voter_id: str, vote: str) -> None:
    """Upsert vote record in PostgreSQL"""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO votes (id, vote) VALUES (%s, %s)", (voter_id, vote)
            )
            conn.commit()
    except errors.UniqueViolation:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute("UPDATE votes SET vote = %s WHERE id = %s", (vote, voter_id))
            conn.commit()
    except Exception as e:
        print(f"Error processing vote: {e}", file=sys.stderr)
        conn.rollback()
        raise


def main_loop():
    """Main processing loop handling votes and connections"""
    try:
        pg_conn = open_db_connection()
        redis_client = open_redis_connection("redis")
        keep_alive = "SELECT 1"

        while True:
            time.sleep(0.1)  # 100ms delay

            # Maintain Redis connection
            try:
                redis_client.ping()
            except RedisError:
                print("Reconnecting Redis...", file=sys.stderr)
                redis_client = open_redis_connection("redis")

            # Process votes
            if json_vote := redis_client.lpop("votes"):
                try:
                    vote_data = json.loads(json_vote)
                    print(
                        f"Processing vote for '{vote_data['vote']}' by '{vote_data['voter_id']}'",
                        file=sys.stderr,
                    )

                    if pg_conn.closed:
                        print("Reconnecting PostgreSQL...", file=sys.stderr)
                        pg_conn = open_db_connection()

                    update_vote(pg_conn, vote_data["voter_id"], vote_data["vote"])
                except Exception as e:
                    print(f"Vote processing failed: {e}", file=sys.stderr)
            else:
                # Maintain PostgreSQL connection
                try:
                    with pg_conn.cursor() as cur:
                        cur.execute(keep_alive)
                except Exception as e:
                    print(f"Reconnecting PostgreSQL...", file=sys.stderr)
                    pg_conn = open_db_connection()

    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # main_loop()

    open_db_connection()
    ip = get_redis_ip("localhost")
    print(ip)
