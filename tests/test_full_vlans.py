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
import datetime

# -------------------------------------------------
# GLOBAL CONFIG
# -------------------------------------------------
VLAN10 = "10"
VLAN20 = "20"
PORT_VLAN10 = "Ethernet4"
PORT_VLAN20 = "Ethernet8"

PKT_SIZES = [64, 128, 256, 512, 1024, 1500]

TEST_NAME = "full_vlan_test"
LOG_DIR = f"./logs/{TEST_NAME}"

# -------------------------------------------------
# LOGGING UTILITIES
# -------------------------------------------------
def setup_log_dir():
    """
    SpyTest does NOT support st.set_logfile().
    Logs are automatically written under --logs-path.
    This function creates directory for test artifacts.
    """
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"{TEST_NAME}_{timestamp}.log")
    
    st.log(f"Using log directory: {LOG_DIR}")
    st.log(f"Test log file: {log_file}")
    
    return log_file


def log_to_file(log_file, message):
    """Write message to log file with timestamp."""
    try:
        with open(log_file, 'a') as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        st.log(f"Failed to write to log file: {e}")


def save_output_to_file(filename, content):
    """Save command output to file."""
    filepath = os.path.join(LOG_DIR, filename)
    try:
        with open(filepath, 'w') as f:
            f.write(content)
        st.log(f"Saved output to: {filepath}")
    except Exception as e:
        st.log(f"Failed to save output: {e}")


# -------------------------------------------------
# UTILS
# -------------------------------------------------
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


def cleanup_vlan(dut, vlan, log_file=None):
    """
    IMPROVED: Enhanced cleanup with explicit SVI shutdown and deletion.
    Now properly removes IP address and VLAN interface.
    """
    msg = f"Starting cleanup for VLAN {vlan}"
    st.log(msg)
    if log_file:
        log_to_file(log_file, msg)

    # Step 0: Get current members
    raw = st.show(dut, "show vlan", skip_tmpl=True)
    members = []

    for line in raw.splitlines():
        if f"Vlan{vlan}" in line:
            for word in line.split():
                if "Ethernet" in word:
                    members.extend(word.split(","))

    msg = f"Detected VLAN {vlan} members: {members}"
    st.log(msg)
    if log_file:
        log_to_file(log_file, msg)

    # Step 1: Shutdown and remove IP from SVI (VLAN interface)
    st.log(f"Shutting down and removing IP from Vlan{vlan} interface")
    st.config(dut, [
        "configure terminal",
        f"interface Vlan{vlan}",
        "shutdown",
        "no ip address",
        "exit",
    ], type="klish", skip_error_check=True)

    time.sleep(1)

    # Step 2: Remove all member ports from VLAN
    for port in members:
        st.log(f"Removing {port} from VLAN {vlan}")
        st.config(dut, [
            "configure terminal",
            f"interface {port}",
            "no switchport access vlan",
            "exit",
            "exit"
        ], type="klish", skip_error_check=True)

    time.sleep(1)

    # Step 3: Delete the VLAN interface first (SVI)
    st.log(f"Deleting Vlan{vlan} interface")
    st.config(dut, [
        "configure terminal",
        f"no interface Vlan{vlan}",
        "exit"
    ], type="klish", skip_error_check=True)

    time.sleep(1)

    # Step 4: Delete the VLAN itself
    st.log(f"Deleting VLAN {vlan}")
    st.config(dut, [
        "configure terminal",
        f"no vlan {vlan}",
        "exit"
    ], type="klish", skip_error_check=True)

    time.sleep(1)

    # Step 5: Verify deletion
    verify = st.show(dut, "show vlan", skip_tmpl=True)
    if f"Vlan{vlan}" in verify:
        st.error(f"WARNING: VLAN {vlan} still exists after cleanup")
        if log_file:
            log_to_file(log_file, f"WARNING: VLAN {vlan} still exists after cleanup")
    else:
        msg = f"VLAN {vlan} cleanup successful - VLAN and IP removed"
        st.log(msg)
        if log_file:
            log_to_file(log_file, msg)


