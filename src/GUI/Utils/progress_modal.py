"""
progress_modal.py
─────────────────
Shared modal progress-window utility for SOCEIS GUI operations.

Usage
-----
    import src.GUI.Utils.progress_modal as _pm

    progress = _pm.open_progress("EIS — Process Data",
                                  "Processing EIS data...",
                                  total_steps=len(config.selected_files))
    try:
        for i, file_name in enumerate(config.selected_files):
            # ... do work ...
            _pm.update_progress(progress, i + 1, file_name)
    finally:
        _pm.close_progress(progress)

All three functions are safe to call with ``ctx=None`` (non-GUI / headless context).
"""

import dearpygui.dearpygui as dpg

_DEFAULT_TAG = "window_operation_progress"


def open_progress(title: str, message: str, total_steps: int,
                  window_tag: str = _DEFAULT_TAG):
    """Open a modal progress window.

    Parameters
    ----------
    title       : Window title bar text.
    message     : Description line shown inside the window.
    total_steps : Total number of steps (denominator for the bar).
    window_tag  : DPG tag for the window.  Use different tags if two
                  progress windows could exist simultaneously.

    Returns
    -------
    dict  – Context ``{window, bar, text, total}`` to pass to
            :func:`update_progress` / :func:`close_progress`.
    None  – if DearPyGui is not running (non-GUI / headless context).
    """
    if not (hasattr(dpg, "is_dearpygui_running") and dpg.is_dearpygui_running()):
        return None

    bar_tag  = f"{window_tag}_bar"
    text_tag = f"{window_tag}_text"

    if dpg.does_item_exist(window_tag):
        dpg.delete_item(window_tag)

    vp_w = dpg.get_viewport_width()
    vp_h = dpg.get_viewport_height()
    width, height = 420, 130

    with dpg.window(
        label=title,
        tag=window_tag,
        modal=True,
        no_close=True,
        no_collapse=True,
        no_resize=True,
        no_move=True,
        width=width,
        height=height,
        pos=(max(10, (vp_w - width) // 2), max(10, (vp_h - height) // 2)),
    ):
        dpg.add_text(message)
        dpg.add_progress_bar(default_value=0.0, tag=bar_tag, width=-1)
        dpg.add_text("0%", tag=text_tag)

    dpg.split_frame()
    return {
        "window": window_tag,
        "bar":    bar_tag,
        "text":   text_tag,
        "total":  max(1, int(total_steps)),
    }


def update_progress(ctx, step: int, label: str = "") -> None:
    """Update the progress bar.

    Parameters
    ----------
    ctx   : Context dict returned by :func:`open_progress`, or None.
    step  : Current 1-based completed step number.
    label : Optional short description appended after the percentage text.
    """
    if not ctx:
        return
    ratio = min(1.0, max(0.0, float(step) / float(ctx["total"])))
    if dpg.does_item_exist(ctx["bar"]):
        dpg.set_value(ctx["bar"], ratio)
    if dpg.does_item_exist(ctx["text"]):
        suffix = f"  {label}" if label else ""
        dpg.set_value(
            ctx["text"],
            f"{int(ratio * 100)}%  ({step}/{ctx['total']}){suffix}",
        )
    dpg.split_frame()


def close_progress(ctx) -> None:
    """Close / remove the progress window.

    Parameters
    ----------
    ctx : Context dict returned by :func:`open_progress`, or None.
    """
    if not ctx:
        return
    if dpg.does_item_exist(ctx["window"]):
        dpg.delete_item(ctx["window"])
        dpg.split_frame()  # commit deletion before any subsequent modal creation


# ─────────────────────────────────────────────
# Error dialog
# ─────────────────────────────────────────────

def show_error_dialog(title: str, message: str, file_hint: str = "") -> None:
    """Show a modal error dialog with a scrollable message and an OK button.

    Parameters
    ----------
    title     : Dialog title bar text.
    message   : Error description / traceback text shown inside the window.
    file_hint : Optional filename/path that caused the error.  When provided
                it is shown in a highlighted line above the error message.
    """
    if not (hasattr(dpg, "is_dearpygui_running") and dpg.is_dearpygui_running()):
        return

    import time as _time
    tag = f"window_error_dialog_{int(_time.monotonic() * 1e6) & 0xFFFFFF}"

    vp_w = dpg.get_viewport_width()
    vp_h = dpg.get_viewport_height()
    win_width  = max(460, int(vp_w * 0.38))
    win_height = max(300, int(vp_h * 0.42))
    _header_h  = 58 if file_hint else 38
    _bottom_h  = 52

    with dpg.window(
        label=title,
        tag=tag,
        modal=True,
        no_collapse=True,
        no_resize=False,
        width=win_width,
        height=win_height,
        pos=(max(10, (vp_w - win_width) // 2), max(10, (vp_h - win_height) // 2)),
    ):
        # ── Top: header / file hint ──────────────────────────────────────
        with dpg.child_window(width=-1, height=_header_h, no_scrollbar=True, border=False):
            if file_hint:
                dpg.add_text(f"File:  {file_hint}", color=(255, 200, 80))
            dpg.add_text("Error", color=(255, 80, 80))
        dpg.add_separator()
        # ── Middle: scrollable message ───────────────────────────────
        with dpg.child_window(width=-1, height=-_bottom_h, horizontal_scrollbar=True):
            dpg.add_text(str(message), wrap=win_width - 30)
        # ── Bottom: OK button ────────────────────────────────────────
        with dpg.child_window(width=-1, height=_bottom_h, no_scrollbar=True, border=True):
            dpg.add_spacer(height=6)
            dpg.add_separator()
            dpg.add_spacer(height=4)
            dpg.add_button(
                label="  OK  ",
                callback=lambda: dpg.delete_item(tag) if dpg.does_item_exist(tag) else None,
            )
    dpg.split_frame()


# ─────────────────────────────────────────────
# Warning dialog
# ─────────────────────────────────────────────

def show_warning_dialog(title: str, message: str) -> None:
    """Show a non-blocking modal warning dialog with an 'Understood' button.

    Parameters
    ----------
    title   : Dialog title bar text.
    message : Warning description shown inside the window.
    """
    if not (hasattr(dpg, "is_dearpygui_running") and dpg.is_dearpygui_running()):
        return

    import time as _time
    tag = f"window_warning_dialog_{int(_time.monotonic() * 1e6) & 0xFFFFFF}"

    vp_w = dpg.get_viewport_width()
    vp_h = dpg.get_viewport_height()
    win_width  = max(460, int(vp_w * 0.38))
    win_height = max(300, int(vp_h * 0.42))
    _header_h  = 38
    _bottom_h  = 52

    with dpg.window(
        label=title,
        tag=tag,
        modal=True,
        no_collapse=True,
        no_resize=False,
        width=win_width,
        height=win_height,
        pos=(max(10, (vp_w - win_width) // 2), max(10, (vp_h - win_height) // 2)),
    ):
        # ── Top: warning header ──────────────────────────────────────────
        with dpg.child_window(width=-1, height=_header_h, no_scrollbar=True, border=False):
            dpg.add_text("Warning", color=(255, 180, 0))
        dpg.add_separator()
        # ── Middle: scrollable message ───────────────────────────────
        with dpg.child_window(width=-1, height=-_bottom_h, horizontal_scrollbar=True):
            dpg.add_text(str(message), wrap=win_width - 30)
        # ── Bottom: Understood button ────────────────────────────────
        with dpg.child_window(width=-1, height=_bottom_h, no_scrollbar=True, border=True):
            dpg.add_spacer(height=6)
            dpg.add_separator()
            dpg.add_spacer(height=4)
            dpg.add_button(
                label="  Understood  ",
                callback=lambda: dpg.delete_item(tag) if dpg.does_item_exist(tag) else None,
            )
    dpg.split_frame()
