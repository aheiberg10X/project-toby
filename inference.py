from itertools import product as cartProduct
import operator
from math import factorial, log

import selective_eval as se
import globles
import db
import deck
import BTclustering as clust
import iterate_decision_points as idp

conn = db.Conn('localhost')

def nCr(n, r):
    r = min(r, n-r)
    if r == 0: return 1
    numer = reduce(operator.mul, xrange(n, n-r, -1))
    denom = reduce(operator.mul, xrange(1, r+1))
    return numer//denom


def loadPA() :#load lookup information...
    PA = []
    visible_nodes = [3,6,9,12]
    for node in visible_nodes :
        PA.append( se.computeTypeFrequencies( [node-1] ) )
    return PA

#action_int is 1-indexed
def lookupPA( PA, street, action_int ) :
    action_str = str(action_int-1)
    if action_str in PA[street] :
        return PA[street][action_str]
    else :
        return 0

def loadPAK() :
    #not layed out in file in a way conduscive to fast or intuitive lookup
    #load the data as-is into interim, re-arrange and put in PAK
    interim = {}
    PAK = {}

    agg_act_nodes = [3,6,9,12]
    streets = [0,1,2,3]

    #read in data
    for (node,street) in zip(agg_act_nodes,streets) :
        interim[street] = []

        print "node: ", node

        fin = open( "AK/CPT%d.csv" % node )
        blob = fin.read().strip()
        lines = blob.split('\n')
        #print "nlines: ", len(lines)
        for line in lines :
            splt = [float(prob) for prob in line.split(',')]
            #print "nsplt: ", len(splt)
            interim[street].append( splt )
        fin.close()

    #reorg for faster lookups
    for (node,street) in zip(agg_act_nodes,streets) :
        PAK[street] = []

        nbuckets = globles.NBUCKETS[street]
        buckets = range(nbuckets)
        nacts = len(interim[street][0]) / nbuckets

        #print "nbuckets,  nacts", nbuckets, nacts

        for k1 in buckets :
            k1_probs = []
            for k2 in buckets :
                k2_probs = []
                for act in range(nacts) :
                    offset = act*nbuckets
                    prob = interim[street][k1][offset+k2]
                    k2_probs.append( prob )
                    #print "given k1,k2: ", k2_probs

                #print "1 or 0, right?: ", sum(k2_probs)
                #if( sum(k2_probs) < .99 ) :
                    #print k1,k2
                    #print k2_probs
                    #assert False
                k1_probs.append( k2_probs )

            PAK[street].append(k1_probs)

    #also load the action_str -> int mapper, AAS2I
    #AAS2I = idp.buildAAS2I()

    return PAK

#action_int is 1-indexed (the MATLAB way) 
#TODO: this should be -1, not -2
#this happened because originaly in iterate_decision_points, the int_repr's
#were not starting at 1, but instead 0.  The 1st (ix=0) action was fddd,
#which was never seen in any games so didn't cause MATLAB 0 index problems
#BUT, it made everything offset by one extra
#will have to reparse now that fix has been made to IDP
def lookupPAK( PAK, street, k1, k2, action_int ) :
    return PAK[street][k1][k2][action_int-2]

#P(k)
def lookupPk( street, bucket ) :
    sname = globles.int2streetname( street )
    return globles.BUCKET_PERCENTILES[sname][bucket]

#P(b)
def lookupPb( street ) :
    if street == 0 : return 1
    elif street == 1 :
        return 5.78168362627e-05
    elif street == 2 :
        return 5.13927433446e-06
    elif street == 3 :
        return 5.84008447098e-07

    #elif 1 <= street <= 3 :
        #l = street + 2
        #n_boards = nCr( (52-(2*globles.POCKET_SIZE)), l )
        #return 1 / float( n_boards )

    else : assert False

