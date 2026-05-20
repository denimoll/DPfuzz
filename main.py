"""DPFuzz — API fuzzer entry point."""
import glob
import json
import logging
import os
import random
import sys
import threading
import timeit
from concurrent.futures import ThreadPoolExecutor, as_completed

import paramiko
import requests
import urllib3

import change_values
import check_response
import config
import create_common_jsons
import create_jsons_for_generation
import create_report
import validate_json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_STATE_FILE = os.path.join(os.path.dirname(__file__), "dpfuzz_state.json")


# ---------------------------------------------------------------------------
# Startup checks
# ---------------------------------------------------------------------------

def _check_radamsa():
    """Verify that the pyradamsa shared library is loadable."""
    try:
        import pyradamsa
        pyradamsa.Radamsa()
    except Exception as exc:
        logger.error(
            "pyradamsa is not working: %s\n"
            "Make sure the Radamsa shared library is compiled and available.\n"
            "See: https://github.com/denimoll/DPfuzz#installation",
            exc,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# State persistence (improvement #4)
# ---------------------------------------------------------------------------

def _load_state():
    if os.path.exists(_STATE_FILE):
        try:
            with open(_STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Could not read state file: %s", exc)
    return None


def _save_state(state):
    try:
        with open(_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as exc:
        logger.warning("Could not save state: %s", exc)


def _clear_state():
    try:
        os.remove(_STATE_FILE)
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def _get_token(url, headers, token_path):
    """Obtain an auth token by sending the login request from token_path."""
    try:
        with open(token_path, encoding="utf-8") as f:
            return requests.post(url, headers=headers, json=json.load(f), verify=False).json().get("result")
    except Exception as exc:
        logger.error("Could not obtain token: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Worker (improvement #8)
# ---------------------------------------------------------------------------

def _send_one(file, api_url, headers, token_holder, token_lock, token_source):
    """Fuzz a single file and return (status, error_or_None)."""
    with open(file, encoding="utf-8") as f:
        data = json.load(f)

    if "for_generation" in file:
        req = change_values.key_generation(data)
    elif random.randint(0, 1):
        req = change_values.dict_mutation(data)
    else:
        req = change_values.key_mutation(data)

    with token_lock:
        current_token = token_holder[0]

    if isinstance(req, dict) and req.get("auth") is not None:
        req["auth"] = current_token

    try:
        response = requests.post(api_url, headers=headers, json=req, verify=False)
    except Exception:
        return None, None, False  # (status, error, responded)

    status, error = check_response.check_response(req, response)

    if status == "auth_problem" and token_source and glob.glob(token_source):
        with token_lock:
            new_token = _get_token(api_url, headers, token_source)
            if new_token:
                token_holder[0] = new_token

    return status, error, True


# ---------------------------------------------------------------------------
# Main fuzzing loop
# ---------------------------------------------------------------------------

def dpfuzz():
    """Main fuzzing loop."""
    _check_radamsa()

    if config.validate_config_parameters() is not True:
        return

    path_to_examples = config.examples()

    # Validate all example JSON files up front
    invalid = 0
    for method in os.listdir(path_to_examples):
        method_path = os.path.join(path_to_examples, method)
        if not os.path.isdir(method_path):
            continue
        files = glob.glob(os.path.join(method_path, "*.json"))
        if not files:
            logger.error("No JSON examples for method: %s", method)
            return
        for file in files:
            with open(file, encoding="utf-8") as j:
                result = validate_json.validate_json(j)
                if result is not True:
                    logger.error("Invalid JSON file %s: %s", file, result)
                    invalid += 1
    if invalid:
        logger.error("Fix the %d invalid file(s) listed above before fuzzing.", invalid)
        return

    create_common_jsons.create_common_jsons(path_to_examples)
    create_jsons_for_generation.create_jsons_for_generation(path_to_examples)

    api_url = config.url().rstrip("/") + "/api_jsonrpc.php"
    headers = {"Content-type": "application/json-rpc"}

    token_source = config.token()
    token = None
    if token_source and token_source != "none":
        if glob.glob(token_source):
            token = _get_token(api_url, headers, token_source)
        else:
            token = token_source
    if not token:
        logger.info("Running without authentication token.")

    iface_request_count = config.max_iface_req_count()
    max_errors = config.max_error_count()
    max_time = config.max_time()
    num_workers = config.workers()

    # Resume state (improvement #4)
    saved = _load_state()
    if saved:
        answer = input("Previous fuzzing state found. Resume? [y/N]: ").strip().lower()
        if answer == "y":
            request_count = saved.get("request_count", 0)
            response_count = saved.get("response_count", 0)
            error_response_count = saved.get("error_response_count", 0)
            json_error_count = saved.get("json_error_count", 0)
            interface_coverage_count = saved.get("interface_coverage_count", 0)
            errors = saved.get("errors", [])
            fuzzing_time = saved.get("fuzzing_time", 0.0)
            logger.info(
                "Resumed: %d requests, %d errors so far.",
                request_count, error_response_count,
            )
        else:
            _clear_state()
            request_count = response_count = error_response_count = 0
            json_error_count = interface_coverage_count = 0
            errors = []
            fuzzing_time = 0.0
    else:
        request_count = response_count = error_response_count = 0
        json_error_count = interface_coverage_count = 0
        errors = []
        fuzzing_time = 0.0

    report = {
        "Count of requests": 0,
        "Count of responses": 0,
        "Count of error responses": 0,
        "Count of JSON-RPC errors": 0,
        "Interfaces covered": 0,
        "Total interfaces": len([
            m for m in os.listdir(path_to_examples)
            if os.path.isdir(os.path.join(path_to_examples, m))
        ]),
        "Full fuzzing time": 0.0,
        "Time per request": 0.0,
        "Errors": [],
    }

    # Optional SSH monitoring
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cpu_list, mem_list = [], []
    ssh_connected = False
    if config.ssh_ip():
        try:
            ssh_client.connect(
                hostname=config.ssh_ip(),
                username=config.ssh_user(),
                password=config.ssh_password(),
                port=22,
            )
            ssh_connected = True
            cpu_list.append(_ssh_cpu(ssh_client))
            mem_list.append(_ssh_mem(ssh_client))
        except Exception as exc:
            logger.warning("SSH monitoring unavailable: %s", exc)

    token_holder = [token]
    token_lock = threading.Lock()

    start_time = timeit.default_timer()

    try:
        while fuzzing_time < max_time and error_response_count < max_errors:
            for method in os.listdir(path_to_examples):
                method_path = os.path.join(path_to_examples, method)
                if not os.path.isdir(method_path):
                    continue
                rule_problem = 0
                files = glob.glob(os.path.join(method_path, "*.json"))

                # Build list of tasks for this method
                tasks = [file for file in files for _ in range(iface_request_count)]

                with ThreadPoolExecutor(max_workers=num_workers) as executor:
                    futures = {
                        executor.submit(
                            _send_one, file, api_url, headers,
                            token_holder, token_lock, token_source,
                        ): file
                        for file in tasks
                    }
                    for future in as_completed(futures):
                        request_count += 1
                        try:
                            status, error, responded = future.result()
                        except Exception as exc:
                            logger.warning("Worker error: %s", exc)
                            continue

                        if responded:
                            response_count += 1

                        if status == "forbidden":
                            rule_problem += 1
                        elif status == "json_error":
                            json_error_count += 1
                        elif status == "error":
                            error_response_count += 1
                            errors.append(error)

                fuzzing_time = timeit.default_timer() - start_time

                if ssh_connected:
                    try:
                        cpu_list.append(_ssh_cpu(ssh_client))
                        mem_list.append(_ssh_mem(ssh_client))
                    except Exception:
                        pass

                if not rule_problem:
                    interface_coverage_count += 1

            if config.CONFIG.get("MAX_TIME") == "none" and config.CONFIG.get("MAX_ERROR_COUNT") == "none":
                break

            # Persist state after each full pass (improvement #4)
            _save_state({
                "request_count": request_count,
                "response_count": response_count,
                "error_response_count": error_response_count,
                "json_error_count": json_error_count,
                "interface_coverage_count": interface_coverage_count,
                "errors": errors,
                "fuzzing_time": fuzzing_time,
            })

    except KeyboardInterrupt:
        logger.info("Interrupted — saving state for resume.")
        _save_state({
            "request_count": request_count,
            "response_count": response_count,
            "error_response_count": error_response_count,
            "json_error_count": json_error_count,
            "interface_coverage_count": interface_coverage_count,
            "errors": errors,
            "fuzzing_time": fuzzing_time,
        })
        ssh_client.close()
        return

    fuzzing_time = timeit.default_timer() - start_time
    _clear_state()
    ssh_client.close()

    report.update({
        "Count of requests": request_count,
        "Count of responses": response_count,
        "Count of error responses": error_response_count,
        "Count of JSON-RPC errors": json_error_count,
        "Interfaces covered": interface_coverage_count,
        "Full fuzzing time": "%.3f" % fuzzing_time,
        "Time per request": "%.3f" % (fuzzing_time / request_count if request_count else 0),
        "Errors": errors,
    })

    fmt = config.report_format()
    if fmt != "default":
        create_report.create_report(report, fmt)

    logger.info("\nFuzzing result:")
    for key, value in report.items():
        if key != "Errors":
            logger.info("  %s: %s", key, value)
    if errors:
        logger.info("\nAll errors:")
        for num, item in enumerate(errors):
            logger.info("#%d", num)
            for pair in item.items():
                logger.info("  %s", str(pair))


def _ssh_cpu(client):
    cmd = "j=0.0;for i in `top -b -n 1 | awk {'print $9'} | tail -n +8`; do j=$(echo '$j + $i' | bc); done; echo $j"
    return client.exec_command(cmd)[1].read().decode()


def _ssh_mem(client):
    return client.exec_command("vmstat -s | grep 'used memory' | awk {'print $1'}")[1].read().decode()


if __name__ == "__main__":
    logger.info("Welcome to DPFuzz!")
    dpfuzz()
