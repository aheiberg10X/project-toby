import pokereval
from deck import Deck, makeMachine, makeHuman, collapseBoard, getStreet, truncate, canonicalize
from itertools import combinations
import rollout
import matplotlib.pyplot as plt
from os import listdir
from os.path import exists
import json
from time import time
import globles
from multiprocessing import Process, Queue, Pool

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

#{pocket:EHS2} -> {pocket:{bucket:%membership}}
def computeBucket( d_pocket_EHS2, bucket_percentages ) :
    print sum(bucket_percentages)
    assert abs( sum(bucket_percentages) - 1.0 ) < .000001
    #sort EHS2
    sorted_pockets = []
    EHS2s = []
    d_reverse = {}
    for pocket in sorted(d_pocket_EHS2, key=lambda x : d_pocket_EHS2[x]) :
        sorted_pockets.append( pocket )
        ehs2 = d_pocket_EHS2[pocket]
        EHS2s.append( ehs2 )
        if ehs2 in d_reverse :
            d_reverse[ehs2].append( pocket )
        else :
            d_reverse[ehs2] = [pocket]

    num_EHS2s = len(EHS2s)
    #how many EHS2s does each bucket get?
    bucket_masses = [int(round(bp*num_EHS2s)) for bp in bucket_percentages]
    #print "sum bucket_masses", sum(bucket_masses), "num_EHS2s", num_EHS2s

    #Info about the bucket we are currently filling
    bucket_ix = 0
    bucket_mass = 0
    bucket_total_mass = bucket_masses[bucket_ix]
   
    #soft bucketing
    #EV : {bucket_ix : percentage}
    membership_probs = {}

    #EHS2s come in sorted order from the file, so we read until we see
    #a new value
    last_seen_ehs2 = EHS2s[0]
    #count up how many of a particular EV value we see
    count = 0 
    #append a -1 so the last run of values gets processed
    EHS2s.append(-1)
    for ehs2,pocket in zip(EHS2s,sorted_pockets) :
        if not ehs2 == last_seen_ehs2 :
            unbucketed_count = count
            remaining_space = bucket_total_mass - bucket_mass
            for pocket in d_reverse[ehs2] :
                membership_probs[pocket] = {}

            #if we can't fit the unbucketed EHS2s in the current bucket
            #fill it up and increment to the next bucket
            #rinse repeat
            while remaining_space < unbucketed_count :
                #fill up current bucket rest of the way
                for pocket in d_reverse[ehs2] :
                    membership_probs[pocket][bucket_ix] = \
                            float(remaining_space) / count
                unbucketed_count -= remaining_space

                #start in on new bucket
                bucket_ix += 1
                bucket_mass = 0
                if bucket_ix >= len(bucket_masses) : break
                bucket_total_mass = bucket_masses[bucket_ix]
                remaining_space = bucket_total_mass
            
            bucket_mass += unbucketed_count
            for pocket in d_reverse[ehs2] :
                membership_probs[pocket][bucket_ix] = \
                        float(unbucketed_count) / count

            #print last_seen_ehs2, membership_probs[last_seen_ehs2]
            last_seen_ehs2 = ehs2
            count = 1
        else :
            count += 1
        
    #dflop_memprobs[collapsed_name] = membership_probs
    #TODO all mem getting used, must print incrementally
    #hope in correct JSON format
    return membership_probs

    assert 'KdAd' in sorted_pockets
        
 