#return {cboards : cluster_id}
#   and {cluster_id : joint}
#for each street { street_name : ({},{}) }
def loadPtrans() :
    Ptrans = {} 
    for street in [1,2,3] :
        street_name = globles.int2streetname(street)

        #to be built
        cluster_map = {}
        joint_map = {}

        map_table_name = "CLUSTER_MAP_%s" % street_name.upper()
        q = """select cboards,cluster_id
               from %s""" % map_table_name
        rows = conn.query(q)
        for (cboards,cluster_id) in rows :
            cluster_map[cboards] = int(cluster_id)

        joint_table_name = "CLUSTERS_%s" % street_name.upper()
        q = """select cluster_id,joint
               from %s """ % joint_table_name
        rows = conn.query(q)
        for (cluster_id,joint_str) in rows :
            #joint_map[cluster_id] = clust.parseTable(joint_str)
            joint_map[cluster_id] = clust.normalize( clust.parseTable(joint_str) )

        Ptrans[street_name] = ( (cluster_map, joint_map) )
    return Ptrans

def lookupPtrans( Ptrans, street, cluster_id ) :
    street_name = globles.int2streetname( street )
    #cluster_id = Ptrans[street_name][0][cboards]
    joint = Ptrans[street_name][1][cluster_id]
    return joint

#will want to replace this with accessing cached clustered version
#deprecated in favor of lookupPtrans
def lookupTransitionProbs( final_street, final_board ) :
    if final_street == 0 :
        print "preflop, no transitions to return"
        return False

    trans_lookup = {"01" : -1, \
                    "12" : -1, \
                    "23" : -1 }
    #TODO: compute TRANSITIONS_FLOP
    for street in range(1,final_street+1) :
        board = final_board[:street+2]
        #if turn or river
        if street > 1 :
            cboardp = deck.collapseBoard( board )
            cboard = deck.collapseBoard( board[:-1] )
            cboards = "%s|%s" % (cboard,cboardp)
        elif street == 1 :
            cboards = deck.collapseBoard( board )

        street_name = globles.int2streetname( street )
        query = """select dist
                   from TRANSITIONS_%s
                   where cboards = '%s'""" % \
                   (street_name.upper(), cboards)
        #print query
        dist = conn.queryScalar( query, str )
        dist = [[float(p) for p in line.split(',')] \
                for line in dist.split(';')]
        lookup_name = "%d%d" % (street-1, street)
        trans_lookup[lookup_name] = dist
    return trans_lookup

#return float(dist.split(';')[k].split(',')[kp])

#(1)
#compute P( k_i=k_i* | board, Actions )
#sum_{k_1...k{i-1}} PROD_j=0^i P(k_j|k_{j-1},b_j,A_j)
#                              product_terms                 
#i is the street number
#evidence is [board,['a11,a12,a13,a14',...,'ai1,ai2,ai3,ai4'] ]
#DEPRECATED FOR particle filter version: pf_P_ki_G_evdnc
def probKi( player_ix, street, evidence ) :

    #generate all the possible bucket assignments for the past streets
    #ie the cartesian product of [1,2,...10] x [1,2,...15] x etc
    l = [range(globles.NBUCKETS[past_street]) for past_street in range(street)]
    all_bucket_assignments = cartProduct( *l )

    #keep track of the last bucket seen for a particular street
    n_past_streets = street
    bucket_assignment = [-1]*n_past_streets

    n_bucket_values = globles.NBUCKETS[street]
    zs = [0]*n_bucket_values
    for bucket_value in range(n_bucket_values) :
        product_terms = [-1]*(street+1)
        for new_bucket_assignment in all_bucket_assignments :
            for past_street in range(n_past_streets) :
                if new_bucket_assignment[past_street] == \
                   bucket_assignment[past_street] :
                    #use the old product_term value
                    pass
                else : #recompute
                    #update
                    bucket_assignment[past_street] = \
                            new_bucket_assignment[past_street]

                    #handle when there is no previous street
                    if past_street == 0 :
                        prev_street_bucket_value = False
                    else :
                        prev_street_bucket_value = \
                                bucket_assignment[past_street-1]

                    product_terms[past_street] = computeProductTerm( \
                                         player_ix, \
                                         past_street, \
                                         new_bucket_assignment[past_street], \
                                         prev_street_bucket_value, \
                                         evidence )

            if street == 0 :
                prev_street_bucket_value = False
            else :
                prev_street_bucket_value = bucket_assignment[street-1]

            product_terms[street] = computeProductTerm( \
                                                   player_ix, \
                                                   street, \
                                                   bucket_value, \
                                                   prev_street_bucket_value, \
                                                   evidence)

            product = reduce( operator.mul, product_terms, 1 )
            zs[bucket_value] += product
        #end bucket assignment iteration
    #end bucket_values interation
    Z = sum(zs)
    return [z/Z for z in zs]


