import binascii

WRITE_OP        = 0x00
READ_OP         = 0x01


FIRM_ID         = 0x00
SENSHW_ID       = 0x04
SENS_ID         = 0x08
WDR_REG         = 0x0C
MIRROR_REG      = 0x10
DENOISE_REG     = 0x14
AGC_REG         = 0x18
LOWLIGTH_REG    = 0x1C
DAYNIGHT_REG    = 0x20
SHUTTER_REG     = 0x24
BRIGHT_REG      = 0x28
AESPEED_REG     = 0x2C
CONTRAST_REG    = 0x30
SAT_REG         = 0x34
SHARP_REG       = 0x38
OVERLAY_REG     = 0x3C

HEADER = "AA55"
FOOTER = "55AA"

def build_frame(op: int, reg: int, value: int) -> str:
    """
    Build a protocol frame:
      HEADER (AA55)
      LEN (2 ASCII, hex length of payload in bytes)
      PAYLOAD = op(2 ASCII) + reg(2 ASCII) + value(2 ASCII)
      CRC32 = over ASCII payload string
      FOOTER (55AA)
    """
    # Encode fields as ASCII hex
    op_str = f"{op:02X}"
    reg_str = f"{reg:02X}"
    value_str = f"{value:02X}"

    payload = op_str + reg_str + value_str

    # Payload length in bytes (not chars)
    length = len(payload) // 2  # since payload is hex string
    length_str = f"{length:02X}"  # 2 ASCII hex chars

    # CRC32 of payload (hex, 8 chars uppercase)
    payload_bytes = bytes.fromhex(payload)
    crc_val = binascii.crc32(payload_bytes) & 0xFFFFFFFF
    crc_str = f"{crc_val:08X}"

    # Frame assembly
    frame = HEADER + length_str + payload.upper() + crc_str + FOOTER
    return frame


def parse_frame(frame: str) -> dict:
    """
    Parse a protocol frame into components.
    Returns a dictionary or raises ValueError if invalid.
    """
    if not (frame.startswith(HEADER) and frame.endswith(FOOTER)):
        raise ValueError("Invalid frame header/footer")

    length_str = frame[4:6]
    try:
        length = int(length_str, 16)
    except ValueError:
        raise ValueError("Invalid length field")

    payload = frame[6:6 + length * 2]
    crc_str = frame[6 + length * 2:6 + length * 2 + 8]

    # Verify CRC
    payload_bytes = bytes.fromhex(payload)
    calc_crc = f"{(binascii.crc32(payload_bytes) & 0xFFFFFFFF):08X}"
    if calc_crc != crc_str:
        raise ValueError(f"CRC mismatch: expected {crc_str}, got {calc_crc}")

    return {
        "length": length,
        "payload": payload,
        "crc": crc_str,
    }
