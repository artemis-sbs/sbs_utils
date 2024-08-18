import random


all_bits = [2**x for x in range(12)]
print(all_bits)
def random_bits(bits, count):
    pick = list(all_bits[:bits])
    ret = 0
    random.shuffle(pick)
    print(pick)
    p = pick[:count]
    print(p)
    for b in p:
        ret |= b
        
    return ret

        
print("R"+str(random_bits(6,3)))
print("R"+str(random_bits(6,3)))
print("R"+str(random_bits(6,3)))
print("R"+str(random_bits(6,3)))
print("R"+str(random_bits(6,3)))

