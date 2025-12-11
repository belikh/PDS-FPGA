
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

        # Arbitration
        p_br = platform.request("br_3v3_n")
        p_bg = platform.request("bg_3v3_n")
        p_bgack = platform.request("bgack_3v3_n")

        # ==============================================================================
        # Signal Definitions
        # ==============================================================================

        # Data Bus (Bidirectional)
        data_in = Signal(32)
        data_out = Signal(32)
        data_oe = Signal()

        # Address Bus (Bidirectional)
        slave_addr_raw = Signal(32)
        slave_addr = Signal(32) # Synchronized
        master_addr = Signal(32)
        master_addr_oe = Signal()

        # Control Signals (Bidirectional)
        # Inputs (for Slave logic)
        slave_as_raw = Signal()
        slave_ds_raw = Signal()
        slave_rw_raw = Signal()
        slave_siz0_raw = Signal()
        slave_siz1_raw = Signal()

        # Synchronized Inputs (for Slave logic)
        as_sys = Signal()
        ds_sys = Signal()
        rw_sys = Signal()
        siz0_sys = Signal()
        siz1_sys = Signal()

        # Outputs (for Master logic)
        master_as = Signal()
        master_ds = Signal()
        master_rw = Signal()
        master_siz0 = Signal()
        master_siz1 = Signal()
        master_ctrl_oe = Signal() # Group OE for control signals

        # DSACK (Bidirectional)
        # Input (for Master logic)
        master_dsack0_raw = Signal()
        master_dsack1_raw = Signal()
        master_dsack0_sys = Signal() # Sync
        master_dsack1_sys = Signal() # Sync

        # Output (for Slave logic)
        slave_dsack0_out = Signal(reset=0) # Always drive 0 when enabled
        slave_dsack1_out = Signal(reset=0)
        slave_dsack_oe = Signal() # Enable when we are the selected slave

        # Arbitration (Bidirectional / Input)
        bg_sys = Signal() # Bus Grant (Input, Sync)

        br_out = Signal(reset=0) # Drive 0 when requesting
        br_oe = Signal() # Enable Output

        bgack_out = Signal(reset=0) # Drive 0 when owning
        bgack_oe = Signal() # Enable Output
        bgack_raw = Signal() # Raw Input

        bgack_sys = Signal() # To monitor bus busy status

        # ==============================================================================
        # IO Buffers (Tristates) & Synchronization
        # ==============================================================================

        if not sim:
             # Data
             self.specials += Tristate(p_data, data_out, data_oe, data_in)

             # Address
             self.specials += Tristate(p_addr, master_addr, master_addr_oe, slave_addr_raw)

             # Control
             self.specials += Tristate(p_as, master_as, master_ctrl_oe, slave_as_raw)
             self.specials += Tristate(p_ds, master_ds, master_ctrl_oe, slave_ds_raw)
             self.specials += Tristate(p_rw, master_rw, master_ctrl_oe, slave_rw_raw)
             self.specials += Tristate(p_siz0, master_siz0, master_ctrl_oe, slave_siz0_raw)
             self.specials += Tristate(p_siz1, master_siz1, master_ctrl_oe, slave_siz1_raw)

             # DSACK
             self.specials += Tristate(p_dsack0, slave_dsack0_out, slave_dsack_oe, master_dsack0_raw)
             self.specials += Tristate(p_dsack1, slave_dsack1_out, slave_dsack_oe, master_dsack1_raw)

             # Arbitration
             # BR is Output (Open Drain emulation via Tristate)
             self.specials += Tristate(p_br, br_out, br_oe, Signal())
             # BG is Input
             # BGACK is InOut (Open Drain) - we need to monitor it too
             self.specials += Tristate(p_bgack, bgack_out, bgack_oe, bgack_raw)

        else:
             # Simulation Logic
             self.comb += [
                 data_in.eq(p_data),
                 slave_addr_raw.eq(p_addr),
                 slave_as_raw.eq(p_as),
                 slave_ds_raw.eq(p_ds),
                 slave_rw_raw.eq(p_rw),
                 slave_siz0_raw.eq(p_siz0),
                 slave_siz1_raw.eq(p_siz1),
                 master_dsack0_raw.eq(p_dsack0),
                 master_dsack1_raw.eq(p_dsack1),
                 bgack_raw.eq(p_bgack)
             ]
             # For outputs in SIM, we usually rely on testbench to check signals directly
             self.data_out = data_out
             self.data_oe = data_oe
             self.slave_dsack_oe = slave_dsack_oe
             self.master_addr = master_addr
             self.master_addr_oe = master_addr_oe
             self.master_as = master_as
             self.master_ctrl_oe = master_ctrl_oe
             self.br_oe = br_oe
             self.bgack_oe = bgack_oe

        # Synchronization
        self.specials += [
            MultiReg(slave_addr_raw, slave_addr),
            MultiReg(slave_as_raw, as_sys),
            MultiReg(slave_ds_raw, ds_sys),
            MultiReg(slave_rw_raw, rw_sys),
            MultiReg(slave_siz0_raw, siz0_sys),
            MultiReg(slave_siz1_raw, siz1_sys),
            MultiReg(master_dsack0_raw, master_dsack0_sys),
            MultiReg(master_dsack1_raw, master_dsack1_sys),
            MultiReg(p_bg, bg_sys),
            MultiReg(bgack_raw, bgack_sys),
        ]

        # Debug signals
        self.dbg_as_sys = as_sys
        self.dbg_addr = slave_addr
        self.dbg_start_cycle = Signal()
        self.dbg_sel = Signal(4)
        self.dbg_my_slot = Signal()

        # Edge Detection for AS (Start of Cycle)
        as_sys_d = Signal()
        self.sync += as_sys_d.eq(as_sys)
        start_cycle = self.dbg_start_cycle
        self.comb += start_cycle.eq(as_sys_d & ~as_sys) # Falling edge of /AS

        # ==============================================================================
        # SLAVE LOGIC
        # ==============================================================================

        # Address Decoding
        # Slot 9: F9xx xxxx, Slot A: FAxx xxxx, Slot B: FBxx xxxx
        my_slot = self.dbg_my_slot
        self.comb += my_slot.eq(
            (slave_addr[24:32] == 0xF9) |
            (slave_addr[24:32] == 0xFA) |
            (slave_addr[24:32] == 0xFB)
        )

        # Byte Select Logic (Wishbone sel)
        wb_sel = Signal(4)
        a0 = slave_addr[0]
        a1 = slave_addr[1]

        # Use synchronized signals
        self.comb += [
             Case(Cat(siz0_sys, siz1_sys), {
                 0b00: wb_sel.eq(0xF), # Long Word
                 0b01: Case(Cat(a0, a1), { # Byte
                     0b00: wb_sel.eq(0b1000),
                     0b01: wb_sel.eq(0b0100),
                     0b10: wb_sel.eq(0b0010),
                     0b11: wb_sel.eq(0b0001),
                 }),
                 0b10: Case(Cat(a0, a1), { # Word
                     0b00: wb_sel.eq(0b1100),
                     0b10: wb_sel.eq(0b0011),
                     "default": wb_sel.eq(0xF)
                 }),
                 0b11: Case(Cat(a0, a1), { # 3 Bytes
                     0b00: wb_sel.eq(0b1110),
                     "default": wb_sel.eq(0xF)
                 })
             })
        ]
        self.comb += self.dbg_sel.eq(wb_sel)

        # Slave FSM
        self.submodules.slave_fsm = slave_fsm = FSM(reset_state="IDLE")

        slave_fsm.act("IDLE",
            If(start_cycle & my_slot,
                If(rw_sys, # Read
                    NextState("READ_WB_REQ")
                ).Else( # Write
                    NextState("WRITE_WAIT_DS")
                )
            )
        )

        # READ PATH
        slave_fsm.act("READ_WB_REQ",
            wb_read.cyc.eq(1),
            wb_read.stb.eq(1),
            wb_read.we.eq(0),
            wb_read.adr.eq(slave_addr[2:32]),
            wb_read.sel.eq(wb_sel),

            If(as_sys, # Master aborted
                NextState("IDLE")
            ).Elif(wb_read.ack,
                NextValue(data_out, wb_read.dat_r),
                NextState("READ_DRIVE")
            )
        )

        slave_fsm.act("READ_DRIVE",
            data_oe.eq(1), # Drive Data Bus
            slave_dsack_oe.eq(1), # Drive DSACK
            # dsack outputs are 0 by default

            If(as_sys, # Wait for AS High
                NextState("IDLE")
            )
        )

        # WRITE PATH
        slave_fsm.act("WRITE_WAIT_DS",
            If(as_sys,
                NextState("IDLE")
            ).Elif(~ds_sys,
                NextState("WRITE_WB_REQ")
            )
        )

        slave_fsm.act("WRITE_WB_REQ",
            wb_write.cyc.eq(1),
            wb_write.stb.eq(1),
            wb_write.we.eq(1),
            wb_write.adr.eq(slave_addr[2:32]),
            wb_write.dat_w.eq(data_in),
            wb_write.sel.eq(wb_sel),

            If(as_sys,
                NextState("IDLE")
            ).Elif(wb_write.ack,
                NextState("WRITE_ACK")
            )
        )

        slave_fsm.act("WRITE_ACK",
            slave_dsack_oe.eq(1),

            If(as_sys,
                NextState("IDLE")
            )
        )

        # ==============================================================================
        # MASTER LOGIC (DMA)
        # ==============================================================================

        # Bus Arbitration FSM
        self.submodules.arb_fsm = arb_fsm = FSM(reset_state="IDLE")

        bus_grant = Signal()
        bus_owned = Signal()

        arb_fsm.act("IDLE",
            If(wb_dma.cyc & wb_dma.stb, # Wishbone Request
                 NextState("REQUEST_BUS")
            )
        )

        arb_fsm.act("REQUEST_BUS",
            br_oe.eq(1), # Assert /BR (Active Low, so drive 0)

            # Wait for /BG (Active Low)
            If(~bg_sys,
                NextState("WAIT_BUS_FREE")
            )
        )

        arb_fsm.act("WAIT_BUS_FREE",
            br_oe.eq(1), # Keep asserting BR

            # Bus is free when /AS is High, /DSACK is High (Inactive), /BGACK is High
            # Note: /BGACK might be driven by us if we own it, but here we are waiting to take it.
            # bgack_sys is synchronized input.

            If(as_sys & master_dsack0_sys & master_dsack1_sys & bgack_sys,
                NextState("OWN_BUS")
            )
        )

        arb_fsm.act("OWN_BUS",
             bgack_oe.eq(1), # Assert /BGACK (Active Low)
             bus_owned.eq(1),

             # If DMA transaction finished, release bus
             If(~(wb_dma.cyc & wb_dma.stb),
                 NextState("IDLE")
             )
        )

        # Master Transfer FSM
        self.submodules.master_fsm = master_fsm = FSM(reset_state="IDLE")

        # Mapping Wishbone Signals to PDS Signals
        # WB Address is Word aligned (typically). PDS is Byte/Word/Long.
        # We assume WB DMA requests are 32-bit for now.

        master_fsm.act("IDLE",
             If(bus_owned & wb_dma.cyc & wb_dma.stb,
                 NextState("DRIVE_ADDR")
             )
        )

        master_fsm.act("DRIVE_ADDR",
             # Assert /BGACK (via bus_owned logic in Arb FSM)

             # Drive Address, FC, SIZ, RW
             master_addr_oe.eq(1),
             master_ctrl_oe.eq(1),

             master_addr.eq(Cat(Signal(2), wb_dma.adr)), # Convert WB word addr to Byte addr
             master_rw.eq(~wb_dma.we), # High = Read, Low = Write

             # SIZ=00 (Long Word) for now. Support Byte later?
             master_siz0.eq(0),
             master_siz1.eq(0),

             If(wb_dma.we,
                 # If Write, we can also drive Data
                 data_oe.eq(1),
                 data_out.eq(wb_dma.dat_w),
                 NextState("ASSERT_AS_DS")
             ).Else(
                 # Read
                 NextState("ASSERT_AS_DS")
             )
        )

        master_fsm.act("ASSERT_AS_DS",
             master_addr_oe.eq(1),
             master_ctrl_oe.eq(1),
             master_addr.eq(Cat(Signal(2), wb_dma.adr)),
             master_rw.eq(~wb_dma.we),
             master_siz0.eq(0),
             master_siz1.eq(0),

             If(wb_dma.we,
                 data_oe.eq(1),
                 data_out.eq(wb_dma.dat_w)
             ),

             master_as.eq(0), # Assert AS (Low)
             master_ds.eq(0), # Assert DS (Low)

             NextState("WAIT_ACK")
        )

        master_fsm.act("WAIT_ACK",
             master_addr_oe.eq(1),
             master_ctrl_oe.eq(1),
             master_addr.eq(Cat(Signal(2), wb_dma.adr)),
             master_rw.eq(~wb_dma.we),
             master_siz0.eq(0),
             master_siz1.eq(0),

             master_as.eq(0),
             master_ds.eq(0),

             If(wb_dma.we,
                 data_oe.eq(1),
                 data_out.eq(wb_dma.dat_w)
             ),

             # Wait for DSACK0 or DSACK1 (Active Low)
             If((~master_dsack0_sys) | (~master_dsack1_sys),
                 If(~wb_dma.we,
                     NextValue(wb_dma.dat_r, data_in)
                 ),
                 wb_dma.ack.eq(1),
                 NextState("COMPLETE")
             )
        )

        master_fsm.act("COMPLETE",
             # Release AS/DS
             master_addr_oe.eq(1),
             master_ctrl_oe.eq(1),

             master_as.eq(1),
             master_ds.eq(1),

             # Wait for DSACK Release? 68030 says we can just negate AS.
             # But good to check.

             NextState("IDLE")
        )
