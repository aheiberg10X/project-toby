from itertools import combinations
from deck import Deck
import pokereval

pe = pokereval.PokerEval()
d = Deck()
count = 0
hole_cards = list(d.draw(2))
print "Hole Cards", d.makeHuman(hole_cards)

for board in combinations(d.cards,5) :
    print "Board,", d.makeHuman(board)
    print "Eval,", pe.best( "hi", hand=hole_cards + list(board) )
    count += 1
    if count > 10 : break
