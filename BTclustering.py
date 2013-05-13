import math
import simplejson as json
from yaml import load, dump
from time import time
import globles
from multiprocessing import Process, Queue, Pool
from random import sample, random
import numpy as np
import db
import myemd


#compute rows start-end_cboard_ix of the distance matrix for the appro street
#each row is the distance between that cboard and all greater than it
#build all n_bucket distance matrices at once
def parseAndNormalize( db_string, make_cdf = False ) :
    dist = []
    for c in db_string.split(';') :
        joints = [float(p) for p in c.split(',')]
        Z = sum(joints)
        if Z == 0 :
            normalized = [float(0)]*len(joints)
        else :
            normalized = [p / Z for p in joints]

        if not make_cdf :
            dist.append( normalized )
        else :
            dist.append( np.cumsum( normalized ) )
    return dist

def stringifyJoint( joint ) :
    r = []
    for row in joint :
        r.append( ",".join([str(t) for t in row]) )
    return ";".join( r )

def addJoints( joint1, joint2 ) :

    assert( len(joint1) == len(joint2) )
    for ix in range(len(joint1)) :
        for jx in range(len(joint1[ix])) :
            joint1[ix][jx] += joint2[ix][jx]

def averageJoint( joint, n ) :
    for ix in range(len(joint)) :
        for jx in range(len(joint[ix])) :
            joint[ix][jx] = round( joint[ix][jx] / float(n), 4 )


#WAY TOO SLOW, use Fast version.  Uses a close form from:
#http://www.cs.columbia.edu/~mmerler/project/code/pdist2.m
#assumes histograms have uniform weight
#sum(abs(cdf(x)-cdf(y)))
def avgEMD( data ) :
    (pinned_joint, compare_joint, F1, F2, streetp ) = data
    n_buckets = len(pinned_joint)
    z = 0
    for k in range(n_buckets) :
        dst = myemd.getBTDistance( streetp, \
                                   pinned_joint[k], \
                                   compare_joint[k], \
                                   F1, F2)
        z += dst
    return z / float(n_buckets)

def avgEMDFast( data ) :
    (pinned_cdfs, compare_cdfs ) = data
    n_buckets = len(pinned_cdfs)
    z = 0
    for k in range(n_buckets) :
        z += sum( [abs(p-c) for (p,c) in zip(pinned_cdfs[k], compare_cdfs[k] )] )
    return z / float(n_buckets)

def cdfEMD( data ) :
    (cdf1, cdf2) = data
    return sum( [abs(o-t) for (o,t) in zip(cdf1,cdf2)] )

#a Group needs to hold the distributinos of the members
#this way an average can be computed when distances need to be compared
#while also allowing new members to be admitted
class Group :
    def __inti__(self) :
        pass


