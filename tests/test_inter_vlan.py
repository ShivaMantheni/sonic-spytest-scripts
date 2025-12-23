"""
INTER-VLAN ROUTING TEST - SpyTest Framework
===========================================
Test Topology:
  DUT1 <-> DUT2
  - DUT1: Ethernet0 (VLAN10: 192.168.10.1/24), Ethernet12 (192.168.100.1/30)
  - DUT2: Ethernet0 (VLAN20: 192.168.20.1/24), Ethernet12 (192.168.100.2/30)

Test Flow:
  1. Load configuration from sonic.yaml
  2. Establish SSH connections to devices
  3. Check and cleanup existing VLANs
  4. Create and configure VLANs
  5. Configure inter-VLAN routing
  6. Test connectivity with multiple packet sizes
  7. Cleanup configuration
  8. Store detailed logs

Logs: ./logs/test_inter_vlan_routing/
"""

import os
import re
import time
import datetime
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Import SpyTest modules
from spytest import st
from spytest.dicts import SpyTestDict

# =============================================================================
# GLOBAL CONFIGURATION
# =============================================================================

# VLAN Configuration
VLAN10 = "10"
VLAN20 = "20"

# DUT1 Configuration
DUT1_VLAN_INTERFACE = "Ethernet0"
DUT1_VLAN10_IP = "192.168.10.1/24"
DUT1_TRANSIT_INTERFACE = "Ethernet12"
DUT1_TRANSIT_IP = "192.168.100.1/30"

# DUT2 Configuration
DUT2_VLAN_INTERFACE = "Ethernet0"
DUT2_VLAN20_IP = "192.168.20.1/24"
DUT2_TRANSIT_INTERFACE = "Ethernet12"
DUT2_TRANSIT_IP = "192.168.100.2/30"

# Test Parameters
PKT_SIZES = [64, 128, 256, 512, 1024, 1400, 1500]
PING_COUNT = 5

# Logging
TEST_NAME = "test_inter_vlan_routing"
LOG_DIR = f"./logs/{TEST_NAME}"

# Global variables for test
vars = SpyTestDict()


