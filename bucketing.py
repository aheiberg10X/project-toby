import pokereval
from deck import Deck, makeMachine, makeHuman, collapseBoard, getStreet, truncate, canonicalize
from itertools import combinations
import rollout
import matplotlib.pyplot as plt
from os import listdir
from os.path import exists
#import json
import simplejson as json
from yaml import load, dump
from time import time
import globles
from multiprocessing import Process, Queue, Pool
from random import sample
import db

num_buckets = 20

pe = pokereval.PokerEval()
d = Deck()

game = 'holdem'
side = 'hi'

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
def computeBucket( data  ) :
    d_reverse = {}

    #[d_pocket_EHS2, bucket_percentiles] = data
    #print sum(bucket_percentiles)
    ##sort EHS2
    #sorted_pockets = []
    EHS2s = []
    #for pocket in sorted(d_pocket_EHS2, key=lambda x : d_pocket_EHS2[x]) :
        #sorted_pockets.append( pocket )
        #ehs2 = round(d_pocket_EHS2[pocket],3)
        #EHS2s.append( ehs2 )
        #if ehs2 in d_reverse :
            #d_reverse[ehs2].append( pocket )
        #else :
            #d_reverse[ehs2] = [pocket]

    [ sorted_pockets, sorted_ehs2s, bucket_percentiles ] = data
    assert abs( sum(bucket_percentiles) - 1.0 ) < .000001
    for pocket, ehs2 in zip(sorted_pockets, sorted_ehs2s) :
        ehs2 = round( ehs2, 3 )
        EHS2s.append( ehs2 )
        if ehs2 in d_reverse :
            d_reverse[ehs2].append( pocket )
        else :
            d_reverse[ehs2] = [pocket]


    num_EHS2s = len(EHS2s)
    #how many EHS2s does each bucket get?
    bucket_masses = [int(round(bp*num_EHS2s)) for bp in bucket_percentiles]
    #print bucket_masses
    diff = sum(bucket_masses) - num_EHS2s
    bucket_masses[-1] -= diff
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
    num_lower_ranked = 0
    #count up how many of a particular EV value we see
    count = 0 
    #append a -1 so the last run of values gets processed
    EHS2s.append(-1)
    for ehs2,pocket in zip(EHS2s,sorted_pockets) :
        if not ehs2 == last_seen_ehs2 :
            unbucketed_count = count
            remaining_space = bucket_total_mass - bucket_mass
            percentile = num_lower_ranked / float(sum(bucket_masses))
            #doprint = pocket[0] == 'Q' and pocket[2] == 'Q' 
            doprint = False
            if doprint :
                print "herer"
                print 'bucketix: ', bucket_ix
                print 'remaining space: ', remaining_space
                print 'unbucketd: ', unbucketed_count
            for pocket in d_reverse[last_seen_ehs2] :
                if doprint : print pocket
                membership_probs[pocket] = {}
                membership_probs[pocket]['percentile'] = percentile

            #if doprint : assert False

            #if we can't fit the unbucketed EHS2s in the current bucket
            #fill it up and increment to the next bucket
            #rinse repeat
            while remaining_space < unbucketed_count :
                #fill up current bucket rest of the way
                for pocket in d_reverse[last_seen_ehs2] :
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
            for pocket in d_reverse[last_seen_ehs2] :
                membership_probs[pocket][bucket_ix] = \
                        float(unbucketed_count) / count

            #print last_seen_ehs2, membership_probs[last_seen_ehs2]
            last_seen_ehs2 = ehs2
            num_lower_ranked += count
            count = 1
        else :
            count += 1
        
    #dflop_memprobs[collapsed_name] = membership_probs
    #TODO all mem getting used, must print incrementally
    #hope in correct JSON format
    return membership_probs

# P( b' | b, board, board' )
def bucketTransitionProb( b_prime, b, board, board_prime, bucket_percentiles ) :
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
    
    ##C
    ##already checked legality of pocket against flop in 'if' above
    ##so just the probability of a given pocket
    #C = 1/float(len(board))

    ##D - board doesn't matter, depends on construction of percentiles
    #D = bucket_percentiles[b]
    
    #C/D is really trying to get 1/(number of pockets in bucket b)

    #print "A*B sum:", acc
    #print "B sum: ", acc2
    #print "C/D weight:", C/D

    return acc / float(acc2)