#estimate P(k_{final_street}=? | [board,actions] )

class BktAssmnt :
    def __init__(self) :
        self.buckets = []

    def extend(self, bucket_tuple ) :
        self.buckets.append( bucket_tuple )

    def copyExtend( self, bucket_tuple ) :
        n = BktAssmnt()
        n.buckets = list(self.buckets)
        n.extend( bucket_tuple )
        return n

    def get( self, street, player=-1 ) :
        if street >= len(self.buckets) :
            print 'dont have buckets for street %d yet' % street
            return False
        if player == -1 :
            return self.buckets[street]
        else :
            return self.buckets[street][player]

    def __str__(self) :
        return str(self.buckets)

    def __len__(self) :
        return len(self.buckets)

#for now, return the full {assignment : prob} dict
#later, will probalbly just need {final_assmnt : prob }
def pf_P_ki_G_evdnc( final_street, evidence, lookups, m=10 ) :

    #the m BktAssmnts we filter after each street
    particles = [BktAssmnt()]
    assignment_probs = {}
    for street in range(final_street+1) :
        #form an extended set of assignments, built on existing particles
        #will compute prob for each assignment, and take the m highest prob
        #as our new particles
        street_bkts = range(globles.NBUCKETS[street])
        new_bkt_tuples = cartProduct( street_bkts, street_bkts )

        assignments = [ t[0].copyExtend(t[1]) for t in \
                        cartProduct( particles, new_bkt_tuples )]


        print "n assignments: ", len(assignments)
        ##compute prob of each assignmnt
        assignment_probs = {}
        for count,assmnt in enumerate( assignments ) :
            p = P_assmnt_G_evdnc( assmnt, evidence, lookups )
            assignment_probs[ str(assmnt) ] = p

        #particle filter step
        if street < final_street :
            sassignments = sorted( assignments, \
                                   key = lambda k: assignment_probs[str(k)], \
                                   reverse = True )
            particles = []
            mm = min( m, len(sassignments) )
            for i in range(mm) :
                assmnt = sassignments[i]
                p = assignment_probs[str(assmnt)]
                print "Assignment: ", str(assmnt), " has prob: ", p
                particles.append( sassignments[i] )

        #for ass in assignments : print ass

    #when done, assignment_probs left with all {assmnt : prob} pairs for all
    #bucket values of the final_street X the m particles
    #1 - sum all probabilities.  This is our normalizing factor
    Z = 0
    final_assmnt_probs = {}
    #print assignment_probs
    for assmnt in assignments :
        #print str(assmnt)
        p = assignment_probs[str(assmnt)]
        Z += p
        final_assmnt = assmnt.get(final_street)
        if final_assmnt in final_assmnt_probs :
            final_assmnt_probs[final_assmnt] += p
        else :
            final_assmnt_probs[final_assmnt] = p

    print "final particles are: ", Z, " percent of the total mass"
    #assert Z > .85  #want to be looking at atleast so much mass

    #normalize
    for assmnt in assignment_probs :
        assignment_probs[assmnt] = assignment_probs[assmnt] / Z

    #sassignments = sorted( assignments, \
                           #key = lambda k: assignment_probs[str(k)], \
                           #reverse = True )

    #for ass in sassignments :
        #print "ass: ", ass, "prob: ", assignment_probs[str(ass)]

    #sort, normalize, and return
    sfinal = sorted( final_assmnt_probs.keys(), \
                     key = lambda k: final_assmnt_probs[k], \
                     reverse = True )
    for f in sfinal :
        print "final assmnt: ", f, " prob: ", final_assmnt_probs[f] / Z



    #2 - sum up all probs where k = some value  i
    #3 - normalize

    pass

#compute P( [ki=ai,...,k0=a0] | [board,actions] )
#an assignment is [(k10,k20),..,(k1i,k2i)]

