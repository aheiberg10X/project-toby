from itertools import combinations
from random import sample
from pokereval import PokerEval
import globles
import re

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

#take integers and output card string
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

#take strings and output card number
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
def canonicalize( cards ) :
    cards = makeMachine(cards)
    cards.sort()
    return ''.join( makeHuman(cards) )

suit_split = re.compile(r'([hsdc])')
def deCanonicalize( card_string ) :
    if card_string.startswith('d') : card_string = card_string[1:]
    splt = suit_split.split( card_string )[:-1]
    return [ "%s%s" % (splt[i],splt[i+1]) \
             for i \
             in range(0,len(splt),2) ]


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

#TODO
#To be continued???
#def numPocketsMakeStraight( sorted_cardinalities ) :
    #values = []
    #counts = {}
    #l = len(sorted_cardinalities)
    #max_count = 0
    #max_value = -1
    #for i,c in enumerate(sorted_cardinalities) :
        #v = c+l-i
        #if v in counts :
            #counts[v] += 1
        #else :
            #counts[v] = 1
        #if counts[v] >= max_count :
            #max_count = counts[v]
            #max_value = v
        #values.append( v )
#
    #print max_value
    #print max_count
#
    ##put a hole on the beginning and end
    #holes = [0]*2 + map( lambda x : x == max_value, values ) + [0]*2


def isStraight( sorted_cardinalities ) :
    if sorted_cardinalities[-1] == 14 :
        if isStraight( [1] + sorted_cardinalities[0:-1] ) :
            return True
      
    value = -1
    l = len(sorted_cardinalities) - 1
    for i,c in enumerate(sorted_cardinalities) :
        i = l - i
        if value == -1 :
            value = i+c
        else :
            if not i+c == value : return False
    return True

#def flushString( suits ) :
    #l = len(suits)
    #combinations( range(l), 


