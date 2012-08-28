from mcts_test import MCTS_Test
from math import sqrt, log
from random import choice

#when rewards in range [0,1], not our case
Cp = 1 / sqrt(2)

NUM_PLAYERS = 1 
DOMAIN_NAME = 'TEST'


########################################################################
#####    DOMAIN SPECIFIC STUFF
########################################################################

if   DOMAIN_NAME == 'TEST'  :  DOMAIN = MCTS_Test()
elif DOMAIN_NAME == 'POKER' :  DOMAIN = MCTS_Poker()
elif DOMAIN_NAME == 'GO'    :  DOMAIN = MCTS_Go()


#########################################################################
###           DATA REP
#########################################################################
class Node :
    def __init__( self, parent, action ) :
        self.parent = parent
        self.visit_count = 0 
        self.total_rewards = [0]*NUM_PLAYERS
        #keyed by action
        self.children = {}
        self.action = action

        #auto mark the root
        if not self.parent :
            self.marked = True
            self.state = DOMAIN.root_state 
        else :
            self.state = DOMAIN.applyAction( getState(parent), action )
            self.marked = False

    def __str__(self) :
        derp = "State:" + str(self.state) + \
               " Marked:" + str(self.marked)
        return derp
#########################################################################
##### Interface to DATA REP
#########################################################################

def createNode( parent, action ) :
    child = Node( parent, action )
    if parent :
        parent.children[action] = child
    return child

def getTotalRewards( node ) :
    return node.total_rewards

def setTotalRewards( node, tr ) :
    node.total_rewards = tr

def getVisitCount( node ) :
    return node.visit_count

def setVisitCount( node, vc ) :
    node.visit_count = vc

def getState( node ) :
    return node.state

def getChildren( node ) :
    return node.children.values()

def getAction( node ) :
    return node.action

def mark( node ) :
    node.marked = True

def isMarked( node ) :
    return node.marked


########################################################################
#########  CORE
########################################################################

def uctsearch( state ) :
    root = createNode( parent=False, action=False )
    node = root

    time_left = True
    count = 0
    while count < 40000 :
        #print "\n====================================================="
        #print "uctsearch iteration %d" % count
        node = treePolicy( root )
        rewards = defaultPolicy( getState(node) )
        #print "rewards:", rewards
        backprop( node, rewards )
        #print "root", root
        count += 1

    for action in root.children :
        child = root.children[action]
        print "Action: ", action, "Total Rewards, Visit Count", getTotalRewards(child), getVisitCount(child)

    return getAction( bestChild( root, 0 ) )

def treePolicy( node ) :
    while isMarked( node ) and not DOMAIN.isTerminal( getState(node) ) :
        num_poss_actions = len( DOMAIN.getAllowableActions( getState(node) ) )
        num_children = len( getChildren(node) )
        assert num_children <= num_poss_actions
        fully_expanded = num_children == num_poss_actions

        if not fully_expanded :
            node = expand(node)
        else :
            node = bestChild( node, Cp )
    mark( node )
    return node

def expand( parent ) :
    tried = set(parent.children.keys())
    possible = set(DOMAIN.getAllowableActions( getState(parent) ))
    action = choice( list(possible-tried) ) 
    return createNode( parent, action )

def bestChild( parent, c, player_ix=0 ) :
    scores = []
    children = getChildren(parent)
    for child in children :
        creward = getTotalRewards(child)[player_ix]
        cvisit = getVisitCount(child)
        pvisit = getVisitCount(parent)
        exploitation = creward / cvisit 
        exploration = c*sqrt( 2*log( pvisit ) / cvisit )
        scores.append( exploitation + exploration )

    m = max(scores)
    return children[scores.index(m)]

def defaultPolicy( state ) :
    while not DOMAIN.isTerminal(state) :
        state = DOMAIN.applyAction( state, DOMAIN.chooseAction(state) )
    
    return DOMAIN.getRewards( state )

def backprop( node, rewards ) :
    while node :
        setVisitCount( node, getVisitCount(node)+1 )
        setTotalRewards( node, applySum( getTotalRewards(node), rewards ) )
        node = node.parent


############################################################################
########    HELPERS
############################################################################
    
def applySum( a,b ) :
    assert len(a) == len(b)
    return [a[i]+b[i] for i in range(len(a))]

def main() :
    action = uctsearch([])
    print action

if __name__ == '__main__' :
    main()
