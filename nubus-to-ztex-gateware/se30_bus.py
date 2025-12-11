
from migen import *
from migen.genlib.fifo import *
from migen.genlib.cdc import MultiReg
from migen.fhdl.specials import Tristate

import litex
from litex.soc.interconnect import wishbone

class SE30PDS(Module):
    def __init__(self, soc, platform, wb_read, wb_write, wb_dma, sim=False):
        # Platform Signals
        pds_clk = platform.request("clk_3v3_n") # 15.6672 MHz (Reference, not used for clocking logic)

        # Address and Data
        p_addr = platform.request("pds_a_3v3_n")
        p_data = platform.request("pds_d_3v3_n") # InOut

        # Control
        p_as = platform.request("as_3v3_n")
        p_ds = platform.request("ds_3v3_n")
        p_rw = platform.request("rw_3v3_n")
        p_dsack0 = platform.request("dsack0_3v3_n")
        p_dsack1 = platform.request("dsack1_3v3_n")
        p_siz0 = platform.request("siz0_3v3_n")
        p_siz1 = platform.request("siz1_3v3_n")
        # p_berr = platform.request("berr_3v3_n") # Not driven yet

        # Internal signals (Active High for convenience inside FPGA)
        addr = Signal(32)
        data_in = Signal(32)
        data_out = Signal(32)
        data_oe = Signal() # Output Enable

        as_sys = Signal() # Synchronized /AS (Active Low)
        ds_sys = Signal() # Synchronized /DS (Active Low)
        rw_sys = Signal() # Synchronized R/W (High=Read, Low=Write)
        siz0_sys = Signal()
        siz1_sys = Signal()

        # Debug signals
        self.dbg_as_sys = as_sys
        self.dbg_addr = addr
        self.dbg_start_cycle = Signal()
        self.dbg_sel = Signal(4)

        # Expose internal signals for simulation
        if sim:
            self.data_out = data_out
            self.data_oe = data_oe

        # Synchronization
        # We use MultiReg to synchronize the async PDS signals to the system clock
        self.specials += [
            MultiReg(p_addr, addr),
            MultiReg(p_as, as_sys),
            MultiReg(p_ds, ds_sys),
            MultiReg(p_rw, rw_sys),
            MultiReg(p_siz0, siz0_sys),
            MultiReg(p_siz1, siz1_sys),
        ]

        # Data Bus Tristate
        if not sim:
             self.specials += Tristate(p_data, data_out, data_oe, data_in)
        else:
             # Simulation Logic: Connect Input directly, ignore output for now (or drive it back?)
             # In sim, we only verify we can read.
             self.comb += data_in.eq(p_data)

        # Edge Detection for AS (Start of Cycle)
        as_sys_d = Signal()
        self.sync += as_sys_d.eq(as_sys)
        #start_cycle = Signal()
        start_cycle = self.dbg_start_cycle
        self.comb += start_cycle.eq(as_sys_d & ~as_sys) # Falling edge of /AS (Active Low) -> High to Low transition

        # Address Decoding
        # Slot 9: F9xx xxxx
        # Slot A: FAxx xxxx
        # Slot B: FBxx xxxx
        # We'll match any of these for now.
        my_slot = Signal()
        self.comb += my_slot.eq(
            (addr[24:32] == 0xF9) |
            (addr[24:32] == 0xFA) |
            (addr[24:32] == 0xFB)
        )
        self.dbg_my_slot = my_slot

        # Signals to drive outputs (Active Low)
        dsack0_out = Signal(reset=1)
        dsack1_out = Signal(reset=1)

        self.comb += [
            p_dsack0.eq(dsack0_out),
            p_dsack1.eq(dsack1_out)
        ]

        # Byte Select Logic (Wishbone sel)
        # 68030 SIZ0/SIZ1/A0/A1 logic to Wishbone SEL (4 bits)
        # SIZ1 SIZ0 Size
        # 0    1    Byte
        # 1    0    Word (2 bytes)
        # 1    1    3 Bytes
        # 0    0    Long Word (4 bytes)
        #
        # WB Sel [3:0] where [3] is MSB (D31-D24)
        # 68030 is Big Endian. A0=0,A1=0 -> MSB.

        wb_sel = Signal(4)
        a0 = addr[0]
        a1 = addr[1]

        # We are using the SYNCHRONIZED signals for logic, not the pins.
        # But wait, addr is synchronized, but siz0/siz1 were also synchronized.
        # Let's verify we are using the sync versions.
        # Original code used p_siz0 and p_siz1 in the Case statement, which is wrong.
        # It should use siz0_sys and siz1_sys.

        self.comb += [
             Case(Cat(siz0_sys, siz1_sys), { # SIZ0 is LSB of Cat. Cat(LSB, MSB).
                 # SIZ1 (MSB), SIZ0 (LSB).
                 # 0 (00): Long Word
                 0b00: wb_sel.eq(0xF),
                 # 1 (01): Byte
                 0b01: Case(Cat(a0, a1), {
                     0b00: wb_sel.eq(0b1000), # D31-D24
                     0b01: wb_sel.eq(0b0100), # D23-D16
                     0b10: wb_sel.eq(0b0010), # D15-D8
                     0b11: wb_sel.eq(0b0001), # D7-D0
                 }),
                 # 2 (10): Word
                 0b10: Case(Cat(a0, a1), {
                     0b00: wb_sel.eq(0b1100), # D31-D16
                     0b10: wb_sel.eq(0b0011), # D15-D0
                     "default": wb_sel.eq(0xF) # Invalid alignment for Word?
                 }),
                 # 3 (11): 3 Bytes
                 0b11: Case(Cat(a0, a1), {
                     0b00: wb_sel.eq(0b1110), # D31-D8
                     "default": wb_sel.eq(0xF)
                 })
             })
        ]
        self.comb += self.dbg_sel.eq(wb_sel)

        # Slave FSM
        self.submodules.fsm = fsm = FSM(reset_state="IDLE")

        # Wishbone Read Logic
        # We need to present address to WB, strobing CYC/STB.
        # Wait for ACK.
        # Then drive data.

        # Wishbone Write Logic
        # Wait for Data Valid (DS Low).
        # Present Address/Data to WB.
        # Wait for ACK.

        fsm.act("IDLE",
            If(start_cycle & my_slot,
                If(rw_sys, # Read
                    NextState("READ_WB_REQ")
                ).Else( # Write
                    NextState("WRITE_WAIT_DS")
                )
            )
        )

        # READ PATH
        fsm.act("READ_WB_REQ",
            wb_read.cyc.eq(1),
            wb_read.stb.eq(1),
            wb_read.we.eq(0),
            wb_read.adr.eq(addr[2:32]), # Word aligned
            wb_read.sel.eq(wb_sel),

            If(as_sys, # Master aborted
                NextState("IDLE")
            ).Elif(wb_read.ack,
                NextValue(data_out, wb_read.dat_r),
                NextState("READ_DRIVE")
            )
        )

        fsm.act("READ_DRIVE",
            data_oe.eq(1), # Enable Output
            dsack0_out.eq(0), # Assert DSACK (Active Low)
            dsack1_out.eq(0),

            # Wait for Master to release AS (End of Cycle)
            # AS is Active Low. We wait for it to go High (Inactive).
            If(as_sys,
                NextState("IDLE")
            )
        )

        # WRITE PATH
        fsm.act("WRITE_WAIT_DS",
            # We need DS to be Active (Low) to ensure data is valid on bus
            If(as_sys, # Master aborted
                NextState("IDLE")
            ).Elif(~ds_sys,
                NextState("WRITE_WB_REQ")
            )
        )

        fsm.act("WRITE_WB_REQ",
            wb_write.cyc.eq(1),
            wb_write.stb.eq(1),
            wb_write.we.eq(1),
            wb_write.adr.eq(addr[2:32]),
            wb_write.dat_w.eq(data_in),
            wb_write.sel.eq(wb_sel),

            If(as_sys, # Master aborted
                NextState("IDLE")
            ).Elif(wb_write.ack,
                NextState("WRITE_ACK")
            )
        )

        fsm.act("WRITE_ACK",
            dsack0_out.eq(0),
            dsack1_out.eq(0),

            If(as_sys,
                NextState("IDLE")
            )
        )
