from mcts_test import MCTS_Test
from mcts_go import MCTS_Go
from math import sqrt, log
from random import choice

#when rewards in range [0,1], not our case
Cp = 1 / sqrt(2)

NUM_PLAYERS = 2 
DOMAIN_NAME = 'GO'


########################################################################
#####    DOMAIN SPECIFIC STUFF
########################################################################

if   DOMAIN_NAME == 'TEST'  :  DOMAIN = MCTS_Test()
elif DOMAIN_NAME == 'POKER' :  DOMAIN = MCTS_Poker()
elif DOMAIN_NAME == 'GO'    :  DOMAIN = MCTS_Go(4)


#########################################################################
###           DATA REP
#########################################################################
#TODO
#give every node a list of possible actions at creation
#recomputing every time is wasteful
class Node :
    def __init__( self, parent, action ) :
        self.parent = parent
        self.visit_count = 0 
        self.total_rewards = [0]*NUM_PLAYERS
        #keyed by action
        self.children = {}
        self.action = action
        self.possible_actions = []

        #auto mark the root
        self.marked = not self.parent

    def __str__(self) :
        derp = " Marked: " + str(self.marked)
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

#def getState( node ) :
    #if not node.parent :
        #return DOMAIN.getRootState()
    #else :
        #return DOMAIN.applyAction( getState(node.parent), node.action )
    #return node.state

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

def uctsearch( root_state ) :
    root = createNode( parent=False, action=False )
    node = root

    time_left = True
    count = 0
    print "root_state", root_state
    while count < 4 :
        print "\n====================================================="
        print "uctsearch iteration %d" % count
        node,state = treePolicy( root, DOMAIN.copyState(root_state) )
        rewards = defaultPolicy( state ) #getState(node) )
        print "rewards:", rewards
        backprop( node, rewards )
        count += 1

    for action in root.children :
        child = root.children[action]
        print "Action: ", action, "Total Rewards, Visit Count", getTotalRewards(child), getVisitCount(child)

    bnode, bstate = bestChild( root, root_state, 0 )
    return getAction( bnode )

def treePolicy( node, state ) :
    print "tp, incoming state", state
    print "is terminal: ", DOMAIN.isTerminal(state)
    while isMarked( node ) and not DOMAIN.isTerminal( state ) : 
        num_allowable = len( DOMAIN.getAllowableActions( state ) ) 
        num_tried = len( getChildren(node) )
        assert num_tried <= num_allowable
        fully_expanded = num_tried == num_allowable

        #TODO: DOMAIN.isChanceAction(state)
        #for poker we treat opp choice nodes as chance, right?
        #because don't know hole cards
        if True :
            if not fully_expanded :
                node,state = expand(node,state)
            else :
                node,state = bestChild( node, state, Cp )
        else :
            pass


        print "Chosen:", node.action, state
    mark( node )
    #print "tp, outgoing state: ", state
    return [node,state]

#SIDE EFFECT: updates pstate
def expand( parent, pstate ) :
    allowable = set(DOMAIN.getAllowableActions( pstate ))
    tried = set(parent.children.keys())
    action = choice( list(allowable-tried) ) 
    DOMAIN.applyAction( pstate, action )
    node = createNode( parent, action )
    return [node,pstate]

def bestChild( parent, pstate, c, player_ix=0 ) :
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
    ix = scores.index(m)
    node = children[ix]
    DOMAIN.applyAction( pstate, node.action )
    return [node,pstate]

def defaultPolicy( state ) :
    while not DOMAIN.isTerminal(state) :
        DOMAIN.applyAction( state, DOMAIN.randomAction(state) )
        #DOMAIN.applyRandomAction( state )
        print "simulation state:\n", state
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
    action = uctsearch( DOMAIN.root_state )
    #print action

if __name__ == '__main__' :
    main()
