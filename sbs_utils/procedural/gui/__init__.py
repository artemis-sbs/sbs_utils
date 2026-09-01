from .console_tab import gui_tab_enable,gui_tab_back,gui_tab_add_top,gui_tab_enable_top,gui_tab_activate, gui_tab_get_active, gui_tab_clear_top, gui_tab_remove_top, gui_tab_is_top
from .console_tab import gui_tab_get_list
from .epadd import (gui_app_register, gui_app_unregister, gui_app_is_registered,
                    gui_app_get_registered, gui_app_list, gui_app_groups,
                    gui_app_mode, gui_app_mode_is_on, gui_app_mode_default,
                    gui_app_adopt_record,
                    gui_app_adopted, epadd_console_name,
                    gui_app_home, gui_app_open, gui_app_chrome)
from .console_types import gui_add_console_type, gui_get_console_type, gui_get_console_type_list, gui_get_console_types, gui_remove_console_type


from .blank import gui_blank
from .hole import gui_hole
from .row import gui_row
from .grid import gui_grid
from .list_view import gui_list
from .section import gui_section, gui_region, gui_sub_section


from .button import gui_button
from .checkbox import gui_checkbox
from .cinematic import gui_cinematic_auto, gui_cinematic_full_control
from .camera import (camera_anchor, camera_assign, camera_track, camera_auto,
                     camera_orbit_lens, camera_shot, camera_move, camera_orbit,
                     camera_rack, camera_move_stop, camera_lens, camera_dolly,
                     camera_chase, camera_assignment, camera_restore)
from .cutscene import (cutscene_define, cutscene_play, cutscene_skip,
                       cutscene_stop, cutscene_playing, cutscene_get,
                       cutscene_framing)
from .viewscreen import (viewscreen_set, viewscreen_clear, viewscreen_mode,
                         viewscreen_subject, viewscreen_is_live, viewscreen_consoles,
                         viewscreen_helm_override, viewscreen_apply, viewscreen_framing,
                         viewscreen_home_ship, viewscreen_reset, viewscreen_restore,
                         viewscreen_effective_state, viewscreen_take,
                         viewscreen_console_enter, viewscreen_view_modes,
                         viewscreen_dial_label,
                         viewscreen_revision,
                         viewscreen_shot_props, viewscreen_mode_for,
                         viewscreen_label_for, SHOT_LABELS)
from .viewscreen_pages import (viewscreen_page_register, viewscreen_page_remove,
                               viewscreen_page_names, viewscreen_pages,
                               viewscreen_hull_percent, viewscreen_relative_bearing)
from .viewscreen_claims import (viewscreen_claim, viewscreen_claim_drop,
                              viewscreen_claimed, viewscreen_owner, viewscreen_owns,
                              viewscreen_owner_token, viewscreen_tier, viewscreen_seq,
                              viewscreen_baseline, viewscreen_baseline_drop,
                              viewscreen_bump, viewscreen_held, viewscreen_hold,
                              viewscreen_hold_take, viewscreen_hold_drop,
                              viewscreen_roster, viewscreen_roster_add,
                              viewscreen_crew_took, viewscreen_crew_holds,
                              viewscreen_crew_lock_remaining,
                              viewscreen_crew_release,
                              TIER_CONSOLE, TIER_STORY, VIEWSCREEN_TIERS,
                              CREW_LOCK_SECONDS)
# The module is hail_gui, not hail_view, because it EXPORTS a function called
# hail_view - and a submodule sharing a name with an exported function is
# shadowed by it, so `from ...gui import hail_view` hands back the function.
# (viewscreen_pages has that shape already; this one does not repeat it.)
from .hail_gui import (hail_view, hail_choice_strip, hail_where_dropdown,
                        hail_where_checkbox,
                        hail_band_show, hail_band_clear,
                        hail_panel_history, hail_transcript_text, hail_panel_icon,
                        hail_rows, hail_list_title, hail_screen_show, hail_screen_clear,
                        hail_audio_checkbox,
                        HAIL_BAND_SLOT, HAIL_BAND_RECT, HAIL_BAND_LAYER)
from .rundown import (rundown_add, rundown_remove, rundown_clear, rundown_shots,
                      rundown_get, rundown_program, rundown_preview, rundown_live,
                      rundown_staged, rundown_punch, rundown_stage, rundown_take,
                      rundown_release, rundown_excitement, rundown_suggest,
                      rundown_tiles)
