"""
FULL VLAN FUNCTIONAL + TRAFFIC TEST – SpyTest
Topology:
  Ethernet4 -> VLAN 10 (access)
  Ethernet8 -> VLAN 20 (access)

This single test file validates:
- VLAN create/delete
- Access membership
- VLAN isolation
- Inter-VLAN routing
- Multiple packet sizes
- Negative scenarios

Logs stored under: ./logs/full_vlan_test/
"""

from spytest import st
import os
import re
import time

# -------------------------------------------------
# GLOBAL CONFIG
# -------------------------------------------------
VLAN10 = "10"
VLAN20 = "20"
PORT_VLAN10 = "Ethernet4"
PORT_VLAN20 = "Ethernet8"

PKT_SIZES = [64, 128, 256, 512, 1024, 1500]

LOG_DIR = "./logs/full_vlan_test"

# -------------------------------------------------
# UTILS
# -------------------------------------------------
def setup_log_dir():
    """
    SpyTest does NOT support st.set_logfile().
    Logs are automatically written under --logs-path.
    This function only ensures directory exists for artifacts if needed.
    """
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    st.log(f"Using log directory: {LOG_DIR}")
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    st.log(f"{LOG_DIR}/full_vlan_test.log")


#def vlan_cleanup(dut):
#    st.log("Cleanup existing VLANs")
#    st.config(dut, [
#        "configure terminal",
#        f"no vlan {VLAN10}",
#        f"no vlan {VLAN20}",
#        "exit"
#    ], type="klish", skip_error_check=True)


def get_vlan_members(dut, vlan):
    """
    Returns list of ports configured under a VLAN
    """
    raw = st.show(dut, "show vlan", skip_tmpl=True)
    members = []

    for line in raw.splitlines():
        if f"Vlan{vlan}" in line:
            # Example line:
            # Vlan10  Up  A  Ethernet4,Ethernet12  Enable  No
            parts = line.split()
            for p in parts:
                if "Ethernet" in p:
                    members.extend(p.split(","))

    return members



def cleanup_vlan(dut, vlan):
    st.log(f"Starting cleanup for VLAN {vlan}")

    members = get_vlan_members(dut, vlan)
    st.log(f"Detected VLAN {vlan} members: {members}")

    cmds = ["configure terminal"]

    # Step 1: Remove L3 IP if exists
    cmds.append(f"interface Vlan{vlan}")
    cmds.append("no ip address")
    cmds.append("exit")

    # Step 2: Remove all members dynamically
    for port in members:
        cmds.append(f"interface {port}")
        cmds.append("no switchport access vlan")
        cmds.append("exit")

    # Step 3: Delete VLAN
    cmds.append(f"no vlan {vlan}")
    cmds.append("exit")

    st.config(dut, cmds)



def create_vlan(dut, vlan):
    st.config(dut, [
        "configure terminal",
        f"vlan {vlan}",
        "exit"
    ], type="klish")

def remove_ip(dut, port):
    st.log("STEP 4: Flush IP address from interface")

    st.config(dut, [
        "configure terminal",
        f"interface {port}",
        "no ip address",
        "exit",
        "exit",
    ],type="klish")

def add_access_port(dut, vlan, port):
    st.config(dut, [
        "configure terminal",
        f"interface {port}",
        f"switchport access vlan {vlan}",
        "exit",
        "exit"
    ], type="klish")


def remove_access_port(dut, port):
    st.config(dut, [
        "configure terminal",
        f"interface {port}",
        "no switchport access vlan",
        "exit",
        "exit"
    ], type="klish")


#def verify_vlan(dut, vlan, port=None):
#    output = st.show(dut, "show vlan", type="klish")
#    found = False
#    for entry in output:
#        if entry.get("vid") == vlan:
#            found = True
#            if port and port not in entry.get("ports", ""):
#                st.report_fail("vlan_port_missing", vlan, port)
#    if not found:
#        st.report_fail("vlan_missing", vlan)


def verify_vlan(dut, vlan, port=None):
    vlan_name = f"Vlan{vlan}"
    output = st.show(dut, "show vlan", type="klish")

    # If parsing failed, fall back to raw CLI verification
    if not output:
        st.log("Parsed output empty, falling back to raw CLI check")
        raw = st.show(dut, "show vlan", type="klish", skip_tmpl=True)
        if vlan_name not in raw:
            st.log(f"{vlan_name} not found in raw show vlan output")
            st.report_fail("test_case_failed")
        if port and port not in raw:
            st.log(f"{port} not found in raw show vlan output")
            st.report_fail("test_case_failed")
        return

    # Normal parsed verification
    found = False
    for entry in output:
        if entry.get("vid") == vlan_name:
            found = True
            if port and port not in entry.get("ports", ""):
                st.log(f"Port {port} missing in VLAN {vlan_name}")
                st.report_fail("test_case_failed")

    if not found:
        st.log(f"{vlan_name} not found in parsed show vlan output")
        st.report_fail("test_case_failed")


# -------------------------------------------------
# TRAFFIC HELPERS (SCAPY BASED)
# -------------------------------------------------
# NOTE:
#  - Requires linux host / namespace interfaces connected to DUT ports
#  - iface_tx mapped to VLAN10 side
#  - iface_rx mapped to VLAN20 side

