from itertools import product as cartesianProduct
import operator
import selective_eval
from math import factorial
import globles

def nCr(n, r):
    r = min(r, n-r)
    if r == 0: return 1
    numer = reduce(operator.mul, xrange(n, n-r, -1))
    denom = reduce(operator.mul, xrange(1, r+1))
    return numer//denom

nbuckets = [10,20,15,10]

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
        sname = globles.int2Streetname( street )
        return globles.BUCKET_PERCENTILES[sname][bucket]

    print lookupBucketProb( 2, 5 )

    #P(b)
    def lookupBoardProb( board ) :
        l = len(board)
        if l == 0 : return 1
        elif l >= 3 and l <= 5:
            n_boards = nCr( (52-(2*globles.POCKET_SIZE)), l )
            return 1 / float( n_boards )
        else : assert False

    print lookupBoardProb( [1,2,3] )

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

def computeProductTerm( player_ix, \
                        street, \
                        bucket_value, \
                        prev_street_bucket_value, \
                        evidence ) :
    if street == 0 :
        board = []
    else :
        board = evidence[0][:street+2]
    actions = evidence[1][street]

    #need P( ki | k_{i-1}, board, actions ) 
    # = ((A * B * C) / Z

    #A = P( ki=bkt_val | k_{i-1}=prev_bkt_val, B=board )
    #   transition lookup

    #B = P( ki=bkt_val, B=board ) = P( ki = bkt_val | B=board )P( B = board )
    #   each term a constant, one def by percentiles, the other by nCr 


    #C = P( A=actions | ki )
    #   learned from EM

    if prev_street_bucket_value :

        pass

    #just need P(k0|A0)
    else :
        pass

    return 1

if __name__ == '__main__' :
    board = ['2c','4c','7h','7c','Td'],
    actions = ['1,12,1,12']*4
    evidence = [board, actions]
    print evidence
    probKi( 1, 2, 10, evidence )
