from mcts_test import MCTS_Test
from mcts_go import MCTS_Go
from mcts_poker import MCTS_Poker
from math import sqrt, log
from random import choice

NUM_PLAYERS = 2 
DOMAIN_NAME = 'POKER'

if   DOMAIN_NAME == 'TEST'  :  
    DOMAIN = MCTS_Test()
    Cp = 1
elif DOMAIN_NAME == 'POKER' :  
    DOMAIN = MCTS_Poker()
    Cp = 2
elif DOMAIN_NAME == 'GO'    :  
    DOMAIN = MCTS_Go(4)
    Cp = 1 / sqrt(2)


#########################################################################
###           DATA REP
#########################################################################
class Node :
    def __init__( self, parent, action, kind ) :
        self.parent = parent
        self.visit_count = 0 
        self.total_rewards = [0]*NUM_PLAYERS
        #keyed by action
        self.children = {}
        self.action = action
        self.value = 0
        self.fully_expanded = False

        self.kind = kind

        #auto mark the root
        self.marked = not self.parent

    def __str__(self) :
        derp = " Marked: " + str(self.marked)
        return derp
#########################################################################
##### Interface to DATA REP
#########################################################################

def createNode( parent, action, kind ) :
    child = Node( parent, action, kind )
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

def search( root_state ) :
    assert not DOMIAN.isChanceAction(root_state)
    root = createNode( parent=False, action=False, kind='decision' )
    node = root

    time_left = True
    count = 0
    #print "root_state", root_state
    while count < 1000 :
        #print "\n====================================================="
        #print "search iteration %d" % count
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
        print "Action: ", action, \
               "Rewards: ", [round(s,2) for s in getTotalRewards(child)], \
               "Visit Count:", getVisitCount(child), \
               "Score: ", round( scoreNode(child, \
                                           root, \
                                           DOMAIN.getPlayerIx(root_state), \
                                           debug=False), 2 )

        #a = raw_input()

    bnode = bestChild( root, \
                       root_state, \
                       player_ix=DOMAIN.getPlayerIx(root_state) )

    return getAction( bnode )

def treePolicy( node, state ) :
    return uctPolicy( node, state )

def randomPolicy( node, state ) :
    pass

def uctPolicy( node, state ) :
    #print "tp, incoming state", state
    #print "is terminal: ", DOMAIN.isTerminal(state)
    while isMarked( node ) and not DOMAIN.isTerminal( state ) : 
        
        tried = node.children.keys()
        action = DOMAIN.randomAction( state, to_exclude=tried )
        if not DOMAIN.isChanceAction(state) :
            #TODO: dont' like this convolution of MCTS and domain
            #domain should care nothing about fully expanded or not
            #came about from slowness of getPossibleActions for Go

            if not DOMAIN.fullyExpanded( action ):
                #print "expanding"
                node = expand(node,state,action)
            else :
                #print "besting"
                node.fully_expanded = True
                node = bestChild( node, state, \
                                  player_ix=DOMAIN.getPlayerIx(state) )
        else :
            DOMAIN.applyAction( state, action )
            if action in node.children.keys() :
                node = node.children[action]
            else :
                node = createNode( node, action, kind='chance' )


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
    node = createNode( parent, action, kind='decision' )
    return node

def scoreNode( state, node, parent, player_ix, c=Cp, debug=False ) :
    creward = getTotalRewards(node)[player_ix]
    cvisit = getVisitCount(node)
    pvisit = getVisitCount(parent)
    exploitation = creward / float(cvisit)
    exploration = c*sqrt( 2*log( pvisit ) / cvisit )
    if debug :
        print "exploration:", exploration
        print "exploitation:", exploitation
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
        if DOMAIN_NAME == 'GO' and count > state.dim^2 * 100 :
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
        if node.kind == 'decision' :
            #TODO replace with fancy pants model? Below is the old way
            setTotalRewards( node, applySum( getTotalRewards(node), rewards ) )
        elif node.kind == 'chance' :
            children = getChilren(node)
            if len(node.children) > 0 :
                value_est = 0
                for child in children :
                    sample_freq =        getVisitCount( child ) / \
                                  float( getVisitCount( node  ) )
                    #TODO
                    #getValue will return an array of values
                    #want to map *
                    value_est += getValue(child) * sample_freq
                setTotalRewards( node, value_est )
            else :
                #we just expanded to this node (it's a sim-leaf),
                #so all we have is the one value
                setTotalRewardes( node, rewards )
        else :
            assert False
        
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
       
    if DOMAIN_NAME == 'POKER' :
        state = DOMAIN.start_state
        while not DOMAIN.isTerminal( state ) :
            print state
            if DOMAIN.isChanceAction(state) :
                print "is chance"
                action = DOMAIN.randomAction(state)
                DOMAIN.applyAction( state, action )
            else :
                print "searching"
                #a = raw_input('-->')
                action = search( state )
            
            print "action: ", action
            print "\n"
            a = raw_input('-->')

        print "rewards",  DOMAIN.getRewards( state )
    
    if DOMAIN_NAME == 'GO' :
        state = DOMAIN.start_state
        while not DOMAIN.isTerminal( state ) :
            print state
            #a = raw_input('-->')
            action = search( state )
            print "action: ", action
            print "\n"
            a = raw_input('-->')

        print "rewards",  DOMAIN.getRewards( state )


if __name__ == '__main__' :
    main()