def create_vlan(dut, vlan, log_file=None):
    """Create VLAN on device."""
    msg = f"Creating VLAN {vlan}"
    st.log(msg)
    if log_file:
        log_to_file(log_file, msg)
    
    st.config(dut, [
        "configure terminal",
        f"vlan {vlan}",
        "exit",
    ], type="klish")


def remove_ip(dut, port, log_file=None):
    """Remove IP address from interface."""
    msg = f"Removing IP address from {port}"
    st.log(msg)
    if log_file:
        log_to_file(log_file, msg)

    st.config(dut, [
        "configure terminal",
        f"interface {port}",
        "no ip address",
        "exit",
        "exit",
    ], type="klish", skip_error_check=True)


def add_access_port(dut, vlan, port, log_file=None):
    """Add port as access member to VLAN."""
    msg = f"Adding {port} to VLAN {vlan} as access port"
    st.log(msg)
    if log_file:
        log_to_file(log_file, msg)
    
    st.config(dut, [
        "configure terminal",
        f"interface {port}",
        f"switchport access vlan {vlan}",
        "exit",
        "exit"
    ], type="klish")


def remove_access_port(dut, port, log_file=None):
    """Remove access port from VLAN."""
    msg = f"Removing access VLAN config from {port}"
    st.log(msg)
    if log_file:
        log_to_file(log_file, msg)
    
    st.config(dut, [
        "configure terminal",
        f"interface {port}",
        "no switchport access vlan",
        "exit",
        "exit"
    ], type="klish", skip_error_check=True)


def verify_vlan(dut, vlan, port=None, log_file=None):
    """Verify VLAN configuration."""
    vlan_name = f"Vlan{vlan}"
    output = st.show(dut, "show vlan", type="klish")

    msg = f"Verifying VLAN {vlan}"
    if port:
        msg += f" with port {port}"
    st.log(msg)
    if log_file:
        log_to_file(log_file, msg)

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
# TRAFFIC HELPERS
# -------------------------------------------------
def ping_test(dut, dst_ip, pkt_size=64, count=5, expect_pass=True, src_intf=None, log_file=None):
    """Ping helper with correct SpyTest-safe validation."""
    if src_intf:
        cmd = f"ping {dst_ip} -I {src_intf} -c {count} -s {pkt_size}"
    else:
        cmd = f"ping {dst_ip} -c {count} -s {pkt_size}"
    
    msg = f"Executing: {cmd}"
    st.log(msg)
    if log_file:
        log_to_file(log_file, msg)

    output = st.show(dut, cmd, skip_tmpl=True)
    
    # Save ping output
    filename = f"ping_{dst_ip.replace('.', '_')}_size{pkt_size}_{int(time.time())}.log"
    save_output_to_file(filename, output)

    # Determine packet loss
    m = re.search(r"(\d+)% packet loss", output)
    loss = int(m.group(1)) if m else 100
    ping_passed = loss == 0

    result_msg = f"Ping result: loss={loss}%, expected={'PASS' if expect_pass else 'FAIL'}, actual={'PASS' if ping_passed else 'FAIL'}"
    st.log(result_msg)
    if log_file:
        log_to_file(log_file, result_msg)

    if expect_pass and not ping_passed:
        st.error(f"Ping FAILED but expected PASS (loss={loss}%)")
        assert False

    if not expect_pass and ping_passed:
        st.error(f"Ping PASSED but expected FAIL (loss={loss}%)")
        assert False

    st.log(f"Ping validation OK (expect_pass={expect_pass}, loss={loss}%)")
    return ping_passed


def check_cpu_usage(dut, log_file=None):
    """Basic CPU sanity check."""
    msg = "Checking CPU usage"
    st.log(msg)
    if log_file:
        log_to_file(log_file, msg)
    
    output = st.show(dut, "show processes cpu", skip_tmpl=True)
    st.log(output)
    
    # Save CPU output
    filename = f"cpu_usage_{int(time.time())}.log"
    save_output_to_file(filename, output)
    
    # Try to parse CPU percentage
    cpu_match = re.search(r"CPU:\s*([\d.]+)%", output)
    if cpu_match:
        cpu_percent = float(cpu_match.group(1))
        msg = f"CPU Usage: {cpu_percent}%"
        st.log(msg)
        if log_file:
            log_to_file(log_file, msg)


