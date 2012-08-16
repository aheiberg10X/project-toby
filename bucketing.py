import pokereval
from deck import Deck, makeMachine, makeHuman, collapseFlop
from itertools import combinations
import rollout
import matplotlib.pyplot as plt

num_buckets = 20

pe = pokereval.PokerEval()
d = Deck()

game = 'holdem'
side = 'hi'

#TODO
#so the EV distributions for different flops/turns/rivers are very different
#what we need to do is:
    #pick the number of buckets and what percentage of holdings go in each them
    #then for each flop EV dist figure out where the partition boundaries lie
#but first need to compute the EV dist for all collapsed flops
#so first need to collapse flops and way to iterate through all of them
#    just maintain dict of previously seen collapsed ____'s? ignore the rest
#    can just use the first flop representing a category, things are symm
#    i.e hold cardinality equal.  
#           one pocket that benefits from suit (A), one that doesn't (B)
#    The EV(B) will be the EV(A) when you symm change the suit of the flop

#board = ['2c','3c','Td','__','__']
#print board
#pocket1 = ['4c','8c']
#pocket2 = ['4d','8h']
#print pe.poker_eval( game, [pocket1, pocket2], board )

#x = range(10)
#plt.hist( x )
#plt.show()

num_known_board = 3
already_seen = {}
for board in combinations( d.cards, num_known_board ) :
    collapsed = collapseFlop( board )
    if collapsed in already_seen : 
        continue
    else :
        board = makeHuman(board) + ['__']*(5-num_known_board)
        pocketEVs = rollout.computeEVs( [], board, 2, num_threads=4 )
        x = []
        for pocket in pocketEVs :
            x.append( int(pocketEVs[pocket]*100) )
        x.sort()

        fout = open("bucketing/%s.evdist" % collapsed, 'w')
        fout.write( "%s\n" % ';'.join([str(t) for t in x]) )
        fout.close()

        plt.hist(x,100)
        plt.savefig("bucketing/%s_evdist.png" % collapsed)
        #plt.show()

        already_seen[collapsed] = True
    break


#board = ['2h','3h','4h','5h','__']
#board = ['Jd','Jh','8c','8d','__']

#board = ['2h','3h','4h','__','__']
#board = ['2c','3c','4c','__','__']
#board = ['3d','8c','Jh','__','__']
#board = ['Jd','Jh','8c','__','__']
#board = ['Jd','Jh','8c','__','__']

#print board

#print pocketEVs['5h,9d']
#print pocketEVs['9d,5c']
#break

