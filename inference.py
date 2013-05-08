from itertools import product as cartesianProduct
import operator
import selective_eval
from math import factorial
import globles
import db
import deck

def nCr(n, r):
    r = min(r, n-r)
    if r == 0: return 1
    numer = reduce(operator.mul, xrange(n, n-r, -1))
    denom = reduce(operator.mul, xrange(1, r+1))
    return numer//denom

nbuckets = [10,20,15,10]

conn = db.Conn('localhost')

def loadLookups() :#load lookup information...
    #P( Ai )
    PA = []
    PA.append( selective_eval.computeTypeFrequencies( [2,3,4,5] ) )
    PA.append( selective_eval.computeTypeFrequencies( [8,9,10,11] ) )
    PA.append( selective_eval.computeTypeFrequencies( [14,15,16,17] ) )
    PA.append( selective_eval.computeTypeFrequencies( [20,21,22,23] ) )

    def lookupActionProb( street, action_str ) :
        return PA[street][action_str]

    print lookupActionProb( 3, '1,12,1,12' )

#P(k)
def lookupBucketProb( street, bucket ) :
    sname = globles.int2streetname( street )
    return globles.BUCKET_PERCENTILES[sname][bucket]

#print lookupBucketProb( 2, 5 )

#P(b)
def lookupBoardProb( street ) :
    if street == 0 : return 1
    elif 1 <= street <= 3 :
        l = street + 2
        n_boards = nCr( (52-(2*globles.POCKET_SIZE)), l )
        return 1 / float( n_boards )
    else : assert False

#print lookupBoardProb( [1,2,3] )

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
#evidence is [board,[['a11,a12,a13,a14'],...,['ai1,ai2,ai3,ai4']] 
def probKi( player_ix, street, evidence ) :
    #generate all the possible bucket assignments for the past streets
    #ie the cartesian product of [1,2,...10] x [1,2,...15] x etc
    l = [range(nbuckets[past_street]) for past_street in range(street)]
    all_bucket_assignments = cartesianProduct( *l )
    #keep track of the last bucket seen for a particular street
    n_past_streets = street
    bucket_assignment = [-1]*n_past_streets

    n_bucket_values = nbuckets[street]
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

def pf_P_ki_G_evdnc( final_street, evidence, m=100 ) :
    #cache some stuff for lookups
    board = evidence[0]

    #{'s0s1' : prob[k][kp]}
    prob_trans = lookupTransitionProbs( final_street, board )
    evidence.append(prob_trans)

    #the m assignments we arrived at after each street
    particles = [[]]
    for street in range(final_street+1) :
        #form an extended set of assignments, built on existing particles
        #will compute prob for each assignment, and take the m highest prob
        #as our new particles
        assignments = [t[0]+[t[1]] for t in \
                       product( particles, range(nbuckets[street]) )]

        #compute prob of each assignmnt
        assignment_probs = {}
        for assgmnt in assignments : 
            p = P_assgmnt_G_evdnc( assgmnt, evidence )
            assignment_probs[assgmnt] = p

        #particle filter step
        if street < final_street :
            sassignments = sorted( assignment_probs.keys(), \
                                   key = lambda k: assignment_probs[k], \
                                   reverse = True )
            particles = []
            for i in range(m) :
                particles.append( sassignments[i] )

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
                                   street_bucket_values = assignment[i], \
                                   evidence = evidence )
        else :
            p = P_ki_G_kimo_evdnc( street = i, \
                                   street_bucket_values = assignment[i], \
                                   prev_street_bucket_values=assignment[i-1], \
                                   evidence = evidence )

        product *= p
    return p


#P( ki | k_{i-1}, [board, actions] ) 
def P_ki_G_kimo_evdnc( street=42, \
                       street_bucket_values=[42,42], \
                       prev_street_bucket_values=[42,42], \
                       evidence=[ ['b','o','a','r','d'],\
                                  ['4actions','etc'], \
                                  "{'s1s2' : prob[k][kp]}" ] ) :

    if street == 0 :
        pass
    else :
        
        prob_trans = evidence[2]
        # = ((BT1 * BT2 * K1 * K2 * B * AK) / Z

        k1,kp1 = prev_street_bucket_values[0], street_bucket_values[0]
        k2,kp2 = prev_street_bucket_values[1], street_bucket_values[1]

        #BT1 = P( k1i=bkt_val | k_{i-1}=prev_bkt_val, B=board )
        key = "%d%d" % (street-1, street)
        BT1 = prob_trans[key][k1][kp1]
        BT2 = prob_trans[key][k2][kp2]

        #K1,K2
        K1 = lookupBucketProb(street,kp1)
        K2 = lookupBucketProb(street,kp2)

        #B = P( B=board ) 
        B = lookupBoardProb(street)

        #   each term a constant, one def by percentiles, the other by nCr 
        AK = 1 #TODO lookup from loaded EM computed weights


        #C = P( A=actions | ki )
        #   learned from EM

    return 1

if __name__ == '__main__' :
    #board = ['2c','4c','7h','7c','Td'],
    #actions = ['1,12,1,12']*4
    #evidence = [board, actions]
    #print evidence
    #probKi( 1, 2, 10, evidence )

    print pf_P_ki_G_evdnc( 3, [['2h','3h','4h','5h','6h'],['actions!']] )
    #print lookupTransitionProbs( 3, ['2h','3h','4h','5h','6h'] ) 
    #"2345_s_4f|23456_s_5f" )
