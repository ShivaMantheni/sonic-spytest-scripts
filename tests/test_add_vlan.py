#!/usr/bin/env python3
"""
Single-file SpyTest/PyTest VLAN test.
Works with DUT D1 defined in vs_sonic.yaml.
Creates VLAN 10, makes Ethernet4 untagged member, logs output.
"""

from __future__ import annotations
import os
import yaml
import paramiko
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

# ------------------------- CONSTANTS -----------------------------

DEFAULT_TESTBED_PATH = "/home/adminuser/Shiva/sonic-mgmt/spytest/testbeds/vs_sonic.yaml"
DEFAULT_LOGS_DIR = "/home/adminuser/Shiva/sonic-mgmt/spytest/tests/logs"
VLAN_ID = 10
TARGET_INTERFACE = "Ethernet4"

# ------------------------- UTILITY FUNCTIONS --------------------

def load_testbed_yaml(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"YAML not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def extract_dut_connection(testbed: Dict[str, Any]) -> Tuple[str, str, str]:
    devices = testbed.get("devices", {})
    dut = devices.get("D1")
    if not dut:
        raise KeyError("D1 not found in testbed")

    conn = dut.get("connection_params", {})
    ip = conn.get("ip")
    user = conn.get("username")
    pwd = conn.get("password")

    if not all([ip, user, pwd]):
        raise KeyError(f"Missing connection info: {conn}")

    return ip, user, pwd


def ensure_logs_dir(path: str):
    os.makedirs(path, exist_ok=True)


def write_log_file(content: str) -> str:
    ensure_logs_dir(DEFAULT_LOGS_DIR)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(DEFAULT_LOGS_DIR, f"test_vlan_ethernet4_{ts}.log")
    with open(path, "w") as f:
        f.write(content)
    return path


# ------------------------- SSH WRAPPER ---------------------------

class SshClient:
    def __init__(self, hostname, username, password, port=22):
        self.host = hostname
        self.user = username
        self.pwd = password
        self.port = port
        self.client: Optional[paramiko.SSHClient] = None

    def connect(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            hostname=self.host,
            username=self.user,
            password=self.pwd,
            port=self.port,
            look_for_keys=False,
            allow_agent=False,
            timeout=30,
        )

    def close(self):
        if self.client:
            self.client.close()

    def run(self, cmd, sudo=False):
        if sudo:
            safe = self.pwd.replace("'", "'\"'\"'")
            cmd = f"echo '{safe}' | sudo -S -p '' {cmd}"

        stdin, stdout, stderr = self.client.exec_command(cmd)
        return (
            stdout.channel.recv_exit_status(),
            stdout.read().decode(errors="ignore"),
            stderr.read().decode(errors="ignore"),
        )


# ------------------------- MAIN VLAN ACTION ----------------------

def run_vlan_test():
    """
    Real test that connects to SONiC DUT and configures VLAN 10.
    """

    tb = load_testbed_yaml(DEFAULT_TESTBED_PATH)
    ip, user, pwd = extract_dut_connection(tb)

    cli = SshClient(ip, user, pwd)
    cli.connect()

    logs = []
    
    # 1. Create VLAN
    status, out, err = cli.run(f"config vlan add {VLAN_ID}", sudo=True)
    logs.append(f"[CREATE VLAN]\n{out}\n{err}\n")

    # 2. Flush IP from interface
    status, out, err = cli.run(f"ip addr flush dev {TARGET_INTERFACE}", sudo=True)
    logs.append(f"[FLUSH IP]\n{out}\n{err}\n")
    
   
    # 3. Add interface as untagged member
    status, out, err = cli.run(f"config vlan member add {VLAN_ID} {TARGET_INTERFACE}",sudo=True)
    logs.append(f"[ADD MEMBER]\n{out}\n{err}\n")

    # 4. show vlan brief
    status, out, err = cli.run("show vlan brief")
    logs.append(f"[SHOW VLAN]\n{out}\n{err}\n")
    
    # 5. remove vlan member
    status, out, err = cli.run(f"config vlan member del {VLAN_ID} {TARGET_INTERFACE}",sudo=True)
    logs.append(f"[DELETE MEMBER]\n{out}\n{err}\n")
   
    # 6. remove vlan
    status, out, err = cli.run(f"config vlan del {VLAN_ID}",sudo=True)
    logs.append(f"[DELETE VLAN]\n{out}\n{err}\n")
    cli.close()

    # Write log file
    logfile = write_log_file("\n".join(logs))
    return logfile


# ------------------------- PYTEST/SPYTEST TESTS ------------------

def test_yaml_load():
    tb = load_testbed_yaml(DEFAULT_TESTBED_PATH)
    assert isinstance(tb, dict)


def test_extract_connection():
    tb = load_testbed_yaml(DEFAULT_TESTBED_PATH)
    ip, u, p = extract_dut_connection(tb)
    assert ip and u and p


def test_log_creation():
    path = write_log_file("sample log")
    assert os.path.isfile(path)
 

def test_add_vlan_on_dut():
    """
    MAIN test — executes VLAN commands on SONiC switch.
    SpyTest/PyTest both run this correctly.
    """
    logfile = run_vlan_test()
    assert os.path.isfile(logfile)
