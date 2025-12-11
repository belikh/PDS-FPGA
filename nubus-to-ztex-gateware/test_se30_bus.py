
from migen import *
from se30_bus import SE30PDS
import litex.soc.interconnect.wishbone

# Mock Platform
class MockPlatformCached:
    def __init__(self):
        self.signals = {}
    def request(self, name):
        if name not in self.signals:
            if name == "pds_d_3v3_n" or name == "pds_a_3v3_n":
                 self.signals[name] = Signal(32, name=name)
            else:
                 self.signals[name] = Signal(name=name)
        return self.signals[name]

def test_bench(dut, platform, wb_read, wb_write):
    # Signals
    p_addr = platform.signals["pds_a_3v3_n"]
    p_as = platform.signals["as_3v3_n"]
    p_ds = platform.signals["ds_3v3_n"]
    p_rw = platform.signals["rw_3v3_n"]
    p_dsack0 = platform.signals["dsack0_3v3_n"]
    p_dsack1 = platform.signals["dsack1_3v3_n"]
    p_data = platform.signals["pds_d_3v3_n"]
    p_siz0 = platform.signals["siz0_3v3_n"]
    p_siz1 = platform.signals["siz1_3v3_n"]

    # Yield initial state (Inactive)
    yield p_as.eq(1)
    yield p_ds.eq(1)
    yield p_rw.eq(1)
    yield p_addr.eq(0)
    yield p_siz0.eq(0)
    yield p_siz1.eq(0)
    yield p_data.eq(0)

    yield
    print("--- READ TEST (Byte access) ---")

    # Start Read Cycle
    # Address = 0xF9000010 (Slot 9)
    # Size = Byte (SIZ1=0, SIZ0=1) -> 01
    yield p_addr.eq(0xF9000010)
    yield p_rw.eq(1) # Read
    yield p_siz1.eq(0)
    yield p_siz0.eq(1) # Byte Read
    yield
    print("Cycle 1: Address Set")

    # Assert AS (Low)
    yield p_as.eq(0)
    yield
    print("Cycle 2: AS Low")

    # Wait for FSM to react
    read_success = False
    for i in range(20):
        yield

        # Check if data output is being driven
        data_oe = yield dut.data_oe
        if data_oe:
             data_out = yield dut.data_out
             # print(f"Data Bus Driven: {hex(data_out)}")

        # Mimic Wishbone Slave response
        cyc = yield wb_read.cyc
        stb = yield wb_read.stb
        if cyc and stb:
            sel = yield wb_read.sel
            # Expect SEL=1000 (D31-D24) for Addr ending in 0 (if aligned 00)
            # 0x10 ends in 00 binary for A1/A0.
            # Byte access at 00 -> 1000.
            if sel != 0b1000:
                 print(f"Error: Unexpected SEL {bin(sel)} for Byte access at 00")

            # print(f"  Wishbone Req detected! SEL={bin(sel)}")
            yield wb_read.ack.eq(1)
            yield wb_read.dat_r.eq(0xDEADBEEF)
        else:
            yield wb_read.ack.eq(0)

        dsack0 = yield p_dsack0
        dsack1 = yield p_dsack1
        if dsack0 == 0 and dsack1 == 0:
            read_success = True
            break

    print(f"DSACK asserted: {read_success}")
    if not read_success:
        print("FAIL: DSACK not asserted within timeout.")
        return

    # Verify Data Out
    d_out = yield dut.data_out
    if d_out != 0xDEADBEEF:
         print(f"FAIL: Data Out mismatch. Expected 0xDEADBEEF, got {hex(d_out)}")

    # Release AS
    yield p_as.eq(1)
    yield
    print("Cycle End: AS High")

    # Wait for DSACK Release (needs sync delay)
    dsack_released = False
    for i in range(5):
        yield
        dsack0 = yield p_dsack0
        if dsack0 == 1:
            dsack_released = True
            break

    print(f"DSACK released: {dsack_released}")
    if not dsack_released:
        print("FAIL: DSACK not released.")

    yield
    yield

    # ---------------------------------------------------------
    print("\n--- WRITE TEST (Long Word) ---")

    # Start Write Cycle
    # Address = 0xFA000020 (Slot A)
    # Data = 0xCAFEBABE
    # Size = Long Word (SIZ1=0, SIZ0=0)

    yield p_addr.eq(0xFA000020)
    yield p_rw.eq(0) # Write
    yield p_siz1.eq(0)
    yield p_siz0.eq(0)
    yield p_data.eq(0xCAFEBABE) # Drive data on bus
    yield

    # Assert AS (Low)
    yield p_as.eq(0)
    yield

    # Assert DS (Low) - Usually happens shortly after AS
    yield p_ds.eq(0)
    yield

    write_success = False
    for i in range(20):
        yield

        # Mimic Wishbone Slave response
        cyc = yield wb_write.cyc
        stb = yield wb_write.stb
        if cyc and stb:
            sel = yield wb_write.sel
            we = yield wb_write.we
            dat_w = yield wb_write.dat_w
            adr = yield wb_write.adr

            if sel != 0xF:
                 print(f"Error: Unexpected SEL {bin(sel)} for Long Word access")

            # Verify data
            if we == 1 and dat_w == 0xCAFEBABE:
                # print(f"  Wishbone Write: Addr={hex(adr*4)} Data={hex(dat_w)}")
                yield wb_write.ack.eq(1)
            else:
                 print(f"  Unexpected WB req: WE={we} Data={hex(dat_w)}")
        else:
            yield wb_write.ack.eq(0)

        dsack0 = yield p_dsack0
        dsack1 = yield p_dsack1
        if dsack0 == 0 and dsack1 == 0:
            write_success = True
            break

    print(f"Write DSACK asserted: {write_success}")
    if not write_success:
         print("FAIL: Write DSACK not asserted.")
         return

    # Release AS and DS
    yield p_as.eq(1)
    yield p_ds.eq(1)
    yield

    # Wait for DSACK Release
    dsack_released = False
    for i in range(5):
        yield
        dsack0 = yield p_dsack0
        if dsack0 == 1:
            dsack_released = True
            break

    print(f"Write DSACK released: {dsack_released}")

    # ---------------------------------------------------------
    print("\n--- READ TEST (Word Misaligned?) ---")
    # Actually SE/30 68030 supports dynamic bus sizing but our slave asserts both DSACK0/1 (32-bit port).
    # If the CPU requests a word at address 2 (0x...2), and we respond as 32-bit port,
    # it expects us to return the data on D15-D0.

    # Let's test Word access at Offset 2.
    # Addr = ...2
    # SIZ = Word (10)

    yield p_addr.eq(0xFB000002)
    yield p_rw.eq(1)
    yield p_siz1.eq(1)
    yield p_siz0.eq(0) # Word
    yield

    yield p_as.eq(0)
    yield

    read_success = False
    for i in range(20):
        yield

        cyc = yield wb_read.cyc
        stb = yield wb_read.stb
        if cyc and stb:
            sel = yield wb_read.sel
            # Addr 2 (binary 10 for A1/A0).
            # Word access at 10 -> D15-D0 -> SEL 0011 (binary)
            if sel != 0b0011:
                print(f"Error: Unexpected SEL {bin(sel)} for Word access at Offset 2")

            yield wb_read.ack.eq(1)
            yield wb_read.dat_r.eq(0x12345678)
        else:
            yield wb_read.ack.eq(0)

        dsack0 = yield p_dsack0
        if dsack0 == 0:
             read_success = True
             break

    print(f"Word Offset 2 DSACK: {read_success}")
    yield p_as.eq(1)
    yield

    # Cleanup for next tests
    for i in range(5): yield

if __name__ == "__main__":
    platform = MockPlatformCached()
    wb_read = litex.soc.interconnect.wishbone.Interface()
    wb_write = litex.soc.interconnect.wishbone.Interface()
    wb_dma = litex.soc.interconnect.wishbone.Interface()

    # Pass sim=True to avoid Tristate
    dut = SE30PDS(None, platform, wb_read, wb_write, wb_dma, sim=True)

    run_simulation(dut, test_bench(dut, platform, wb_read, wb_write))
