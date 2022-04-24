from math import log
y1 = 1.7
y2 = 0.79
x1 = 200
x2 = 1000

m = log(y2/y1) / log(x2/x1)

print("M = {}".format(round(m, 5)))

midy = 1.2
midx = 500
b = log(midy) - (m)*log(midx)

print("B = {}".format(round(b, 5)))

print("")
send_str = "PPM = 10 ^ {[log(ratio) -" + str(round(b, 3)) + "] / " + str(round(m, 3)) + "}"
print(send_str)