def computeDistances( conn, street, streetp ) :
    n_buckets = len(globles.BUCKET_PERCENTILES[street])
    n_bucketsp = len(globles.BUCKET_PERCENTILES[streetp])
    F1 = [(1,i) for i in range(n_bucketsp)]
    F2 = [(1,i) for i in range(n_bucketsp)]

    #q = """select count(*)
           #from TRANSITIONS_%s""" % (streetp.upper())
    #n_cboards = conn.queryScalar( q, int )
    groups = {}
    #just_changed = set([])

    q = """select cboards, dist
           from TRANSITIONS_%s
           order by id 
           """ % (streetp.upper())

    rows = conn.query(q)
    n_cboards = len(rows)
    remaining_group_ids = set(range(n_cboards))
    remaining_unexamined_ids = set(range(n_cboards))

    all_cboards = [row[0] for row in rows]
    print "parse,normalize,make CDF starting"
    joints = [parseAndNormalize( row[1] ) for row in rows]
    #for row in joints[0] :
        #print row
        #assert( sum(row) > .99 and sum(row) < 1.01)
    cdfs = [parseAndNormalize( row[1], make_cdf=True) for row in rows]

    num_threads = 8
    p = Pool(processes=num_threads)

    thresh = .45
    k = 0

    num_under_thresh = 0
    while len(remaining_unexamined_ids) > 0 :
        print "\n\nnew iteration!"

        #randomly select the element/group to act as a reference
        #TODO: only select from singletons?  being able to merge groups
        #could get dangerous, could keep averaging so that they keep
        #blobbing together?
        pinned_id = sample( remaining_unexamined_ids, 1 )[0]
        remaining_unexamined_ids.remove(pinned_id)
        pinned_cboards = all_cboards[pinned_id]
        pinned_joint = cdfs[pinned_id]

        print "pinned id: ", pinned_id
        print "pinned cboard:", pinned_cboards

        #one to one correspondence between these:
        #datas holds the (joint1,joint2) pairs whose distance is TBC
        #global_ids holds the absolute index of joint2 in terms of 
        #placement in full ordering by SQL query (by DB "id" field)
        datas = []
        global_ids = []
        for ID in range(n_cboards) :
            if ID in remaining_group_ids and ID != pinned_id :
                datas.append( (pinned_joint, cdfs[ID]) )
                global_ids.append(ID)

        print "len datas", len(datas)

        group = [pinned_id]
        dists = p.map( avgEMDFast, datas )
        for ID, dist in zip(global_ids, dists) :
            if dist<thresh :
                #TODO, if a group gets appended to, extended to, etc
                #mark its joint as needing to be recomputed
                #else, we can just use the value from last time
                if ID in groups :
                    print "CLOSE TO A GROUP, MERGING"
                    group.extend( groups[ID] )
                    del groups[ID]
                else:
                    group.append( ID )

                #just_changed.add(pinned_id)
                if ID in remaining_unexamined_ids :
                    remaining_unexamined_ids.remove(ID)

                remaining_group_ids.remove(ID)


        groups[pinned_id] = group
        print "len group: ", len(group)
        print "remaining unexamined", len(remaining_unexamined_ids)

        #if a new member member(s) got added to it last time
        #recompute the working CDF
        ID = pinned_id
        print "recomputing CDF for ID:", ID
        #setup an empty joint into which to add up and average values
        avg_joint = []
        for dummy in range(n_buckets) :
            avg_joint.append([0]*n_bucketsp)
        for member_id in groups[ID] :
            addJoints( avg_joint, joints[member_id] )
        averageJoint( avg_joint, len(groups[ID]) )

        cdfs[ID] = [np.cumsum(c) for c in avg_joint]


    #end while len(remaining_unexaminde) > 0

    for group_id in groups :
        print "\n\nGroup: ", group_id
        print len(groups[group_id])

        avg_joint = []
        for dummy in range(n_buckets) :
            avg_joint.append([0]*n_bucketsp)
        for member_id in groups[group_id] :
            addJoints( avg_joint, joints[member_id] )
        averageJoint( avg_joint, len(groups[group_id]) )
        #for hist in avg_joint :
            #print hist

        for ID in groups[group_id] :
            conn.insert( "CLUSTER_MAP_%s" % streetp.upper(), \
                         [all_cboards[ID], group_id] )
            #print "    ", all_cboards[ID]
        conn.insert( "CLUSTERS_%s" % streetp.upper(), \
                     [group_id, stringifyJoint(avg_joint)] )

    print  "ngroups:" , len(groups)

    #average group sizes
    #print out groups in some fashion( if do IDs, remember +1 to make it jive
    #with DB ordering
    #want a reverse lookup:
        #cboards : group_id
    #then another table with group_id: joint

    #print "avg nut:", num_under_thresh / float(len(joints))

def printTransitions( conn, street, streetp ) :
    q = """select id, cboards, dist
           from TRANSITIONS_%s
           order by id""" % (streetp.upper())
    rows = conn.query( q )
    fout = open( "joints.txt", 'w' )
    for row in rows :
        fout.write( row[2] + "\n" )
    fout.close()

def distBetween( conn, cboards1, cboards2, street, streetp  ) :
    n_buckets = len(globles.BUCKET_PERCENTILES[street])
    n_bucketsp = len(globles.BUCKET_PERCENTILES[streetp])
    F1 = [(1,i) for i in range(n_bucketsp)]
    F2 = [(1,i) for i in range(n_bucketsp)]

    q1 =  """select dist 
             from TRANSITIONS_%s
             where cboards = '%s' """ % (streetp.upper(), cboards1 )
    q2 = """select dist 
            from TRANSITIONS_%s
            where cboards = '%s' """ % (streetp.upper(), cboards2 )

    joint1 = parseAndNormalize( conn.queryScalar( q1, str ) )
    joint2 = parseAndNormalize( conn.queryScalar( q2, str ) )

    print avgEMD( (joint1, joint2, F1, F2, streetp ) )

def iterateDistances( street, streetp, k ) :
    q = """select distances
           from DISTANCES_%s
           where k = %d
           order by cboards""" % (streetp.upper(), k)
    rows = conn.query(q)
    last_len = -1
    for row in rows :
        distances = [float(p) for p in row.split(',')]
        this_len = len(row.split(','))
        if last_len != -1 :
            assert this_len == last_len - 1
        last_len = this_len

        #for distance in distances :
            #yield distance

if __name__ == '__main__' :
    conn = db.Conn("localhost")
    #computeDistances( conn, "preflop", "flop" )
    computeDistances( conn, "flop", "turn" )
