import pokereval
from deck import Deck, makeMachine, makeHuman, collapseBoard, getStreet, truncate
from itertools import combinations
import rollout
import matplotlib.pyplot as plt
from os import listdir
from os.path import exists
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
    if outstanding.startswith('r') or outstanding == 'b' :
        return action == 'f' or \
               action == 'c' or \
               action.startswith('r')
    elif outstanding == 'k' :
        return not action.startswith('r') and \
               not action == 'c' and \
               not action == 'f'
    else :
        print "outstanding: ",outstanding
        return False

def isTerminal( stack, num_players, pix ) :
    if stack[pix] == 'f' : return True
    if len(stack) >= num_players :
        if all([a == 'k' for a in stack[-num_players:]]) :
            return True
        elif all([a == 'c' or a == 'f' for a in stack[-num_players+1:]]) :
            return True
        else :
            return False
    else :
        return False

def isFolded( stack, pix, num_players ) :
    if 0 <= pix-num_players < len(stack) :
        return stack[pix-num_players] == 'f'
    else :
        return False

#a heavily modified DFS thru iteration
def iterateDecisionPoints( num_players, max_rounds, button, player_ix ) :
    #actions available to players
    actions = ['f','k','c','b','r1-2p','r1p','r3-2p','r2p']
    final_actions = ['f','k','c']

    #the actions taken by the players
    stack = []

    #virtual_player % num_players represents the player in some round
    #there are only max rounds where players are free to act (i.e keep raising)
    #the final round players must only choose from final_actions 
    num_virtual = num_players * (max_rounds + 1)
    
    #for each player, hold an iterator of actions
    actions_iters = [42]*num_virtual

    #refill the action iters based on the betting round they belong to
    def refill( pix ) :
        if pix >= num_virtual - num_players :
            actions_iters[pix] = iter(final_actions)
        else :
            actions_iters[pix] = iter(actions)

    [refill(pix) for pix in range(num_virtual)]

    #(virtual) player index
    pix = 0
    last_to_act = -1
 
    #the action each player must base their next off of
    outstanding = ['k']*num_virtual

    while True :
        try :
            #if this player just gave an action and must do so again
            if last_to_act == pix :
                stack.pop()
                #if I just acted, and my previous self folded, I am 
                #all out of options
                if isFolded(stack,pix,num_players ) : 
                    raise StopIteration
            
            if isFolded(stack,pix,num_players) : 
                next_action = 'f'
            #else get new valid action
            else :
                next_action = actions_iters[pix].next()
                while not isLegal(next_action, outstanding[pix]) :
                    next_action = actions_iters[pix].next()

            stack.append( next_action )
            #print "\n\n",pix, stack 

            last_to_act = pix

            #if the action terminates the betting we dont care
            if isTerminal( stack, num_players, pix ) :
                continue

            #if not the last player, set the next player's outstanding action
            #and make it so next player must act next time thru loop
            if pix < num_virtual-1 : 
                if next_action == 'b' or \
                   next_action.startswith('r') or \
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
                refill(pix)
                last_to_act = pix-1
                pix -= 1



def makeRound( EV ) :
    return int( EV * 100 )

def computeEVDists(num_known_board=4) :
    already_seen = {}
    count = 0
    
    if num_known_board == 3 : street = 'flops'
    elif num_known_board == 4 : street = 'turns'
    elif num_known_board == 5 : street = 'rivers'
    else : assert False

    for board in combinations( d.cards, num_known_board ) :
        collapsed = collapseBoard( board )
        path = "evdists/%s/%s.evdist" % (street,collapsed)
        if collapsed in already_seen or exists(path) : 
            continue
        else :
            print count, collapsed
            count += 1
            #board = makeHuman(board) + ['__']*(5-num_known_board)
            #pocketEVs = rollout.computeEVs( [], board, 2, num_threads=4 )
            #x = []
            #for pocket in pocketEVs :
                #x.append( makeRound( pocketEVs[pocket] ) )
            #x.sort()
#
            #fout = open(path, 'w')
            #fout.write( "%s\n" % ';'.join([str(t) for t in x]) )
            #fout.close()

            already_seen[collapsed] = True

        #print "breaking"
        #break

def visualizeEVDist( filepath, buckets=40 ) :
    path,filename = filepath.rsplit('/',1)
    name,ext = filename.rsplit('.',1)
    x = [int(n) for n in open(filepath).read().strip().split(';')]
    #TODO:
    #make ranges all 0-100
    plt.hist(x,buckets)
    plt.savefig("%s/%s.png" % (path,name) )
    plt.clf()


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
    #count = 0
    #for decision_stack in iterateDecisionPoints ( num_players=2, \
                                                  #max_rounds=2, \
                                                  #button=0, \
                                                  #player_ix=0) :
        #print decision_stack
        #count += 1
    #print count
    #for listing in listdir("evdists" ) :
        #if listing.endswith("evdist") :
            #visualizeEVDist( "evdists/%s" % listing )
    
    #visualizeEVDist( "evdists/37TQ_h_3fxxox.evdist" )
    #visualizeEVDist( "evdists/37TK_h_4f.evdist" )
    #visualizeEVDist( "evdists/37TK_h_3fxxxo.evdist" )

    computeEVDists()
    
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