# P( b' | b, board, board' )
def getTransitionProbs( board, n_buckets, \
                        board_prime, n_buckets_prime ) :
    #P( b' | b,board,board' ) = sum_pockets P( b' | p,board') * P(p | board,b)
    #                                             [A]
    #P( p | board,b ) = P( b|p,board) * P(p|F) / P(b|board)
    #                      [B]            [C]      [D]

    #print board
    #print "\n\n"
    #print board_prime

    #will store (A*B,B) accumulators for every bucket x bucket_prime pair
    acc = {}
    for b in range(n_buckets) :
        acc[b] = {}
        for bprime in range(n_buckets_prime) :
            acc[b][bprime] = [0,0]

    for pocket in combinations(range(52),globles.POCKET_SIZE) :
        for b in range(n_buckets) :
            for bprime in range(n_buckets_prime) :
                pocket_str = canonicalize(list(pocket))
                A = 0
                if pocket_str in board_prime and \
                   bprime in board_prime[pocket_str] :
                    A = board_prime[pocket_str][bprime]

                B = 0
                if pocket_str in board and \
                   b in board[pocket_str] :
                    B = board[pocket_str][b]
                
                acc[b][bprime][0] += A * B 
                acc[b][bprime][1] += B
    
    for b in range(n_buckets) :
        for bprime in range(n_buckets_prime) :
            if acc[b][bprime][1] == 0 :
                assert acc[b][bprime][0] == 0
                acc[b][bprime] = 0
                print b, bprime
                assert "oh so very unlikely" == "asdf"
            else :
                #TODO: if 0 prob, remove the bprime key from the dict, sparse
                v = round( acc[b][bprime][0] / float(acc[b][bprime][1]), 4 )
                if v > 0.0 :
                    acc[b][bprime] = v
                else :
                    del acc[b][bprime]

    return acc

flop_bucket_map = {}
def bucketPocket( pocket, board ) :
    global flop_bucket_map

    collapsed = collapseBoard( board )
    EV = makeRound( rollout.computeEV( pocket, board ) )
    street = getStreet( board )
    if street == 'flop' :
        if not flop_bucket_map :
            fflop = open("evdists/flop/membership_probs.txt")
            #flop_bucket_map = json.loads( fflop.read() )
            flop_bucket_map = load( fflop.read() )
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

def computeEHS2DistsLongways() :
    pool = Pool( processes = 8 )
    count = 0
    timea = time()

    for board_size in range(5,6) :
        start_time = time()

        already_repped = {}

        if board_size == 3 :  
            street_name = 'flops'
            print_every = 10
        elif board_size == 4 : 
            street_name = 'turns'
            print_every = 100
        else : 
            street_name = 'rivers'
            print_every = 1000
        count = 0

        for board in combinations( range(52), board_size ) :
            cboard = collapseBoard( board )
            if cboard not in already_repped :
                d_pocket_EHS2 = rollout.mapReduceComputeEHS2( pool,list(board) )
                filename = "hsdists/%s/%s.hsdist" % (street_name, cboard)
                fout = open( filename, 'w' )
                fout.write( json.dumps( d_pocket_EHS2 ) )
                fout.close()
                already_repped[cboard] = makeHuman(board)
            else :
                pass

            count += 1
            if count % print_every == 0 :
                print "board_size: ", board_size, " count: ", count
                print "time: ", time() - timea 
                timea = time()

        fout = open("hsdists/%s/representatives.txt" % street_name, 'w' )
        fout.write( json.dumps( already_repped ) )
        fout.close()

        print "time for board_size: ", board_size, " was: ", time() - start_time

    pool.close()

