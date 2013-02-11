BET_RATIOS = [0,.2,.3,.4,.5,.75,1]
BUCKET_PERCENTILES = {'flop' : [.4,.1,.1] + [.05]*4 + [.02]*10, \
                      'turn' : [.4,.1,.1] + [.05]*4 + [.02]*10, \
                      'river': [.45,.15,.14,.05,.05,.05,.05,.02,.02,.02] }

EVALUATOR = "pokereval"
GAME = 'holdem'
NA = 'xx'
if GAME == 'holdem' or GAME == 'omaha' :
    #STREET_NAMES = ["undealt","preflop","flop","turn","river","over"]
    STREET_NAMES = [-1,0,1,2,3,4]

if GAME == 'holdem' :
    POCKET_SIZE = 2

if EVALUATOR == 'pokereval' :
    #numerical rep of a folded card
    FOLDED = 254

    #numerical rep of an unknown
    WILDCARD = 255

    #Computed EV can range from from 0-1000
    EV_RANGE = 1000


def veryClose( a,b,p=.00001 ) :
    return abs(a-b) < p