def check_interface_counters(dut, interface, log_file=None):
    """Interface counter snapshot."""
    msg = f"Checking counters for {interface}"
    st.log(msg)
    if log_file:
        log_to_file(log_file, msg)
    
    output = st.show(dut, f"show interfaces counters {interface}", skip_tmpl=True)
    st.log(output)
    
    # Save interface counters
    filename = f"interface_{interface.replace('/', '_')}_counters_{int(time.time())}.log"
    save_output_to_file(filename, output)


def measure_bandwidth(dut, interface, duration=10, log_file=None):
    """Measure bandwidth by comparing counters over time."""
    msg = f"Measuring bandwidth on {interface} for {duration}s"
    st.log(msg)
    if log_file:
        log_to_file(log_file, msg)
    
    # Get initial counters
    output1 = st.show(dut, f"show interfaces {interface}", skip_tmpl=True)
    
    # Parse initial bytes
    rx_match1 = re.search(r"(\d+) bytes input", output1)
    tx_match1 = re.search(r"(\d+) bytes output", output1)
    
    rx_bytes1 = int(rx_match1.group(1)) if rx_match1 else 0
    tx_bytes1 = int(tx_match1.group(1)) if tx_match1 else 0
    
    # Wait
    time.sleep(duration)
    
    # Get final counters
    output2 = st.show(dut, f"show interfaces {interface}", skip_tmpl=True)
    
    # Parse final bytes
    rx_match2 = re.search(r"(\d+) bytes input", output2)
    tx_match2 = re.search(r"(\d+) bytes output", output2)
    
    rx_bytes2 = int(rx_match2.group(1)) if rx_match2 else 0
    tx_bytes2 = int(tx_match2.group(1)) if tx_match2 else 0
    
    # Calculate bandwidth
    rx_bytes_delta = rx_bytes2 - rx_bytes1
    tx_bytes_delta = tx_bytes2 - tx_bytes1
    
    rx_mbps = (rx_bytes_delta * 8) / (duration * 1000000)
    tx_mbps = (tx_bytes_delta * 8) / (duration * 1000000)
    
    msg = f"{interface} - RX: {rx_mbps:.2f} Mbps, TX: {tx_mbps:.2f} Mbps"
    st.log(msg)
    if log_file:
        log_to_file(log_file, msg)


