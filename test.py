import sbs_utils.layout as layout
w = layout.wrap(80,100, 19, 4,col=2, v_dir=-1, h_dir=-1)
T = next(w)
print( T[0],T[1],T[2],T[3] )
                
print(next(w))
print(next(w))
print(next(w))
print(next(w))
