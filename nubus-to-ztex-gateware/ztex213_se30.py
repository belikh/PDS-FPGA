#
# Copyright (c) 2015 Yann Sionneau <yann.sionneau@gmail.com>
# Copyright (c) 2015-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2020-2021 Romain Dolbeau <romain@dolbeau.org>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *
from litex.build.generic_platform import *
from litex.build.xilinx import XilinxPlatform

try:
    from VintageBusFPGA_Common.ztex_21x_common import ZTexPlatform
except ImportError:
    # Fallback if path not set up
    from ztex_21x_common import ZTexPlatform

# IOs ----------------------------------------------------------------------------------------------

# I/O for SE/30 PDS (using NuBus board pins + extras)
# Mapping Strategy:
# - Address Bus (A0-A31) -> Mapped to 'ad' pins (32 bits)
# - Data Bus (D0-D31) -> Mapped to 'tm0', 'tm1', 'id', 'arb', 'ack', 'start', 'rqst' + P1 connector
#   This is a HYPOTHETICAL MAPPING for a new adapter board.

_se30_pds_io = [
    # SE/30 PDS Signals
    # CPUCLK (15.6672 MHz)
    ("clk_3v3_n",          0, Pins("H16"), IOStandard("lvttl")),

    # Address Bus (A0-A31) - Reusing 'ad' pins
    ("pds_a_3v3_n",        0, Pins("A13 A14 C12 B12 B13 B14 A15 A16 "
                                   "D12 D13 D14 C14 B16 B17 D15 C15 "
                                   "B18 A18 C16 C17 E15 E16 F14 F13 "
                                   "D17 D18 E17 E18 F15 F18 F16 G18 "), IOStandard("lvttl")),

    # Data Bus (D0-D31) - Reusing Control + P1 pins (Hypothetical)
    # 32 pins needed.
    # Reusing:
    # ID (3), TM0 (1), TM1 (1), TM2 (1), ARB (3), ACK (1), START (1), RQST (1), NMRQ (1), RESET (1) -> 14 pins
    # P1 (12 pins) -> 26 pins
    # LED/Serial (2) -> 28 pins
    # CLK2X (1) -> 29 pins
    # Extra: G17 -> 30 pins
    # Extra: H17 -> 31 pins
    # Extra: T6 (Was tm0_o_n) -> 32 pins
    # Removed U6 from here (used for SIZ0)
    # Removed T4 from here (used for sdcard data)

    ("pds_d_3v3_n",        0, Pins(
        "U7 V6 V7 " +             # ID (3)
        "U2 V2 K6 " +             # TM0, TM1, TM2 (3)
        "T8 V4 V5 " +             # ARB (3) - Removed U6
        "J17 K15 J18 " +          # ACK, START, RQST (3)
        "K16 " +                  # NMRQ (1)
        "M1 L1 N2 N1 R2 P2 T1 R1 P4 P3 P5 N5 " + # P1 (12)
        "V9 U9 " +                # LED/Serial (2)
        "T5 " +                   # CLK2X (1)
        "T6 " +                   # EXTRA (1) - Was TM0_O_N
        "G17 " +                  # RESET (1) - WARNING: G17 is nubus_ad_dir on carrier!
        "H17"                     # MASTER_DIR (1) - WARNING: H17 is arb_o_n on carrier!
    ), IOStandard("lvttl")),

    # Control Signals
    # /AS
    ("as_3v3_n",           0, Pins("J13"), IOStandard("lvttl")), # Was arbcy_n
    # /DS
    ("ds_3v3_n",           0, Pins("U8"), IOStandard("lvttl")), # Moved from G13. U8 is Input Only (Reset on NuBus). Slave Mode Only.
    # NUBUS_OE (G13) - Must be driven Low to enable buffers
    ("nubus_oe_n",         0, Pins("G13"), IOStandard("lvttl")),

    # R/W
    ("rw_3v3_n",           0, Pins("G16"), IOStandard("lvttl")), # Was nubus_ad_dir
    # /DSACK0
    ("dsack0_3v3_n",       0, Pins("H15"), IOStandard("lvttl")), # Was grant
    # /DSACK1
    ("dsack1_3v3_n",       0, Pins("H14"), IOStandard("lvttl")), # Was fpga_to_cpld_clk
    # SIZ0
    ("siz0_3v3_n",         0, Pins("U6"),  IOStandard("lvttl")), # Was tmoen (Reused)
    # SIZ1
    ("siz1_3v3_n",         0, Pins("J14"), IOStandard("lvttl")), # Was fpga_to_cpld_signal

    # FC0-2
    ("fc_3v3_n",           0, Pins("G14 R3 R5"), IOStandard("lvttl")), # Misc pins

    # Interrupts /IRQ1-3
    ("irq_3v3_n",          0, Pins("K13 J15"), IOStandard("lvttl")), # Removed U8 (used for DS). Only 2 pins available.

    # Bus Arbitration
    ("br_3v3_n",           0, Pins("R6"), IOStandard("lvttl")),
    ("bg_3v3_n",           0, Pins("R7"), IOStandard("lvttl")),
    ("bgack_3v3_n",        0, Pins("R8"), IOStandard("lvttl")),
]

