from itertools import combinations, product
from deck import Deck, makeMachine, makeHuman, canonicalize
import pokereval
from time import time
import globles
from multiprocessing import Process, Queue, Pool

pe = pokereval.PokerEval()

def computeSingleEHS2( pocket, board ) :
    r = computeEHS2( [ [['__','__'],pocket], board, 'HS' ] )
    return r[canonicalize(pocket)]

def computeEHS2( data ) :
    [pocket_assignment, board, EV_or_HS] = data
    d = Deck()
    d.remove( board )
    valid = all([d.remove(pa) for pa in pocket_assignment])
    results = {}
    if valid :
        canonical_pockets = [canonicalize(p) for p in pocket_assignment]
        num_unknown_board = 5-len(board)
        HS2sums = {}
        counts = {}
        for pocket in canonical_pockets :
            HS2sums[pocket] = 0
            counts[pocket] = 0
        for board_suffix in combinations( d.cards, num_unknown_board ) :
            full_board = board + makeHuman(board_suffix)
            #print makeHuman(pocket), full_board
            data = [ pocket_assignment, full_board, EV_or_HS]
            HS2s = computeHS2(data)
            for pocket in canonical_pockets :
                HS2sums[pocket] += HS2s[pocket]
                counts[pocket] += 1

        for pocket in canonical_pockets :
            results[pocket] = HS2sums[pocket] / float(counts[pocket])
    return results

#apply the rollout procedure to a specific pocket assignment
def computeHS2( data ) :
    [pocket_assignment, board, EV_or_HS] = data
    if len(board) != 5 :
        print "HS2 only works on board lengths of 5"
        assert False
    results = {}
    d = Deck()
    d.remove( board )
    valid = all([d.remove(pa) for pa in pocket_assignment])
    if valid :
        r = pe.poker_eval( game=globles.GAME, \
                           pockets=pocket_assignment, \
                           board=board )
        if EV_or_HS == 'EV' :
            for pocket,evl in zip( pocket_assignment, r["eval"] ) :
                results[canonicalize(pocket)] = evl["ev"] / float(globles.EV_RANGE)
        else :
            for i, pocket in enumerate(pocket_assignment) :
                wins   = r["eval"][i]["winhi"]
                ties   = r["eval"][i]["tiehi"]
                losses = r["eval"][i]["losehi"]
                hs = (wins + float(ties/2)) / (wins + ties + losses)
                hs2 = hs*hs;
                #if canonicalize(pocket) == '8d8c' :
                    #print data, hs2
                results[canonicalize(pocket)] = hs2
    else :
        pass
        #raise Exception("Invalid Assignment")

    return results

#helper to mapReduceComputeHS2
def wrapWithGlobals( possible_unknown_pockets, \
                     known_pockets, \
                     remaining_cards, \
                     board,
                     EV_or_HS ) :
    #print 'known:', known_pockets
    #print 'possible:',possible_unknown_pockets
    #print 'board:',board
    for unknown_pockets in possible_unknown_pockets :
        #print unknown_pockets
        yield [ [list(pocket) for pocket in unknown_pockets] + known_pockets, \
                board, EV_or_HS]

def mapReduceComputeEHS2( pool, \
                          board, \
                         num_opponents = 1 ) :

    known_pockets = [['__','__']]
    dek = Deck()
    dek.shuffle()
    dek.remove( board )
    remaining_cards = dek.cards
    possible_pockets = combinations( remaining_cards, globles.POCKET_SIZE )
    possible_pocket_assignments = combinations( possible_pockets, \
                                                num_opponents )
   
    #map
    a = time()
    all_pockets_plus_globals = wrapWithGlobals( possible_pocket_assignments, \
                                                known_pockets, \
                                                remaining_cards, \
                                                board, \
                                                'HS')
    mapped = pool.map( computeEHS2, all_pockets_plus_globals )
    #mapped: [{pocket1: HS2, __: HS2},{pocket2: HS2, __:HS2},...]
    
    d_pocket_HS2 = {}
    for pocket_hs in mapped :
        for pocket in pocket_hs :
            if pocket != canonicalize(['__','__']) :
                d_pocket_HS2[pocket] = pocket_hs[pocket]

    #print d_pocket_HS2
    return d_pocket_HS2 

