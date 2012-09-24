from itertools import combinations, product
from deck import Deck
import pokereval
from multiprocessing import Process, Queue, P

num_threads = 2

#hole card rollout for arbitrary number of players
def main() :
    num_players = 2
    d = Deck()
    #some hole card assignments will be impossible
    #e.g 2c2d 2c7h
    #but these impossible ones are excluded later by deck.remove below
    all_hole_cards = combinations( combinations(d.cards,2), num_players )
    

    procs = []
    length = len(all_hole_cards)
    print length
    for i in range(num_threads) :
        p = Process(target=rollout, args=(q,all_hole_cards,))
        procs.append( p )
        p.start()
        p.join()

    print q.get()

    #print 'adsfasdfadsf'
    #fresults = open( "%s_player_rollout.txt" % num_players, 'w' )
    #for r in results :
        #print r, results[r]
        #fresults.write( "%s, %s" % (r,results[r]) )
    #fresults.close()


def rollout( hole_cards_list ) :
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
    for hole_cards in hole_cards_list :
        #start with a new deck each time
        d.shuffle()

        #if deck.remove() lets us take out each pair of hole cards
        #then the assignment is valid one
        valid = all([d.remove(hc) for hc in hole_cards])
        if valid :
            #just turn it into lists for poker_eval
            hole_cards = [list(hc) for hc in hole_cards]
            print hole_cards
            #do the exhaustive rollout simulation
            r = pe.poker_eval( game, hole_cards, dead=["__"], board=board )

            #add the EV's up
            for hc,evl in zip(hole_cards,r["eval"]) :
                EV = evl["ev"]
                dhc = d.collapseHC( hc )
                if dhc in results :
                    results[dhc][0] += EV 
                    results[dhc][1] += 1
                    
                else :
                    results[dhc] = []
                    results[dhc].append( EV )
                    results[dhc].append( 1 )

            print "\n"
        
        count += 1
        if count > 100 : break

    return results


if __name__ == "__main__" :
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
