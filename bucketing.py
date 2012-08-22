import pokereval
from deck import Deck, makeMachine, makeHuman, collapseBoard, getStreet, truncate
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

#board = ['2c','3c','Td','__','__']
#print board
#pocket1 = ['4c','8c']
#pocket2 = ['4d','8h']
#print pe.poker_eval( game, [pocket1, pocket2], board )

#x = range(10)
#plt.hist( x )
#plt.show()

def isLegal( action, outstanding ) :
    if outstanding == 'r' or outstanding == 'b' :
        return action == 'f' or \
               action == 'c' or \
               action == 'r'
    elif outstanding == 'k' :
        return not action == 'r' and \
               not action == 'c' and \
               not action == 'f'
    else :
        print "outstanding: ",outstanding
        return False

def isTerminal( stack, num_players ) :
    if len(stack) >= num_players :
        if all([a == 'k' for a in stack[-num_players:]]) :
            return True
        elif all([a == 'c' or a == 'f' for a in stack[-num_players+1:]]) :
            return True
        else :
            return False
    else :
        return False

#a heavily modified DFS thru iteration
def iteratePossibleActions( num_players, max_rounds, button, player_ix ) :
    actions = ['f','k','c','b','r']
    final_actions = ['f','k','c']
    stack = []
    iters = []
    #virtual_player % num_players represents the player in some round
    #there are only max rounds where players are free to act (i.e keep raising)
    #the final round players must finally decide on a terminal action
    num_virtual = num_players * (max_rounds + 1)
    folded = [False]*num_virtual
    print "hello"
    for player in range(num_virtual) :
        if player >= num_virtual - num_players :
            iters.append( iter(final_actions) )
        else :
            iters.append( iter(actions) )

    #(virtual) player index
    pix = 0
    last_to_act = -1
    #the action each player must deal with
    outstanding = ['k']*num_virtual
    while True :
        try :
            #print "\n\n",pix, stack#, folded

            #if this player just gave an action and must do so again
            if last_to_act == pix :
                stack.pop()
                #if folded and past self folded, nothing more to do
                if folded[pix] and folded[pix-num_players] :
                    folded[pix] = False
                    raise StopIteration
            
            #past self folded, so must fold
            if folded[pix-num_players] :
                next_action = 'f'
            #else get new valid action
            else :
                next_action = iters[pix].next()
                while not isLegal(next_action, outstanding[pix]) :
                    next_action = iters[pix].next()

            stack.append( next_action )
            folded[pix] = next_action == 'f'
            last_to_act = pix

            #if the action terminates the betting we dont care
            if isTerminal( stack, num_players ) :
                continue

            #if not the last player, set the next player's outstanding action
            #and make it so next player must act next time thru loop
            if pix < num_virtual-1 : 
                if next_action == 'b' or \
                   next_action == 'r' or \
                   next_action == 'k' :
                    outstanding[pix+1] = next_action
                else :
                    outstanding[pix+1] = outstanding[pix]

                pix += 1
                #if next player is the one we are interested in, 
                #return the decision history up until this point
                if pix % num_players == player_ix :
                    yield stack

        #if a player runs out of moves, refill his moves and jump back to 
        #the previous player
        except StopIteration :
            if pix == 0 : break
            else :
                #print "pix refilling", pix
                if pix >= num_virtual - num_players :
                    iters[pix] = iter(final_actions) 
                else :
                    iters[pix] = iter(actions)
                last_to_act = pix-1
                pix -= 1



def makeRound( EV ) :
    return int( EV * 100 )

def computeEVDists(num_known_board=4) :
    already_seen = {}
    for board in combinations( d.cards, num_known_board ) :
        collapsed = collapseBoard( board )
        if collapsed in already_seen : 
            continue
        else :
            board = makeHuman(board) + ['__']*(5-num_known_board)
            pocketEVs = rollout.computeEVs( [], board, 2, num_threads=4 )
            x = []
            for pocket in pocketEVs :
                x.append( makeRound( pocketEVs[pocket] ) )
            x.sort()

            fout = open("evdists/%s.evdist" % collapsed, 'w')
            fout.write( "%s\n" % ';'.join([str(t) for t in x]) )
            fout.close()

            #plt.hist(x,100)
            ##plt.savefig("evdists/%s_evdist.png" % collapsed)
            #plt.show()
            already_seen[collapsed] = True

        #print "breaking"
        #break


