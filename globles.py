EVALUATOR = "pokereval"
GAME = 'holdem'
NA = 'xx'
if GAME == 'holdem' or GAME == 'omaha' :
    STREET_NAMES = ["undealt","preflop","flop","turn","river"]

if GAME == 'holdem' :
    POCKET_SIZE = 2

if EVALUATOR == 'pokereval' :
    #numerical rep of a folded card
    FOLDED = 254

    #numerical rep of an unknown
    WILDCARD = 255

    #Computed EV can range from from 0-1000
    EV_RANGE = 1000