def collapseBoard( board ) :
    board = truncate(board)
    board = sorted(board, key=lambda c : getCardinality(c))

    cardinalities = [getCardinality(c) for c in board]
    card_counts = {}
    for c in cardinalities :
        if c in card_counts :
            card_counts[c] += 1
        else :
            card_counts[c] = 1
    #cardinalities.sort()
    num_cardinalities = len(card_counts.keys()) #set(cardinalities))
    
    suits = [getSuit(c) for c in board]
    num_suits = len(set(suits))
    if len(board) == 3 :
        if   num_cardinalities == 1 : rcard = 't'
        elif num_cardinalities == 2 : rcard = 'p'
        else :
            if isStraight(cardinalities) : rcard = 's'
            else :                         rcard = 'h'

        if   num_suits == 1 : rsuit = '3f'
        elif num_suits == 2 : 
            if rcard == 'p' :
                rsuit = '2f'
            else :
                if   suits[0] == suits[1] : rsuit = '2fxxo'
                elif suits[0] == suits[2] : rsuit = '2fxox'
                elif suits[1] == suits[2] : rsuit = '2foxx'
                else : assert False
        else                : rsuit = 'r'

        #s3f  3-Straight-Flush = 12
        #t    Trips = 13
        #s2f 3-Straight 2-flush = 12 * 3 = 36
        #sr   3-Straight rainbow = 12
        #3f    3-Flush = c(13,3)-12 = 274
        #pr   Paired rainbow = 13 *12 = 156
        #p2f  Paired 2-flush = 13 * 12 = 156
        #h2f  High-Card-Flops 2-flush: [c(13,3)-12] * 3 = 822
        #hr   High-Card-Flops Rainbow: [c(13,3)-12] = 274
    elif len(board) == 4 : 
        if   num_cardinalities == 1 : rcard = 'q'
        elif num_cardinalities == 2 : 
            counts = list(card_counts.values())
            if counts[0] == counts[1] == 2 :
                rcard = '2p'
            else :
                rcard = 't'
        elif num_cardinalities == 3 :
            rcard = 'p'
        else :
            if isStraight(cardinalities) : rcard = 's'
            else :                         rcard = 'h'

        if   num_suits == 1 : rsuit = '4f'
        elif num_suits == 2 : 
            #impossible with: quads, trips
            if rcard == 'p' :
                rsuit = '3f'
            elif rcard == '2p' :
                rsuit = '22f'
            elif rcard == 'h' or rcard == 's' : 
                if   suits[0] == suits[1] == suits[2] : rsuit = '3fxxxo'
                elif suits[0] == suits[1] == suits[3] : rsuit = '3fxxox'
                elif suits[0] == suits[2] == suits[3] : rsuit = '3fxoxx'
                elif suits[1] == suits[2] == suits[3] : rsuit = '3foxxx'
                elif suits[0] == suits[1] and suits[2] == suits[3] :
                    rsuit = '22fxxoo'
                elif suits[0] == suits[2] and suits[1] == suits[3] :
                    rsuit = '22fxoxo'
                elif suits[0] == suits[3] and suits[1] == suits[2] :
                    rsuit = '22fxoox'
                else :
                    print suits
                    assert False
            else :
                print rcard
                assert False
        elif num_suits == 3 :
            if rcard == 'p' or rcard == 'h' or rcard == 's' :
                if   suits[0] == suits[1] : temp = 'xxoo'
                elif suits[0] == suits[2] : temp = 'xoxo'
                elif suits[0] == suits[3] : temp = 'xoox'
                elif suits[1] == suits[2] : temp = 'oxxo'
                elif suits[1] == suits[3] : temp = 'oxox'
                elif suits[2] == suits[3] : temp = 'ooxx'
                else : assert False

                if rcard == 'p' :
                    for c in card_counts :
                        if card_counts[c] == 2 :
                            ix = cardinalities.index(c)
                    sub = temp[ix:ix+2]
                    if sub == 'ox' or sub == 'xo' :
                        temp = temp[:ix] + 'x' + temp[ix+2:]
                    elif sub == 'oo' :
                        temp = temp[:ix] + 'o' + temp[ix+2:]
                    else :
                        assert False

                rsuit = '2f' + temp

            elif rcard == '2p' :
                rsuit = '2f'
            elif rcard == 't' :
                rsuit = '2f'
            elif rcard == 'h' :
                pass
            else : 
                print rcard
                assert False
        else                : rsuit = 'r'

    elif len(board) == 5 : 
        if   num_cardinalities == 1 : 
            assert False
        elif num_cardinalities == 2 : 
            if max( card_counts.values() ) == 3 :
                rcard = 'b'#oat
            else :
                rcard = 'q'
        elif num_cardinalities == 3 : 
            if max( card_counts.values() ) == 2 :
                rcard = '2p'
            else :
                rcard = 't'
        elif num_cardinalities == 4 : 
            rcard = 'p'
        elif num_cardinalities == 5 :
            if isStraight(cardinalities) : rcard = 's'
            else                         : rcard = 'h'

        if num_suits == 1 :
            rsuit = '5f'
        elif num_suits == 2 :
            if rcard == 'p' :
                rsuit = '4f' 
            else :
                assert False

        elif num_suits == 3 :
            if rcard == 'p' :
                pass
            elif rcard == '2p' :
                pass
            elif rcard == 't' :
                rsuit = '3f' 
            elif rcard == 'b' :
                rsuit = ""
            else :
                assert False

        elif num_suits == 4 :
            rsuit = ""
        else :
            assert False
    else :
        pass

    crdnlts = ''.join([stringifyCardinality(c) for c in cardinalities])
    return "%s_%s_%s" % (crdnlts, rcard, rsuit)

def getStreet( board ) :
    num_unknown = sum([c == '__' for c in board])
    if   num_unknown == 5 : return 'preflop'
    elif num_unknown == 2 : return 'flop'
    elif num_unknown == 1 : return 'turn'
    elif num_unknown == 0 : return 'river'

def truncate( board ) :
    try :
        return board[0:board.index('__')]
    except ValueError :
        return board
 
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
    #d = Deck()
    #d.remove([1,2,3])
    #d.remove([4,1])
#
    #print collapsePocket([25,51])
    #print makeMachine(['2h','As'])
    #print numPocketsMakeStraight([10,13,14])
    #print collapseBoard(['3d','7c','7s','7h'])
    print deCanonical( '3d8cTs' )

if __name__ == '__main__' :
    main()