_se30_peripherals = [
    ## USB
    ("usb", 0,
     Subsignal("dp", Pins("B11")),
     Subsignal("dm", Pins("A11")),
     IOStandard("LVCMOS33")
    ),
    ## HDMI (Using V1.2 pins)
    ("hdmi", 0,
        Subsignal("clk_p",   Pins("M4"), IOStandard("TMDS_33")),
        Subsignal("clk_n",   Pins("N4"), IOStandard("TMDS_33")),
        Subsignal("data0_p", Pins("M3"), IOStandard("TMDS_33")),
        Subsignal("data0_n", Pins("M2"), IOStandard("TMDS_33")),
        Subsignal("data1_p", Pins("K5"), IOStandard("TMDS_33")),
        Subsignal("data1_n", Pins("L4"), IOStandard("TMDS_33")),
        Subsignal("data2_p", Pins("K3"), IOStandard("TMDS_33")),
        Subsignal("data2_n", Pins("L3"), IOStandard("TMDS_33")),
        Subsignal("hpd",     Pins("N6"), IOStandard("LVCMOS33")),
        Subsignal("sda",     Pins("M6"), IOStandard("LVCMOS33")),
        Subsignal("scl",     Pins("L6"), IOStandard("LVCMOS33")),
        Subsignal("cec",     Pins("L5"), IOStandard("LVCMOS33")),
    ),
    ## micro-sd
    ("sdcard", 0,
        Subsignal("data", Pins("U1 T3 T4 U4"), Misc("PULLUP True")),
        Subsignal("cmd",  Pins("U3"), Misc("PULLUP True")),
        Subsignal("clk",  Pins("V1")),
        Misc("SLEW=FAST"),
        IOStandard("LVCMOS33"),
    ),
]

class SE30Platform(ZTexPlatform):
    def __init__(self, variant="ztex2.13a"):
        # The base ZTexPlatform expects 'connectors'.
        # In ztex213_nubus.py, it passed connectors based on version.
        # Here we hardcode or pass empty if we used P1 pins for data.
        # But wait, we used "P1" pins in our definition, but defined them as explicit pins in _se30_pds_io.
        # So we don't need 'connectors' list unless we want to use the "P1:x" syntax.
        # But we explicitly listed the pins (M1 L1...).
        # So we can pass connectors=[]

        # We need to manually call init because ZTexPlatform.__init__ calls XilinxPlatform.__init__
        # And if we pass connectors=None (default), it fails iterating.

        ZTexPlatform.__init__(self, variant=variant, version="V1.2", connectors=[])
        self.add_extension(_se30_pds_io)
        self.add_extension(_se30_peripherals)