def computeBuckets( street, bucket_percentages ) :
    assert int(sum(bucket_percentages)) == 1 
    #wtf <= works but not ==
    #assert sum(bucket_percentages) == 1.0

    #TODO: 
    #variable names hard coded for flop

    dflop_memprobs = {}
    for flop_file in listdir( "evdists/%s" % street) :
        print flop_file

        if not flop_file.endswith('evdist') : break
        collapsed_name = flop_file.split('.')[0]

        fin = open( "evdists/%s/%s" % (street, flop_file) )
        EVs = [int(ev) for ev in fin.read().strip().split(';')]
        fin.close()

        num_EVs = len(EVs)
        #how many EVs does each bucket get?
        bucket_masses = [int(round(bp*num_EVs)) for bp in bucket_percentages]
        print "sum bucket_masses", sum(bucket_masses), "num_EVs", num_EVs


        #Info about the bucket we are currently filling
        bucket_ix = 0
        bucket_mass = 0
        bucket_total_mass = bucket_masses[bucket_ix]
       
        #soft bucketing
        #EV : {bucket_ix : percentage}
        membership_probs = {}

        #EVs come in sorted order from the file, so we read until we see
        #a new value
        last_seen_ev = EVs[0]
        #count up how many of a particular EV value we see
        count = 0 
        #append a -1 so the last run of values gets processed
        EVs.append(-1)
        for ev in EVs :
            if not ev == last_seen_ev :
                unbucketed_count = count
                remaining_space = bucket_total_mass - bucket_mass
                membership_probs[last_seen_ev] = {}

                #if we can't fit the unbucketed EVs in the current bucket
                #fill it up and increment to the next bucket
                #rinse repeat
                while remaining_space < unbucketed_count :
                    #fill up current bucket rest of the way
                    membership_probs[last_seen_ev][bucket_ix] = \
                            float(remaining_space) / count
                    unbucketed_count -= remaining_space

                    #start in on new bucket
                    bucket_ix += 1
                    bucket_mass = 0
                    if bucket_ix >= len(bucket_masses) : break
                    bucket_total_mass = bucket_masses[bucket_ix]
                    remaining_space = bucket_total_mass
                
                bucket_mass += unbucketed_count
                membership_probs[last_seen_ev][bucket_ix] = \
                        float(unbucketed_count) / count

                print last_seen_ev, membership_probs[last_seen_ev]
                last_seen_ev = ev
                count = 1
            else :
                count += 1
            
            dflop_memprobs[collapsed_name] = membership_probs

        print "bucket counts", bucket_counts, "sum", sum(bucket_counts)
        print "num EVs bucketed:", tcount
        break
    #print dflop_memprobs
    fout = open("evdists/flop/membership_probs.txt",'w')
    fout.write( json.dumps( dflop_memprobs ) )
    fout.close()

flop_bucket_map = {}
def bucketPocket( pocket, board ) :
    global flop_bucket_map

    collapsed = collapseBoard( board )
    EV = makeRound( rollout.computeEV( pocket, board ) )
    street = getStreet( board )
    if street == 'flop' :
        if not flop_bucket_map :
            fflop = open("evdists/flop/membership_probs.txt")
            flop_bucket_map = json.loads( fflop.read() )
            fflop.close()
        memberships = flop_bucket_map[collapsed]
        keys = memberships.keys()
        keys.sort()
        for k in keys :
            print k, memberships[k]
        #TODO:
        #right, so what do we do with the membership probs?
        #the idea is to reduce the complexity, having another float 
    else :
        pass


def main() :
    pass

if __name__ == '__main__' :
    for decision_stack in iteratePossibleActions( num_players=3, \
                                                  max_rounds=2, \
                                                  button=0, \
                                                  player_ix=2) :
        print decision_stack
    #computeEVDists()
    
    #dmass = {'flop' : [.4,.1,.1] + [.05]*4 + [.02]*10, \
             #'turn' : 20, \
             #'river': 10 }
    #computeBuckets( 'flop', dmass['flop'] )

    #print bucketPocket( ['Ah','7d'], ['Ad','7h','8c','__','__'] )
    
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

