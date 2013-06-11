from itertools import product as cartProduct
import operator
from math import factorial

import selective_eval
import globles
import db
import deck
import BTclustering as clust

conn = db.Conn('localhost')

def nCr(n, r):
    r = min(r, n-r)
    if r == 0: return 1
    numer = reduce(operator.mul, xrange(n, n-r, -1))
    denom = reduce(operator.mul, xrange(1, r+1))
    return numer//denom


def loadPALookups() :#load lookup information...
    #P( Ai )
    PA = []
    PA.append( selective_eval.computeTypeFrequencies( [2,3,4,5] ) )
    PA.append( selective_eval.computeTypeFrequencies( [8,9,10,11] ) )
    PA.append( selective_eval.computeTypeFrequencies( [14,15,16,17] ) )
    PA.append( selective_eval.computeTypeFrequencies( [20,21,22,23] ) )
    return PA

def lookupPA( PA, street, action_str ) :
    return PA[street][action_str]

#P(k)
def lookupPk( street, bucket ) :
    sname = globles.int2streetname( street )
    return globles.BUCKET_PERCENTILES[sname][bucket]

#P(b)
def lookupPb( street ) :
    if street == 0 : return 1
    elif 1 <= street <= 3 :
        l = street + 2
        n_boards = nCr( (52-(2*globles.POCKET_SIZE)), l )
        return 1 / float( n_boards )
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
def P_assgmnt_G_evdnc( assignment, evidence ) :
    n_streets = len(assignment)
    assert n_streets >= 1
    product = 1
    for i in range(n_streets) :
        if i == 0 :
            p = P_ki_G_kimo_evdnc( street = i, \
                                   bucket_tuple = assignment[i], \
                                   evidence = evidence )
        else :
            p = P_ki_G_kimo_evdnc( street = i, \
                                   bucket_tuple = assignment[i], \
                                   prev_bucket_tuple=assignment[i-1], \
                                   evidence = evidence )

        product *= p
    return p

#P( ki | k_{i-1}, [board, actions] ) 
def P_ki_G_kimo_evdnc( street=42, \
                       bucket_tuple=[42,42], \
                       prev_bucket_tuple=[42,42], \
                       evidence=[ ['b','o','a','r','d'],\
                                  ['4actions','etc'] ], \
                       lookups = ['Ptran','PA','Pb','Pk'] ) :

    
    if street == 0 :
        pass
    else :
        #unpack
        board, actions = evidence[0], evidence[1]
        Ptrans,PA,Pb,Pk = [lookups[i] for i in range(4)]

        #derive
        print "board: ", board
        (cboard,cboardp) = deck.board2cboards( board, street )
        cboards = deck.canonicalizeCboards( cboard,cboardp )
        print " cboards:" , cboards

        # = ((BT1 * BT2 * K1 * K2 * B * AK) / Z

        k1,kp1 = prev_bucket_tuple[0], bucket_tuple[0]
        k2,kp2 = prev_bucket_tuple[1], bucket_tuple[1]

        #BT1 = P( k1i=bkt_val | k_{i-1}=prev_bkt_val, B=board )
        joint = lookupPtrans( Ptrans, street, cboards )
        BT1 = joint[k1][kp1]
        BT2 = joint[k2][kp2]
        print BT1,BT2
        #key = "%d%d" % (street-1, street)
        #BT1 = prob_trans[key][k1][kp1]
        #BT2 = prob_trans[key][k2][kp2]

        #K1,K2
        #K1 = lookupBucketProb(street,kp1)
        #K2 = lookupBucketProb(street,kp2)

        #B = P( B=board ) 
        #B = lookupBoardProb(street)

        #   each term a constant, one def by percentiles, the other by nCr 
        #AK = 1 #TODO lookup from loaded EM computed weights


        #C = P( A=actions | ki )
        #   learned from EM

    return 1

if __name__ == '__main__' :

    #cluster_id = Ptrans["flop"][0]["dummy|237_h_3f"]
    #joint = Ptrans["flop"][1][cluster_id]
    #print cluster_id, joint

    board = ['2c','4c','7h','7c','Td']
    actions = ['1,12,1,12']*4
    evidence = [board, actions]

    Ptrans = loadPtrans()

    lookups = [Ptrans,-1,-1,-1]
    P_ki_G_kimo_evdnc( street=1, \
                       bucket_tuple = (1,1), \
                       prev_bucket_tuple = (1,1), \
                       evidence = evidence, \
                       lookups = lookups )
    #print evidence
    #probKi( 1, 2, 10, evidence )

    #print pf_P_ki_G_evdnc( 1, [['2h','3h','4h','5h','6h'],['actions!']] )
    
    #print lookupTransitionProbs( 3, ['2h','3h','4h','5h','6h'] ) 
    #"2345_s_4f|23456_s_5f" )
