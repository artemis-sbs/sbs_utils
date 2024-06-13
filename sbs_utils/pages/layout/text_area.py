from .layout import Column, Bounds, get_font_size
from ...helpers import FrameContext
from ...gui import get_client_aspect_ratio
import re
import sbs

class TextLine:
    def __init__(self, text, style, width, height, is_sec_end) -> None:
        self.text = text.strip()
        self.style = style
        self.height = height
        self.width = width
        self.is_sec_end = is_sec_end

class TextArea(Column):
    styles = {
        "t": {"style": "font:gui-6;color:#bbb;", "prepend": "", "indent": 0, "height": 48},
        "h1":{"style":  "font:gui-5;color:#bbb;", "prepend": "1 ", "indent": 0, "height": 32},
        "h2":{"style":  "font:gui-4;color:#bbb;", "prepend": "1 ", "indent": 0, "height": 28},
        "h3":{"style":  "font:gui-3;color:#bbb;", "prepend": "1 ", "indent": 0, "height": 24},
        "p1":{"style":  "font:gui-2;color:#11f;", "prepend": "", "indent": 0, "height": 20},
        "ul":{"style":  "font:gui-2;color:#11f;", "prepend": "", "indent": 2, "height": 20},
        "ol":{"style":  "font:gui-2;color:#11f;", "prepend": "1", "indent": 2, "height": 20},
        "_" :{"style":  "font:gui-2;color:white;", "prepend": "", "indent": 0, "height": 20}
        }
    
    def __init__(self, tag, message) -> None:
        super().__init__()
        
        self.content = []
        # This needs to be before self.value=
        self.simple_text = False
        self.value = message
        self.need_v_scroll = False
        
        self.tag = tag
        self.active_tags = set()
        self.lines = []
        self.start_line = 0
        self.last_line = 0
        self.max_tag = 0
        self.region = None
        self.local_region_tag = self.tag+"$$"


    def invalidate_regions(self):
        self.region = None

                
    def get_style(self, key):
        ret = self.styles.get(key, None)
        if ret is None:
            ret = self.styles.get("_", None)
        return ret

    def calc(self, client_id):
        if self.simple_text:
            return
        
        content_lines = self.content.copy()
        self.lines = []
        calc_height = 0
        self.start_line = 0

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
            elif prepend_fmt is not None:
                return prepend_fmt
            return prepend
        
        def clear_sub_headings(style_key):
            if style_key == "t":
                style_key = "h0"
                
            suffix = re.split('[^\d]', style_key)
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
                #print(f"clearing {sk}")
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
            if some_lines.startswith("$"):
                sp = some_lines.find(" ")
                nl = some_lines.find("\n")
                if sp>=0:
                    style_key = some_lines[1:sp]
                    some_lines = some_lines[sp:]
                elif nl >0:
                    style_key = some_lines[1:nl]
                    some_lines = some_lines[nl:]

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
            char_width = height *65 / ar.x
            max_char = int(self.bounds.width // char_width)

            is_end = False
            lines = some_lines.split("\n")
            last_line = None

            if is_a_list:
                heading_numbers[style_key] = 1
            else:
                clear_sub_headings(style_key)

            for line in lines:
                if len(line.strip()) == 0:
                    continue
                while len(line) >0:
                    left_over = ""
                    if len(line)>max_char:
                        chop_sp = line.rfind(" ", 0, max_char)
                        if chop_sp!=-1:
                            left_over = line[chop_sp:].strip()
                            line = line[:chop_sp].strip()

                    # Chop up string by length?
                    screen_height = height *100 / ar.y
                    calc_height += screen_height
                
                    is_a_list = style_key.startswith("ol") or  style_key.startswith("ul")
                    if is_a_list:
                        prepend = get_prepend(style_key)
                        line = prepend +  line
                    last_line = TextLine(line,style_key, char_width, screen_height, False)
                    self.lines.append(last_line)
                    line = left_over

            if last_line is not None:
                last_line.is_end = True
                last_line.height *= 1.5

        #
        # Calculate the right size for the scrollbar
        #
        self.need_v_scroll = calc_height > self.bounds.height
        self.last_line = len(self.lines)
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
            # print(f"LL {height}")
            calc_height += height
            
    def _present_simple(self, event):
        ctx = FrameContext.context
        message = self.content[0]
        if "text:" not in message:
            message = f"text:{message};"

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
        
        bounds = Bounds(self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        # Room for scrollbar always
        bounds.right -= 20*100/ar.x
        #TODO: calc line to start drawing
        tags = set()
        text_line: TextLine
        for i, text_line in enumerate(self.lines):
            style_obj = self.get_style(text_line.style)
            style = style_obj.get("style")
            indent = style_obj.get("indent", 0) 

            message = f"text:{text_line.text};{style}"
            
            tag = f"{self.tag}:{i}"
            tags.add(tag)
            # For now draw all lines 
            # draw off screen if they should not be seen.
            if i < self.start_line:
                bounds.top = 1000
            elif i == self.start_line:
                bounds.top = self.bounds.top
            bounds.bottom = bounds.top + text_line.height

            ctx.sbs.send_gui_text(CID, self.local_region_tag,
                tag, message,  
                bounds.left+indent*text_line.width, bounds.top, bounds.right, bounds.bottom)
            bounds.top = bounds.bottom
            if text_line.is_sec_end:
                bounds.top += text_line.height/2

            if bounds.top > self.bounds.bottom:
                bounds.top = 1000

        # This should hide any tags used prior that are no needed right now
        hide_tags =  self.active_tags - tags
        for t in hide_tags:
            ctx.sbs.send_gui_text(CID, self.local_region_tag,
                t, "text: ;",  
                bounds.left, 1000, bounds.right, 1000)
        self.active_tags = tags

        # Add Scroll if needed
        scroll_bounds = Bounds(self.bounds)
        if not self.need_v_scroll:
            scroll_bounds.top = -1000
            scroll_bounds.bottom = -1000

        max = -(self.last_line+1)
        cur = self.start_line

        ctx.sbs.send_gui_slider(CID,self.local_region_tag, f"{self.tag}vbar", -int(cur), f"low:{max}; high: 0; show_number:no",
            scroll_bounds.right-20*100/ar.x, scroll_bounds.top,
            scroll_bounds.right, scroll_bounds.bottom)

    def present(self, event):
        CID = event.client_id
        is_update = self.region is not None
        # If first time create sub region
        if not is_update:
            sbs.send_gui_sub_region(CID, self.region_tag, self.local_region_tag, "draggable:False;", 0,0,100,100)
            self.region = True
            super().present(event)
        else:
            sbs.send_gui_clear(CID, self.local_region_tag)
            super().present(event)
            sbs.send_gui_complete(CID, self.local_region_tag)

        #sbs.target_gui_sub_region(CID, "")
        

    def update(self, message):
        # print(f"{message}")
        self.message = message

    
    @property
    def value(self):
         return self.message
       
    @value.setter
    def value(self, message):
        message = message.strip()
        message = message.replace("^", "\n")
        # Split into sections
        message = re.split(r"\n\n+", message)

        if len(message)==1:
            # if "text:" in message[0]:
            self.simple_text = True
            self.content = message
            return

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
                    if s_indent.isdigit():
                        indent = int(s_indent)
                prepend = prepend[0].strip()
                if prepend == "":
                    prepend = ""
            self.styles[key] = {"style": style, "prepend": prepend, "indent": indent, "height": height}



    def on_message(self, event):
        if event.sub_tag != f"{self.tag}vbar":
            return
        print("TextArea")
        value = -int(event.sub_float)
        if value != self.start_line:
            self.start_line = value
            self.gui_state = "redraw"
            self.present(event)
        