def P_assmnt_G_evdnc( assignment, evidence, lookups ) :
    n_streets = len(assignment)
    assert n_streets >= 1
    
    Ptrans = lookups[2]

    product = 1
    for i in range(n_streets) :
        if i == 0 :
            p = P_ki_G_kimo_evdnc( street = i, \
                                   ki = assignment.get(i), \
                                   action_int = actions[i], \
                                   #evidence = evidence, \
                                   lookups = lookups )
            #print "prob for street:", i, p
        else :
            street_name = globles.int2streetname(i)
            cboards = evidence[0][i]
            cluster_id = Ptrans[street_name][0][cboards]
            p = P_ki_G_kimo_evdnc( street = i, \
                                   ki = assignment.get(i), \
                                   kimo = assignment.get(i-1), \
                                   cluster_id = cluster_id, \
                                   action_int = actions[i], \
                                   #evidence = evidence, \
                                   lookups = lookups )
            #print "prob for street:", i, p

        product *= p
    return product

#(3)
#P( ki | k_{i-1}, [board, actions] ) 
#cluster_id is the cluster the board -> cboard got assigned to
def P_ki_G_kimo_evdnc( street = -1, \
                       ki = [-1,-1], \
                       kimo = [-1,-1], \
                       cluster_id = -1, \
                       action_int = -1, \
                       #evidence = [ '{ street : cboards}', \
                                    #['agg_action_int','...' ] ], \
                       lookups = ['PA','PAK','Ptrans'], \
                       return_Z = False ) :

    #unpack
    PA,PAK,Ptrans = [lookups[i] for i in range(3)]

    if street == 0 :
        #P(k|A) = P(A|k)*P(k) / P(A)
        P_A_g_k = lookupPAK( PAK, street, ki[0], ki[1], action_int )
        #print "P(A|K): ", P_A_g_k

        Pk1 = lookupPk( street, ki[0] )
        Pk2 = lookupPk( street, ki[1] )
        Pk = Pk1*Pk2
        #print "P(k): ", Pk

        P_A = lookupPA( PA, street, action_int )
        #print "P(A) : ", P_A

        k_given_A = P_A_g_k * Pk / P_A
        #print "k_given_A", k_given_A
        return k_given_A
    else :

        # = ((BT1 * BT2 * K1 * K2 * B * AK) / Z
        #num and denom in (3)
        numerator = 0
        Z = 0

        #each players bucket in the previous round
        kimo_p1 = kimo[0]
        kimo_p2 = kimo[1]
        #print "kimo_p1, kimo_p2: ", kimo_p1, kimo_p2

        #K1,K2
        PKIMO1 = lookupPk(street-1,kimo_p1)
        PKIMO2 = lookupPk(street-1,kimo_p2)
        #print "PKIMO1,2: " , PKIMO1, PKIMO2

        #B = P( B=board ) 
        B = lookupPb(street)
        #print "P board: ", B

        joint = lookupPtrans( Ptrans, street, cluster_id )
        #joint = lookupPtrans( Ptrans, street, cboards )

        #all possible bucket assignments for the current street
        #used to compute the partition Z
        ki_buckets = range(globles.NBUCKETS[street])
        all_ki_pairs = cartProduct(ki_buckets, ki_buckets)

        terms = {}
        for (ki_p1,ki_p2) in all_ki_pairs :

            #print ""
            #print "\nki_p1,ki_p2", ki_p1, ki_p2

            ##BT1 = P( k1i=bkt_val | k_{i-1}=prev_bkt_val, B=board )
            PK1 = lookupPk(street, ki_p1) #joint[kimo_p1][ki_p1] # #
            PK2 = lookupPk(street, ki_p2) #joint[kimo_p2][ki_p2]
            print "PK1,PK2: " , PK1, PK2

            BT1 = joint[kimo_p1][ki_p1] # #
            BT2 = joint[kimo_p2][ki_p2]

            #print "    "
            #print "street: ", street
            #print "cluste_id: " , cluster_id
            #print "    kimo_p1, ki_p1", kimo_p1, ki_p1
            #print "    BT1,BT2: ", BT1,BT2
            #print "    PK1,PK2: ", PK1, PK2

            AK = lookupPAK( PAK, street, ki_p1, ki_p2, action_int )
            #print "    AK: ", AK

            #term = (BT1*PKIMO1) * (BT2*PKIMO2) * B * AK
            term = (PK1) * (PK2) * AK

            #print  "    prob:", term
            #print "    log prob: ", log(term)
            terms["%d,%d" % (ki_p1,ki_p2)] = term

            ##if this assignment is same as the one passed in
            if ki == (ki_p1,ki_p2) :
                #print" =============== TARGET --------------"
                #print "BT1,BT2: ", BT1,BT2
                #print "AK: ", AK
                #print "prob: ", term
                numerator = term

            Z += term

        #for pair in terms :
            #print pair, " : ", terms[pair] / Z

        #print "Z: ", Z
        if return_Z : return Z
        #print "num/Z: ", numerator/Z
        return numerator/Z
        #return Z