########################################################################

if __name__ == "__main__" :

    print computeSingleEHS2( ['2h','9d'], [] )

    #pocket_assignment = [['7d','2h'],['__','__']]
    #board = ['Ts','Jh','5s','7h','6d']
    #r = pe.poker_eval( game=globles.GAME, \
                       #pockets=pocket_assignment, \
                       #board=board )
    #print r

    #for pocket in combinations( range(52), 2 ) :
        #print pocket, computeEHS2( list(pocket), ['2h','5h','9c'] )

    pass



#################################################################
########  DEPRECATED
##################################################################

#DEPRECATED, using HS2 instead
#def computeEV( pocket, board ) :
    #return computeEVs( [pocket], board, 2 )[canonicalize(pocket)]

#take what information is known and return the EV's of all possible pockets
#first create an iter of all combinations of pockets
#apply computeHS2 to each one
#combine the results and return the {pocket:EV} dicitonary 
#DEPRECATED using HS2 instead
#def computeEVs( known_pockets, board, num_players, num_threads=4 ) :
    #deck = Deck()
    #deck.remove( board )
    #for pocket in known_pockets :
        #deck.remove( pocket )
    #remaining_cards = deck.cards
#
    #remaining_pockets = combinations( remaining_cards, globles.POCKET_SIZE )
    #num_opponents = num_players - len(known_pockets)
    #all_pocket_assignments = combinations( remaining_pockets, num_opponents )
#
    ##map
    #p = Pool(processes=num_threads)
    #a = time()
    #all_pockets_plus_globals = wrapWithGlobals( all_pocket_assignments, \
                                                #known_pockets, \
                                                #remaining_cards, \
                                                #board, \
                                                #'EV' )
#
    #mapped = p.map( computeHS2, all_pockets_plus_globals )
    #b  = time()
    ##print "mapping took: %fs" % (b-a)
   # 
    ##reduce
    #results = {}
    #c = time()
    #for ev_dict in mapped :
        #for pocket in ev_dict :
            #if pocket in results :
                #results[pocket][0] += ev_dict[pocket]
                #results[pocket][1] += 1
            #else :
                #results[pocket] = []
                #results[pocket].append( ev_dict[pocket] )
                #results[pocket].append( 1 )
    #d = time()
    ##print "reducing took %fs" % (d-c)
#
    #average_evs = {}
    #for pocket in results :
        #average_evs[pocket] = float(results[pocket][0]) / results[pocket][1] 
#
    #p.close()
    #p.join()
    #return average_evs
#TODO, this should go in bucketing
# really just belongs as part of computeDistsHS as it is just a wrapper
# to multi thred.  The logic of it's input and output is handled explicitly in computeDistsHS
def computeHSs( known_pockets, board, num_threads=4 ) :
    #wtf is going on that I have to make the range explicit?
    dek = Deck()
    dek.shuffle()
    dek.remove( board )
    for pocket in known_pockets :
        dek.remove( pocket )
    remaining_cards = dek.cards

    results = {}
    print "\n"
    print board
    print remaining_cards
    pockets = combinations( remaining_cards, globles.POCKET_SIZE )
    possible_unknown_pockets = combinations( pockets, 1 )
    #print pocket_assignment

    #map
    p = Pool(processes=num_threads)
    a = time()
    all_pockets_plus_globals = wrapWithGlobals( possible_unknown_pockets, \
                                                known_pockets, \
                                                remaining_cards, \
                                                board, \
                                                'HS')
    mapped = p.map( computeHS2, all_pockets_plus_globals )
    #print mapped
    b  = time()
    #print "mapping took: %fs" % (b-a)
    
    #reduce
    c = time()
    for pocket_hs in mapped :
        for pocket in pocket_hs :
            results[pocket] = pocket_hs[pocket]
    d = time()
    #print "reducing took %fs" % (d-c)
    
    p.close()
    p.join()

    return results


