import pokereval
from deck import Deck, makeMachine, makeHuman, collapseBoard, getStreet, truncate, canonicalize, listify, symmetricComplement, completeStemToMakeCboard
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

#input is DB connection, collapseBoard( board[:-1] ), collapseBoard( board )
#output is P(k',k | cboard_prime, cboard )
def computeBucketTransitions( conn, cboard, cboard_prime ) :
    print cboard, cboard_prime
    #get the aboards, for which the EHS2 and buckets have been computed
    q = "select aboard from REPRESENTATIVES where cboard = '%s'"
    aboard = conn.queryScalar( q % cboard, listify )
    aboard_prime = conn.queryScalar( q % cboard_prime, listify )


    #street names and bucket sizes
    if len(aboard_prime) == 5 :
        street_prime = 'river'
        street = 'turn'
    elif len(aboard_prime) == 4 :
        street_prime = 'turn'
        street = 'flop'
    else : assert False
    nbuckets = len(globles.BUCKET_PERCENTILES[street])
    nbuckets_prime = len(globles.BUCKET_PERCENTILES[street_prime])

    #setup the output P[bucket] = {bucket_prime : prob, ...}
    P = {}
    for bucket in range( nbuckets ) :
        P[bucket] = {}

    #the memberships against cboard_prime
    pocket_prime_membs = {}
    legal_pockets = []
    q = """select pocket, memberships
           from %s%s
           where cboard = '%s'""" % \
           (globles.BUCKET_TABLE_PREFIX, \
            street_prime.upper(), \
            cboard_prime)
    for p_prime,membs in conn.query(q) :
        legal_pockets.append(p_prime)
        pocket_prime_membs[p_prime] = [float(m) for m in membs.split(':')]
    #print "p_prime memberships built"

    #the memberships against cboard
    pocket_membs = {}
    q = """select pocket, memberships
           from %s%s
           where cboard = '%s'""" % \
           (globles.BUCKET_TABLE_PREFIX, \
            street.upper(), \
            cboard)
    for p,membs in conn.query(q) :
        pocket_membs[p] = [float(m) for m in membs.split(':')]
    #print "p memberships built"

    #determine the pocket map between prime and aboard
    pocket_map = {}

    no_map_necessary = aboard == aboard_prime[:-1]
    if no_map_necessary :
        for pocket in legal_pockets :
            pocket_map[pocket] = pocket
    else :
        #print aboard, aboard_prime
        #print aboard_prime, cboard_prime

        #figure out which card, when added to aboard, gives cboard_prime
        #call this aboard_prime_wish
        aboard_prime_wish = completeStemToMakeCboard( aboard, cboard_prime )

        #new set of legal_pockets
        legal_pockets = []
        dek = Deck()
        dek.shuffle()
        dek.remove(aboard_prime_wish)
        for p in combinations( dek.cards, 2) :
            legal_pockets.append(canonicalize(list(p)))

        #print "wish", aboard_prime_wish, collapseBoard(aboard_prime_wish)
        #find mapping between aboard_prime and wish
        for pocket in legal_pockets :
            print pocket
            symm_pocket = symmetricComplement( aboard_prime_wish, \
                                               pocket, \
                                               aboard_prime )
            pocket_map[pocket] = symm_pocket

    #main computation
    C = 1 / float(len(legal_pockets))
    for k in range(nbuckets) :
        for k_prime in range(nbuckets_prime) :
            s = 0
            for p in legal_pockets :
                p_prime = pocket_map[p]
                A = pocket_prime_membs[p_prime][k_prime]
                B = pocket_membs[p][k]
                s += A*B*C
            P[k][k_prime] = s

    dist = []
    marginals = []
    total_sum = 0
    for k in range(nbuckets) :
        conditionals = []
        for k_prime in range(nbuckets_prime) :
            conditionals.append( round(P[k][k_prime],6) )
        marg = sum(conditionals)
        total_sum += marg
        if marg > 0 :
            cond_sum = sum([c / marg for c in conditionals])
            assert .99 < cond_sum < 1.01
        dist.append( ",".join( [str(c) for c in conditionals] ) )

    assert .99 < total_sum < 1.01

    dist = ';'.join(dist)
    conn.insert( 'TRANSITIONS', ["%s|%s" % (cboard, cboard_prime),dist], \
                 skip_dupes=True)
    print "inserted"



