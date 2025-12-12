"""
Spytest SSH Connection Validation Script
Loads testbed YAML and performs SSH connectivity check.

Logs stored at:
  /home/adminuser/Shiva/sonic-mgmt/spytest/tests/logs/
"""

from __future__ import annotations
import yaml
import pytest
from datetime import datetime
from pathlib import Path
import paramiko
from spytest import st
from spytest import SpyTestDict
import apis.system.basic as basic_api

# YAML file path
YAML_PATH = "/home/adminuser/Shiva/sonic-mgmt/spytest/testbeds/vs_sonic.yaml"

# Log directory
LOG_DIR = "/home/adminuser/Shiva/sonic-mgmt/spytest/tests/logs"


def load_testbed_yaml() -> SpyTestDict:
    """Load DUT details from YAML testbed file."""
    if not Path(YAML_PATH).is_file():
        raise FileNotFoundError(f"Testbed YAML not found: {YAML_PATH}")

    with open(YAML_PATH, "r") as f:
        data = yaml.safe_load(f)

    return SpyTestDict(data)


def create_log_file(test_name: str) -> Path:
    """Create timestamp-based log filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(LOG_DIR) / f"{test_name}_{timestamp}.log"

    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    log_file.touch()

    st.log(f"Log file created: {log_file}")
    return log_file


@pytest.fixture(scope="module")
def testbed_data():
    """Return loaded testbed data for all tests."""
    data = load_testbed_yaml()
    st.log("Successfully loaded YAML testbed data.")
    return data


def test_load_yaml(testbed_data):
    """Test 1: Validate YAML loading and print DUT details."""
    log_file = create_log_file("test_load_yaml")

    dut = testbed_data.devices["D1"]

    ip = dut.connection_params.ip
    username = dut.connection_params.username
    password = dut.connection_params.password

    st.log(f"DUT Loaded from YAML:")
    st.log(f"  IP Address : {ip}")
    st.log(f"  Username   : {username}")
    st.log(f"  Password   : {password}")

    if not ip or not username:
        st.report_fail("msg", "YAML missing required connection fields")

    st.report_pass("test_case_passed")



def test_ssh_connection(testbed_data):
    """Test 2: Validate SSH access to DUT using Paramiko inside SpyTest."""
    log_file = create_log_file("test_ssh_connection")

    dut = testbed_data.devices["D1"]

    ip = dut.connection_params.ip
    username = dut.connection_params.username
    password = dut.connection_params.password

    st.log(f"Attempting SSH connection to DUT {ip} using Paramiko...")

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            ip,
            username=username,
            password=password,
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
        st.log("SSH connection established successfully.")
        client.close()
        st.report_pass("test_case_passed")

    except Exception as e:
        st.error(f"SSH FAILED: {e}")
        st.report_fail("msg", f"SSH connection to {ip} failed: {e}")
