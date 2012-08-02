from itertools import combinations, product
from deck import Deck
import pokereval

#hole card rollout for arbitrary number of players

game = "holdem"
pe = pokereval.PokerEval()
d = Deck()

num_players = 2
#some of these aren't valid, e.g [(0,1),(0,1)]
#but the impossible ones are excluded later
all_hole_cards = product( combinations(d.cards,2), repeat=num_players )

count = 0

#five wildcards
board = ["__"]*5

#store the accumlated EV's for each of the 169 distinct HCs
results = {}
for hole_cards in all_hole_cards :
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
                results[dhc] += EV 
            else :
                results[dhc] = 0
        print "\n"
    
    count += 1
    if count > 300 : break

print 'adsfasdfadsf'
for r in results :
    print r, results[r]


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
