"""
demo.py — Example script-engine usage of cosmos_dev.mockgui.sbs

Run with:
    python demo.py

Open any number of browser tabs at http://localhost:8765/
Each tab gets a unique clientID assigned by the server.
Press Ctrl+C to shut down.
"""

import queue
import time
import cosmos_dev.mockgui.sbs as sbs
from cosmos_dev.mockgui.sbs import (
    send_gui_clear, send_gui_complete,
    send_gui_text, send_gui_button, send_gui_checkbox,
    send_gui_typein, send_gui_slider, send_gui_dropdown,
    send_gui_sub_region, send_gui_clickregion,
    send_gui_colorbutton, send_gui_icon, send_gui_face,
)

# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def draw_main_screen(client_id):
    send_gui_clear(client_id, "main")

    send_gui_text(client_id, "", "title", "text:SBS Remote GUI Demo;color:blue",
                  2, 2, 98, 8)

    send_gui_sub_region(client_id, "", "left_panel", "",
                        2, 10, 48, 90)

    send_gui_text(client_id,     "left_panel", "lbl_name", "text:`Name:`",
                  2, 3, 98, 11)
    send_gui_typein(client_id,   "left_panel", "inp_name", "desc:Enter name…",
                    2, 13, 98, 23)
    send_gui_text(client_id,     "left_panel", "lbl_vol", "text:Volume",
                  2, 26, 98, 34)
    send_gui_slider(client_id,   "left_panel", "sld_volume", 65.0, "low:0;high:100",
                    2, 35, 98, 45)
    send_gui_checkbox(client_id, "left_panel", "chk_mute", "text:Mute",
                      2, 48, 65, 57)
    send_gui_text(client_id,     "left_panel", "lbl_mode", "text:`Mode:`",
                  2, 60, 98, 68)
    send_gui_dropdown(client_id, "left_panel", "dd_mode", "list:Normal,Debug,Verbose",
                      2, 70, 98, 80)

    send_gui_sub_region(client_id, "", "right_panel", "",
                        52, 10, 98, 90)

    send_gui_button(client_id,      "right_panel", "btn_ok",     "text:OK",
                    4, 3, 57, 12)
    send_gui_button(client_id,      "right_panel", "btn_cancel", "text:Cancel",
                    4, 15, 57, 24)
    send_gui_colorbutton(client_id, "right_panel", "col_red",   "color:#6b6565",
                         4, 30, 26, 38)
    send_gui_colorbutton(client_id, "right_panel", "col_green", "color:#22c55e",
                         30, 30, 52, 38)
    send_gui_colorbutton(client_id, "right_panel", "col_blue",  "color:#4f8ef7",
                         56, 30, 78, 38)
    send_gui_icon(client_id, "right_panel", "ico_star", "text:⭐",
                  4, 42, 26, 54)
    send_gui_icon(client_id, "right_panel", "ico_bell", "text:🔔",
                  30, 42, 52, 54)
    send_gui_face(client_id, "right_panel", "face_happy", "😄",
                  4, 57, 44, 73)
    send_gui_clickregion(client_id, "right_panel", "clk_zone", "text:click me!",
                         4, 77, 98, 90)

    send_gui_complete(client_id, "main")


def draw_detail_screen(client_id):
    send_gui_clear(client_id, "detail")

    send_gui_text(client_id, "", "detail_title", "text:Detail View",
                  2, 2, 98, 8)

    send_gui_sub_region(client_id, "", "detail_panel", "",
                        10, 12, 90, 80)

    send_gui_text(client_id, "detail_panel", "detail_msg",
                  "text:`You clicked OK.\nThis is the detail page.`",
                  5, 5, 95, 40)

    send_gui_button(client_id, "detail_panel", "btn_back", "text:← Back",
                    5, 75, 40, 90)

    send_gui_complete(client_id, "detail")


_DRAW_FN = {
    "main":   draw_main_screen,
    "detail": draw_detail_screen,
}

# ---------------------------------------------------------------------------
# Main loop  (no threading, no asyncio)
# ---------------------------------------------------------------------------

def main():
    sbs.start_server()
    print("[demo] server started — waiting for browser connections…  (Ctrl+C to quit)")

    # clientID -> current page name
    pages: dict[int, str] = {}

    while True:
        # --- connection events -------------------------------------------
        try:
            while True:
                ev  = sbs.client_event_queue.get_nowait()
                cid = ev["clientID"]
                if ev["event"] == "connect":
                    print(f"[demo] client {cid} connected")
                    pages[cid] = "main"
                    draw_main_screen(cid)
                elif ev["event"] == "disconnect":
                    print(f"[demo] client {cid} disconnected")
                    pages.pop(cid, None)
        except queue.Empty:
            pass

        # --- widget events -----------------------------------------------
        try:
            while True:
                ev   = sbs.gui_event_queue.get_nowait()
                cid  = ev.get("clientID")
                tag  = ev.get("tag")
                kind = ev.get("type")

                if cid not in pages:
                    continue

                if kind == "click":
                    if tag == "btn_ok":
                        print(f"[demo] client {cid} → detail page")
                        pages[cid] = "detail"
                        draw_detail_screen(cid)
                    elif tag == "btn_back":
                        print(f"[demo] client {cid} → main page")
                        pages[cid] = "main"
                        draw_main_screen(cid)
        except queue.Empty:
            pass

        time.sleep(0.05)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()   # required on Windows
    try:
        main()
    except KeyboardInterrupt:
        print("\n[demo] shutdown")
