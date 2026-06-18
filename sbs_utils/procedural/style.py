from ..mast.parsers import StyleDefinition
from ..gui import get_client_aspect_ratio

def compile_formatted_string(message):
    """Compile a format string into a Python code object for faster repeated evaluation.

    Strings containing ``{`` are wrapped in an f-string and compiled with
    ``eval`` mode. Strings without ``{`` are returned unchanged.

    Args:
        message (str): The format string, optionally containing ``{var}``
            placeholders.

    Returns:
        CodeType | str | None: A compiled code object if the string contains
            ``{``, the original string otherwise, or ``None`` if ``message``
            is ``None``.
    """
    if message is None:
        return message
    if "{" in message:
        message = f'''f"""{message}"""'''
        code = compile(message, "<string>", "eval")
        return code
    else:
        return message
    



def apply_style_name(style_name, layout_item, task):
    """Look up a named style definition and apply it to a layout item.

    Args:
        style_name (str): Name of the style to apply.
        layout_item (LayoutItem): Layout item to receive the style.
        task (MastAsyncTask): GUI task used for string formatting.
    """
    if style_name is None:
        return
    style_def = StyleDefinition.styles.get(style_name)
    apply_style_def(style_def, layout_item, task)

def apply_style_def(style_def, layout_item, task):
    """Apply a style definition dict directly to a layout item.

    Handles ``area``, ``orientation``, ``row-height``, ``col-width``,
    ``margin``, ``border``, ``padding``, ``color``, ``font``, ``justify``,
    ``background``, ``background-color``, ``background-image``,
    ``border-image``, ``border-color``, ``click_*``, and ``tag`` keys.

    Args:
        style_def (dict): Parsed style definition (key → value).
        layout_item (LayoutItem): Layout item to receive the style.
        task (MastAsyncTask): GUI task used for string formatting.
    """
    if style_def is None:
        return
    aspect_ratio = get_client_aspect_ratio(task.main.page.client_id)
    # aspect_ratio = task.main.page.aspect_ratio
    if aspect_ratio.x == 0:
        aspect_ratio.x = 1
    if aspect_ratio.y == 0:
        aspect_ratio.y = 1

    st = style_def.get("area")
    if st is not None:
        layout_item.bounds_style = st
    ori = style_def.get("orientation")
    if ori is not None:
        layout_item.set_orientation(ori)        
    
    height = style_def.get("row-height")
    if height is not None:
        layout_item.set_row_height(height)        
    ###############
    width = style_def.get("col-width")
    if width is not None:
        layout_item.set_col_width(width)        
    ###############
    margin = style_def.get("margin")
    if margin is not None:
        layout_item.margin_style = margin
    ###############
    border = style_def.get("border")
    if border is not None:
        layout_item.border_style =border
    ###############        
    padding = style_def.get("padding")
    if padding is not None:
        layout_item.padding_style = padding
    ######
    st = style_def.get("color")
    if st is not None:
        st = compile_formatted_string(st)
        layout_item.default_color = task.format_string(st)

    st = style_def.get("font")
    if st is not None:
        st = compile_formatted_string(st)
        layout_item.default_font = task.format_string(st)

    st = style_def.get("justify")
    if st is not None:
        st = compile_formatted_string(st)
        layout_item.default_justify = task.format_string(st)

    background = style_def.get("background")
    if background is not None:
        background = compile_formatted_string(background)
        layout_item.background_color = task.format_string(background)

    background = style_def.get("background-color")
    if background is not None:
        background = compile_formatted_string(background)
        layout_item.background_color = task.format_string(background)

    st = style_def.get("background-image")
    if st is not None:
        st = compile_formatted_string(st)
        layout_item.background_image = task.format_string(st)

    st = style_def.get("border-image")
    if st is not None:
        st = compile_formatted_string(st)
        layout_item.border_image = task.format_string(st)

    st = style_def.get("border-color")
    if st is not None:
        st = compile_formatted_string(st)
        layout_item.border_color = task.format_string(st)

    click_text = style_def.get("click_text")
    if click_text is not None:
        click_text = compile_formatted_string(click_text)
        layout_item.click_text = task.format_string(click_text)

    click_font = style_def.get("click_font")
    if click_font is not None:
        click_font = compile_formatted_string(click_font)
        layout_item.click_font = task.format_string(click_font)

    click_color = style_def.get("click_color")
    if click_color is not None:
        click_color = compile_formatted_string(click_color)
        layout_item.click_color = task.format_string(click_color)

    click_bk = style_def.get("click_background")
    if click_bk is not None:
        click_bk = compile_formatted_string(click_bk)
        layout_item.click_background = task.format_string(click_bk)

    click_tag = style_def.get("click_tag")
    if click_tag is not None:
        click_tag = compile_formatted_string(click_tag)
        layout_item.click_tag = task.format_string(click_tag).strip()

    tag = style_def.get("tag")
    if tag is not None:
        tag = compile_formatted_string(tag)
        layout_item.tag = task.format_string(tag).strip()

def apply_control_styles(control_name, extra_style, layout_item, task):
        """Apply a named control style and optional overrides to a layout item.

        ``extra_style`` may be a raw CSS-style string (``"key:value;..."``) or
        a style name. It is applied on top of the base ``control_name`` style.

        Args:
            control_name (str): Base control style name.
            extra_style (str | dict | None): Additional style string, name, or
                parsed dict applied after the base style.
            layout_item (LayoutItem): Layout item to receive the style.
            task (MastAsyncTask): GUI task used for string formatting.
        """
        apply_style_name(control_name, layout_item, task)
        if extra_style is not None:
            if isinstance(extra_style,str):
                if ":" in extra_style:
                    apply_style_def(StyleDefinition.parse(extra_style),  layout_item, task)
                else:
                    apply_style_name(extra_style, layout_item, task)
            else:
                apply_style_def(extra_style,  layout_item, task)


