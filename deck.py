from itertools import combinations
from random import sample

class Deck:
    def __init__(self) :
        self.cards = range(52)
        self.suits = ('h','d','c','s')
        #human-readable values for the 52 cards
        #matches that of pypoker-eval
        self.humancards = []
        for suit in self.suits :
            for num in [str(v) for v in range(2,11)] + ['J','Q','K','A'] :
                self.humancards.append( str(num)+suit )

    #draw n from the cards remaining in the deck
    def draw( self, n ) :
        selections = sample(self.cards, n)
        for s in selections :
            self.cards.remove(s)
        return selections
        #return tuple( self.humancards[s] for s in selections )    

    def getCardinality( self, card ) :
        if type(card) == int :
            return card/4+1
        elif type(card) == str :
            return card[0]
        else :
            assert "go" == "fuck yourself"

    def getSuit( self, card ) :
        if type(card) == int :
            return self.suits[card % 4]
        elif type(card) == str :
            return card[1]
        else :
            assert "go" == "fuck yourself"

    #convenience
    def makeHuman( self, cards ) :
        return [self.humancards[c] for c in cards]

def main() :
    d = Deck()
    for i in range(52) : 
        print i
        print d.humancards[i]
    #print d.humancards
    drawn = d.draw(3)
    print drawn
    print d.getCardinality(drawn[0])
    print d.getSuit(drawn[0])
    print d.humancards.index(drawn[0])

if __name__ == '__main__' :
    main()