def precomputeDenominators( lookups ) :
    street = 3
    kimo_buckets = range(globles.NBUCKETS[street-1])
    all_kimo_pairs = cartProduct(kimo_buckets, kimo_buckets)

    PA,PAK,Ptrans = [lookups[i] for i in range(3)]


    count = 0
    for kimo_pair in all_kimo_pairs :
        count += 1
        if count < 100 :
            continue
        #TODO automate cluster size depending on street w/ query
        for cluster in range( 1,173 ) : #nclusters[street] ) :
            #TODO automate
            nacts = 1315
            for action in range( 1,nacts+1) :

                p = P_ki_G_kimo_evdnc( street = street, \
                                   ki = [42,42], \
                                   kimo = kimo_pair, \
                                   action_int = action, \
                                   cluster_id = cluster, \
                                   #evidence = [ '{ street : cboards}', \
                                                #['agg_action_int','...' ] ], \
                                   lookups = lookups, \
                                   return_Z = True) 

                if p > 0 :
                    print "kimo, cluster, action", kimo_pair, cluster, action
                    print "Prob: ", p

                    #if( p < .0001 ) : assert False

                    Pa = lookupPA( PA, street, action )
                    #Pkimo1 = lookupPk( street-1, kimo_pair[0] )
                    #Pkimo2 = lookupPk( street-1, kimo_pair[1] )
                    #Pb = lookupPb( street ) 
                    approx = Pa

                    print  "approv Prob: ", approx
                    if approx < p : 
                        print "EURRRREREKEKAKKAKA"

def setupEvidence( board, actions ) :
    #derive
    street_cboards = {}
    for street in range(4) :
        if street == 0 :
            street_cboards[0] = "n/a"
        else :
            (cboard,cboardp) = deck.board2cboards( board, street )
            cboards = deck.canonicalizeCboards( cboard,cboardp )
            street_cboards[street] = cboards

    evidence = [street_cboards, actions]
    return evidence

def setupLookups() :
    PA = loadPA()
    print "PA loaded"
    PAK = loadPAK()
    print "PAK loaded"
    Ptrans = loadPtrans()
    print "Ptrans loaded"

    lookups = [PA,PAK,Ptrans]

    return lookups

def loadPAKSanityCheck() :
    #sanity check for loading of EM P(A|K) weights
    PAK = loadPAK()
    for street in range(4) :
        for k1 in range( globles.NBUCKETS[street] ) :
            for k2 in range( globles.NBUCKETS[street] ) :
                s = sum(PAK[street][k1][k2])
                assert .9999 <= s <= 1.0001

if __name__ == '__main__' :

    #actions = [3, 3, 3, 148]
    #board = ['As', 'Ac', '3s', 'Jc', '4s']

    board = ['9h','3h','6h','5c','8d']
    actions = [441,5,187,315]

    evidence = setupEvidence(board,actions)
    lookups = setupLookups()


    #prob = P_ki_G_kimo_evdnc( street=1, \
                              #ki = (1,1), \
                              #kimo = (1,1), \
                              #evidence = evidence, \
                              #lookups = lookups )

    precomputeDenominators( lookups )

    #print prob
    
    #assignment = BktAssmnt()
    #assignment.extend((2,2))
    #assignment.extend((5,9))
    #assignment.extend((9,7))
    #assignment.extend((1,1))
    #assignment.extend((0,2))
    #prob = P_assmnt_G_evdnc( assignment, evidence, lookups )
    #print "assmnt_G_evdnc: ", prob
    
    #pf_P_ki_G_evdnc(3, evidence, lookups, m=50 )