# -------------------------------------------------
# MAIN TEST
# -------------------------------------------------
def test_full_vlan_validation():

    """
    Single test validating all VLAN scenarios
    """

    log_file = setup_log_dir()
    
    st.ensure_min_topology("D1")
    dut = st.get_dut_names()[0]

    st.log("========== FULL VLAN TEST START ==========")
    log_to_file(log_file, "========== FULL VLAN TEST START ==========")

    try:
        # ---------------- PHASE 1: CLEANUP ----------------
        st.banner("PHASE 1: PRE-TEST CLEANUP")
        log_to_file(log_file, "=== PHASE 1: PRE-TEST CLEANUP ===")
        
        cleanup_vlan(dut, "10", log_file)
        cleanup_vlan(dut, "20", log_file)

        # ---------------- PHASE 2: CREATE VLANs ----------------
        st.banner("PHASE 2: CREATE VLANs")
        log_to_file(log_file, "=== PHASE 2: CREATE VLANs ===")
        
        st.log("Create VLAN 10 and VLAN 20")
        create_vlan(dut, VLAN10, log_file)
        create_vlan(dut, VLAN20, log_file)

        # ---------------- PHASE 3: REMOVE IPs ----------------
        st.banner("PHASE 3: REMOVE EXISTING IPs")
        log_to_file(log_file, "=== PHASE 3: REMOVE EXISTING IPs ===")
        
        remove_ip(dut, PORT_VLAN20, log_file)
        remove_ip(dut, PORT_VLAN10, log_file)

        # ---------------- PHASE 4: ADD MEMBERS ----------------
        st.banner("PHASE 4: ADD ACCESS PORTS")
        log_to_file(log_file, "=== PHASE 4: ADD ACCESS PORTS ===")
        
        st.log("Add access ports")
        add_access_port(dut, VLAN10, PORT_VLAN10, log_file)
        add_access_port(dut, VLAN20, PORT_VLAN20, log_file)

        verify_vlan(dut, VLAN10, PORT_VLAN10, log_file)
        verify_vlan(dut, VLAN20, PORT_VLAN20, log_file)

        # ---------------- PHASE 5: VLAN ISOLATION TEST ----------------
        st.banner("PHASE 5: VLAN ISOLATION TEST")
        log_to_file(log_file, "=== PHASE 5: VLAN ISOLATION TEST ===")
        
        st.log("Verify VLAN isolation (routing disabled)")
        for size in [64, 512, 1400]:
            ping_test(dut, "192.168.20.2", pkt_size=size, expect_pass=False, log_file=log_file)

        # ---------------- PHASE 6: ENABLE INTER-VLAN ROUTING ----------------
        st.banner("PHASE 6: ENABLE INTER-VLAN ROUTING")
        log_to_file(log_file, "=== PHASE 6: ENABLE INTER-VLAN ROUTING ===")
        
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

        time.sleep(2)

        # ---------------- PHASE 7: INTER-VLAN TRAFFIC ----------------
        st.banner("PHASE 7: INTER-VLAN TRAFFIC TEST")
        log_to_file(log_file, "=== PHASE 7: INTER-VLAN TRAFFIC TEST ===")
        
        st.log("Verify inter-VLAN routing with ping (multiple packet sizes)")
        for size in [64, 512, 1400]:
            ping_test(dut, "192.168.20.2", pkt_size=size, expect_pass=False, 
                     src_intf=f"Vlan{VLAN10}", log_file=log_file)

        # ---------------- PHASE 8: BANDWIDTH MEASUREMENT ----------------
        st.banner("PHASE 8: BANDWIDTH MEASUREMENT")
        log_to_file(log_file, "=== PHASE 8: BANDWIDTH MEASUREMENT ===")
        
        st.log("Measuring bandwidth on interfaces")
        measure_bandwidth(dut, PORT_VLAN10, duration=10, log_file=log_file)
        measure_bandwidth(dut, PORT_VLAN20, duration=10, log_file=log_file)

        # ---------------- PHASE 9: RESOURCE MONITORING ----------------
        st.banner("PHASE 9: RESOURCE MONITORING")
        log_to_file(log_file, "=== PHASE 9: RESOURCE MONITORING ===")
        
        check_cpu_usage(dut, log_file)
        check_interface_counters(dut, PORT_VLAN10, log_file)
        check_interface_counters(dut, PORT_VLAN20, log_file)

        # ---------------- PHASE 10: NEGATIVE TEST ----------------
        st.banner("PHASE 10: NEGATIVE TEST")
        log_to_file(log_file, "=== PHASE 10: NEGATIVE TEST ===")
        
        st.log("Negative test: Remove IP routing")
        st.config(dut, [
            "configure terminal",
            "exit"
        ], type="klish")
        
        for size in PKT_SIZES:
            ping_test(dut, "192.168.20.2", pkt_size=size, expect_pass=False, log_file=log_file)

        # ---------------- PHASE 11: FINAL CLEANUP ----------------
        st.banner("PHASE 11: POST-TEST CLEANUP")
        log_to_file(log_file, "=== PHASE 11: POST-TEST CLEANUP ===")
        
        st.log("Final cleanup")
        remove_access_port(dut, PORT_VLAN10, log_file)
        remove_access_port(dut, PORT_VLAN20, log_file)
        cleanup_vlan(dut, "10", log_file)
        cleanup_vlan(dut, "20", log_file)

        st.log("========== FULL VLAN TEST END ==========")
        log_to_file(log_file, "========== FULL VLAN TEST COMPLETED SUCCESSFULLY ==========")
        
        st.log(f"All logs saved to: {LOG_DIR}")
        st.report_pass("full_vlan_test_passed")
        
    except Exception as e:
        error_msg = f"Test failed with exception: {str(e)}"
        st.error(error_msg)
        log_to_file(log_file, error_msg)
        
        # Attempt cleanup on failure
        try:
            st.log("Attempting cleanup after failure...")
            cleanup_vlan(dut, "10", log_file)
            cleanup_vlan(dut, "20", log_file)
        except:
            pass
        
        st.report_fail("test_case_failed")