def bucketAllEHS2Dists_DB( bucket_table, bucket_percentiles ) :
    street_name = 'flop'
    conn = db.Conn("localhost")
    conn2 = db.Conn("localhost", dry_run=False)
    q = """select cboard,pocket,ehs2
           from EHS2_%s
           order by cboard,ehs2
           """ % (street_name.upper())

    fout = open("%s_bulk_load.csv" % street_name,'w')
    
    def process() :
        buffer = []
        data = [pockets, ehs2s, bucket_percentiles[street_name]]
        d_pocket_bucket = computeBucket( data )
        for pocket in d_pocket_bucket :
            perc = d_pocket_bucket[pocket]['percentile']
            values = [cboard,pocket,perc]
            #print values
            db_buckets = max([len(bucket_percentiles[sn]) for sn in bucket_percentiles])
            for b in range(db_buckets) :
                if b in d_pocket_bucket[pocket] :
                    values.append( d_pocket_bucket[pocket][b] )
                else :
                    values.append( 0 )
            ##print values
            #conn2.insert( bucket_table, values, skip_dupes = True )
            buffer.append( ",".join( [str(v) for v in values] ) )
        fout.write( '\n'.join( buffer ) )

    last_cboard = ""
    pockets = []
    ehs2s = []
    for i,row in enumerate( conn.query( q ) ) :
        [cboard,pocket,ehs2] = row
        if not last_cboard == cboard :
            if last_cboard == "" :
                pass
            else :
                process()
            last_cboard = cboard
            pockets = [pocket]
            ehs2s = [ehs2]
        else : 
            pockets.append( pocket )
            ehs2s.append( ehs2 )

        if i % 10000 == 0 : print i

    process()

    fout.close()

def bucketAllEHS2Dists( bucket_percentiles ) :
    pool = Pool( processes = 4 )
    atime = time()
    for street_name in ['flop','turn','river'] :
        dirname = "hsdists/%ss/" % street_name

        chunk_size = 20 

        names = []
        data = []
        for filename in listdir( dirname ) :
            if not filename.endswith( 'hsdist' ) :
                continue
            [name,ext] = filename.rsplit( '.', 1 )
            path = "%s/%s" % (dirname,filename)
            print path
            fin = open( path )
            d_pocket_EHS2 = load( fin.read() )
            fin.close()
            data.append( [d_pocket_EHS2,bucket_percentiles[street_name]] )
            names.append( name )
            print len(data)
            if len(data) == chunk_size :
                print "mapping!"
                results = pool.map( computeBucket, data )


            #d_pocket_bucket = computeBucket( d_pocket_EHS2, \
                                             #bucket_percentiles[street_name] )
                for (name,d_pocket_bucket) in zip(names,results) :
                    fout = open( "%s/%s.bkts" % (dirname, name), 'w' )
                    fout.write( dump( d_pocket_bucket ) )
                    fout.close()
                names = []
                data = []

        #clean up
        print "last map"
        results = pool.map( computeBucket, data )
        #d_pocket_bucket = computeBucket( d_pocket_EHS2, \
                                         #bucket_percentiles[street_name] )
        for (name,d_pocket_bucket) in zip(names,results) :
            fout = open( "%s/%s.bkts" % (dirname, name), 'w' )
            fout.write( dump( d_pocket_bucket ) )
            fout.close()

        break

    print "took: ", time()-atime
    pool.close()

def sampleTransitionProbs( street, n_samples, bucket_percentiles ) :
    pool = Pool( processes = 4 )
    dirname = "hsdists/%ss" % street

    fout1 = open( "%s/transition_names.txt" % dirname, 'w' )
    fout2 = open( "%s/transition_probs.txt" % dirname, 'w' )
    write_buffer_1 = []
    write_buffer_2 = [] # [[cboard, cboard', tran probs],[],...]

    fin = open( "%s/collapsed_representatives.txt" % dirname )
    representatives = load( fin.read() )
    fin.close()

    bkt_filenames = ["%s/%s" % (dirname, file) \
                      for file in listdir( dirname ) \
                      if file.endswith('bkts')]

    dek = Deck()
    for bkt_filename in sample( bkt_filenames, n_samples ) :
        timea = time()
        fin = open( bkt_filename) 
        d_pocket_buckets = load( fin.read() )
        fin.close()

        [rest,fileext] = bkt_filename.rsplit('/',1)
        [file,ext] = fileext.rsplit('.',1)

        actual_board = [str(t) for t in representatives[file]]
        dek.remove( actual_board )

        #enumerate the possible collapsed flops
        d_cboard_aboard = {}
        for next_card in dek.cards :
            aboard = actual_board + makeHuman([next_card])
            cboard = collapseBoard( aboard )
            if cboard not in d_cboard_aboard :
                d_cboard_aboard[cboard] = aboard


        for cboard in d_cboard_aboard :
            print bkt_filename, aboard
            aboard = d_cboard_aboard[cboard]
            d_pocket_EHS2 = rollout.mapReduceComputeEHS2( pool, aboard )
            d_pocket_buckets_prime = computeBucket( d_pocket_EHS2, bucket_percentiles[street] )

            n_buckets = len(bucket_percentiles[street])
            if street == "flop" :
                n_buckets_prime = len(bucket_percentiles['turn'])
            elif street == 'turn' :
                n_buckets_prime = len(bucket_percentiles['river'])
            else : assert False

            #print actual_board, aboard
            tprobs = getTransitionProbs( d_pocket_buckets, \
                                      n_buckets, \
                                      d_pocket_buckets_prime, \
                                      n_buckets_prime )
            prob_vector = []
            for b in range(n_buckets) :
                for bprime in range(n_buckets_prime) :
                    if b in tprobs and bprime in tprobs[b] :
                        prob_vector.append( tprobs[b][bprime] )
                    else :
                        prob_vector.append( 0.0 )

            #write_buffer_1.append( "%s\t%s" % (file,cboard) )
            fout1.write( "%s\t%s\n" % (file,cboard) )
            fout2.write( dump( prob_vector, width=6000 )[1:-2] + "\n" )
            #write_buffer_2.append ( prob_vector )


        #print bkt_filename
        #print len(d_cboard_aboard)
        dek.shuffle()
        #fout1.write( dump( write_buffer_1 ) )
        #fout2.write( dump( write_buffer_2, width=5000 )[2:] )
        #write_buffer_1 = []
        #write_buffer_2 = []
        timeb = time()
        print "board: ", bkt_filename, " took: ", timeb-timea

    pool.close()