# input  : [sorted_pockets, sorted_ehs2s, bucket_percentiles ] = data
# output : {pocket:{bucket:%membership}}
def computeBucket( data  ) :
    [ sorted_pockets, sorted_ehs2s, bucket_percentiles ] = data

    #print sum(bucket_percentiles)
    EHS2s = []
    assert abs( sum(bucket_percentiles) - 1.0 ) < .000001

    #holds {EHS2 : [pockets sharing this rounded EHS2]}
    d_reverse = {}
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
    #correct any discrepancy from rounding
    bucket_masses[-1] -= diff
    #print "sum bucket_masses", sum(bucket_masses), "num_EHS2s", num_EHS2s

    #Start of the algorithm

    #Info about the bucket we are currently filling
    bucket_ix = 0
    bucket_mass = 0
    bucket_total_mass = bucket_masses[bucket_ix]

    #what we will be returning
    #pocket : {bucket_ix : percentage}
    membership_probs = {}

    #EHS2s come in sorted order from the file, so we read until we see
    #a new value
    last_seen_ehs2 = EHS2s[0]

    #will also be computing a percentile for each pocket
    #i.e what percentage of hands had a lower EHS2?
    num_lower_ranked = 0

    #count up how many of a particular EHS2 value we see
    count = 0

    #append a -1 so the last run of values gets processed
    EHS2s.append(-1)
    sorted_pockets.append(-1)

    for ehs2,pocket in zip(EHS2s,sorted_pockets) :
        if not ehs2 == last_seen_ehs2 :
            unbucketed_count = count
            remaining_space = bucket_total_mass - bucket_mass
            percentile = num_lower_ranked / float(sum(bucket_masses))

            #setup
            for pocket in d_reverse[last_seen_ehs2] :
                membership_probs[pocket] = {}
                membership_probs[pocket]['percentile'] = percentile

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

    return membership_probs

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

#this was for merging a fix in with existing values
#for cboards ending in _p_22f
#Still need?
def computeEHS2DistsLongways_special() :
    pool = Pool( processes = 8 )
    count = 0
    timea = time()

    for board_size in range(4,5) :
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
            if cboard.endswith( "_p_22f" ) and cboard not in already_repped :
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

        fout = open("hsdists/%s/special_representatives.txt" % street_name, 'w' )
        fout.write( json.dumps( already_repped ) )
        fout.close()

        print "time for board_size: ", board_size, " was: ", time() - start_time

    pool.close()

def bucketAllEHS2Dists_DB( bucket_table, bucket_percentiles ) :
    street_name = 'turn'
    conn = db.Conn("localhost")
    conn2 = db.Conn("localhost", dry_run=False)
    assert "fix"=="query"
    q = """select cboard,pocket,ehs2
           from EHS2_%s
           where cboard like '____\_p\_22f'
           order by cboard,ehs2
           """ % (street_name.upper())

    fout = open("/var/lib/mysql/toby/%s_bulk_load_22f.csv" % street_name,'w')
    #then run "mysql> load data infile '<file>' into table toby.<BUCKET>;"
    
    def process() :
        buffer = []
        data = [pockets, ehs2s, bucket_percentiles[street_name]]
        d_pocket_bucket = computeBucket( data )
        #print d_pocket_bucket
        for pocket in d_pocket_bucket :
            perc = d_pocket_bucket[pocket]['percentile']
            values = [last_cboard,pocket,perc]
            #print values
            #db_buckets = max([len(bucket_percentiles[sn]) for sn in bucket_percentiles])
            nbuckets = len(bucket_percentiles[street_name])
            bucket_string = []
            for b in range(nbuckets) : #db_buckets) :
                if b in d_pocket_bucket[pocket] :
                    #values.append
                    bucket_string.append( d_pocket_bucket[pocket][b] )
                else :
                    bucket_string.append( 0 )
            ##print values
            #conn2.insert( bucket_table, values, skip_dupes = True )
            bucket_string = ':'.join([str(t) for t in bucket_string])
            values.append(bucket_string)
            buffer.append( ",".join( [str(v) for v in values] ) )
        fout.write( '\n'.join( buffer ) + '\n' )

    last_cboard = ""
    pockets = []
    ehs2s = []
    for i,row in enumerate( conn.iterateQuery( q ) ) :
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

