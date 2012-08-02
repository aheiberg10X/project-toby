from itertools import combinations
from random import sample

class Deck:
    def __init__(self) :
        self.cards = set(range(52))
        self.suits = ('h','d','c','s')
        #human-readable values for the 52 cards
        #matches that of pypoker-eval
        self.humancards = []
        for suit in self.suits :
            for num in [str(v) for v in range(2,10)] + ['T','J','Q','K','A'] :
                self.humancards.append( str(num)+suit )

    def shuffle(self) :
        self.cards = set(range(52))

    #if all the cards are present to be be removed, do so and return True
    #if not, do not remove anything and return False
    def remove( self, cards ) :
        try :
            ix = 0
            for c in cards : 
                self.cards.remove(c)
                ix += 1
            return True
        except KeyError as ve :
            #put back the removed cards
            for i in range(ix) :
                self.cards.add(cards[i])
            return False

    #since d.cards is a set don't need to worry about duplicates
    def replace( self, cards ) :
        for c in cards : self.cards.add(c)

    #draw n at random from the cards remaining in the deck
    def draw( self, n ) :
        selections = sample(self.cards, n)
        self.remove( selections )
        return selections
        #return tuple( self.humancards[s] for s in selections )    

    def getCardinality( self, card ) :
        if type(card) == int :
            return (card % 13)+2
        elif type(card) == str :
            return card[0]
        else :
            assert "go" == "fuck yourself"

    def getSuit( self, card ) :
        if type(card) == int :
            return self.suits[card / 13]
        elif type(card) == str :
            return card[1]
        else :
            assert "go" == "fuck yourself"

    #convenience
    def makeHuman( self, cards ) :
        return [self.humancards[c] for c in cards]

    def stringifyCardinality( self, c ) :
        d = {2:'2',3:'3',4:'4',5:'5',6:'6',7:'7',8:'8',9:'9', \
             10:'T',11:'J',12:'Q',13:'K',14:'A'}
        return d[c]

    #return the distinct type of hole card (1326 -> 169)
    #hole_cards are [int,int]
    def collapseHC( self, hole_cards ) :
        c1 = self.getCardinality(hole_cards[0])
        c2 = self.getCardinality(hole_cards[1])
        s1 = self.getSuit(hole_cards[0])
        s2 = self.getSuit(hole_cards[1])
        if s1 == s2 :
            suit = 's'
        else:
            suit = 'o'

        if c1 < c2 :
            return ('%s%s%s' % (self.stringifyCardinality(c1), \
                                self.stringifyCardinality(c2), \
                                suit) )
        elif c1 == c2 :
            return ('%s%s' % (self.stringifyCardinality(c1), \
                              self.stringifyCardinality(c2)))
        else :
            return ('%s%s%s' % (self.stringifyCardinality(c1), \
                                self.stringifyCardinality(c2),
                                suit) )



def main() :
    d = Deck()
    d.remove([1,2,3])
    d.remove([4,1])

    print d.collapseHC([25,51])
    print d.cards
    #print d.humancards
    #drawn = d.draw(3)
    #print drawn
    #print d.getCardinality(drawn[0])
    #print d.getSuit(drawn[0])
    #print d.humancards.index(drawn[0])

if __name__ == '__main__' :
    main()
