from .layout import Column, Bounds, get_font_size
from .measure import (measure_line_width, measure_line_height, wrap_to_width,
                      measure_block_height, measure_props)
from ...helpers import FrameContext, split_props, merge_props, gui_text_escape
from ...gui import get_client_aspect_ratio
from textwrap import TextWrapper

import re
image_pattern = re.compile(r"""!\[(?P<alt>\w+)?\]\((?P<name>\w+)://(?P<url>.*)\)""")


from ..widgets.control import Control

class TextLine:
    def __init__(self, text, style, width, height, is_sec_end) -> None:
        self.text = text.strip()
        self.style = style
        self.height = height
        self.width = width
        self.is_sec_end = is_sec_end

def parse_url(text):
    ret = {}

    url = text.split("?")
    text = url[0]
    ret["url"] = text
    
    if len(url)>1:
        values = url[1].split("&")
        for value in values:
            kv = value.split("=")
            if len(kv)==2:
                key = kv[0].strip()
                value = kv[1].strip()
                ret[key] = value
    return ret

def to_float(text, defa):
    if text is None:
        return defa
    try:
        return float(text)
    except:
        pass
    return defa

class FaceLine:
    def __init__(self, text, ar) -> None:
        url_data = parse_url(text)

        self.text = url_data.get("url")
        height = to_float(url_data.get("height"), 50.0)
        self.align = url_data.get("align")

        self.height = 0
        self.is_sec_end = False
        self.width = (height / ar.x) * 100
        self.height = (height / ar.y) * 100

    def send_gui(self, SBS, client_id, region_tag, tag, left, top, right, bottom):
        # clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
        if self.align == "center":
            mid = left+ (right-left)/2.0
            half = self.width /2.0
            SBS.send_gui_face(client_id, region_tag, tag, self.text, mid-half, top, mid+half, bottom)
        elif self.align == "right":
            SBS.send_gui_face(client_id, region_tag, tag, self.text, right-self.width, top, right, bottom)
        else:
            SBS.send_gui_face(client_id, region_tag, tag, self.text, left, top, left+self.width, bottom)    
        #print(f"hull_tag:{self.text} {self.height} {left},{top},{right},{bottom}")


class ShipLine:
    def __init__(self, text, ar) -> None:
        url_data = parse_url(text)

        self.text = url_data.get("url")
        height = to_float(url_data.get("height"), 50.0)
        self.align = url_data.get("align")

        self.height = 0
        self.is_sec_end = False
        self.width = (height / ar.x) * 100
        self.height = (height / ar.y) * 100

    def send_gui(self, SBS, client_id, region_tag, tag, left, top, right, bottom):
        # clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
        if self.align == "center":
            mid = left+ (right-left)/2
            half = self.width /2
            SBS.send_gui_3dship(client_id, region_tag, tag, f"hull_tag:{self.text};", mid-half, top, mid+half, bottom)
        elif self.align == "right":
            SBS.send_gui_3dship(client_id, region_tag, tag, f"hull_tag:{self.text};", right-self.width, top, right, bottom)
        else:
            SBS.send_gui_3dship(client_id, region_tag, tag, f"hull_tag:{self.text};", left, top, left+self.width, bottom)
        #print(f"hull_tag:{self.text} {self.height} {left},{top},{right},{bottom}")


class ImageLine:
    def __init__(self, text, ar) -> None:
        from ...procedural.gui.image import gui_image_get_atlas

        url_data = parse_url(text)

        text = url_data.get("url")
        scale = to_float(url_data.get("scale"), 1.0)
        self.color = url_data.get("color")
        self.fill = 2
        v = url_data.get("fill")

        if v == "fit":
            self.fill = 0
        elif v == "center":
            self.fill = 3

        self.atlas = gui_image_get_atlas(text)
        
        self.height = 0
        self.is_sec_end = False
        if self.atlas:
            _, height = self.atlas.get_size()
            # Height needs to be in percent 
            self.height = (height / ar.y) * 100 * scale

    def send_gui(self, SBS, client_id, region_tag, tag, left, top, right, bottom):
        self.atlas.send_gui_image(SBS, client_id, region_tag, tag, self.fill,
                    left, top, right, bottom, self.color)


