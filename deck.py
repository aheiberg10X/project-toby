from itertools import combinations
from random import sample
from pokereval import PokerEval
import globles

#DEPRECATED, just using pokereval string2card and card2string to convert
#human-readable values for the 52 cards
#matches that of pypoker-eval
#humancards = []
#for suit in suits :
    #for num in [str(v) for v in range(2,10)] + ['T','J','Q','K','A'] :
        #humancards.append( str(num)+suit )
#WILDCARD 52
#humancards.append( '__' )
#WILDCARD 53
#humancards.append( 'x' )

suits = ('h','d','c','s')
pe = PokerEval()

#annoyingly, pokereval API doesn't give a way to do this
def getCardinality( card ) :
    if type(card) == int :
        return (card % 13)+2
    elif type(card) == str :
        return intifyCardinality(card[0])
    else :
        assert "go" == "fuck yourself"

#annoyingly, pokereval API doesn't give a way to do this
def getSuit( card ) :
    if type(card) == int :
        return suits[card / 13]
    elif type(card) == str :
        return card[1]
    else :
        assert "go" == "fuck yourself"

#convenience
def makeHuman( cards ) :
    #if already in right format, leave alone
    if type(cards[0]) == str : return cards
    r = []
    for c in cards :
        if c == globles.FOLDED : 
            r.append('x')
        else :
            r.append( pe.card2string(c) )
    return r

def makeMachine( cards ) :
    #if already in right format, leave alone
    if type(cards[0]) == int : return cards
    r = []
    for c in cards :
        if c == 'x' :
            r.append(globles.FOLDED)
        else :
            r.append( pe.string2card(c) )
    return r


CARDINALITIES = [str(v) for v in range(2,10)] + ['T','J','Q','K','A']
def stringifyCardinality( c ) :
    d = {}
    for i in range(2,15) :
        d[i] = CARDINALITIES[i-2]
    #d = {2:'2',3:'3',4:'4',5:'5',6:'6',7:'7',8:'8',9:'9', \
         #10:'T',11:'J',12:'Q',13:'K',14:'A'}
    return d[c]
def intifyCardinality( c ) :
    d = {}
    for i,card in enumerate(CARDINALITIES) :
        d[card] = i+2
    return d[c]

#return a comma separated list of human readable cards, sorted by numeric value
def canonical( cards ) :
    cards = makeMachine(cards)
    cards.sort()
    return ','.join( makeHuman(cards) )

#return the distinct type of hole card (1326 -> 169)
#hole_cards are [int,int]
def collapsePocket( hole_cards ) :
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

def collapseBoard( board ) :
    if len(board) == 3 :
        cardinalities = [getCardinality(c) for c in board]
        cardinalities.sort()
        num_cardinalities = len(set(cardinalities))
        if   num_cardinalities == 1 : rcard = 't'
        elif num_cardinalities == 2 : rcard = 'p'
        else :
            if cardinalities[0] + 2 == cardinalities[1] + 1 == cardinalities[2] :
                rcard = 's'
            else :
                rcard = 'h'


        suits = [getSuit(c) for c in board]
        num_suits = len(set(suits))
        if   num_suits == 1 : rsuit = '3f'
        elif num_suits == 2 : rsuit = '2f'
        else                : rsuit = 'r'

        return "%s%s%s" % (''.join([str(c) for c in cardinalities]), rcard, rsuit)
        #s3f  3-Straight-Flush = 12
        #t    Trips = 13
        #s2f 3-Straight 2-flush = 12 * 3 = 36
        #sr   3-Straight rainbow = 12
        #3f    3-Flush = c(13,3)-12 = 274
        #pr   Paired rainbow = 13 *12 = 156
        #p2f  Paired 2-flush = 13 * 12 = 156
        #h2f  High-Card-Flops 2-flush: [c(13,3)-12] * 3 = 822
        #hr   High-Card-Flops Rainbow: [c(13,3)-12] = 274
    elif len(board) == 4 : pass
    elif len(board) == 5 : pass
    else :
        pass

def computeBuckets( street ) :
    if street == 'flop' :
        for flop_file in os.listdir( "evdists/flops" ) :
            print flop_file
        pass
    elif street == 'turn' : pass
    elif street == 'river' : pass
    else : pass
#would be cool to stream possible hole card combinations given
#our best guess at each players holding distribution.  

class Deck:
    def __init__(self, set_of_cards=set(range(52)) ) :
        self.cards = set_of_cards
    
    def shuffle(self) :
        self.cards = set(range(52))

    #if all the cards are present to be be removed, do so and return True
    #if not, do not remove anything and return False
    def remove( self, cards ) :
        cards = makeMachine(cards)
        try :
            removed = []
            for c in cards : 
                if c < 52 :
                    self.cards.remove(c)
                    removed.append(c) 
            return True
        except KeyError as ve :
            self.replace( removed )
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

    print collapsePocket([25,51])
    print makeMachine(['2h','As'])

    print collapseFlop(['2d','3d','4d'])

if __name__ == '__main__' :
    main()
