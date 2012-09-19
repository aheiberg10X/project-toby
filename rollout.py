from itertools import combinations, product
from deck import Deck, makeMachine, makeHuman, canonical
import pokereval
from multiprocessing import Process, Queue, Pool
from time import time
import globles

pe = pokereval.PokerEval()

def computeEV( pocket, board ) :
    return computeEVs( [pocket], board, 2 )[canonical(pocket)]

#take what information is known and return the EV's of all possible pockets
#first create an iter of all combinations of pockets
#apply rolloutPocketAssignment to each one
#combine the results and return the {pocket:EV} dicitonary 
def computeEVs( known_pockets, board, num_players, num_threads=4 ) :
    deck = Deck()
    deck.remove( board )
    for pocket in known_pockets :
        deck.remove( pocket )
    remaining_cards = deck.cards

    remaining_pockets = combinations( remaining_cards, globles.POCKET_SIZE )
    num_opponents = num_players - len(known_pockets)
    all_pocket_assignments = combinations( remaining_pockets, num_opponents )

    #map
    p = Pool(processes=num_threads)
    a = time()
    all_pockets_plus_globals = wrapWithGlobals( all_pocket_assignments, \
                                                known_pockets, \
                                                remaining_cards, \
                                                board )
    mapped = p.map( rolloutPocketAssignment, all_pockets_plus_globals )
    b  = time()
    print "mapping took: %fs" % (b-a)
    
    #reduce
    results = {}
    c = time()
    for ev_dict in mapped :
        for pocket in ev_dict :
            if pocket in results :
                results[pocket][0] += ev_dict[pocket]
                results[pocket][1] += 1
            else :
                results[pocket] = []
                results[pocket].append( ev_dict[pocket] )
                results[pocket].append( 1 )
    d = time()
    print "reducing took %fs" % (d-c)

    average_evs = {}
    for pocket in results :
        average_evs[pocket] = float(results[pocket][0]) / results[pocket][1] 

    p.close()
    p.join()
    return average_evs

# rolloutPocketAssignments job is to rollout a specific pocket_assignment
# BUT, it also needs the global information (i.e what we know beforehand) 
# this function takes an iterator of all the pocket assignment 
# and returns it with the global info
#TODO is this where all the memory is getting gobbled, I thought it was lazy
#     or maybe the results is what is taking all the room, can I reduce as I go?
def wrapWithGlobals( all_pocket_assignments, \
                     known_pockets, \
                     remaining_cards, \
                     board ) :
    for pa in all_pocket_assignments :
        yield [pa, known_pockets, remaining_cards, board]

#apply the rollout procedure to a specific pocket assignment
def rolloutPocketAssignment( data ) :
    [pocket_assignment, known_pockets, remaining_cards, board] = data
    results = {}
    d = Deck(set(remaining_cards))
    valid = all([d.remove(p) for p in pocket_assignment])
    if valid :
        pocket_assignment = [list(pp) for pp in pocket_assignment]
        pocket_assignment = pocket_assignment + known_pockets
        r = pe.poker_eval( game=globles.GAME, \
                           pockets=pocket_assignment, \
                           board=board )
        for pocket,evl in zip( pocket_assignment, r["eval"] ) :
            results[canonical(pocket)] = evl["ev"] / float(globles.EV_RANGE)

    return results

########################################################################

def rollout( hole_cards ) :
    game = "holdem"
    #five wildcards
    num_known_board = 0
    board = ["__"]*(5-num_known_board)
    d = Deck()
    #store the accumlated EV's for each of the 169 distinct HCs
    #[acc_ev,num_trials]
    results = {}
    count = 0

    #if deck.remove() lets us take out each pair of hole cards
    #then the assignment is valid one
    valid = all([d.remove(hc) for hc in hole_cards])
    if valid :
        #just turn it into lists for poker_eval
        hole_cards = [list(hc) for hc in hole_cards]
        #do the exhaustive rollout simulation
        r = pe.poker_eval( game, \
                           hole_cards, \
                           dead=["__"]*3, \
                           board=board) 
                           #iterations = 500000)

        #add the EV's up
        for hc,evl in zip(hole_cards,r["eval"]) :
            EV = evl["ev"]
            dhc = d.collapsePocket( hc )
            if dhc in results :
                results[dhc] += EV 
                
            else :
                results[dhc] = EV

    
    #count += 1
    #if count > 100 : break

    return results

#hole card rollout for arbitrary number of players
def rolloutMapReduce() :
    num_threads = 4 
    
    num_players = 2
    d = Deck()
    #some hole card assignments will be impossible
    #e.g 2c2d 2c7h
    #but these impossible ones are excluded later by deck.remove in rollout 
    all_hole_cards = combinations( combinations(d.cards,2), num_players )

    results={}

    #map
    p = Pool(processes=num_threads)
    a = time()
    r = p.map( rollout, all_hole_cards )
    b  = time()
    
    #reduce
    c = time()
    for d in r :
        for hand in d :
            if hand in results :
                results[hand][0] += d[hand]
                results[hand][1] += 1
            else :
                results[hand] = []
                results[hand].append( d[hand] )
                results[hand].append( 1 )
    d = time()

    p.close()
    p.join()

    fresults = open( "%s_player_rollout_pmap.txt" % num_players, 'w' )
    fresults.write("mapping time: %s\n" % str(b-a) )
    fresults.write("reduce time: %s\n" % str(d-c) )
    for r in results :
        #print r, results[r]
        fresults.write( "%s, %s\n" % (r,results[r]) )
    fresults.close()

#########################################################################

def main() :
    board = ['2c','2d','Td','__','__']
    pocket1 = ['2h','As']
    pocket2 = ['2s','Kd']
    print computeEV( pocket1, board )
    #results = computeEVs( [pocket1], board, 2 )
    #print results[canonical(pocket1)]
    #print results


if __name__ == "__main__" :
    #print computeEV( ['2c','5d'], ['2h','6d','Th'] )
    main()


#a = list(d.draw(2))
#b = list(d.draw(2))
#print "Player A - Hole Cards", d.makeHuman(a)
#print "Player B - Hold Cards", d.makeHuman(b)
#
#num_known_board = 3
#for board in combinations(d.cards, num_known_board) :
    #pockets = [a,b]
    #board = d.makeHuman(board) + ["__"] * (5-num_known_board)
    #print "Board,", board
    #print r["info"]
    #for pr in r["eval"] :
        #print pr["ev"]
#
    #print "\n\n"
    #count += 1
    #if count > 10 : break