def insertRepresentatives() :
    conn = db.Conn("localhost")
    for street_name in ['flop','turn','river'] :
        dirname = "hsdists/%ss/" % street_name
        fin = open("%s/representatives.txt" % dirname)
        reps = load( fin.read() )
        fin.close()
        for cboard in reps :
            aboard = ''.join(reps[cboard])
            conn.insert('REPRESENTATIVES',[cboard,aboard]  )



if __name__ == '__main__' :
    #sampleTransitionProbs( "flop", 5, globles.BUCKET_PERCENTILES )
    ##bucket_percentiles = [.5,.3,.1,.05,.02,.02,.01]
    bucketAllEHS2Dists_DB( 'BUCKET_HANDCRAFTED', globles.BUCKET_PERCENTILES_SMALL ) 
    #insertRepresentatives()
    #computeEHS2DistsLongways()
    assert False

    #board = ['2d','3s','8h','Qd']
    #board_prime = ['2d','3s','8h','Qd','Td']
    board = ['3d','7s','9h','Kd']
    board_prime = ['3d','7s','9h','Ad','Kd']
    #board = ['2h','3c','8d','Qd']
    #board_prime = ['2h','3c','8d','Qd','5h']

    pool = Pool( processes = 2)

    n_buckets = len(globles.BUCKET_PERCENTILES['turn'])
    n_buckets_prime = len(globles.BUCKET_PERCENTILES['river'])
    probs = getTransitionProbs( d_pocket_bucket, \
                                n_buckets, \
                                d_pocket_bucket_prime, \
                                n_buckets_prime )

    for b in range(n_buckets ) :
        for bprime in range(n_buckets_prime ) :
            print "%d - %d : %f" % (b,bprime,probs[b][bprime])
        print "\n\n"

    pool.close()

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


#deprecated for being a pain in the ass
#and i wasted so much time on it 
def computeEHS2Dists() :
    already_repped = set([])
    results = {}   
    count = 0
    a = time()
    for board in combinations( range(52), 5 ) :
        count += 1
        if count % 100 == 0 : 
            print count
            print time() - a
            a = time()
        
        #pit every possible hand against 'mystery' known_pocket
        #and compute the HS2 from rollout
        known_pockets = ['__','__']
        d_pocket_HS2 = rollout.mapReduceComputeEHS2( list(board) )


        flop = ''.join( makeHuman(board[0:3]) )
        cflop = collapseBoard( flop )
        turn = ''.join( makeHuman(board[0:4]) ) 
        cturn = collapseBoard( turn )
        river = ''.join( makeHuman(board) )
        if river == '2s2c3s4s5s' :
            print d_pocket_HS2
            assert False
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
        if not exists(name) :
            friver = open( name, 'w' )
            friver.write( json.dumps( river_hs2 ) )
            #friver.write( ";".join( [str(t) for t in sorted(river_hs2)] ) + "\n" )
            friver.close()
            pass

        if count == 500 :
            #fout = open("test.txt",'w')
            #fout.write( json.dumps(results) )
            #fout.close()
            break
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