#TODO: remake this to use DB and the symmetriComplememnt tactic
def sampleTransitionProbs_DB( n_samples, bucket_percentiles ) :
    dek = Deck()

    conn1 = db.Conn("localhost")
    conn2 = db.Conn("localhost")
    q = """select cboard,aboard from REPRESENTATIVES"""
    for cboard, aboard in conn1.query(q) :
        dek.shuffle()
        aboard = listify( aboard )
        dek.remove( aboard )
        for next_card in dek.cards :
            next_board = aboard + [next_card]

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
    for street_name in ['turn'] : #['flop','turn','river'] :
        dirname = "hsdists/%ss/" % street_name
        fin = open("%s/special_representatives.txt" % dirname)
        reps = load( fin.read() )
        fin.close()
        for cboard in reps :
            aboard = canonicalize( reps[cboard] )
            conn.insert('REPRESENTATIVES',[cboard,aboard]  )


def testSymmetric() :
    conn  = db.Conn("localhost")
    tests = []
    #cboard is 455_p_r
    #representative is 4h5d5c
    board = ['4d','5h','5c']
    pocket = ['5d','7s']
    tests.append( (board,pocket,'FLOP') )

    #cboard is 9TQ_h_2fxox
    #rep is 9hQhTd
    board = ['9s','Qs','Tc']
    pocket = ['7h','Th']
    tests.append( (board,pocket,'FLOP') )

    #cboard is 34QK_h_3foxxx
    #rep is 3h3dQdKd
    board = ['3s','3h','Qh','Kh']
    pocket = ['7h','Tc']
    tests.append( (board, pocket, 'TURN') )

    #cboard is
    #rep is   2h   4h   7d   9d   Ad
    board = ['2c','4h','7d','9h','Ah']
    pocket = ['3c','Kh']
    tests.append( (board,pocket,'RIVER') ) 

    #cboard is 2335K_p_4f
    #2h3h5hKh3d
    board = ['2c','3d','3c','5c','Kc']
    pocket = ['5s','Qc']
    tests.append( (board,pocket,'RIVER') )

    board = ['5c','5d','7c','7d','Qs']
    pocket = ['6c','Qh']
    tests.append( (board,pocket,'RIVER') )

    for (board,pocket,street_name) in tests :

        cboard = collapseBoard( board )
        #print "cboard", cboard
        q = """select aboard from REPRESENTATIVES where cboard = '%s'""" % \
                (cboard)
        [[aboard]] = conn.query(q)
        #print "board", board
        #print "aboard", listify(aboard)
        #print "pocket", pocket

        pocketp = listify( symmetricComplement( board, \
                                                pocket,\
                                                listify(aboard) ) )

        #print "pocketp: " , pocketp
        ehs2 = rollout.computeSingleEHS2( pocket, board )
        print ehs2
        q = """select ehs2 from EHS2_%s
               where cboard = '%s' and pocket = '%s'""" % (street_name, \
                                                           cboard, \
                                                           canonicalize(pocketp) )
        [[ehs2p]] = conn.query(q)
        ehs2p = float(ehs2p)
        print ehs2p
        assert round(ehs2,4) == round(ehs2p,4)
        #ehs2p = 

