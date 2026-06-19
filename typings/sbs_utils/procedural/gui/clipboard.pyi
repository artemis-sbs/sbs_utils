from builtins import unicode_type
def gui_clipboard_copy (s):
    """Write a text string to the Windows clipboard.
    
    Windows-only. Replaces whatever is currently on the clipboard.
    ``gui_clipboard_copy`` is an alias for this function.
    
    Args:
        s (str): The text to place on the clipboard.
    
    Example:
        gui_clipboard_put("TSN Artemis — Mission Report")"""
def gui_clipboard_get ():
    """Read the current text content of the Windows clipboard.
    
    Windows-only. Returns ``None`` if the clipboard is empty or contains
    non-text data.
    
    Returns:
        str | None: The clipboard text, or ``None`` if unavailable.
    
    Example:
        text = gui_clipboard_get()
        if text is not None:
            gui_text("Pasted: {text}")"""
def gui_clipboard_put (s):
    """Write a text string to the Windows clipboard.
    
    Windows-only. Replaces whatever is currently on the clipboard.
    ``gui_clipboard_copy`` is an alias for this function.
    
    Args:
        s (str): The text to place on the clipboard.
    
    Example:
        gui_clipboard_put("TSN Artemis — Mission Report")"""
