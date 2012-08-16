from itertools import combinations, product
from deck import Deck
import pokereval
from multiprocessing import Process, Queue, Pool
from time import time


def square(x) : 
    return x*x

def rollout( hole_cards ) :
    game = "holdem"
    #five wildcards
    num_known_board = 0
    board = ["__"]*(5-num_known_board)
    d = Deck()
    pe = pokereval.PokerEval()
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
            dhc = d.collapseHC( hc )
            if dhc in results :
                results[dhc] += EV 
                
            else :
                results[dhc] = EV

        print "\n"
    
    #count += 1
    #if count > 100 : break

    return results

#hole card rollout for arbitrary number of players
def main() :
    num_threads = 4 
    
    num_players = 2
    d = Deck()
    #some hole card assignments will be impossible
    #e.g 2c2d 2c7h
    #but these impossible ones are excluded later by deck.remove below
    all_hole_cards = combinations( combinations(d.cards,2), num_players )

    #test = []
    #for i in range(3000) :
        #test.append( all_hole_cards.next() )

    results={}
    #def callback( hand_scores ) :
        #for hand in hand_scores :
            #if hand in results :
                #results[hand] += hand_scores[hand]
            #else :
                #results[hand] = hand_scores[hand]


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

    print results
    p.close()
    p.join()

    fresults = open( "%s_player_rollout_pmap.txt" % num_players, 'w' )
    fresults.write("mapping time: %s\n" % str(b-a) )
    fresults.write("reduce time: %s\n" % str(d-c) )
    for r in results :
        #print r, results[r]
        fresults.write( "%s, %s\n" % (r,results[r]) )
    fresults.close()



if __name__ == "__main__" :
    #print rollout( ((0,1),(4,5)) )
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
