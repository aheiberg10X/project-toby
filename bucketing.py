import pokereval
from deck import Deck, makeMachine, makeHuman
from itertools import combinations

num_buckets = 20

pe = pokereval.PokerEval()
d = Deck()

game = 'holdem'
side = 'hi'

board = ['2c','3c','Td','__','__']
print board
pocket1 = ['4c','8c']
pocket2 = ['4d','8h']

print pe.poker_eval( game, [pocket1, pocket2], board )

#for board in combinations( d.cards, 3 ) :
    #d.shuffle()
    #d.remove( board )
   # 
    #for holding in combinations( d.cards, 2 ) :
        #pass


