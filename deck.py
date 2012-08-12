from itertools import combinations
from random import sample


suits = ('h','d','c','s')
#human-readable values for the 52 cards
#matches that of pypoker-eval
humancards = []
for suit in suits :
    for num in [str(v) for v in range(2,10)] + ['T','J','Q','K','A'] :
        humancards.append( str(num)+suit )
#WILDCARD 52
humancards.append( '__' )
#WILDCARD 53
humancards.append( 'x' )


def getCardinality( card ) :
    if type(card) == int :
        return (card % 13)+2
    elif type(card) == str :
        return card[0]
    else :
        assert "go" == "fuck yourself"

def getSuit( card ) :
    if type(card) == int :
        return suits[card / 13]
    elif type(card) == str :
        return card[1]
    else :
        assert "go" == "fuck yourself"

#convenience
def makeHuman( cards ) :
    return [humancards[c] for c in cards]

def stringifyCardinality( c ) :
    d = {2:'2',3:'3',4:'4',5:'5',6:'6',7:'7',8:'8',9:'9', \
         10:'T',11:'J',12:'Q',13:'K',14:'A'}
    return d[c]

#return the distinct type of hole card (1326 -> 169)
#hole_cards are [int,int]
def collapseHC( hole_cards ) :
    c1 = getCardinality(hole_cards[0])
    c2 = getCardinality(hole_cards[1])
    s1 = getSuit(hole_cards[0])
    s2 = getSuit(hole_cards[1])
    if s1 == s2 :
        suit = 's'
    else:
        suit = 'o'

    if c1 < c2 :
        return ('%s%s%s' % (stringifyCardinality(c1), \
                            stringifyCardinality(c2), \
                            suit) )
    elif c1 == c2 :
        return ('%s%s' % (stringifyCardinality(c1), \
                          stringifyCardinality(c2)))
    else :
        return ('%s%s%s' % (stringifyCardinality(c1), \
                            stringifyCardinality(c2),
                            suit) )


class Deck:
    def __init__(self) :
        self.cards = set(range(52))
    
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
        #return tuple( humancards[s] for s in selections )    

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
