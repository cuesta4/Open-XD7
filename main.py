import hid
import os
import time
import sys
from typing import Dict, Optional, Tuple

POLLING_MAP = {
    250:  [0x04, 0x51],
    500:  [0x02, 0x53],
    1000: [0x01, 0x54],
}

DPI_MAP = {
    800:  {'byte': 0x0f, 'aux': 0x37},
    1600: {'byte': 0x1f, 'aux': 0x17},
    3200: {'byte': 0x3f, 'aux': 0xd7},
    8000: {'byte': 0x9f, 'aux': 0x17},
}

VID = 0x25A7
PID = 0xFA7C

class FantechAria:
    def __init__(self):
        self.device = hid.device()

    def preparar_sistema(self):
        os.system("taskkill /F /IM OemDrv.exe >nul 2>&1")
        time.sleep(0.5)

    def conectar(self) -> bool:
        interfaces = hid.enumerate(VID, PID)
        target = next((i for i in interfaces if i.get('interface_number') == 1), None)
        if target:
            try:
                self.device.open_path(target['path'])
                return True
            except Exception as e:
                print(f"Error opening connection: {e}")
        else:
            print("Device not found (VID/PID/interface mismatch).")
        return False

    def fechar(self):
        try:
            self.device.close()
        except Exception:
            pass

    def enviar_handshake(self):
        self.device.send_feature_report([0x08, 0x03] + ([0x00] * 14) + [0x4a])
        time.sleep(0.01)

    def commit_flash(self):
        self.device.send_feature_report([0x08, 0x04] + ([0x00] * 14) + [0x49])
        time.sleep(0.01)

    def aplicar_polling(self, freq_hz: int):
        if freq_hz not in POLLING_MAP:
            raise ValueError(f"Polling {freq_hz}Hz not supported.")
        b6, b7 = POLLING_MAP[freq_hz]
        try:
            self.enviar_handshake()
            payload = [0x08, 0x07, 0x00, 0x00, 0x00, 0x02, b6, b7] + ([0x00] * 8) + [0xef]
            print(f"Sending polling {freq_hz}Hz -> bytes {b6:02x} {b7:02x}")
            self.device.send_feature_report(payload)
            time.sleep(0.02)
            self.commit_flash()
            print("Polling aplicado.")
        except Exception as e:
            raise RuntimeError(f"Error applying polling: {e}")

    def build_dpi_frame(self, main_byte: int, aux_byte: int):
        return [0x08, 0x07, 0x00, 0x00, 0x0c, 0x04,
                main_byte, main_byte, 0x00, aux_byte] + ([0x00] * 6) + [0xe1]

    def aplicar_dpi(self, dpi_value: int):
        if dpi_value not in DPI_MAP:
            raise ValueError(f"DPI {dpi_value} not supported.")
        entry = DPI_MAP[dpi_value]
        main = entry['byte']
        aux = entry['aux']
        try:
            self.enviar_handshake()
            frame = self.build_dpi_frame(main, aux)
            print(f"Sending DPI {dpi_value} -> main {main:02x}, aux {aux:02x}")
            self.device.send_feature_report(frame)
            time.sleep(0.02)
            self.commit_flash()
            print("DPI applied.")
        except Exception as e:
            raise RuntimeError(f"Error applying DPI: {e}")

#CLI: ACCEPTS --250 --3200 OR --poll=250 --dpi=3200 SYNTAX
def parse_args(argv) -> Tuple[Optional[int], Optional[int]]:
    polling = None
    dpi = None
    for raw in argv[1:]:
        if not raw:
            continue

        if raw.startswith('--') and raw[2:].isdigit():
            val = int(raw[2:])
            if val in POLLING_MAP:
                polling = val
                continue
            if val in DPI_MAP:
                dpi = val
                continue

        if raw.startswith('--') and '=' in raw:
            key, val = raw.lstrip('-').split('=', 1)
            if val.isdigit():
                n = int(val)
                if key in ('poll', 'polling') and n in POLLING_MAP:
                    polling = n
                    continue
                if key in ('dpi',) and n in DPI_MAP:
                    dpi = n
                    continue

        if raw in ('-p', '--poll') or raw in ('-d', '--dpi'):
            try:
                next_val = argv[argv.index(raw) + 1]
                if next_val.isdigit():
                    n = int(next_val)
                    if raw in ('-p', '--poll') and n in POLLING_MAP:
                        polling = n
                    if raw in ('-d', '--dpi') and n in DPI_MAP:
                        dpi = n
            except Exception:
                pass
    return polling, dpi

def escolher_polling_interativo() -> int:
    poll_map = {1:125, 2:250, 3:500, 4:1000}
    print("Escolha polling rate (1-4):")
    print(" 1 → 125 Hz (not working rn)")
    print(" 2 → 250 Hz")
    print(" 3 → 500 Hz")
    print(" 4 → 1000 Hz")
    escolha = input("Polling (1-4) [default 2]: ").strip() or "2"
    try:
        idx = int(escolha)
        hz = poll_map.get(idx, 250)
    except Exception:
        hz = 250
    if hz == 125:
        print("Warning: 125Hz iffy. Won't apply.")
    return hz

def escolher_dpi_interativo() -> int:
    items = sorted(DPI_MAP.keys())
    print("Choose DPI:")
    for i, d in enumerate(items, start=1):
        e = DPI_MAP[d]
        print(f" {i} → {d} DPI (main {e['byte']:02x}, aux {e['aux']:02x})")
    escolha = input(f"Choose (1-{len(items)}) [default 3]: ").strip() or "3"
    try:
        idx = int(escolha)
        dpi = items[idx-1]
    except Exception:
        dpi = items[2] 
    return dpi

def main():
    polling_arg, dpi_arg = parse_args(sys.argv)

    if polling_arg is None or dpi_arg is None:
        print("Interactive mode (missing argument).")
        if polling_arg is None:
            polling_arg = escolher_polling_interativo()
        if dpi_arg is None:
            dpi_arg = escolher_dpi_interativo()

    if polling_arg == 125:
        print("125Hz not working, skipping.")
        apply_poll = False
    else:
        apply_poll = True

    drv = FantechAria()
    drv.preparar_sistema()

    if not drv.conectar():
        print("Connection failed. Check cable/driver/interface.")
        sys.exit(2)

    exit_code = 0
    try:
        if apply_poll:
            try:
                drv.aplicar_polling(polling_arg)
            except Exception as e:
                print(f"Error applying polling: {e}")
                exit_code = 3
        time.sleep(0.05)
        try:
            drv.aplicar_dpi(dpi_arg)
        except Exception as e:
            print(f"Error applying DPI: {e}")
            exit_code = 4
    finally:
        drv.fechar()
        if exit_code == 0:
            print("Success.")
        else:
            print(f"Error (code {exit_code}).")
        sys.exit(exit_code)

if __name__ == "__main__":
    main()