#TODO take two sequential - {pocket:{bucket:%}} and compute, given bucket X
# in the first, what is the likely hood of bucket Y?
# P( b' | b, board, board' )
def bucketTransitionProb( b_prime, b, board, board_prime, bucket_percentages ) :
    #P( b' | b,board,board' ) = sum_pockets P( b' | p,board') * P(p | board,b)
    #                                             [A]
    #P( p | board,b ) = P( b|p,board) * P(p|F) / P(b|board)
    #                      [B]            [C]      [D]
    acc = 0
    acc2 = 0
    for pocket in combinations(range(52),globles.POCKET_SIZE) :
        #print ""
        pocket = canonicalize(list(pocket))
        #print makeHuman(pocket)
        #A
        A = 0
        if pocket in board_prime and b_prime in board_prime[pocket] :
            A = board_prime[pocket][b_prime]

        #B
        B = 0
        if pocket in board and b in board[pocket] :
            B = board[pocket][b]

               
        #if A > 0 and B > 0:
            #print "\nbucket", b_prime
            #print makeHuman(pocket)
            #print "A,B", A,B
        acc += A * B 
        acc2 += B
    
    #C
    #already checked legality of pocket against flop in 'if' above
    #so just the probability of a given pocket
    C = 1/float(len(board))

    #D - board doesn't matter, depends on construction of percentiles
    D = bucket_percentages[b]
    
    #C/D is really trying to get 1/(number of pockets in bucket b)

    #print "A*B sum:", acc
    #print "B sum: ", acc2
    #print "C/D weight:", C/D

    return acc / float(acc2)

#TODO
#how much space/performace trade off is there in rounding off the hs2 values?
#currently using 4 decimal places, maybe 2 is sufficient
#and will cut down on dictionary size in memory
#TODO: use computeBucket, once we get get everything settled
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

        ##Moved to computeBucket

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

def computeEHS2Dists() :
    already_repped = set([])
    results = {}   
    count = 0
    a = time()
    
    pool = Pool(processes=8)
    for board in combinations( range(52), 5 ) :
        count += 1
        if count % 100 == 0 : 
            print count
            print time() - a
            a = time()
        
        #pit every possible hand against 'mystery' known_pocket
        #and compute the HS2 from rollout
        known_pockets = ['__','__']

        d_pocket_HS2 = rollout.mapReduceComputeEHS2( pool, list(board) )

        flop = ''.join( makeHuman(board[0:3]) )
        cflop = collapseBoard( flop )
        turn = ''.join( makeHuman(board[0:4]) ) 
        cturn = collapseBoard( turn )
        river = ''.join( makeHuman(board) )
        criver =collapseBoard( river )

        streets = [flop,turn,river]
        cstreets = [cflop, cturn, criver]

        for street, cstreet in zip(streets[:2],cstreets[:2]) :
            if cstreet not in already_repped and street not in results :
                results[street] = {}

        for cstreet in cstreets :
            already_repped.add( cstreet )

        
        #rounding precision
        precision = 4
        #collect the HS2 for the river
        river_hs2 = {} 
        for pocket in d_pocket_HS2 :
            hs2 = d_pocket_HS2[pocket]
            #flop and turn
            for street in streets[:2] :
                if street in results :
                    if pocket not in results[street] :
                        results[street][pocket] = [hs2,1]
                    else :
                        results[street][pocket][0] += hs2
                        results[street][pocket][1] += 1
                else :
                    pass
                    #already_repped

            river_hs2[pocket] =makeRound(hs2,precision)
           
        #the 5 card board is unique, so we can print out right away
        name = "hsdists/rivers/%s.hsdist" % criver
        if criver not in already_repped : #not exists(name) :
            friver = open( name, 'w' )
            friver.write( json.dumps( river_hs2 ) )
            #friver.write( ";".join( [str(t) for t in sorted(river_hs2)] ) + "\n" )
            friver.close()
            already_repped.add( criver )
            pass

        if count == 500 :
            #fout = open("test.txt",'w')
            #fout.write( json.dumps(results) )
            #fout.close()
            #break
            pass
    
    print "printing"
    #once all the boards are done, have results[board][pocket] = HS2sum, count
    for board in results :
        collapsed_board = collapseBoard( board )
        num_cards = len(collapsed_board.split('_')[0])
        if num_cards == 3 :   street_name = 'flops'
        elif num_cards == 4 : street_name = 'turns'
        else: assert False

        #print "collapsed name:", collapsed_board, " street name: " , street_name

        d_pocket_EHS2 = {}
        for pocket in results[board] :
            (HS2sum, count) = results[board][pocket]
            ehs2 = makeRound( HS2sum / count, precision )
            d_pocket_EHS2[pocket] = ehs2

        filename = "hsdists/%s/%s.hsdist" % (street_name, collapsed_board)
        fout = open( filename, 'w' )
        #print "len HS2s: ", len(HS2s)
        fout.write( json.dumps( d_pocket_EHS2 ) )
        #fout.write( ';'.join( [str(t) for t in sorted(HS2s)] )+"\n" )
        fout.close()