from .clickable import gui_click
from .content import gui_content
from .dropdown import gui_drop_down
from .face import gui_face
from .icon import gui_icon_name, gui_icon_add_atlas, gui_icon_add_atlas_grid, gui_icon, gui_icon_button, gui_icon_recolor
from .image import gui_image_add_atlas_grid, gui_image, gui_image_absolute, gui_image_keep_aspect_ratio, gui_image_keep_aspect_ratio_center, gui_image_stretch, gui_image_add_atlas,gui_image_size,gui_image_get_atlas
from .input import gui_input
from .options_button import gui_options_button, gui_options_button_flag, gui_options_button_clear
from .radio import gui_radio, gui_vradio
from .ship import gui_ship
from .slider import gui_int_slider, gui_slider
from .text import gui_text, gui_text_area, gui_text_escape

from .listbox import gui_list_box, gui_list_box_header,gui_listbox_items_convert_headers, gui_list_box_is_header
from .table import gui_table
from .property_listbox import gui_properties_set, gui_property_list_box, gui_property_list_box_stacked
from .map_picker import gui_map_picker
from .update import gui_hide, gui_refresh, gui_represent, gui_show, gui_rebuild, gui_update, gui_update_shared
from .style import gui_set_style_def, gui_style_def

from .navigation import gui_reroute_server, gui_reroute_clients, gui_reroute_client
from .navigation import gui_history_store, gui_history_back, gui_history_forward, gui_history_jump, gui_history_clear, gui_history_redirect

from .console import gui_console, gui_activate_console, gui_console_clients, gui_console_enter
from .widgets import gui_update_widget_list, gui_update_widgets, gui_widget_list, gui_widget_list_clear, gui_layout_widget, gui_widget_offscreen


# Screenshot + clipboard use the Win32 API (ctypes.WinDLL) at import time, so they
# only import on Windows. On other platforms (e.g. Linux CI) provide stubs that
# raise if actually called, so the library still imports everywhere.
import sys as _sys
if _sys.platform == "win32":
    from .screen_shot import gui_screenshot
    from .clipboard import gui_clipboard_copy, gui_clipboard_get, gui_clipboard_put
else:
    def _gui_win_only(_name):
        def _stub(*args, **kwargs):
            raise RuntimeError(_name + " is Windows-only (Win32 API)")
        _stub.__name__ = _name
        return _stub
    gui_screenshot = _gui_win_only("gui_screenshot")
    gui_clipboard_copy = _gui_win_only("gui_clipboard_copy")
    gui_clipboard_get = _gui_win_only("gui_clipboard_get")
    gui_clipboard_put = _gui_win_only("gui_clipboard_put")
from .client_string import gui_request_client_string

from .message import gui_message, gui_message_label, gui_message_callback, gui_message_clear
from .change import gui_change


from .gui import ButtonPromise, gui_properties_change
from .gui import gui, gui_hide_choice, gui_screen_size, gui_screen_size_known, gui_percent_from_pixels, gui_percent_from_ems, gui_task_for_client, gui_client_id

from .tabbed_panel import gui_tabbed_panel, gui_panel_widget_show, gui_panel_widget_hide
from .tabbed_panel import gui_panel_console_message, gui_panel_console_message_list,gui_panel_upgrade_list, gui_panel_console_message_tick
from .tabbed_panel import gui_info_panel, gui_info_panel_send_message, gui_info_panel_add, gui_info_panel_remove
# The ship's log as an info-panel tab (mkdocs build/messages.md) - the text waterfall's
# replacement. Exported here so a console can name it in gui_info_panel_add.
from .log_panel_gui import (gui_panel_log, gui_panel_log_ship,
                            gui_panel_log_mission, gui_panel_log_tick,
                            gui_log_tail)
from .overlay import overlay_show, overlay_clear, overlay_register, overlay_register_label, overlay_slot_define, overlay_hero, overlay_debug_log
from .overlay import overlay_clear_console
from .overlay import overlay_kind, consoles_of
from .overlay import overlay_signal_show, overlay_signal_clear
from .overlay import overlay_toast, overlay_banner, overlay_lower_third, overlay_lower_third_portrait, overlay_credits, overlay_choice
from .overlay import overlay_hud, overlay_hud_update, overlay_letterbox, overlay_flash
from .icon_sheet import ICON_DOMAIN, icon_resolve, icon_names, ICON_INDEX, ICON_ALIAS
