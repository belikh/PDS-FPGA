
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
    print("--- READ TEST ---")

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
        fsm_state = yield dut.fsm.state

        # Mimic Wishbone Slave response
        cyc = yield wb_read.cyc
        stb = yield wb_read.stb
        if cyc and stb:
            sel = yield wb_read.sel
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
    print("\n--- WRITE TEST ---")

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

if __name__ == "__main__":
    platform = MockPlatformCached()
    wb_read = litex.soc.interconnect.wishbone.Interface()
    wb_write = litex.soc.interconnect.wishbone.Interface()
    wb_dma = litex.soc.interconnect.wishbone.Interface()

    # Pass sim=True to avoid Tristate
    dut = SE30PDS(None, platform, wb_read, wb_write, wb_dma, sim=True)

    run_simulation(dut, test_bench(dut, platform, wb_read, wb_write))
