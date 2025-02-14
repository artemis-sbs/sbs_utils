class Bounds:
    def __init__(self, left=0, top=0, right=0, bottom=0) -> None:
        if left is None:
            self.left=0
            self.top=0
            self.right=0
            self.bottom=0
        elif isinstance(left, Bounds):
            self.left=left.left
            self.top=left.top
            self.right=left.right
            self.bottom=left.bottom
        else:
            self.left=left
            self.top=top
            self.right=right
            self.bottom=bottom

    def __str__(self) -> str:
        return f"l: {self.left:3.2f} r: {self.right:3.2f} t: {self.top:3.2f} b: {self.bottom:3.2f}"
    @property
    def height(self):
        return self.bottom-self.top
    
    @height.setter
    def height(self, h):
        self.bottom = self.top+h

    @property
    def width(self):
        return self.right-self.left
    @width.setter
    def width(self, w):
        self.right = self.left + w

    def __repr__(self) -> str:
        return f"{self.left}, {self.top}, {self.right}, {self.bottom}"

    def __add__(self, o):
        return Bounds(self.left+o.left,
            self.top+o.top,
            self.right+o.right,
            self.bottom+o.bottom)
    
    def __sub__(self, o):
        return Bounds(self.left-o.left,
            self.top-o.top,
            self.right-o.right,
            self.bottom-o.bottom)
    
    
    def shrink(self, o):
        if o is None:
            return
        self.left   +=  o.left
        self.top    += o.top
        self.right  -= o.right
        self.bottom -= o.bottom
    
    def grow(self, o):
        if o is None:
            return
        self.left   -=  o.left
        self.top    -= o.top
        self.right  += o.right
        self.bottom += o.bottom

    def merge(self, b):
        if b is None:
            return
        self.left = min(b.left, self.left)
        self.top= min(b.top, self.top)
        self.right= max(b.right, self.right)
        self.bottom = max(b.bottom, self.bottom)
