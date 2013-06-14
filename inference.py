from itertools import product as cartProduct
import operator
from math import factorial

import selective_eval
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


#there is no P(A) term why did I put these here?
#def loadPALookups() :#load lookup information...
    ##P( Ai )
    #PA = []
    #PA.append( selective_eval.computeTypeFrequencies( [2,3,4,5] ) )
    #PA.append( selective_eval.computeTypeFrequencies( [8,9,10,11] ) )
    #PA.append( selective_eval.computeTypeFrequencies( [14,15,16,17] ) )
    #PA.append( selective_eval.computeTypeFrequencies( [20,21,22,23] ) )
    #return PA
#
#def lookupPA( PA, street, action_str ) :
    #return PA[street][action_str]

def loadPAK() :
    #not layed out in file in a way conduscive to fast lookup
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
                k1_probs.append( k2_probs )

            PAK[street].append(k1_probs)

    #also load the action_str -> int mapper, AAS2I
    #AAS2I = idp.buildAAS2I()

    return PAK

def lookupPAK( PAK, street, k1, k2, action_int ) :
    return PAK[street][k1][k2][action_int]

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
            joint_map[cluster_id] = clust.parseTable(joint_str)

        Ptrans[street_name] = ( (cluster_map, joint_map) )
    return Ptrans

def lookupPtrans( Ptrans, street, cboards ) :
    street_name = globles.int2streetname( street )
    cluster_id = Ptrans[street_name][0][cboards]
    joint = Ptrans[street_name][1][cluster_id]
    return joint

#will want to replace this with accessing cached clustered version
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

    def get( self, street, player ) :
        if street >= len(self.buckets) :
            print 'dont have buckets for street %d yet' % street
            return False
        return self.buckets[street][player]

    def __str__(self) :
        return str(self.buckets)

def pf_P_ki_G_evdnc( final_street, evidence, m=100 ) :
    #cache some stuff for lookups
    board = evidence[0]

    #{'s0s1' : prob[k][kp]}
    ##deprecated
    #prob_trans = lookupTransitionProbs( final_street, board )
    #evidence.append(prob_trans)

    #the m BktAssmnts we filter after each street
    particles = [BktAssmnt()]
    for street in range(final_street+1) :
        #form an extended set of assignments, built on existing particles
        #will compute prob for each assignment, and take the m highest prob
        #as our new particles
        street_bkts = range(globles.NBUCKETS[street])
        new_bkt_tuples = cartProduct( street_bkts, street_bkts )

        assignments = [ t[0].copyExtend(t[1]) for t in \
                        cartProduct( particles, new_bkt_tuples )]


        ##compute prob of each assignmnt
        assignment_probs = {}
        for assgmnt in assignments :
            #p = P_assgmnt_G_evdnc( assgmnt, evidence )
            p = .1
            assignment_probs[assgmnt] = p

        #particle filter step
        if street < final_street :
            sassignments = sorted( assignment_probs.keys(), \
                                   key = lambda k: assignment_probs[k], \
                                   reverse = True )
            particles = []
            for i in range(m) :
                particles.append( sassignments[i] )

        #for ass in assignments : print ass

    #when done, assignment_probs left with all {assgmnt : prob} pairs for all
    #bucket values of the final_street X the m particles
    #1 - sum all probabilities.  This is our normalizing factor
    #2 - sum up all probs where k = some value
    #3 - normalize

    pass

#compute P( [ki=ai,...,k0=a0] | [board,actions] )
#an assignment is [(k10,k20),..,(k1i,k2i)]

#TODO: add lookups
def P_assgmnt_G_evdnc( assignment, evidence ) :
    n_streets = len(assignment)
    assert n_streets >= 1
    product = 1
    for i in range(n_streets) :
        if i == 0 :
            p = P_ki_G_kimo_evdnc( street = i, \
                                   ki = assignment[i], \
                                   evidence = evidence )
        else :
            p = P_ki_G_kimo_evdnc( street = i, \
                                   ki = assignment[i], \
                                   kimo = assignment[i-1], \
                                   evidence = evidence )

        product *= p
    return p

#(3)
#P( ki | k_{i-1}, [board, actions] ) 
def P_ki_G_kimo_evdnc( street = 42, \
                       ki = [42,42], \
                       kimo = [42,42], \
                       evidence = [ ['b','o','a','r','d'],\
                                    ['4actions','etc'] ], \
                       lookups = ['PAK','Ptrans'] ) :

    if street == 0 :
        print "what to do here?"
        assert False
        pass
    else :
        #unpack
        board, actions = evidence[0], evidence[1]
        PAK,Ptrans = [lookups[i] for i in range(2)]

        #derive
        print "board: ", board
        (cboard,cboardp) = deck.board2cboards( board, street )
        cboards = deck.canonicalizeCboards( cboard,cboardp )
        print " cboards:" , cboards

        # = ((BT1 * BT2 * K1 * K2 * B * AK) / Z

        kimo_p1 = kimo[0]
        kimo_p2 = kimo[1]

        #num and denom in (3)
        numerator = 0
        Z = 0

        #all possible bucket assignments for the current street
        #used to compute the partition Z
        ki_buckets = range(globles.NBUCKETS[street])
        all_ki_pairs = cartProduct(ki_buckets, ki_buckets)

        #B = P( B=board ) 
        B = lookupPb(street)

        for (ki_p1,ki_p2) in all_ki_pairs :

            #BT1 = P( k1i=bkt_val | k_{i-1}=prev_bkt_val, B=board )
            joint = lookupPtrans( Ptrans, street, cboards )
            BT1 = joint[kimo_p1][ki_p1]
            BT2 = joint[kimo_p2][ki_p2]
            print BT1,BT2

            #K1,K2
            K1 = lookupPk(street,kimo_p1)
            K2 = lookupPk(street,kimo_p2)

            #   each term a constant, one def by percentiles, the other by nCr 
            action_str = actions[street]
            print "action_str, ", action_str
            AK = lookupPAK( PAK, street, ki_p1, ki_p2, action_str )

            term = (BT1*K1) * (BT2*K2) * B * AK

            #if this assignment is same as the one passed in
            if ki == (ki_p1,ki_p2) :
                numerator = term

            Z += term

    return 1

if __name__ == '__main__' :

    ##sanity check for loading of EM P(A|K) weights
    #(PAK,AAS2I) = loadPAK()
    #for street in range(4) :
        #for k1 in range( globles.NBUCKETS[street] ) :
            #for k2 in range( globles.NBUCKETS[street] ) :
                #s = sum(PAK[street][k1][k2])
                #assert .9999 <= s <= 1.0001
    #assert False

    #cluster_id = Ptrans["flop"][0]["dummy|237_h_3f"]
    #joint = Ptrans["flop"][1][cluster_id]
    #print cluster_id, joint

    board = ['2c','4c','7h','7c','Td']
    #2 = 'k,k,d,d'
    actions = [2,2,2,2]
    #actions = ['1,12,1,12']*4
    evidence = [board, actions]

    PAK = loadPAK()
    Ptrans = loadPtrans()

    lookups = [PAK,Ptrans]
    P_ki_G_kimo_evdnc( street=1, \
                       ki = (1,1), \
                       kimo = (1,1), \
                       evidence = evidence, \
                       lookups = lookups )
    #print evidence
    #probKi( 1, 2, 10, evidence )

    #print pf_P_ki_G_evdnc( 1, [['2h','3h','4h','5h','6h'],['actions!']] )
    
    #print lookupTransitionProbs( 3, ['2h','3h','4h','5h','6h'] ) 
    #"2345_s_4f|23456_s_5f" )
