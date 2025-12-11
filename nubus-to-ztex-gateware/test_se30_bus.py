
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

    yield
    print("Cycle 0: Init")

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
    for i in range(15):
        yield
        fsm_state = yield dut.fsm.state
        dbg_as = yield dut.dbg_as_sys
        dbg_addr = yield dut.dbg_addr
        dbg_start = yield dut.dbg_start_cycle
        dbg_my_slot = yield dut.dbg_my_slot
        dbg_sel = yield dut.dbg_sel

        print(f"Cycle {3+i}: Wait... State={fsm_state}, AS={dbg_as}, Addr={hex(dbg_addr)}, SEL={bin(dbg_sel)}")

        # Mimic Wishbone Slave response
        cyc = yield wb_read.cyc
        stb = yield wb_read.stb
        if cyc and stb:
            sel = yield wb_read.sel
            print(f"  Wishbone Req detected! SEL={bin(sel)}")
            yield wb_read.ack.eq(1)
            yield wb_read.dat_r.eq(0xDEADBEEF)
        else:
            yield wb_read.ack.eq(0)

    # Check DSACK
    dsack0 = yield p_dsack0
    dsack1 = yield p_dsack1
    print(f"DSACK0={dsack0}, DSACK1={dsack1}")

    if dsack0 == 0 and dsack1 == 0:
        print("PASS: DSACK asserted.")
    else:
        print("FAIL: DSACK not asserted.")

    # Release AS
    yield p_as.eq(1)
    yield
    print("Cycle End: AS High")

    # Check DSACK Release
    yield
    dsack0 = yield p_dsack0
    print(f"DSACK0={dsack0}")
    if dsack0 == 1:
        print("PASS: DSACK released.")


if __name__ == "__main__":
    platform = MockPlatformCached()
    wb_read = litex.soc.interconnect.wishbone.Interface()
    wb_write = litex.soc.interconnect.wishbone.Interface()
    wb_dma = litex.soc.interconnect.wishbone.Interface()

    # Pass sim=True to avoid Tristate
    dut = SE30PDS(None, platform, wb_read, wb_write, wb_dma, sim=True)

    run_simulation(dut, test_bench(dut, platform, wb_read, wb_write))
