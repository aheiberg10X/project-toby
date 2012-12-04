import pokereval
from deck import Deck, makeMachine, makeHuman, collapseBoard, getStreet, truncate
from itertools import combinations
import rollout
import matplotlib.pyplot as plt
from os import listdir
from os.path import exists
import json
from time import time

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

#a heavily customized DFS thru iteration
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

#TODO replace with python func
def makeRound( num, precision=2 ) :
    return int( num * pow(10,precision) )

def computeDists(num_known_board, EV_or_HS) :
    already_seen = {}
    count = 0
    
    if num_known_board == 3 : street = 'flops'
    elif num_known_board == 4 : street = 'turns'
    elif num_known_board == 5 : street = 'rivers'
    else : assert False

    for board in combinations( d.cards, num_known_board ) :
        collapsed = collapseBoard( board )
        if EV_or_HS == 'EV' :
            path = "evdists/%s/%s.evdist" % (street,collapsed)
        else :
            path = "hsdists/%s/%s.hsdist" % (street,collapsed)

        if collapsed in already_seen or exists(path) : 
            continue
        else :
            print count, collapsed
            count += 1
            board = makeHuman(board) + ['__']*(5-num_known_board)
            
            x = []
            if EV_or_HS == 'EV' :
                d_pocket_EV = rollout.computeEVs( [], board, 2, num_threads=4 )
                for ev in d_pocket_EV.values() :
                    x.append( makeRound( ev ) )
            else :
                d_pocket_HS = rollout.computeHSs( board, num_threads=4 )
                for hs in d_pocket_HS.values() :
                    x.append( hs )

            x.sort()
            
            fout = open(path, 'w')
            fout.write( "%s\n" % ';'.join([str(t) for t in x]) )
            fout.close()

            already_seen[collapsed] = True

        #print "breaking"
        #break

def visualizeEVDist( filepath, buckets=40 ) :
    path,filename = filepath.rsplit('/',1)
    name,ext = filename.rsplit('.',1)
    x = [int(n) for n in open(filepath).read().strip().split(',')]
    #TODO:
    #make ranges all 0-100
    plt.hist(x,buckets)
    filename = "%s/%s.png" % (path,name)
    print "saving to: ", filename
    plt.savefig( filename )
    plt.clf()

#TODO
#how much space/performace trade off is there in rounding off the hs2 values?
#currently using 4 decimal places, maybe 2 is sufficient
#and will cut down on dictionary size in memory
def computeBuckets( street, bucket_percentages ) :
    print sum(bucket_percentages)
    assert abs( sum(bucket_percentages) - 1.0 ) < .000001

    folder = "hsdists"
    #dflop_memprobs = {}
    fout = open("%s/%s/membership_probs.txt" % (folder,street),'w')

    for i,dist_file in enumerate(listdir( "%s/%s" % (folder,street) )) :
        if not dist_file.endswith('dist') : 
            continue 
        collapsed_name = dist_file.split('.')[0]
        print i, "bucketing ", collapsed_name

        fin = open( "%s/%s/%s" % (folder, street, dist_file) )
        EVs = [int(ev) for ev in fin.read().strip().split(',')]
        fin.close()

        num_EVs = len(EVs)
        #how many EVs does each bucket get?
        bucket_masses = [int(round(bp*num_EVs)) for bp in bucket_percentages]
        #print "sum bucket_masses", sum(bucket_masses), "num_EVs", num_EVs


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

                #print last_seen_ev, membership_probs[last_seen_ev]
                last_seen_ev = ev
                count = 1
            else :
                count += 1
            
        #dflop_memprobs[collapsed_name] = membership_probs
        #TODO all mem getting used, must print incrementally
        #hope in correct JSON format
        fout.write( '"%s" : %s\n' % (collapsed_name, json.dumps(membership_probs)))
        #print len(dflop_memprobs)
        #print membership_probs
        #print len(membership_probs)
        #a = raw_input()

        #print "bucket counts", bucket_counts, "sum", sum(bucket_counts)
        #print "num EVs bucketed:", tcount
        #break
    #print dflop_memprobs
    #fout.write( json.dumps( dflop_memprobs ) )
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