class TableLine:
    """A GFM pipe-table rendered as a grid of text cells — a block-line like
    ImageLine/FaceLine (owns its rect via send_gui). Columns are sized to their
    measured content then shrunk to fit the region width (never overflow — there's
    no horizontal scroll); row height is the tallest wrapped cell. Per-column
    alignment comes from the |:--|--:| separator row. Keep tables SMALL/static:
    scrolling is line-indexed so a tall table clips at the block boundary."""
    HDR_FONT = "gui-3"
    BODY_FONT = "gui-2"

    def __init__(self, rows, aligns, ar, pixel_width, sbs) -> None:
        self.is_sec_end = False
        self.ar = ar
        self.aligns = aligns
        ncols = max((len(r) for r in rows), default=0)
        self.ncols = ncols
        self.rows = [r + [""] * (ncols - len(r)) for r in rows]
        self.col_px = []
        self.row_h_px = []
        self.cell_pad_px = 0
        self.height = 0
        if ncols == 0 or not self.rows:
            return

        # Natural column widths (px) — measure real glyphs (header in header font).
        col_px = [0.0] * ncols
        for ri, r in enumerate(self.rows):
            f = self.HDR_FONT if ri == 0 else self.BODY_FONT
            for c in range(ncols):
                if r[c]:
                    w = measure_line_width(f, r[c])
                    if w > col_px[c]:
                        col_px[c] = w
        self.cell_pad_px = measure_line_width(self.BODY_FONT, "MM")        # gutter
        avail = max(1.0, pixel_width - self.cell_pad_px * (ncols - 1))
        natural = sum(col_px)
        if natural > avail and natural > 0:                                # fit-to-width
            col_px = [w * (avail / natural) for w in col_px]
        floor = min(measure_line_width(self.BODY_FONT, "MMM"), avail / ncols)
        col_px = [max(w, floor) for w in col_px]                           # min column
        self.col_px = col_px

        # Row heights (px) from the tallest wrapped cell in each row.
        for ri, r in enumerate(self.rows):
            f = self.HDR_FONT if ri == 0 else self.BODY_FONT
            h = 0
            for c in range(ncols):
                cw = int(col_px[c])
                bh = (measure_block_height(f, r[c], cw) if (r[c] and cw > 0)
                      else measure_line_height(f, "M"))
                if bh > h:
                    h = bh
            self.row_h_px.append(h)
        self.height = (sum(self.row_h_px) / ar.y) * 100                    # percent

    def send_gui(self, SBS, client_id, region_tag, tag, left, top, right, bottom):
        if not self.rows or self.ncols == 0:
            return
        ar = self.ar
        col_pct = [(w / ar.x) * 100 for w in self.col_px]
        pad_pct = (self.cell_pad_px / ar.x) * 100
        just_map = {"l": "left", "c": "center", "r": "right"}
        y = top
        for ri, r in enumerate(self.rows):
            f = TableLine.HDR_FONT if ri == 0 else TableLine.BODY_FONT
            row_h = (self.row_h_px[ri] / ar.y) * 100
            color = "#bbb" if ri == 0 else "white"
            x = left
            for c in range(self.ncols):
                a = self.aligns[c] if c < len(self.aligns) else "l"
                style = f"font:{f};justify:{just_map.get(a, 'left')};color:{color}"
                SBS.send_gui_text(client_id, region_tag, f"{tag}:r{ri}c{c}",
                                  f"$text:{gui_text_escape(r[c])};{style}",
                                  x, y, x + col_pct[c], y + row_h)
                x += col_pct[c] + pad_pct
            y += row_h


class HrLine:
    """Horizontal rule (`<hr>` / `<hr/>`) — a thin full-width divider. Uses `<hr>`
    rather than `---` so it never clashes with the table separator row."""
    def __init__(self, ar) -> None:
        self.is_sec_end = False
        self._ar = ar
        self.height = (12.0 / ar.y) * 100          # ~12px slot

    def send_gui(self, SBS, client_id, region_tag, tag, left, top, right, bottom):
        mid = top + (bottom - top) / 2.0
        half = (1.0 / self._ar.y) * 100
        SBS.send_gui_image(client_id, region_tag, tag,
                           "image:smallwhite;color:#888;draw_layer:1000;",
                           left, mid - half, right, mid + half)


class LinkLine:
    """A whole-line hyperlink `[Display](ref://key)`. Renders as styled clickable
    text plus a transparent clickregion on top whose click_tag routes back to the
    owning TextArea's on_message, which resolves the key (intra-document nav)."""
    def __init__(self, display, click_tag, ar, sbs, font="gui-2") -> None:
        self.display = display
        self.click_tag = click_tag
        self.font = font
        self.is_sec_end = False
        self.height = (measure_line_height(font, display) / ar.y) * 100

    def send_gui(self, SBS, client_id, region_tag, tag, left, top, right, bottom):
        SBS.send_gui_text(client_id, region_tag, tag,
                          f"$text:{gui_text_escape(self.display)};color:#6cf;font:{self.font}",
                          left, top, right, bottom)
        # transparent hit area on top; its click_tag carries the target key
        SBS.send_gui_clickregion(client_id, region_tag, self.click_tag,
                                 "background_color:#00000000;",
                                 left, top, right, bottom)


