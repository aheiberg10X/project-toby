import pokereval
from deck import Deck, makeMachine, makeHuman, collapseBoard
from itertools import combinations
import rollout
import matplotlib.pyplot as plt
from os import listdir
import json

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

#One thing we are not considering is the two to a flush combinations
#3d8dJh has slightly diff dist from 3h8dJd, but we treat them as same
#hopefully not a huge deal, will save space and time

#board = ['2c','3c','Td','__','__']
#print board
#pocket1 = ['4c','8c']
#pocket2 = ['4d','8h']
#print pe.poker_eval( game, [pocket1, pocket2], board )

#x = range(10)
#plt.hist( x )
#plt.show()

def computeEVDists() :

    num_known_board = 3
    already_seen = {}
    for board in combinations( d.cards, num_known_board ) :
        board = ['Td','Jd','Qd','Kd','Ad']
        collapsed = collapseBoard( board )
        print collapsed
        if collapsed in already_seen : 
            continue
        else :
            board = makeHuman(board) + ['__']*(5-num_known_board)
            pocketEVs = rollout.computeEVs( [], board, 2, num_threads=4 )
            x = []
            for pocket in pocketEVs :
                x.append( int(pocketEVs[pocket]*100) )
            x.sort()

            #fout = open("evdists/%s.evdist" % collapsed, 'w')
            #fout.write( "%s\n" % ';'.join([str(t) for t in x]) )
            #fout.close()

            plt.hist(x,100)
            #plt.savefig("evdists/%s_evdist.png" % collapsed)
            plt.show()

            already_seen[collapsed] = True
        print "breaking"
        break

def computeBuckets( street, bucket_percentages ) :
    assert int(sum(bucket_percentages)) == 1 
    #wtf <= works but not ==
    #assert sum(bucket_percentages) == 1.0

    dflop_memprobs = {}
    for flop_file in listdir( "evdists/%s" % street) :
        print flop_file

        collapsed_name,ext = flop_file.split('.')
        if not ext == 'evdist' : break

        fin = open( "evdists/%s/%s" % (street, flop_file) )
        EVs = [int(ev) for ev in fin.read().strip().split(';')]
        num_EVs = len(EVs)
        bucket_masses = [int(round(bp*num_EVs)) for bp in bucket_percentages]
        #print "bucket_masses", bucket_masses
        EVs.append(-1)

        bucket_ix = 0
        bucket_mass = 0
        bucket_total_mass = bucket_masses[bucket_ix]
        
        #EV : {bucket_ix : percentage}
        membership_probs = {}

        last_seen_ev = EVs[0]
        count = 0 
        for ev in EVs :
            if not ev == last_seen_ev :
                unbucketed_count = count
                remaining_space = bucket_total_mass - bucket_mass
                membership_probs[last_seen_ev] = {}
                #print "unbucketed count", unbucketed_count
                #print "remaining_space", remaining_space

                while remaining_space < unbucketed_count :
                    #print "unbucketed count", unbucketed_count
                    #print "remaining_space", remaining_space
                    assert remaining_space >= 0
                    assert count >= 0
                    membership_probs[last_seen_ev][bucket_ix] = \
                            float(remaining_space) / count
                    unbucketed_count -= remaining_space
                    bucket_ix += 1
                    bucket_mass = 0
                    if bucket_ix >= len(bucket_masses) : break
                    bucket_total_mass = bucket_masses[bucket_ix]
                    remaining_space = bucket_total_mass
                
                bucket_mass += unbucketed_count
                assert unbucketed_count >= 0
                assert count >= 0
                membership_probs[last_seen_ev][bucket_ix] = \
                        float(unbucketed_count) / count


                #print last_seen_ev, membership_probs[last_seen_ev]
                last_seen_ev = ev
                count = 1
            else :
                count += 1
            
            dflop_memprobs[collapsed_name] = membership_probs

        fin.close()
        #break
    #print dflop_memprobs
    fout = open("evdists/flop/membership_probs.txt",'w')
    fout.write( json.dumps( dflop_memprobs ) )
    fout.close()

def main() :
    pass

if __name__ == '__main__' :
    #computeEVDists()
    
    dmass = {'flop' : [.4,.1,.1] + [.05]*4 + [.02]*10, \
             'turn' : 20, \
             'river': 10 }
    computeBuckets( 'flop', dmass['flop'] )
    
    #board = ['2h','3h','4h','5h','__']
    #board = ['Jd','Jh','8c','8d','__']

    #board = ['2h','3h','4h','__','__']
    #board = ['2c','3c','4c','__','__']
    board = ['3c','8d','Jd','__','__']
    #board = ['Jd','Jh','8c','__','__']
    #board = ['Jd','Jh','8c','__','__']

    #print board

    #print pocketEVs['5h,9d']
    #print pocketEVs['9d,5c']
    #break