def main() :
    pass

if __name__ == '__main__' :
    a = time()
    for i in range(1000) :
        exists("hsdists/rivers/%d.hsdist" % i)
    b = time()
    print b-a

    a = time()
    for i in range(1000) :
        exists("%d.hsdist" % i)
    b = time()
    print b-a
    #computeEHS2Dists()
    assert False


    #board = ['2d','3s','8h','Qd']
    #board_prime = ['2d','3s','8h','Qd','Td']
    #board = ['3d','7s','9h','Kd']
    #board_prime = ['3d','7s','9h','Ad','Kd']
    #board = ['2s','3c','8d','Qd']
    #board_prime = ['2s','3c','8d','Qd','Td']

    #data = [[['Tc','4s'],['__','__']], board, 'HS']

    #d_pocket_EHS2 = rollout.mapReduceComputeEHS2( board )
    #d_pocket_EHS2_prime = rollout.mapReduceComputeEHS2( board_prime )
    #assert 'KdAd' in d_pocket_EHS2_prime

    #fout = open( "d_pocket_EHS2.json",'w')
    #fout.write( json.dumps( d_pocket_EHS2 ) )
    #fout.close()

    #fout = open( "d_pocket_EHS2_prime.json",'w')
    #fout.write( json.dumps( d_pocket_EHS2_prime ) )
    #fout.close()

    #d_pocket_EHS2 = json.loads( open('d_pocket_EHS2.json').read() )
    #d_pocket_EHS2_prime = json.loads( open('d_pocket_EHS2_prime.json').read() )

    #bucket_percentages = [.5,.3,.1,.05,.02,.02,.01]
    #d_pocket_bucket = computeBucket( d_pocket_EHS2, bucket_percentages )
    #d_pocket_bucket_prime = computeBucket( d_pocket_EHS2_prime, bucket_percentages )
    #assert 'KdAd' in d_pocket_bucket_prime

    #fout = open( "d_pocket_bucket.json",'w')
    #fout.write( json.dumps( d_pocket_bucket ) )
    #fout.close()

    #fout = open( "d_pocket_bucket_prime.json",'w')
    #fout.write( json.dumps( d_pocket_bucket_prime ) )
    #fout.close()

    #for pocket in d_pocket_bucket :
        #print pocket, d_pocket_EHS2[pocket], d_pocket_bucket[pocket]

    #for b in range(len(bucket_percentages)) :
        #acc = 0
        #for b_prime in range(len(bucket_percentages)) :
        ##b_prime = 3 
            #prob = bucketTransitionProb( b_prime, b, d_pocket_bucket, \
                                         #d_pocket_bucket_prime, \
                                         #bucket_percentages )
            #print "b: ", b, " b_prime: ", b_prime, " prob: ", prob
            #acc += prob
        #print "sum: ", acc

    #print collapseBoard( board )
    #print collapseBoard( board_prime )

####################################
    #print "HS2:", rollout.computeHS2( data )
    #count = 0
    #for decision_stack in iterateDecisionPoints ( num_players=2, \
                                                  #max_rounds=2, \
                                                  #button=0, \
                                                  #player_ix=0) :
        #print decision_stack
        #count += 1
    #print count


    #folder = "hsdists"
    #dmass = {'flops' : [.4,.1,.1] + [.05]*4 + [.02]*10, \
             #'turns' : [.4,.1,.1] + [.05]*4 + [.02]*10, \
             #'rivers': [.45,.15,.14,.05,.05,.05,.05,.02,.02,.02] }
    #computeBuckets( 'turns', dmass['turns'] )


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





#deprecated in favor of computeDistsHS
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

