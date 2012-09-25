from mcts_test import MCTS_Test
from mcts_go import MCTS_Go
from math import sqrt, log
from random import choice

#when rewards in range [0,1], not our case
Cp = 1 / sqrt(2)
NUM_PLAYERS = 2 
DOMAIN_NAME = 'GO'

if   DOMAIN_NAME == 'TEST'  :  DOMAIN = MCTS_Test()
elif DOMAIN_NAME == 'POKER' :  DOMAIN = MCTS_Poker()
elif DOMAIN_NAME == 'GO'    :  DOMAIN = MCTS_Go(6)


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
    #print "root_state", root_state
    while count < 2 :
        #print "\n====================================================="
        #print "uctsearch iteration %d" % count
        state = DOMAIN.copyState(root_state)
        #print "state before tree policy", state
        #for ix in range(len(DOMAIN.states)) :
            #print "\npast_state", ix
            #print DOMAIN.states[ix]
        node = treePolicy( root, state )
        #print "state after tree policy", state
        rewards = defaultPolicy( state ) #getState(node) )
        #print "state after defaultPolicy", state
        backprop( node, rewards )
        count += 1

    for action in root.children :
        child = root.children[action]
        print "Action: ", action, "Total Rewards, Visit Count", getTotalRewards(child), getVisitCount(child), "Score: ", scoreNode(child, root, DOMAIN.getPlayerIx(root_state) )

        #a = raw_input()

    bnode = bestChild( root, root_state, 0 )
    return getAction( bnode )

def treePolicy( node, state ) :
    #print "tp, incoming state", state
    #print "is terminal: ", DOMAIN.isTerminal(state)
    while isMarked( node ) and not DOMAIN.isTerminal( state ) : 
        
        tried = node.children.keys()
        action = DOMAIN.randomAction( state, to_exclude=tried )
        if not DOMAIN.isChanceAction(state) :
            #TODO: if action is PASS, can't go to bestChild because
            #there is nothing to choose from
            #But using the 0 action as False to expand was a mistake
            if not DOMAIN.fullyExpanded( action ):
                #print "expanding"
                node = expand(node,state,action)
            else :
                #print "besting"
                node = bestChild( node, state, \
                                  player_ix=DOMAIN.getPlayerIx(state) )
        else :
            DOMAIN.applyAction( state, action )
            if action in node.children.keys() :
                node = node.children[action]
            else :
                node = createNode( node, action )


        #print "Chosen:", node.action, state
    mark( node )
    #print "tp, outgoing state: ", state
    return node

#SIDE EFFECT: updates pstate
def expand( parent, pstate, action ) :
    #allowable = set(DOMAIN.getAllowableActions( pstate ))
    #tried = set(parent.children.keys())
    #action = choice( list(allowable-tried) ) 
    DOMAIN.applyAction( pstate, action )
    node = createNode( parent, action )
    return node

def scoreNode( node, parent, player_ix, c=Cp ) :
    creward = getTotalRewards(node)[player_ix]
    cvisit = getVisitCount(node)
    pvisit = getVisitCount(parent)
    exploitation = creward / cvisit 
    exploration = c*sqrt( 2*log( pvisit ) / cvisit )
    return exploitation + exploration

def bestChild( parent, pstate, player_ix=0 ) :
    scores = []
    children = getChildren(parent)
    #if len(childen) == 0 :
        #print "children keys", parent.children.keys()
        #print "getChildren", children
        #raise Exception("no children in bestChild")
    for child in children :
        scores.append( scoreNode(child,parent,player_ix) )

    if len(scores) == 0 :
        print "children", children
        raise Exception("wtf scores")
    #TODO: randoly select from tie set
    m = max(scores)

    ix = scores.index(m)
    node = children[ix]
    DOMAIN.applyAction( pstate, node.action )
    return node

def defaultPolicy( state ) :
    count = 0
    while not DOMAIN.isTerminal(state) :
        #TODO: this is hacky
        if count > state.dim^2 * 100 :
            print "probably in loop somehow"
            break
        DOMAIN.applyAction( state, DOMAIN.randomAction(state) )
        count += 1
        #DOMAIN.applyRandomAction( state )
        #print "simulation state:\n", state
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

############################################################################
########   Client
############################################################################


def main() :
       
    state = DOMAIN.start_state
    while not DOMAIN.isTerminal( state ) :
        print state
        #a = raw_input('-->')
        action = uctsearch( state )
        print "action: ", action
        print "\n"


if __name__ == '__main__' :
    main()
