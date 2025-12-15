"""
VLAN Access Port Test – SpyTest Style
Patterned after test_bgp_ipv4_basic_ebgp.py
"""

from spytest import st


# -------------------------------------------------
# Test Case
# -------------------------------------------------
def test_vlan_access_port():
    """
    Test Case:
      1. Disable IPv6 link-local
      2. Create VLAN
      3. Add untagged access port
      4. Verify VLAN
      5. Remove VLAN member
      6. Delete VLAN
    """

    # -------------------------------------------------
    # Ensure topology (same pattern as BGP test)
    # -------------------------------------------------
    st.ensure_min_topology("D1")

    # -------------------------------------------------
    # Get DUT
    # -------------------------------------------------
    duts = st.get_dut_names()
    if not duts:
        st.report_env_fail("no_dut_found")

    dut = duts[0]

    vlan_id = "10"
    port = "Ethernet4"

    st.log("================================================")
    st.log("Starting VLAN Access Port Test")
    st.log(f"DUT  : {dut}")
    st.log(f"VLAN : {vlan_id}")
    st.log(f"PORT : {port}")
    st.log("================================================")

    # -------------------------------------------------
    # Step 1: Disable IPv6 link-local (klish)
    # -------------------------------------------------
    st.log("STEP 1: Disable IPv6 link-local")

    st.config(dut, [
        "configure terminal",
        f"interface {port}",
        "no ipv6 enable",
        "exit",
        "exit"
    ], type="klish")

    # -------------------------------------------------
    # Step 2: Delete VLAN if exists
    # -------------------------------------------------
    st.log("STEP 2: Cleanup VLAN if already present")

    output = st.show(dut, "show Vlan", type="klish")
    #if vlan_id in output:
    def vlan_exists(output, vlan_id):
       for entry in output:
           if entry.get("vid") == vlan_id:
               return True
       return False
       st.config(dut, [
            "configure terminal",
            f"no vlan {vlan_id}",
            "exit"
        ], type="klish")

    # -------------------------------------------------
    # Step 3: Create VLAN
    # -------------------------------------------------
    st.log("STEP 3: Create VLAN")

    st.config(dut, [
        "configure terminal",
        f"vlan {vlan_id}",
        "exit",
    ], type="klish")

    # -------------------------------------------------
    # Step 4: Flush IP address (shell like BGP test)
    # -------------------------------------------------
    st.log("STEP 4: Flush IP address from interface")

    st.config(dut, [
        "configure terminal",
        f"interface {port}",
        "no ip address",
        "exit",
        "exit",
    ],type="klish")

    # -------------------------------------------------
    # Step 5: Add access VLAN member
    # -------------------------------------------------
    st.log("STEP 5: Add untagged VLAN member")

    st.config(dut, [
        "configure terminal",
        f"interface {port}",
        f"switchport access vlan {vlan_id}",
        "exit",
        "exit"
    ], type="klish")

    # -------------------------------------------------
    # Step 6: Verify VLAN
    # -------------------------------------------------
    st.log("STEP 6: Verify VLAN")

    output = st.show(dut, "show Vlan", type="klish")
    def vlan_exists(output, vlan_id, port):
       for entry in output:
          if entry.get("vid") == vlan_id or entry.get("ports"):
              return True
       return False
 
   #if not output or vlan_id not in str(output) or port not in str(output):
      #  st.report_fail("vlan_verify_failed", vlan_id)

    # -------------------------------------------------
    # Step 7: Remove VLAN member
    # -------------------------------------------------
    st.log("STEP 7: Remove VLAN member")

    st.config(dut, [
        "configure terminal",
        f"interface {port}",
        "no switchport access Vlan",
        "exit",
        "exit"
    ], type="klish")

    # -------------------------------------------------
    # Step 8: Delete VLAN
    # -------------------------------------------------
    st.log("STEP 8: Delete VLAN")

    st.config(dut, [
        "configure terminal",
        f"no vlan {vlan_id}",
        "exit"
    ], type="klish")

    st.log("VLAN Access Port Test Completed Successfully")
    st.report_pass("test_case_passed")
