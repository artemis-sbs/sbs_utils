

def wrap(left, top, width, height, col=1, h_gutter=1, v_gutter=1, v_dir=1, h_dir=1):
    start_left = left
    this_col = 0
    while(top<=100):
        l = left
        r = left+width
        t = top
        b = top+height
        if v_dir ==-1:
            b = top
            t = top-height
        if h_dir ==-1:
            r = left
            l = left-width
        


        yield (l, t, r, b)

        this_col += 1
        left += h_dir*(width + h_gutter)
        if this_col>=col:
            this_col = 0
            top+= v_dir*(height + v_gutter)
            left = start_left


    