def iterateTransitions() :
    transitions = {}
    conn = db.Conn("localhost")

    for i, board_prime in enumerate( combinations( range(52), 5 ) ):
        print i
        board = board_prime[:-1]
        cboard = collapseBoard(board)
        cboard_prime = collapseBoard(board_prime)
        comb = "%s_%s" % (cboard, cboard_prime)
        if comb not in transitions :
            transitions[comb] = True
            computeBucketTransitions( conn, cboard, cboard_prime )

    print len(transitions)
        

if __name__ == '__main__' :

    iterateTransitions()
    #testSymmetric()
    #conn = db.Conn("localhost")
    #getTransitionProbs_DB( conn, \
                           #['2h','2c','2d','2s'], 'turn', \
                           #['2h','2c','2d','2s','As'], 'river' )
                            ##['2h','4h','7d'], 'flop', \
                            ##['2h','4h','7d','Td'], 'turn' )

    #sampleTransitionProbs( "flop", 5, globles.BUCKET_PERCENTILES )
    ##bucket_percentiles = [.5,.3,.1,.05,.02,.02,.01]
    #bucketAllEHS2Dists_DB( globles.BUCKET_TABLE_PREFIX, \
                           #globles.BUCKET_PERCENTILES )
    #insertRepresentatives()
    #computeEHS2DistsLongways_special()
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


#DEPRECATED BECAUSE IT DIDN"T WORK
## P( b' | b, board, board' )
##for all b,b' pairs 
##{b : {b' : prob, ...}, ...}
#def getTransitionProbs( board, n_buckets, \
                        #board_prime, n_buckets_prime ) :
    ##P( b' | b,board,board' ) = sum_pockets P( b' | p,board') * P(p | board,b)
    ##                                             [A]
    ##P( p | board,b ) = P( b|p,board) * P(p|F) / P(b|board)
    ##                      [B]            [C]      [D]
#
    ##print board
    ##print "\n\n"
    ##print board_prime
#
    ##store (A*B,B) accumulators for every bucket x bucket_prime pair
    #acc = {}
    #for b in range(n_buckets) :
        #acc[b] = {}
        #for bprime in range(n_buckets_prime) :
            #acc[b][bprime] = [0,0]
#
    #for pocket in combinations(range(52),globles.POCKET_SIZE) :
        #for b in range(n_buckets) :
            #for bprime in range(n_buckets_prime) :
                #pocket_str = canonicalize(list(pocket))
                #A = 0
                #try :
                    #if pocket_str in board_prime and \
                       #bprime in board_prime[pocket_str] :
                        #A = board_prime[pocket_str][bprime]
                #except Exception as e :
                    #print e
                    #print pocket_str
                    #print board_prime
                    #assert False
#
                #B = 0
                #if pocket_str in board and \
                   #b in board[pocket_str] :
                    #B = board[pocket_str][b]
#
                #acc[b][bprime][0] += A * B 
                #acc[b][bprime][1] += B
#
    #for b in range(n_buckets) :
        #for bprime in range(n_buckets_prime) :
            #if acc[b][bprime][1] == 0 :
                #assert acc[b][bprime][0] == 0
                #acc[b][bprime] = 0
                #print b, bprime
                #assert "oh so very unlikely" == "asdf"
            #else :
                ##f 0 prob, remove the bprime key from the dict, sparse
                #v = round( acc[b][bprime][0] / float(acc[b][bprime][1]), 4 )
                #if v > 0.0 :
                    #acc[b][bprime] = v
                #else :
                    #del acc[b][bprime]
#
    #return acc

## P( b' | b, board, board' )
##for all b,b' pairs 
##{b : {b' : prob, ...}, ...}
#def getTransitionProbs_DB( conn, \
                           #board, street_name, \
                           #board_prime, street_name_prime ) :
    ##board = makeMachine(board)
    ##board_prime = makeMachine(board_prime)
#
    #n_buckets = len(globles.BUCKET_PERCENTILES[street_name])
    #n_buckets_prime = len(globles.BUCKET_PERCENTILES[street_name_prime])
#
    #cboard = collapseBoard( board )
    #cboard_prime = collapseBoard( board_prime )