def computeDistsHS() :
    results = {}   
    count = 0
    a = time()
    for board in combinations( range(52), 5 ) :
        if count % 100 == 0 : 
            print count
            print time() - a
            a = time()
        d_pocket_HS2 = rollout.computeHSs( known_pockets = [['__','__']] ,\
                                           board = list(board) )
        flop = collapseBoard( board[0:3] )
        turn = collapseBoard( board[0:4] )
        river =collapseBoard( board )
        streets = [flop, turn, river]
        for street in streets[:2] :
            if street not in results :
                results[street] = {}
        
        #rounding precision
        precision = 4
        #collect the HS2 for the river
        river_hs2 = []
        for pocket in d_pocket_HS2 :
            hs2 = d_pocket_HS2[pocket]
            #flop and turn
            for street in streets[:2] :
                if pocket not in results[street] :
                    results[street][pocket] = [hs2,1]
                else :
                    results[street][pocket][0] += hs2
                    results[street][pocket][1] += 1

            river_hs2.append( makeRound(hs2,precision) )
           
        #the 5 card board is unique, so we can print out right away
        name = "hsdists/rivers/%s.hsdist" % river
        if not exists(name) :
            friver = open( name, 'w' )
            friver.write( ";".join( [str(t) for t in sorted(river_hs2)] ) + "\n" )
            friver.close()

        count += 1
        if count == 5000 :
            #fout = open("test.txt",'w')
            #fout.write( json.dumps(results) )
            #fout.close()
            break
    
    #once all the boards are done, have results[board][pocket] = HS2sum, count
    for collapsed_board in results :
        num_cards = len(collapsed_board.split('_')[0])
        if num_cards == 3 :   street_name = 'flops'
        elif num_cards == 4 : street_name = 'turns'
        else: assert False

        #print "collapsed name:", collapsed_board, " street name: " , street_name

        HS2s = []
        for pocket in results[collapsed_board] :
            (HS2sum, count) = results[collapsed_board][pocket]
            avg = makeRound( HS2sum / count, precision )
            if collapsed_board == '234_s_3f' :
                print pocket, HS2sum, count 
            HS2s.append( avg )

        filename = "hsdists/%s/%s.hsdist" % (street_name, collapsed_board)
        fout = open( filename, 'w' )
        #print "len HS2s: ", len(HS2s)
        fout.write( ';'.join( [str(t) for t in sorted(HS2s)] )+"\n" )
        fout.close()

def main() :
    pass

if __name__ == '__main__' :
    #computeDistsHS()

    #count = 0
    #for decision_stack in iterateDecisionPoints ( num_players=2, \
                                                  #max_rounds=2, \
                                                  #button=0, \
                                                  #player_ix=0) :
        #print decision_stack
        #count += 1
    #print count
    folder = "hsdists"
    dmass = {'flops' : [.4,.1,.1] + [.05]*4 + [.02]*10, \
             'turns' : [.4,.1,.1] + [.05]*4 + [.02]*10, \
             'rivers': [.45,.15,.14,.05,.05,.05,.05,.02,.02,.02] }
    computeBuckets( 'turns', dmass['turns'] )
    #for street in listdir( folder ) :
        #for listing in listdir("%s/%s" % (folder,street)) :
            #if listing.endswith("hsdist") :
                #visualizeEVDist( "%s/%s/%s" % (folder,street,listing) )
    
    #visualizeEVDist( "hsdists/flops/234_s_3f.hsdist" )
    #visualizeEVDist( "evdists/37TK_h_4f.evdist" )
    #visualizeEVDist( "evdists/37TK_h_3fxxxo.evdist" )

    #computeDists(3,'HS')
    #visualizeEVDist( "hsdists/flops/234_s_3f.hsdist" )
    

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

