import imp
emd = imp.load_source('emd','python-emd/emd.py')
from emd import emd
from globles import bucketCentroidDistance

def bucketTransferCostClosure(street) :
    def inner(F1,F2) :
        #print "\n\n",F1,F2
        #print street
        (b1,bp1) = F1
        (b2,bp2) = F2
        if b1 != b2 :
            assert False
            return 9999999;
        else :
            dist = bucketCentroidDistance(street,bp1,bp2)
            return dist
    return inner

def getBTDistance( street, W1, W2 ) :
    W1 = [float(t) for t in W1]
    W2 = [float(t) for t in W2]
    F1 = [(1,i) for i in range(len(W1))]
    F2 = [(1,i) for i in range(len(W2))]
    return emd( (F1,W1), (F2,W2), bucketTransferCostClosure(street) )


def test() :
    #print "wrong cause python is 0 indexed"
    #assert False
    #F1 = [[1,1],[1,2],[1,3],[1,4],[1,5]];
    #F2 = [[1,1],[1,2],[1,3],[1,4]];
    W1 = [0.043367,0.093112,0.060374,0.042942,0.039541,0.034864,0.026361,0.007653,0.0,0.005102,0.005102,0.001276,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]
    W2 = [0.043367,0.096939,0.052296,0.045918,0.035714,0.035714,0.026361,0.008503,0.00085,0.007653,0.005102,0.001701,0.00085,0.0,0.0,0.0,0.0,0.0,0.0,0.00085]
    W3 = [0.060162,0.083121,0.066043,0.034297,0.033163,0.017857,0.01977,0.020196,0.011054,0.007653,0.003401,0.004677,0.00085,0.0,0.0,0.0,0.0,0.0,0.0,0.00085]
    #dummy|238_h_3f, k=2
    W4 = [0.087372,0.018707,0.037415,0.018282,0.030825,0.007653,0.0,0.005102,0.005952,0.009354,0.005102,0.003047,0.006179,0.002041,0.001701,0.0,0.0,0.0,0.0,0.0]
    #dummy|23A_s_3f   k = 2
    W5 = [0.08716,0.04932,0.040816,0.022959,0.007653,0.007653,0.0,0.012755,0.002551,0.004252,0.00085,0.004039,0.003614,0.003486,0.002041,0.0,0.001701,0.0,0.0,0.0]
    print getBTDistance( "flop", W4,W5 )

if __name__ == "__main__" :
    test()

#from collections import namedtuple
#from math import sqrt
#
#Feature = namedtuple("Feature", ["x", "y", "z"])
#
#
#def distance(f1, f2):
    #return sqrt( (f1.x - f2.x)**2  + (f1.y - f2.y)**2 + (f1.z - f2.z)**2 )
#
#
#def main():
    #features1 = [Feature(100, 40, 22), Feature(211, 20, 2),
                 #Feature(32, 190, 150), Feature(2, 100, 100)]
    #weights1  = [0.4, 0.3, 0.2, 0.1]
   # 
    #features2 = [Feature(0, 0, 0), Feature(50, 100, 80), Feature(255, 255, 255)]
    #weights2  = [0.5, 0.3, 0.2]
   # 
    #print emd( (features1, weights1), (features2, weights2), distance )
#
#
#if __name__ == "__main__":
    #pass
    #main() 