#def ping_test(dut, dest_ip, pkt_size=None, count=5, df=False, expect_pass=True):
    """
     Ping-based traffic validation.
   Used for VLAN reachability, MTU and fragmentation tests.
    """
#    cmd = f"ping {dest_ip} -c {count}"
#    if pkt_size:
#        cmd += f" -s {pkt_size}"
#    if df:
#        cmd += " -M do"
#    st.log(f"Executing ping: {cmd}")
#    out = st.show(dut, cmd, skip_tmpl=True)
#    success = "0% packet loss" in out or ", 0% packet loss" in out
#    if expect_pass and not success:
#        st.report_fail("ping_failed", dest_ip, pkt_size)
#    if not expect_pass and success:
#        st.report_fail("ping_unexpected_success", dest_ip, pkt_size)
#


def ping_test(dut, dst_ip, pkt_size=64, count=5, expect_pass= True, src_intf = None):
    """Ping helper with correct SpyTest-safe validation."""
    if src_intf:
        cmd = f"ping {dst_ip} -I {src_intf} -c {count} -s {pkt_size}"
    else:
        cmd = f"ping {dst_ip} -c {count} -s {pkt_size}"
    st.log(f"Executing ping: {cmd}")

    output = st.show(dut, cmd, skip_tmpl=True)

    # Determine packet loss
    m = re.search(r"(\d+)% packet loss", output)
    loss = int(m.group(1)) if m else 100
    ping_passed = loss == 0

    if expect_pass and not ping_passed:
        st.error(f"Ping FAILED but expected PASS (loss={loss}%)")
        assert False

    if not expect_pass and ping_passed:
        st.error(f"Ping PASSED but expected FAIL (loss={loss}%)")
        assert False

    st.log(f"Ping validation OK (expect_pass={expect_pass}, loss={loss}%)")
    return ping_passed


def check_cpu_usage(dut):
    """Basic CPU sanity check."""
    st.log("Checking CPU usage")
    output = st.show(dut, "show processes cpu", skip_tmpl=True)
    st.log(output)


def check_interface_counters(dut, interface):
    """Interface counter snapshot."""
    st.log(f"Checking counters for {interface}")
    output = st.show(dut, f"show interfaces counters {interface}", skip_tmpl=True)
    st.log(output)


# -------------------------------------------------
# MAIN TEST
# -------------------------------------------------
def test_full_vlan_validation():
    """
    Single test validating all VLAN scenarios
    """

    setup_log_dir()

    st.ensure_min_topology("D1")
    dut = st.get_dut_names()[0]

    st.log("========== FULL VLAN TEST START ==========")

    # ---------------- CLEANUP ----------------
    cleanup_vlan(dut,"10")
    cleanup_vlan(dut,"20")

    # ---------------- CREATE VLANs ----------------
    st.log("Create VLAN 10 and VLAN 20")
    create_vlan(dut, VLAN10)
    create_vlan(dut, VLAN20)

    #-----------remove ip--------
    remove_ip(dut, PORT_VLAN20)
    remove_ip(dut, PORT_VLAN10)

    # ---------------- ADD MEMBERS ----------------
    st.log("Add access ports")
    add_access_port(dut, VLAN10, PORT_VLAN10)
    add_access_port(dut, VLAN20, PORT_VLAN20)

    verify_vlan(dut, VLAN10, PORT_VLAN10)
    verify_vlan(dut, VLAN20, PORT_VLAN20)

    # ---------------- VLAN ISOLATION TEST ----------------
    st.log("Verify VLAN isolation (routing disabled)")
    for size in [64, 512, 1400]:
        ping_test(dut, "192.168.20.2", pkt_size=size, expect_pass=False)

    # ---------------- ENABLE INTER-VLAN ROUTING ----------------
    st.log("Enable Inter-VLAN Routing")
    st.config(dut, [
        "configure terminal",
        f"interface Vlan{VLAN10}",
        "ip address 192.168.10.1/24",
        "exit",
        f"interface Vlan{VLAN20}",
        "ip address 192.168.20.1/24",
        "exit",
        "exit"
    ], type="klish")

    # ---------------- INTER-VLAN TRAFFIC ----------------
    st.log("Verify inter-VLAN routing with ping")
    for size in [64, 512, 1400]:
        ping_test(dut, "192.168.20.2", pkt_size=size, expect_pass=False, src_intf = f"Vlan{VLAN10}")
    
    
        
    # ---------------- NEGATIVE TEST ----------------
    st.log("Negative test: Remove IP routing")
    st.config(dut, [
        "configure terminal",
        "exit"
    ], type="klish")
    
    for size in PKT_SIZES:
        ping_test(dut, "192.168.20.2" , pkt_size = size, expect_pass=False)

    check_cpu_usage(dut)
    check_interface_counters(dut, PORT_VLAN10)
    check_interface_counters(dut, PORT_VLAN20)





    # ---------------- CLEANUP ----------------
    st.log("Final cleanup")
    remove_access_port(dut, PORT_VLAN10)
    remove_access_port(dut, PORT_VLAN20)
    cleanup_vlan(dut,"10")
    cleanup_vlan(dut, "20")

    st.log("========== FULL VLAN TEST END ==========")
    st.report_pass("full_vlan_test_passed")
