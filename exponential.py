from math import pow

ks = [(.6,20),(.75,40),(.7,30),(.65,20)]
k = 3 


ratio = ks[k][0]
percentiles = []
nbuckets = ks[k][1]

for i in range(1,nbuckets+1) :
     percentiles.append( pow( ratio,i ) )


acc = sum(percentiles)
normalized = [p / acc for p in percentiles]
a = normalized[:nbuckets/2]
b = normalized[nbuckets/2:]
print [a[i] + b[nbuckets/2-i-1] for i in range(nbuckets/2)]
#for i in range(nbuckets/2) :
    #print nbuckets-1-i
  