class TextArea(Control):
    #
    # NOTE the `height` in each style below is INERT. Line heights are measured
    # from the style's own font (measure_block_height), which is the only number
    # that matches what the engine draws -- these nominals disagree with it (h3
    # says 24 where gui-3 occupies 28). The reads were removed rather than the
    # keys, because a custom style dict may still carry one; it is ignored.
    #
    # It is the same shape of bug as get_font_size(None) and the old
    # measure_line_height: a hardcoded number sitting next to a font, drifting
    # away from what that font actually measures.
    #
    styles = {
        "t": {"style": "font:gui-6;color:#bbb;", "prepend": "", "indent": 0, "height": 48},
        # `#`/`##`/`###` markdown headings map to h1/h2/h3. NON-numbered (like standard
        # markdown); use the numbered variants nh1/nh2/nh3 (`$nh1 ...`) if you want an
        # auto-numbered outline. (Numbering used to be the h1-3 default; retired so `#`,
        # now the canonical heading syntax, behaves like markdown.)
        "h1":{"style":  "font:gui-5;color:#bbb;", "prepend": "", "indent": 0, "height": 32},
        "h2":{"style":  "font:gui-4;color:#bbb;", "prepend": "", "indent": 0, "height": 28},
        "h3":{"style":  "font:gui-3;color:#bbb;", "prepend": "", "indent": 0, "height": 24},
        "nh1":{"style": "font:gui-5;color:#bbb;", "prepend": "1", "indent": 0, "height": 32},
        "nh2":{"style": "font:gui-4;color:#bbb;", "prepend": "1", "indent": 0, "height": 28},
        "nh3":{"style": "font:gui-3;color:#bbb;", "prepend": "1", "indent": 0, "height": 24},
        "p1":{"style":  "font:gui-2;color:#11f;", "prepend": "", "indent": 0, "height": 20},
        "ul":{"style":  "font:gui-2;color:#11f;", "prepend": "-", "indent": 2, "height": 20},
        "ol":{"style":  "font:gui-2;color:white;", "prepend": "1", "indent": 2, "height": 20},
        "_" :{"style":  "font:gui-2;color:white;", "prepend": "", "indent": 0, "height": 20}
        }
    
    # Old style system
    rule_style_def = re.compile(r"=\$(?P<style_name>\w+)[ \t]*(?P<remainder>.*)")
    rule_style_ref = re.compile(r"\$(?P<style_name>\w+)[ \t]*(?P<remainder>.*)")
    # New markdown system style, image,face, ship
    rule_link_def = re.compile(r"!?\[(?P<link_name>\w*)\]:[ \t]+(?P<ns>\w+):(//)?(?P<urn>.*)")
    # The ! is optional
    rule_link_ref = re.compile(r"!?\[(?P<link_name>\w+)?\](\((?P<ns>\w+):(//)?(?P<urn>.+)\))?(?P<remainder>.+)?")
    
    
    def __init__(self, tag, message) -> None:
        super().__init__(0,0,0,0)
        
        self.content = []
        # This needs to be before self.value=
        self.simple_text = False
        self.value = message
        self.need_v_scroll = False
        
        self.tag = tag
        self.active_tags = set()
        self.lines = []
        self.scroll_line = 0
        self.last_line = 0
        self.max_tag = 0
        self.absolute = True
        self.recalc = True
        self.error_line = ""
        self.error_line_num = 0
        self.styles = TextArea.styles.copy()
        self.link_resolver = None   # fn(key) -> new text; drives [x](ref://key) nav
        self.on_link_cb = None      # fn(key, self); notified on any link click
        self._link_map = {}         # click_tag -> target key
        #self.region = None
        #self.local_region_tag = self.tag+"$$"


    def invalidate_regions(self):
        self.region = None
        self.recalc = True

                
    def get_style(self, key):
        if  isinstance(key, dict):
            return key
        ret = self.styles.get(key, None)
        if ret is None:
            ret = self.styles.get("_")
        return ret

    def calc(self, client_id):
        if self.simple_text:
            return
        
        try:
            self.calc_rich(client_id)
        except Exception:
            self.simple_text = True
            self.content = [f"Document syntax issue line number {self.error_line_num} {self.error_line}"]
            print(self.content)
            self.mark_layout_dirty()


    def measure(self, client_id, mode, avail_px, font, ar):
        """Deliberately unmeasurable, for two independent reasons.

        A text area already handles its own overflow by scrolling -- it adds a
        vertical slider when the content exceeds its bounds -- so it does not
        need the row to grow around it the way a plain label does.

        And measuring it would mean running the whole rich-text parse (images,
        ship/face embeds, tables, wrapping) at a width the parent has not
        committed to yet, then throwing that work away. Falling back to flex is
        both cheaper and closer to what the widget is for.
        """
        return None

    # Width the vertical scrollbar occupies, in PIXELS. Named because the
    # measure pass and the draw pass must agree about it -- see calc_rich.
    V_SCROLL_PX = 20

    def calc_rich(self, client_id, _retry=True):
        if self.simple_text:
            return

        # What the scrollbar decision was BEFORE this pass, so we can tell
        # whether measuring changed it (see the re-run at the end).
        measured_with_scroll = self.need_v_scroll

        content_lines = self.content.copy()
        
        

        self.lines = []
        self._link_map = {}
        links = {}
        calc_height = 0
        self.scroll_line = 0

        ar = get_client_aspect_ratio(client_id)
        # style_default = self.get_style("_")
        style_key = "_"
        heading_numbers = {}
        def get_prepend(style_key):
            prepend = ""
            prepend_fmt = style.get("prepend", "")
            number = heading_numbers.get(style_key,1)
            if prepend_fmt == "1":
                prepend = f"{number}."
                heading_numbers[style_key] = number + 1
            elif prepend_fmt == "a":
                number = number % len(alpha) # wrap don't crash
                prepend = f"{alpha[number].lower()}."
                heading_numbers[style_key] = number + 1
            elif prepend_fmt == "A":
                number = number % len(alpha) # wrap don't crash
                prepend = f"{alpha[number]}."
                heading_numbers[style_key] = number + 1
            elif prepend_fmt == "i":
                number = number % len(roman) # wrap don't crash
                prepend = f"{roman[number]}."
                heading_numbers[style_key] = number + 1
            elif prepend_fmt== "I":
                number = number % len(roman) # wrap don't crash
                prepend = f"{roman[number].upper()}."
                heading_numbers[style_key] = number + 1
            elif prepend_fmt== "*" or prepend_fmt== "-":
                prepend = prepend_fmt
            elif prepend_fmt is not None:
                return prepend_fmt
            return prepend
        
        def clear_sub_headings(style_key):
            if style_key == "t":
                style_key = "h0"
                
            suffix = re.split(r'[^\d]', style_key)
            # title clears all headings

            if len(suffix) != 2 or suffix[1]=="":
                return
            prefix = style_key[:-len(suffix[1])]
            level = int(suffix[1])
            #
            # Only support six levels
            #
            for x in range(level+1, 6):
                sk = f"{prefix}{x}"
                cur = heading_numbers.get(sk, None)
                if cur is None:
                    break
                heading_numbers[sk]=1


        style = None
        style_key = "_"
        prepend = ""
        is_a_list = None
        #
        # Measure at the width the text will actually be DRAWN at, which is
        # narrower when a scrollbar is present. Measuring at the full width and
        # drawing 20px narrower makes the engine wrap a line we did not count,
        # and since the engine does not clip, that line is drawn ON TOP of its
        # neighbour. It showed up as overlapping text in LM's Library document
        # at 1024x768 -- long enough to scroll, so the scrollbar was always
        # there, and roughly one paragraph in eight wraps inside that 20px.
        #
        pixel_width = (self.bounds.right-self.bounds.left)/100 * ar.x
        if self.need_v_scroll:
            pixel_width -= self.V_SCROLL_PX
        alpha = "_ABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890"
        roman = ["_", "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", 
                "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx"]
        
        table_skip = 0
        for i, line in enumerate(content_lines):
            if i < table_skip:                 # lines consumed by a table block
                continue
            self.error_line = line
            self.error_line_num = i
            # EMPTY LINE reset style and prepend
            line_len = len(line.strip())
            if  line_len == 0 or style is None:
                clear_sub_headings(style_key)
                if  line_len == 0:
                    heading_numbers["ol"] = 1
                    heading_numbers["ul"] = 1

                style = self.get_style("_")
                # style = style_default
                # To simplify calculation these start with an item that will never be used
                prepend = None
                is_a_list = None
                if line_len == 0:
                    continue

            # Horizontal rule: <hr> / <hr/> (not '---', which is a table separator)
            if line.strip().lower() in ("<hr>", "<hr/>"):
                hr = HrLine(ar)
                self.lines.append(hr)
                calc_height += hr.height
                continue

            # Whole-line hyperlink: [Display](ref://key) -> clickable LinkLine that
            # navigates within the document via the TextArea's link_resolver.
            m_link = TextArea._whole_link_re.match(line.strip())
            if m_link is not None:
                ctag = f"{self.tag}:lnk{len(self.lines)}"
                self._link_map[ctag] = m_link.group("key").strip()
                ln = LinkLine(m_link.group("disp").strip(), ctag, ar,
                              FrameContext.context.sbs)
                self.lines.append(ln)
                calc_height += ln.height
                continue

            # GFM pipe table: 2+ consecutive lines starting with '|' become a
            # TableLine block. A lone '|' line falls through to normal text.
            if (line.strip().startswith("|") and i + 1 < len(content_lines)
                    and content_lines[i + 1].strip().startswith("|")):
                traw = []
                j = i
                while j < len(content_lines) and content_lines[j].strip().startswith("|"):
                    traw.append(content_lines[j].strip())
                    j += 1
                table_skip = j
                tbl = self._build_table(traw, ar, pixel_width)
                if tbl is not None and tbl.height > 0:
                    self.lines.append(tbl)
                    calc_height += tbl.height
                continue

            style_key, line = self.get_line_style(line, style)
            
            if isinstance(style_key, str):
                style = self.get_style(style_key)
                prepend = get_prepend(style_key)
            elif isinstance(style_key, dict):
                style = style_key
                prepend = style_key.get("prepend")
                if prepend is None:
                    prepend = ""
                style_key = "$"

            # If this is a list each line is numbered
            # otherwise just the first line
            if is_a_list is None:
                is_a_list = style_key.startswith("ol") or  style_key.startswith("ul")
                if is_a_list:
                    is_a_list = style_key
                
            # if not is_a_list:
            line = prepend +  line
            
            last_line = None

            st1 = style.get("style", "font:gui-3;")
            props = split_props(st1, "font")
            font = props.get("font", "gui-3")

            
            ns = None

            if m := TextArea.rule_style_def.match(line):
                """Parse a old style style definitions """
                g = m.groupdict()
                style_name = g.get("style_name")
                remainder = g.get("remainder")
                data  = self.parse_style_line(remainder) 
                if data is not None:
                    self.styles[style_name] = data
                continue
            # elif m := TextArea.rule_style_ref.match(line):
            #     """
            #     Parse a old style style reference 
            #     Handled in get_line_style
            #     """
            #     pass                    
            elif m := TextArea.rule_link_def.match(line):
                # <link_name> <ns>\w+): (?P<urn>.*)
                g = m.groupdict()
                link_name = g.get("link_name")
                ns = g.get("ns")
                urn = g.get("urn")
                
                links[link_name] = {"ns": ns, "urn": urn}
                continue

                
            elif m := TextArea.rule_link_ref.match(line):
                g = m.groupdict()
                link_name = g.get("link_name")
                ns = g.get("ns")
                urn = g.get("urn")
                line = g.get("remainder")

                if link_name is not None and ns is None:
                    test_style = self.get_style(link_name)
                    
                    if test_style is not None and test_style != self.styles.get("_"):
                        st1 = style.get("style", "font:gui-3;")
                        props = split_props(st1, "font")
                        font = props.get("font", "gui-3")
                        style = test_style
                    else:
                        g = links.get(link_name)
                        if g is None:
                            continue
                        ns = g.get("ns")
                        urn = g.get("urn")
                # The rest is handle below
            # Image line
            if ns == "image":
                last_line = ImageLine(urn, ar)
                self.lines.append(last_line)
                calc_height += last_line.height
                continue
            elif ns == "ship":
                last_line = ShipLine(urn, ar)
                self.lines.append(last_line)
                calc_height += last_line.height
                continue
            elif ns == "face":
                last_line = FaceLine(urn, ar)
                self.lines.append(last_line)
                calc_height += last_line.height
                continue
            elif ns == "style":
                style = dict(self.get_style("_"))
                
                props = split_props(urn, "font")
                font = props.get("font", "gui-3")
                style["background"] = props.get("background")
                props.pop("background", None)
                style["style"] = merge_props(props)
                # Let this fall through if there is a line
                if line is None or len(line.strip()) == 0:
                    continue
                
            if line is None:
                continue
            

            # Break lines on MEASURED word widths, not on a character count.
            #
            # This used to estimate "how many characters fit" from the line's
            # average glyph width and hand that to TextWrapper. An average is
            # wrong in both directions -- it breaks early on a run of narrow
            # glyphs and late on wide ones -- so lines ended short of the edge
            # for no visible reason ("...walks into / a bar" taking three lines
            # where two fit). Measuring the words removes the estimate.
            sub_lines = wrap_to_width(font, line, pixel_width)

            for sub_line in sub_lines:
                ll = sub_line.strip().lower()

                pixel_height = measure_block_height(font, sub_line, int(pixel_width))
            
                #buffer = 0.1
                #percent_height = ((pixel_height + buffer*pixel_line_height) / ar.y) * 100
                percent_height = (pixel_height/ ar.y) * 100
                
                if ll =="<br>" or ll =="<br/>":
                    sub_line = "^"
                last_line = TextLine(sub_line,style, self.bounds.width, percent_height, False)
                
                self.lines.append(last_line)
                calc_height += percent_height

        #
        # Calculate the right size for the scrollbar
        #
        self.need_v_scroll = calc_height > self.bounds.height

        #
        # The scrollbar decision depends on the wrapped height, and the wrapped
        # height depends on whether the scrollbar is there -- a genuine cycle.
        # Break it the same way the layout breaks the square/content cycle: one
        # bounded re-run, never iterate to convergence. The measurements are
        # memoized, so the second pass is nearly free.
        #
        if _retry and self.need_v_scroll != measured_with_scroll:
            self.calc_rich(client_id, _retry=False)
            return

        self.last_line = len(self.lines)
        self.scroll_line = self.last_line
        if not self.need_v_scroll:
            return
        
        # Back track to find the last line
        calc_height = 0
        while calc_height < self.bounds.height:
            self.last_line-=1
            if self.last_line<=0:
                break
            
            height = self.lines[self.last_line].height

            if self.lines[self.last_line].is_sec_end:
                calc_height += 0.5*height
            calc_height += height
        
        self.last_line = min(self.last_line+1, len(self.lines))
        self.scroll_line = min(self.last_line+1,len(self.lines))
        

    _table_sep_re = re.compile(r"^:?-{2,}:?$")
    _whole_link_re = re.compile(r"^\[(?P<disp>[^\]]+)\]\((?:ref|link)://(?P<key>[^)]+)\)$")

    def _build_table(self, raw_rows, ar, pixel_width):
        """Parse GFM pipe rows into a TableLine. The |:--|--:| separator row (if
        present) supplies per-column alignment and is dropped from the data; a
        table with no separator row just renders all-left with row 0 as header."""
        rows = []
        aligns = []
        for rr in raw_rows:
            cells = [c.strip() for c in rr.strip().strip("|").split("|")]
            non_empty = [c for c in cells if c != ""]
            if non_empty and all(TextArea._table_sep_re.match(c) for c in non_empty):
                aligns = []
                for c in cells:
                    lft, rgt = c.startswith(":"), c.endswith(":")
                    aligns.append("c" if lft and rgt else "r" if rgt else "l")
                continue
            rows.append(cells)
        if not rows:
            return None
        return TableLine(rows, aligns, ar, pixel_width, FrameContext.context.sbs)

    def get_line_style(self, some_lines, previous):
        style_key = None
        if some_lines.startswith("$$"):
            s = some_lines.split(" ",1)
            if len(s) == 2:
                st = self.parse_style_line(s[0][2:])
                return st,s[1]
            return "_",some_lines
        elif some_lines.startswith("$"):
            some_lines, style_key = self.split_styled_lines(some_lines)
        else:
            return self.get_markdown_line_style(some_lines, previous)
        
        return style_key,some_lines

    def split_styled_lines(self, some_lines):
        sp = some_lines.find(" ")
        nl = some_lines.find("\n")
        style_key="_"
        if sp>=0 and (nl <0 or sp <nl):
            style_key = some_lines[1:sp]
            some_lines = some_lines[sp:]
        elif nl >0:
            style_key = some_lines[1:nl]
            some_lines = some_lines[nl:]
        return some_lines,style_key
    
    def get_markdown_line_style(self, some_lines, previous):
        style_key = None
        if some_lines.startswith("#"):
            count = 0
            while some_lines[count]=="#":
                count+=1

            style_key = f"h{count}"
            some_lines = some_lines[count:]

        elif some_lines.startswith("-"):
            
            style_key = f"ul"
            sp = some_lines.split(" ",1)
            if len(sp)>1:
                some_lines = sp[1]

        elif some_lines[0].isdigit():
            style_key = f"ol"
            sp = some_lines.split(" ",1)
            if len(sp)>1:
                some_lines = sp[1]
        
        if style_key is None:
            if previous is None:
                return "_"
            return previous, some_lines
        return style_key,some_lines
            
    def _promote_if_overflowing(self, client_id):
        """A one-line message that does not FIT is not a simple label.

        The simple/rich choice is made in the `value` setter, before the widget
        has bounds -- so "one line" there means "contains no newline", NOT
        "draws as one line". Hand a whole paragraph to gui_text_area as
        `$text:...` and it took the fast path: a single send_gui_text across the
        widget's rect, with no wrap accounting, no line list and no scrollbar.
        The engine wraps it anyway and, since it does not clip, draws the tail
        below the widget. Reaching for gui_text_area to fix a spilling label
        therefore changed nothing -- the widget quietly declined to be a text
        area, which is what sent LM's mission picker down this path.

        So ask the question again HERE, where the bounds exist: measure the text
        at the width it will be drawn at, and if it is taller than the widget,
        rewrite it as rich content so calc_rich wraps it and gives it a
        scrollbar. Text that fits keeps the cheap path untouched, which is the
        overwhelmingly common case (a one-line styled label).

        The rewrite uses the `$$<props> <text>` line form DELIBERATELY. The
        author wrote a styled label, not markdown, so a description that happens
        to start with '-' or a digit must not silently become a bullet or a
        numbered list item. `$$` names the style outright and skips the markdown
        sniffing in get_line_style.

        Promotion is one-way until the value is re-set. Re-deciding every frame
        would oscillate: the rich form is exactly what makes the text fit.
        """
        if not self.content:
            return False
        ar = get_client_aspect_ratio(client_id)
        avail_px = (self.bounds.right - self.bounds.left) / 100 * ar.x
        if avail_px <= 0:
            return False

        message = self.content[0]
        # mode=None: natural size wrapped to the width we will actually draw at.
        size = measure_props(message, None, avail_px, self.get_font(), ar)
        if size is None or size[1] <= self.bounds.height:
            # Fits, or is unmeasurable (no engine metrics) -- leave it alone.
            return False

        props = split_props(message, "$text")
        text = props.pop("$text", None)          # both spellings leave `props`,
        alt = props.pop("text", None)            # which is now style-only
        if text is None:
            text = alt
        if text is None:
            return False
        text = text.strip()
        if len(text) >= 2 and text.startswith("`") and text.endswith("`"):
            text = text[1:-1]
        if not text:
            return False

        #
        # The rich path builds its own message and does NOT append the cascade,
        # so anything the row/section was contributing has to be folded in now.
        # The widget's own props win, matching what the engine draws today.
        #
        for k, v in split_props(self.get_cascade_props(True, True, True), "font").items():
            props.setdefault(k, v)
        # Values are stripped because the `$$` form splits style from text on
        # the FIRST space -- an authored `justify: left` would end it early.
        style = merge_props({k: str(v).strip() for k, v in props.items()})

        self.content = [f"$${style} {text}"]
        self.simple_text = False
        self.recalc = True
        return True

    def _present_simple(self, event):
        ctx = FrameContext.context
        message = self.content[0]
        if "$text:" not in message:
            if "text:" not in message:
                message = f"$text:{gui_text_escape(message)};"

        message += self.get_cascade_props(True, True, True)

        ctx.sbs.send_gui_text(event.client_id, self.local_region_tag,
            self.tag, message,  
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)



    def _present(self, event):
        #
        # Handle simple gui_text. This is the first point at which the widget
        # knows its bounds, so it is also where a "simple" message that turns
        # out to be a whole paragraph gets promoted to the rich path -- see
        # _promote_if_overflowing.
        #
        if self.simple_text:
            if not self._promote_if_overflowing(event.client_id):
                return self._present_simple(event)
        ctx = FrameContext.context
        CID = event.client_id
        
        ar = get_client_aspect_ratio(CID)
        if self.recalc:
            self.calc(event.client_id)
            self.recalc = False

        first_line = self.last_line - self.scroll_line
        
        
        bounds = Bounds(self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        # Room for scrollbar always
        if self.need_v_scroll:
            bounds.right -= self.V_SCROLL_PX*100/ar.x
        #TODO: calc line to start drawing
        text_line: TextLine
        for i, text_line in enumerate(self.lines):
            tag = f"{self.tag}:{i}"
            # For now draw all lines 
            # draw off screen if they should not be seen.
            if i < first_line:
                continue
            elif i == first_line:
                bounds.top = self.bounds.top

            new_bottom = bounds.top + text_line.height
            if new_bottom  > self.bounds.bottom:
                break
            
            bounds.bottom = new_bottom 

            
            if isinstance(text_line, TextLine):
                style_obj = text_line.style
                style = style_obj.get("style")
                background = style_obj.get("background")
                
                indent = style_obj.get("indent", 0) 
                message = f"$text:{gui_text_escape(text_line.text)};{style}"
                # if bounds.top < 900:
                #     print(f"Sending line {message} {bounds} {self.local_region_tag}")
                space_width = measure_line_width("gui-2", "X") / ar.x *100
                if background:
                    props = f"image:smallwhite;color:{background};draw_layer:1000;"
                    ctx.sbs.send_gui_image(CID, self.local_region_tag,
                        tag, props,  
                        bounds.left+indent*space_width, bounds.top, bounds.right, bounds.bottom)
                    
                ctx.sbs.send_gui_text(CID, self.local_region_tag,
                    tag, message,  
                    bounds.left+indent*space_width, bounds.top, bounds.right, bounds.bottom)
            else:
                text_line.send_gui(ctx.sbs, CID, self.local_region_tag, tag,  
                    bounds.left, bounds.top, bounds.right, bounds.bottom)
            
            bounds.top = bounds.bottom


            if text_line.is_sec_end:
                bounds.top += text_line.height/2

            #    bounds.top = 1000

        # Add Scroll if needed
        if self.need_v_scroll:
            scroll_bounds = Bounds(self.bounds)
            max = (self.last_line+1)
            cur = self.scroll_line

            # print(f"TEXT AREA {cur} {max}")

            ctx.sbs.send_gui_slider(CID,self.local_region_tag, f"{self.tag}vbar", int(cur), f"low:0; high: {max}; show_number:no",
                scroll_bounds.right-self.V_SCROLL_PX*100/ar.x, scroll_bounds.top,
                scroll_bounds.right, scroll_bounds.bottom)


    def update(self, message):
        self.value = message

    
    @property
    def value(self):
         return self.content
       
    @value.setter
    def value(self, message):
        message = message.strip()
        message = message.replace("^", "\n")
        # Split into sections
        message_list = message.split("\n")

        if len(message_list)==1:
            if "$text:" in message_list[0]:
                self.simple_text = True
                self.content = message_list
                self.mark_visual_dirty()
                return
            if not (message_list[0].startswith("=") or message_list[0].startswith("$")):
                self.simple_text = True
                self.content = message_list
                self.mark_visual_dirty()
                return
        # Make sure there is an end line
        self.simple_text = False
        self.recalc = True

        # check for style header section
        self.content = message_list

        # self.styles = TextArea.styles.copy()
        self.mark_visual_dirty()


    def parse_header(self, header):
        # "t": {"style": "font:gui-6;color:#bbb;", "prepend": "", "indent": 0},
        header = header.split("\n")
        self.styles = TextArea.styles.copy()
        for temp in header:
            # just skip comment or bad formatting
            if m := TextArea.rule_link_def.match(temp):
                key = m.group("link_name")
                st = m.group("urn")
                ns = m.group("ns")
                if key is None or st is None or ns != "style":
                    continue
            elif temp.startswith("=$"):
                sp = temp.find(" ")
                # again just skip bad formatting
                if sp == -1:
                    continue

                key = temp[2:sp]
                st = temp[sp:].strip()
            else:
                continue
            
            data  = self.parse_style_line(st)
            if data is not None:
                self.styles[key] = data

    def parse_style_line(self,line):
        value = line.strip().rsplit(" | ")
        style = value[0]
        indent = 0
        prepend = None
        
        kv = split_props(style, "font")
        font = kv.get("font")
        background = kv.get("background")
        if background is not None:
            kv.pop("background")
        style = merge_props(kv)
        
        height = get_font_size(font)

        if len(value)==2:
            
            prepend = value[1].split(">")

            if len(prepend) == 2:
                indent = 0 # Default is just one space
                s_indent = prepend[1].strip()
                s_indent = s_indent.strip(';')
                if s_indent.isdigit():
                    indent = int(s_indent)
            prepend = prepend[0].strip()
            if prepend == "":
                prepend = ""
        
        return {"style": style, "prepend": prepend, "indent": indent, "height": height, "background": background}



    def on_message(self, event):
        # Hyperlink click: resolve the key and navigate within the document.
        if event.sub_tag in self._link_map:
            key = self._link_map[event.sub_tag]
            if self.on_link_cb is not None:
                self.on_link_cb(key, self)
            if self.link_resolver is not None:
                new_text = self.link_resolver(key)
                if new_text is not None:
                    self.value = new_text        # triggers recalc on next present
                    self.scroll_line = 0
                    self.present(event)
            return
        if event.sub_tag != f"{self.tag}vbar":
            return
        value = int(event.sub_float)
        #value = int(-event.sub_float+self.last_line+0.5)
        if value != self.scroll_line:
            self.scroll_line = value
            self.gui_state = "redraw"
            self.present(event)
        