#
    #q = """select aboard
           #from REPRESENTATIVES
           #where cboard = '%s'""" % (cboard_prime)
    #[[aboard_prime]] = conn.query(q)
    #aboard_prime = listify(aboard_prime)
#
    #q = """select pocket, memberships
           #from %s%s
           #where cboard = '%s'""" % (globles.BUCKET_TABLE_PREFIX, \
                                     #street_name.upper(),\
                                     #cboard)
    #d_pocket_bucket = {}
    ##for pocket, memberships in conn.query(q) :
        #d_pocket_bucket[pocket] = {}
        #for i,memb in enumerate(memberships.split(":")) :
            ##print memb
            ##d_pocket_bucket[pocket][i] = float(memb)
   # 
    #q = """select pocket, memberships
           #from %s%s
           #where cboard = '%s'""" % (globles.BUCKET_TABLE_PREFIX, \
                                     #street_name_prime.upper(),\
                                     #cboard_prime)
    #d_pocket_bucket_prime = {}
    #for pocket, memberships in conn.query(q) :
        #d_pocket_bucket_prime[pocket] = {}
        #for i,memb in enumerate(memberships.split(":")) :
            #d_pocket_bucket_prime[pocket][i] = float(memb)
#
    ##d_pocket_bucket = {'2h2c':{0:1}, \
                       #'2h2s':{1:1}, \
                       #'2h2d':{0:1}, }
#
           ## 
#
    #print board, cboard
    #print board_prime, cboard_prime
    #print aboard_prime
    ##store (A*B,B) accumulators for every bucket x bucket_prime pair
    #acc = {}
    #for b in range(n_buckets) :
        #acc[b] = {'count':0}
        #for bprime in range(n_buckets_prime) :
            #acc[b][bprime] = [0,0]
#
    #for pocket in combinations(range(52),globles.POCKET_SIZE) :
        #pocket = list(pocket)
        ##print makeHuman(pocket)
#
        #print pocket
        #pocket_prime_str = symmetricComplement( board_prime, \
                                                #pocket, \
                                                #aboard_prime )
        #print "pps", pocket_prime_str
        #pocket_str = canonicalize(pocket)
#
        ##print pocket_prime_str
        #for b in range(n_buckets) :
            #B = 0
            #if pocket_str in d_pocket_bucket and \
               #b in d_pocket_bucket[pocket_str] :
                #B = d_pocket_bucket[pocket_str][b]
#
            #for bprime in range(n_buckets_prime) :
                #A = 0
                #if pocket_prime_str in d_pocket_bucket_prime and \
                   #bprime in d_pocket_bucket_prime[pocket_prime_str] :
                    #A = d_pocket_bucket_prime[pocket_prime_str][bprime]
#
                ##B = 0
                ##if pocket_str in d_pocket_bucket and \
                   ##b in d_pocket_bucket[pocket_str] :
                    ##B = d_pocket_bucket[pocket_str][b]
#
                #acc[b][bprime][0] += A * B 
                ##acc[b][bprime][1] += B
            #acc[b]['count'] += B
#
    #for b in range(n_buckets) :
        #for bprime in range(n_buckets_prime) :
            ##if acc[b][bprime][1] == 0 :
                ##assert acc[b][bprime][0] == 0
                ##acc[b][bprime] = 0
                ##print b, bprime
                ##assert "oh so very unlikely" == "asdf"
            ##else :
            ##f 0 prob, remove the bprime key from the dict, sparse
            ##v = round( acc[b][bprime][0] / float(acc[b][bprime][1]), 4 )
            #v = round( acc[b][bprime][0] / float(acc[b]["count"]), 4 )
            #if v > 0.0 :
                #acc[b][bprime] = v
            #else :
                #del acc[b][bprime]
#
    #for b in range(n_buckets) :
        #print "b:", b
        #s = 0
        #for bp in range(n_buckets_prime) :
            #if b in acc and bp in acc[b] :
                #prob = acc[b][bp]
            #else :
                #prob = 0
            #s += prob 
            #print "    bp: ", bp, prob
        #print "sum: ", s
    #return acc




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