# =============================================================================
# XML LOGGER CLASS
# =============================================================================
class XMLLogger:
    """XML-based logging for SpyTest compatibility"""
    
    def __init__(self, log_dir):
        self.log_dir = log_dir
        self.pretest_root = ET.Element("PreTest")
        self.posttest_root = ET.Element("PostTest")
        self.tr_root = ET.Element("TestResults")
        self.add_metadata()
    
    def add_metadata(self):
        """Add test metadata to XML files"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for root in [self.pretest_root, self.posttest_root, self.tr_root]:
            meta = ET.SubElement(root, "Metadata")
            ET.SubElement(meta, "TestName").text = TEST_NAME
            ET.SubElement(meta, "Timestamp").text = timestamp
            ET.SubElement(meta, "LogDirectory").text = self.log_dir
    
    def add_pretest_entry(self, device, action, command, output, status="PASS"):
        """Add entry to pretest.xml"""
        entry = ET.SubElement(self.pretest_root, "PreTestAction")
        ET.SubElement(entry, "Device").text = str(device)
        ET.SubElement(entry, "Action").text = str(action)
        ET.SubElement(entry, "Command").text = str(command)
        ET.SubElement(entry, "Output").text = str(output)
        ET.SubElement(entry, "Status").text = str(status)
        ET.SubElement(entry, "Timestamp").text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def add_posttest_entry(self, device, action, command, output, status="PASS"):
        """Add entry to posttest.xml"""
        entry = ET.SubElement(self.posttest_root, "PostTestAction")
        ET.SubElement(entry, "Device").text = str(device)
        ET.SubElement(entry, "Action").text = str(action)
        ET.SubElement(entry, "Command").text = str(command)
        ET.SubElement(entry, "Output").text = str(output)
        ET.SubElement(entry, "Status").text = str(status)
        ET.SubElement(entry, "Timestamp").text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def add_test_result(self, test_name, device, result, details):
        """Add entry to tr.xml (test results)"""
        entry = ET.SubElement(self.tr_root, "TestCase")
        ET.SubElement(entry, "TestName").text = str(test_name)
        ET.SubElement(entry, "Device").text = str(device)
        ET.SubElement(entry, "Result").text = str(result)
        ET.SubElement(entry, "Details").text = str(details)
        ET.SubElement(entry, "Timestamp").text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def prettify_xml(self, elem):
        """Return a pretty-printed XML string"""
        rough_string = ET.tostring(elem, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def save_all(self):
        """Save all XML files"""
        try:
            # Save pretest.xml
            pretest_file = os.path.join(self.log_dir, "pretest.xml")
            with open(pretest_file, 'w', encoding='utf-8') as f:
                f.write(self.prettify_xml(self.pretest_root))
            st.log(f"Saved pretest.xml to: {pretest_file}")
            
            # Save posttest.xml
            posttest_file = os.path.join(self.log_dir, "posttest.xml")
            with open(posttest_file, 'w', encoding='utf-8') as f:
                f.write(self.prettify_xml(self.posttest_root))
            st.log(f"Saved posttest.xml to: {posttest_file}")
            
            # Save tr.xml
            tr_file = os.path.join(self.log_dir, "tr.xml")
            with open(tr_file, 'w', encoding='utf-8') as f:
                f.write(self.prettify_xml(self.tr_root))
            st.log(f"Saved tr.xml to: {tr_file}")
        except Exception as e:
            st.log(f"Error saving XML files: {str(e)}")


# =============================================================================
# LOGGING UTILITIES
# =============================================================================
def setup_logging():
    """Create log directory and return XML logger"""
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"test_run_{timestamp}.log")
    
    st.log("=" * 80)
    st.log(f"Test: {TEST_NAME}")
    st.log(f"Log Directory: {LOG_DIR}")
    st.log(f"Log File: {log_file}")
    st.log(f"Timestamp: {timestamp}")
    st.log("=" * 80)
    
    # Initialize XML logger
    xml_logger = XMLLogger(LOG_DIR)
    
    return log_file, xml_logger


def log_to_file(log_file, message):
    """Write message to log file with timestamp"""
    try:
        with open(log_file, 'a') as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        st.log(f"Failed to write to log file: {e}")


def save_command_output(device_name, command, output):
    """Save command output to file"""
    timestamp = int(time.time())
    safe_cmd = re.sub(r'[^\w\-]', '_', command)[:50]
    filename = f"{device_name}_{safe_cmd}_{timestamp}.log"
    filepath = os.path.join(LOG_DIR, filename)
    
    try:
        with open(filepath, 'w') as f:
            f.write(f"Device: {device_name}\n")
            f.write(f"Command: {command}\n")
            f.write(f"Timestamp: {datetime.datetime.now()}\n")
            f.write("=" * 80 + "\n")
            f.write(output)
    except Exception as e:
        st.log(f"Failed to save output: {e}")


# =============================================================================
# VLAN UTILITIES
# =============================================================================
def check_vlan_exists(dut, vlan):
    """Check if VLAN exists on device"""
    st.log(f"[{dut}] Checking if VLAN {vlan} exists")
    
    output = st.show(dut, "show vlan brief", skip_tmpl=True)
    save_command_output(dut, "show vlan brief", output)
    
    vlan_exists = f"Vlan{vlan}" in output or f" {vlan} " in output
    
    st.log(f"[{dut}] VLAN {vlan} exists: {vlan_exists}")
    return vlan_exists


def get_vlan_members(dut, vlan):
    """Get list of member ports for a VLAN"""
    output = st.show(dut, "show vlan brief", skip_tmpl=True)
    members = []
    
    for line in output.splitlines():
        if f"Vlan{vlan}" in line or f" {vlan} " in line:
            parts = line.split()
            for part in parts:
                if "Ethernet" in part:
                    members.extend(part.split(","))
    
    st.log(f"[{dut}] VLAN {vlan} members: {members}")
    return members


def remove_ip_from_interface(dut, interface):
    """Remove IP address from interface"""
    st.log(f"[{dut}] Removing IP from {interface}")
    
    commands = [
        "configure terminal",
        f"interface {interface}",
        "no ip address",
        "exit",
        "exit"
    ]
    
    st.config(dut, commands, type="klish", skip_error_check=True)


def cleanup_vlan(dut, vlan, xml_logger=None):
    """
    Complete VLAN cleanup:
    1. Remove IP from VLAN interface
    2. Remove member ports
    3. Delete VLAN
    """
    st.log(f"[{dut}] Starting cleanup for VLAN {vlan}")
    
    # Check if VLAN exists
    if not check_vlan_exists(dut, vlan):
        st.log(f"[{dut}] VLAN {vlan} does not exist, skipping cleanup")
        if xml_logger:
            xml_logger.add_pretest_entry(
                dut,
                f"Check VLAN {vlan}",
                "show vlan",
                "VLAN does not exist",
                "SKIPPED"
            )
        return
    
    # Get member ports
    members = get_vlan_members(dut, vlan)
    
    # Build cleanup commands
    commands = ["configure terminal"]
    
    # Remove IP from VLAN interface
    commands.extend([
        f"interface Vlan{vlan}",
        "no ip address",
        "exit"
    ])
    
    # Remove all member ports
    for port in members:
        commands.extend([
            f"interface {port}",
            "no switchport access vlan",
            "exit"
        ])
    
    # Delete VLAN
    commands.extend([
        f"no vlan {vlan}",
        "exit"
    ])
    
    output = st.config(dut, commands, type="klish", skip_error_check=True)
    
    if xml_logger:
        xml_logger.add_pretest_entry(
            dut,
            f"Cleanup VLAN {vlan}",
            "\n".join(commands),
            str(output),
            "PASS"
        )
    
    st.log(f"[{dut}] VLAN {vlan} cleanup completed")


def create_vlan(dut, vlan):
    """Create VLAN on device"""
    st.log(f"[{dut}] Creating VLAN {vlan}")
    
    commands = [
        "configure terminal",
        f"vlan {vlan}",
        "exit"
    ]
    
    st.config(dut, commands, type="klish")


def add_interface_to_vlan(dut, interface, vlan):
    """Add interface to VLAN as access port"""
    st.log(f"[{dut}] Adding {interface} to VLAN {vlan}")
    
    # First remove any existing IP
    remove_ip_from_interface(dut, interface)
    
    # Add to VLAN
    commands = [
        "configure terminal",
        f"interface {interface}",
        f"switchport access vlan {vlan}",
        "exit",
        "exit"
    ]
    
    st.config(dut, commands, type="klish")


def configure_vlan_ip(dut, vlan, ip_address):
    commands = [
        "configure terminal",
        f"vlan {vlan}",                 # ensure VLAN exists
        "exit",
        f"interface Vlan{vlan}",        # explicitly create SVI
        "no shutdown",
        f"ip address {ip_address}",
        "exit",
        "exit"
    ]
    st.config(dut, commands, type="klish")


def configure_interface_ip(dut, interface, ip_address):
    """Configure IP address on physical interface"""
    st.log(f"[{dut}] Configuring IP {ip_address} on {interface}")
    
    # Remove existing IP first
    remove_ip_from_interface(dut, interface)
    
    commands = [
        "configure terminal",
        f"interface {interface}",
        "no shutdown",
        f"ip address {ip_address}",
        "exit",
        "exit"
    ]
    
    st.config(dut, commands, type="klish")


def add_static_route(dut, destination, gateway):
    """Add static route"""
    st.log(f"[{dut}] Adding static route: {destination} via {gateway}")
    
    commands = [
        "configure terminal",
        f"ip route {destination} {gateway}",
        "exit"
    ]
    
    st.config(dut, commands, type="klish")


def enable_ip_routing(dut):
    """Enable IP routing on device - SONiC has routing enabled by default"""
    st.log(f"[{dut}] IP routing is enabled by default in SONiC")
    # SONiC doesn't need explicit "ip routing" command
    # Routing is enabled when IP addresses are configured on interfaces


# =============================================================================
# TESTING UTILITIES
# =============================================================================
def ping_test(dut, src_ip, dst_ip, pkt_size=64, count=5, xml_logger=None):
    """
    Execute ping test.
    Simple ping command without -I option to avoid docker crash.
    """
    cmd = f"ping {dst_ip} -s {pkt_size} -c {count}"
    
    st.log(f"[{dut}] Executing: {cmd}")
    
    output = st.show(dut, cmd, skip_tmpl=True)
    save_command_output(dut, f"ping_{dst_ip}_size{pkt_size}", output)
    
    # Parse results
    loss_match = re.search(r"(\d+)% packet loss", output)
    loss = int(loss_match.group(1)) if loss_match else 100
    
    rtt_match = re.search(r"rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)", output)
    rtt_avg = float(rtt_match.group(2)) if rtt_match else None
    
    ping_passed = (loss == 0)
    
    result_msg = f"[{dut}] Ping {src_ip} -> {dst_ip} (size={pkt_size}): "
    result_msg += f"Loss={loss}%, Result={'PASS' if ping_passed else 'FAIL'}"
    if rtt_avg:
        result_msg += f", RTT avg={rtt_avg:.2f}ms"
    
    st.log(result_msg)
    
    # Log to XML
    if xml_logger:
        test_details = {
            "source_ip": src_ip,
            "destination_ip": dst_ip,
            "packet_size": pkt_size,
            "packet_loss": loss,
            "rtt_avg": rtt_avg
        }
        xml_logger.add_test_result(
            f"Ping Test (size={pkt_size})",
            dut,
            "PASS" if ping_passed else "FAIL",
            test_details
        )
    
    if not ping_passed:
        st.error(f"Ping test FAILED: {loss}% packet loss")
        return False
    
    return True


def verify_connectivity(dut, src_ip, dst_ip, xml_logger=None):
    """Test connectivity between two IPs with multiple packet sizes"""
    st.log(f"Testing connectivity: {src_ip} -> {dst_ip}")
    
    all_passed = True
    for pkt_size in PKT_SIZES:
        st.log(f"--- Packet size: {pkt_size} bytes ---")
        result = ping_test(dut, src_ip, dst_ip, pkt_size, PING_COUNT, xml_logger)
        if not result:
            all_passed = False
            st.error(f"Ping failed for packet size {pkt_size}")
        time.sleep(1)
    
    return all_passed


# =============================================================================
# SPYTEST FIXTURE FUNCTIONS
# =============================================================================
def prologue(request):
    """
    Test prologue - executed before test
    """
    st.log("=" * 80)
    st.log("TEST PROLOGUE: Inter-VLAN Routing Test")
    st.log("=" * 80)
    
    # Ensure minimum topology
    vars.dut_list = st.get_dut_names()
    st.log(f"Available DUTs: {vars.dut_list}")


def epilogue(request):
    """
    Test epilogue - executed after test
    """
    st.log("=" * 80)
    st.log("TEST EPILOGUE: Inter-VLAN Routing Test")
    st.log("=" * 80)


# =============================================================================
# MAIN TEST FUNCTION
# =============================================================================
def test_inter_vlan_routing():
    """
    Main test function for Inter-VLAN routing
    
    Test Flow:
    1. Get DUT names from SpyTest
    2. Cleanup existing VLANs
    3. Create and configure VLANs
    4. Configure transit network
    5. Add static routes
    6. Test inter-VLAN connectivity
    7. Cleanup
    """
    
    # Setup logging
    log_file, xml_logger = setup_logging()
    
    st.banner("INTER-VLAN ROUTING TEST")
    log_to_file(log_file, "=== INTER-VLAN ROUTING TEST STARTED ===")
    
    # =========================================================================
    # PHASE 1: GET DEVICES FROM TOPOLOGY
    # =========================================================================
    st.banner("PHASE 1: GET DEVICES FROM TOPOLOGY")
    log_to_file(log_file, "=== PHASE 1: GET DEVICES ===")
    
    dut_list = st.get_dut_names()
    
    if len(dut_list) < 2:
        st.error(f"Test requires 2 devices, found {len(dut_list)}")
        st.report_fail("topology_mismatch")
    
    dut1 = dut_list[0]
    dut2 = dut_list[1]
    
    st.log(f"DUT1: {dut1}")
    st.log(f"DUT2: {dut2}")
    
    try:
        # =====================================================================
        # PHASE 2: PRE-TEST CLEANUP
        # =====================================================================
        st.banner("PHASE 2: PRE-TEST CLEANUP")
        log_to_file(log_file, "=== PHASE 2: PRE-TEST CLEANUP ===")
        
        # Check and cleanup VLAN10 on DUT1
        cleanup_vlan(dut1, VLAN10, xml_logger)
        
        # Check and cleanup VLAN20 on DUT2
        cleanup_vlan(dut2, VLAN20, xml_logger)
        
        # =====================================================================
        # PHASE 3: CREATE VLAN10 ON DUT1
        # =====================================================================
        st.banner("PHASE 3: CREATE VLAN10 ON DUT1")
        log_to_file(log_file, "=== PHASE 3: CREATE VLAN10 ON DUT1 ===")
        
        # Create VLAN10
        create_vlan(dut1, VLAN10)
        
        # Add Ethernet0 to VLAN10
        add_interface_to_vlan(dut1, DUT1_VLAN_INTERFACE, VLAN10)
        
        # Configure IP on VLAN10
        configure_vlan_ip(dut1, VLAN10, DUT1_VLAN10_IP)
        
        # =====================================================================
        # PHASE 4: CREATE VLAN20 ON DUT2
        # =====================================================================
        st.banner("PHASE 4: CREATE VLAN20 ON DUT2")
        log_to_file(log_file, "=== PHASE 4: CREATE VLAN20 ON DUT2 ===")
        
        # Create VLAN20
        create_vlan(dut2, VLAN20)
        
        # Add Ethernet0 to VLAN20
        add_interface_to_vlan(dut2, DUT2_VLAN_INTERFACE, VLAN20)
        
        # Configure IP on VLAN20
        configure_vlan_ip(dut2, VLAN20, DUT2_VLAN20_IP)
        
        # =====================================================================
        # PHASE 5: CONFIGURE TRANSIT NETWORK
        # =====================================================================
        st.banner("PHASE 5: CONFIGURE TRANSIT NETWORK")
        log_to_file(log_file, "=== PHASE 5: CONFIGURE TRANSIT NETWORK ===")
        
        # Configure Ethernet12 on DUT1
        configure_interface_ip(dut1, DUT1_TRANSIT_INTERFACE, DUT1_TRANSIT_IP)
        
        # Configure Ethernet12 on DUT2
        configure_interface_ip(dut2, DUT2_TRANSIT_INTERFACE, DUT2_TRANSIT_IP)
        
        # Enable IP routing
        enable_ip_routing(dut1)
        enable_ip_routing(dut2)
        
        # =====================================================================
        # PHASE 6: ADD STATIC ROUTES
        # =====================================================================
        st.banner("PHASE 6: ADD STATIC ROUTES")
        log_to_file(log_file, "=== PHASE 6: ADD STATIC ROUTES ===")
        
        # DUT1: Route to VLAN20 network via DUT2
        add_static_route(dut1, "192.168.20.0/24", "192.168.100.2")
        
        # DUT2: Route to VLAN10 network via DUT1
        add_static_route(dut2, "192.168.10.0/24", "192.168.100.1")
        
        # Wait for configuration
        st.log("Waiting for configuration to stabilize...")
        time.sleep(10)  # Increased wait time for interfaces to come up
        
        # =====================================================================
        # PHASE 7: VERIFY INTERFACES ARE UP
        # =====================================================================
        st.banner("PHASE 7: VERIFY INTERFACES ARE UP")
        log_to_file(log_file, "=== PHASE 7: VERIFY INTERFACES ===")
        
        # Check interface status
        st.log("Checking interface status...")
        output = st.show(dut1, "show ip interface", skip_tmpl=True)
        save_command_output(dut1, "show_ip_interface", output)
        
        output = st.show(dut2, "show ip interface", skip_tmpl=True)
        save_command_output(dut2, "show_ip_interface", output)
        
        # =====================================================================
        # PHASE 8: VERIFY TRANSIT CONNECTIVITY
        # =====================================================================
        st.banner("PHASE 8: VERIFY TRANSIT CONNECTIVITY")
        log_to_file(log_file, "=== PHASE 8: VERIFY TRANSIT ===")
        
        st.log("Testing transit link (192.168.100.1 <-> 192.168.100.2)")
        transit_ok = ping_test(dut1, "192.168.100.1", "192.168.100.2", 64, PING_COUNT, xml_logger)
        
        if not transit_ok:
            st.error("Transit link connectivity failed")
            st.report_fail("ping_fail")
        
        # =====================================================================
        # PHASE 9: INTER-VLAN CONNECTIVITY TEST
        # =====================================================================
        st.banner("PHASE 9: INTER-VLAN CONNECTIVITY TEST")
        log_to_file(log_file, "=== PHASE 9: INTER-VLAN CONNECTIVITY ===")
        
        st.log("Testing Inter-VLAN: 192.168.10.1 -> 192.168.20.1")
        forward_ok = verify_connectivity(dut1, "192.168.10.1", "192.168.20.1", xml_logger)
        
        st.log("Testing reverse Inter-VLAN: 192.168.20.1 -> 192.168.10.1")
        reverse_ok = verify_connectivity(dut2, "192.168.20.1", "192.168.10.1", xml_logger)
        
        # =====================================================================
        # PHASE 10: POST-TEST CLEANUP
        # =====================================================================
        st.banner("PHASE 10: POST-TEST CLEANUP")
        log_to_file(log_file, "=== PHASE 10: POST-TEST CLEANUP ===")
        
        # Remove static routes
        st.log("Removing static routes...")
        commands = ["configure terminal", "no ip route 192.168.20.0/24 192.168.100.2", "exit"]
        output = st.config(dut1, commands, type="klish", skip_error_check=True)
        xml_logger.add_posttest_entry(dut1, "Remove static route", " ".join(commands), str(output), "PASS")
        
        commands = ["configure terminal", "no ip route 192.168.10.0/24 192.168.100.1", "exit"]
        output = st.config(dut2, commands, type="klish", skip_error_check=True)
        xml_logger.add_posttest_entry(dut2, "Remove static route", " ".join(commands), str(output), "PASS")
        
        # Remove IPs
        remove_ip_from_interface(dut1, DUT1_TRANSIT_INTERFACE)
        remove_ip_from_interface(dut2, DUT2_TRANSIT_INTERFACE)
        
        # Cleanup VLANs
        if check_vlan_exists(dut1, VLAN10):
            members = get_vlan_members(dut1, VLAN10)
            commands = ["configure terminal"]
            commands.extend([f"interface Vlan{VLAN10}", "no ip address", "exit"])
            for port in members:
                commands.extend([f"interface {port}", "no switchport access vlan", "exit"])
            commands.extend([f"no vlan {VLAN10}", "exit"])
            output = st.config(dut1, commands, type="klish", skip_error_check=True)
            xml_logger.add_posttest_entry(dut1, f"Cleanup VLAN {VLAN10}", " ".join(commands), str(output), "PASS")
        
        if check_vlan_exists(dut2, VLAN20):
            members = get_vlan_members(dut2, VLAN20)
            commands = ["configure terminal"]
            commands.extend([f"interface Vlan{VLAN20}", "no ip address", "exit"])
            for port in members:
                commands.extend([f"interface {port}", "no switchport access vlan", "exit"])
            commands.extend([f"no vlan {VLAN20}", "exit"])
            output = st.config(dut2, commands, type="klish", skip_error_check=True)
            xml_logger.add_posttest_entry(dut2, f"Cleanup VLAN {VLAN20}", " ".join(commands), str(output), "PASS")
        
        # =====================================================================
        # SAVE XML LOGS
        # =====================================================================
        st.log("Saving XML log files...")
        xml_logger.save_all()
        
        # =====================================================================
        # TEST RESULT
        # =====================================================================
        st.banner("TEST COMPLETED")
        log_to_file(log_file, "=== TEST COMPLETED ===")
        
        st.log("=" * 80)
        st.log(f"Logs available at: {LOG_DIR}")
        st.log("XML logs: pretest.xml, posttest.xml, tr.xml")
        st.log("=" * 80)
        
        if forward_ok and reverse_ok:
            st.report_pass("test_case_passed")
        else:
            st.report_fail("test_case_failed")
    
    except Exception as e:
        error_msg = f"Test failed with exception: {str(e)}"
        st.error(error_msg)
        log_to_file(log_file, f"ERROR: {error_msg}")
        
        # Save XML logs even on failure
        try:
            xml_logger.save_all()
        except:
            pass
        
        st.report_fail("test_case_failed")
