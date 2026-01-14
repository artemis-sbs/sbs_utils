from .layout import Column, Bounds, get_font_size
from ...helpers import FrameContext
from ...gui import get_client_aspect_ratio

import re

from ..widgets.control import Control

class TextLine:
    def __init__(self, text, style, width, height, is_sec_end) -> None:
        self.text = text.strip()
        self.style = style
        self.height = height
        self.width = width
        self.is_sec_end = is_sec_end

class ImageLine:
    def __init__(self, text, ary) -> None:
        from ...procedural.gui.image import gui_image_get_atlas

        url = text.split("?")
        text = url[0]
        scale = 1.0
        self.color = None
        self.fill = 2

        if len(url)>1:
            values = url[1].split("&")
            for value in values:
                kv = value.split("=")
                if len(kv)==2:
                    key = kv[0].strip()
                    if key == "scale":
                        try:
                            scale = float(kv[1].strip())
                        except ValueError:
                            pass
                    if key == "color":
                        self.color = kv[1]
                    if key == "fill":
                        v = kv[1].strip()
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
            self.height = (height / ary) * 100 * scale


class TextArea(Control):
    styles = {
        "t": {"style": "font:gui-6;color:#bbb;", "prepend": "", "indent": 0, "height": 48},
        "h1":{"style":  "font:gui-5;color:#bbb;", "prepend": "1 ", "indent": 0, "height": 32},
        "h2":{"style":  "font:gui-4;color:#bbb;", "prepend": "1 ", "indent": 0, "height": 28},
        "h3":{"style":  "font:gui-3;color:#bbb;", "prepend": "1 ", "indent": 0, "height": 24},
        "p1":{"style":  "font:gui-2;color:#11f;", "prepend": "", "indent": 0, "height": 20},
        "ul":{"style":  "font:gui-2;color:#11f;", "prepend": "-", "indent": 2, "height": 20},
        "ol":{"style":  "font:gui-2;color:white;", "prepend": "1", "indent": 2, "height": 20},
        "_" :{"style":  "font:gui-2;color:white;", "prepend": "", "indent": 0, "height": 20}
        }
    
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
        #self.region = None
        #self.local_region_tag = self.tag+"$$"


    # def invalidate_regions(self):
    #     self.region = None

                
    def get_style(self, key):
        ret = self.styles.get(key, None)
        if ret is None:
            ret = self.styles.get("_", "font:gui-2;color:white;")
        return ret

    def calc(self, client_id):
        if self.simple_text:
            return
        
        content_lines = self.content.copy()
        self.lines = []
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



        for some_lines in content_lines:
            # style = style_default
            height = 20
            style_key = "_"
            # To simplify calculation these start with an item that will never be used
            alpha = "_ABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890"
            roman = ["_", "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", 
                     "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx"]
            prepend = None
            style_key, some_lines = self.get_line_style(some_lines)

            style = self.get_style(style_key)
            height = style.get("height", 90)
            prepend = get_prepend(style_key)
            # If this is a list each line is numbered
            # otherwise just the first line
            is_a_list = style_key.startswith("ol") or  style_key.startswith("ul")
            if not is_a_list:
                some_lines = prepend +  some_lines


            # Not sure why 50 expected 100, but
            # it is proportional and a guess?
            # char_width = (self.bounds.width * 20) / ar.x
            # max_char = int(self.bounds.width // char_width)
            pixel_width = (self.bounds.right-self.bounds.left)/100 * ar.x
            lines = some_lines.split("\n")
            last_line = None

            if is_a_list:
                heading_numbers[style_key] = 1
            else:
                clear_sub_headings(style_key)

            font = style.get("font", "gui-3")
            for line in lines:
                if len(line.strip()) == 0:
                    continue
                
                #is_a_list = style_key.startswith("ol") or  style_key.startswith("ul")
                if is_a_list:
                    prepend = get_prepend(style_key)
                    line = prepend +  line

                if line.startswith("!"):
                    # Image line
                    line = line[1:]
                    last_line = ImageLine(line, ar.y)
                    self.lines.append(last_line)
                    calc_height += last_line.height
                else:
                    pixel_height = FrameContext.context.sbs.get_text_block_height(font, line, int(pixel_width))
                    pixel_line_height = FrameContext.context.sbs.get_text_line_height(font, line)
                    # Adds 10 pixels for buffer
                    buffer = 1.5
                    if is_a_list:
                        buffer = 0.2
                    percent_height = ((pixel_height + buffer*pixel_line_height) / ar.y) * 100
                    last_line = TextLine(line,style_key, self.bounds.width, percent_height, False)
                    self.lines.append(last_line)
                    calc_height += percent_height

        #
        # Calculate the right size for the scrollbar
        #
        self.need_v_scroll = calc_height > self.bounds.height
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
        

    def get_line_style(self, some_lines):
        style_key = "_"
        if some_lines.startswith("$"):
            some_lines, style_key = self.split_styled_lines(some_lines)
        else:
            return self.get_markdown_line_style(some_lines)
        
        return style_key,some_lines

    def split_styled_lines(self, some_lines):
        sp = some_lines.find(" ")
        nl = some_lines.find("\n")
        if sp>=0 and (nl <0 or sp <nl):
            style_key = some_lines[1:sp]
            some_lines = some_lines[sp:]
        elif nl >0:
            style_key = some_lines[1:nl]
            some_lines = some_lines[nl:]
        return some_lines,style_key
    
    def get_markdown_line_style(self, some_lines):
        style_key = "_"
        if some_lines.startswith("#"):
            count = 0
            while some_lines[count]=="#":
                count+=1

            style_key = f"h{count}"
            some_lines = some_lines[count:]

        elif some_lines.startswith("-"):
            lines = some_lines.split("\n")
            style_key = f"ul"
            some_lines = [""]
            for line in lines:
                if line.startswith("-"):
                    sp = line.split(" ",1)
                    if len(sp)>1:
                        some_lines.append(sp[1])
                    else:
                        some_lines.append(sp[0])
                else:
                    some_lines[-1]+= "\n"+line
            some_lines = "\n".join(some_lines)

        elif some_lines[0].isdigit():
            style_key = f"ol"
            lines = some_lines.split("\n")
            some_lines = [""]
            for line in lines:
                if line[0].isdigit():
                    sp = line.split(" ",1)
                    if len(sp)>1:
                        some_lines.append(sp[1])
                    else:
                        some_lines.append(sp[0])
                else:
                    some_lines[-1]+= "\n"+line
            some_lines = "\n".join(some_lines)

        # elif some_lines.startswith(">"):
        #     count = 0
        #     while some_lines[count]==">":
        #         count+=1

        #     style_key = f"block"
        #     some_lines = some_lines[count:]

        return style_key,some_lines
            
    def _present_simple(self, event):
        ctx = FrameContext.context
        message = self.content[0]
        if "$text:" not in message:
            if "text:" not in message:
                message = f"$text:{message};"

        message += self.get_cascade_props(True, True, True)

        ctx.sbs.send_gui_text(event.client_id, self.local_region_tag,
            self.tag, message,  
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)



    def _present(self, event):
        #
        # Handle simple gui_text
        #
        if self.simple_text:
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
            bounds.right -= 20*100/ar.x
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

            
            if isinstance(text_line, ImageLine):
                text_line.atlas.send_gui_image(ctx.sbs, CID, tag, self.local_region_tag, text_line.fill,  
                    bounds.left, bounds.top, bounds.right, bounds.bottom, text_line.color)
            else:

                style_obj = self.get_style(text_line.style)
                style = style_obj.get("style")
                
                indent = style_obj.get("indent", 0) 
                message = f"$text:{text_line.text};{style}"
                # if bounds.top < 900:
                #     print(f"Sending line {message} {bounds} {self.local_region_tag}")
                space_width = FrameContext.context.sbs.get_text_line_width("gui-2", "X") / ar.x *100
                ctx.sbs.send_gui_text(CID, self.local_region_tag,
                    tag, message,  
                    bounds.left+indent*space_width, bounds.top, bounds.right, bounds.bottom)
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
                scroll_bounds.right-20*100/ar.x, scroll_bounds.top,
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
        message = re.split(r"\n\n\n*", message)

        if len(message)==1:
            if "$text:" in message[0]:
                self.simple_text = True
                self.content = message
                return
            if not (message[0].startswith("=") or message[0].startswith("$")):
                self.simple_text = True
                self.content = message
                return
        # Make sure there is an end line
        self.simple_text = False
        self.recalc = True

        # print("-------")
        # for i,m in enumerate(message):
        #     print(f"{i}[{m}]")
        # print("-------")

        # check for style header section
        if len(message) > 0 and message[0].startswith("=$"):
            self.parse_header(message[0])
            message.pop(0)
        self.content = message 


    def parse_header(self, header):
        # "t": {"style": "font:gui-6;color:#bbb;", "prepend": "", "indent": 0},
        self.styles = TextArea.styles.copy()
        header = header.split("\n")
        for temp in header:
            # just skip comment or bad formatting
            if not temp.startswith("=$"):
                continue

            sp = temp.find(" ")
            # again just skip bad formatting
            if sp == -1:
                continue

            key = temp[2:sp] 
            value = temp[sp:].strip().rsplit(" | ")
            style = value[0]
            indent = 0
            prepend = None
            font = None
            f = style.find("font:")
            if f >=0:
                semi = style.find(";", f)
                f +=5
                if semi >= 0:
                    font = style[f:semi]

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
            
            self.styles[key] = {"style": style, "prepend": prepend, "indent": indent, "height": height}



    def on_message(self, event):
        if event.sub_tag != f"{self.tag}vbar":
            return
        value = int(event.sub_float)
        #value = int(-event.sub_float+self.last_line+0.5)
        if value != self.scroll_line:
            self.scroll_line = value
            self.gui_state = "redraw"
            self.present(event)
        


