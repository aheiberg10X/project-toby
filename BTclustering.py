import math
import simplejson as json
from yaml import load, dump
from time import time
import globles
from multiprocessing import Process, Queue, Pool
from random import sample, random, seed
import numpy as np
import db
import myemd

#take a joint distibutino string (prob from database) and turn it into a 
#P(k,k'|b') = float[k][k'] 
def parse_old( db_string ) :
    joint = []
    for c in db_string.split(';') :
        joint.append( [float(p) for p in c.split(',')] )
    return joint

def parse( db_string ) :
    joint = []
    for c in db_string.split(';') :
        for p in c.split(',') :
            joint.append( float(p) )
    return joint

#usually don't care about joint, rather conditional P(k'|k,b')
#normalize each row of the joint
def normalize( joint, make_cdf=False ) :
    njoint = []
    for row in joint :
        Z = sum(row)
        if Z == 0 :
            normalized = [float(0)]*len(row)
        else :
            normalized = [p / Z for p in row]

        if not make_cdf :
            njoint.append( normalized )
        else :
            njoint.append( np.cumsum( normalized ) )
    return njoint

#turn a float[][] back into a string
def stringifyJoint( joint, n_bucketsp ) :
    rows = []
    row = []
    row_count = 0
    for p in joint :
        row.append( str(p) )
        row_count += 1
        if row_count == n_bucketsp :
            rows.append( ",".join(row) )
            row = []
            row_count = 0
    return ";".join(rows)

def stringifyJoint_old( joint ) :
    r = []
    for row in joint :
        r.append( ",".join([str(t) for t in row]) )
    return ";".join( r )

#add two float[][] together, putting the new values back in joint1
def addJoints( joint1, joint2 ) :
    assert( len(joint1) == len(joint2) )
    for ix in range(len(joint1)) :
        joint1[ix] += joint2[ix]

def addJoints_old( joint1, joint2 ) :
    assert( len(joint1) == len(joint2) )
    for ix in range(len(joint1)) :
        for jx in range(len(joint1[ix])) :
            joint1[ix][jx] += joint2[ix][jx]

#divide each term in float[][] by n, putting the result back into joint
def averageJoint( joint, n ) :
    for ix in range(len(joint)) :
        joint[ix] = joint[ix] / n

def averageJoint_old( joint, n ) :
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

#TODO: want to weight each Z by the avg marginal probability of being in k
#that is, still normalize, cdf-ize to utilize the closed form
#but want data to consist of both joints, so the avg prob of being in bucket
#k to being with can be obtained.  Then, EMD distance will contribute to the 
#total difference ....
#BETTER YET:  just unroll each joint as a one dimensional instead.  Apply CDF,
#and use fastEMD approach.  In this way, no weighting and/or marginalizing 
#is necessary
def avgEMDFast_old( data ) :
    (pinned_cdfs, compare_cdfs ) = data
    n_buckets = len(pinned_cdfs)
    z = 0
    for k in range(n_buckets) :
        z += sum( [abs(p-c) for (p,c) in zip(pinned_cdfs[k], compare_cdfs[k] )] )
    return z / float(n_buckets)

def cdfEMD( data ) :
    (cdf1, cdf2) = data
    return sum( [abs(o-t) for (o,t) in zip(cdf1,cdf2)] )

#cluster the P(k',k|cboards) joints in TRANSITION_X tables
def clusterJoints( conn, street, streetp ) :
    seed()
    n_buckets = len(globles.BUCKET_PERCENTILES[street])
    n_bucketsp = len(globles.BUCKET_PERCENTILES[streetp])
    F1 = [(1,i) for i in range(n_bucketsp)]
    F2 = [(1,i) for i in range(n_bucketsp)]

    #each transition will be handled via it ID
    #clusters will be {ID*: [ID*,ID1,ID2,...]} 
    clusters = {}

    q = """select cboards, dist
           from TRANSITIONS_%s
           order by id 
           """ % (streetp.upper())

    rows = conn.query(q)
    n_cboards = len(rows)

    #to start, every transition is in its own cluster
    remaining_cluster_ids = set(range(n_cboards))
    #for expediency, will only look at each cluster once
    remaining_unexamined_ids = set(range(n_cboards))

    #the cboard identifiers for each ID
    all_cboards = [row[0] for row in rows]

    print "parse,normalize,make CDF starting"
    #will precompute the normalized cdfs for each transitions joint prob
    #TODO: see avgEMDFast
    joints = [parse( row[1] ) for row in rows]
    cdfs = [np.cumsum(joint) for joint in joints]
    #used parse_old
    #cdfs = [ normalize( joint, make_cdf=True ) for joint in joints ]

    num_threads = 8
    p = Pool(processes=num_threads)

    #the threshhold for clustering, under which we consider to joint 
    #probabilities to be the same
    thresh = .45

    #TODO
    #make this its own function???
    #want to reues to cluster again on k= level
    while len(remaining_unexamined_ids) > 0 :
        print "\n\nnew iteration!"

        #randomly select the element/group to act as a reference
        #TODO: only select from singletons?  being able to merge groups
        #could get dangerous, could keep averaging so that they keep
        #blobbing together?
        pinned_id = sample( remaining_unexamined_ids, 1 )[0]
        remaining_unexamined_ids.remove(pinned_id)
        pinned_cboards = all_cboards[pinned_id]
        pinned_cdf = cdfs[pinned_id]

        print "pinned id: ", pinned_id
        print "pinned cboard:", pinned_cboards

        #one to one correspondence between these:
        #datas holds the (joint1,joint2) pairs whose distance is TBC
        #global_ids holds the absolute index of joint2 in terms of 
        #placement in full ordering by SQL query (by DB "id" field)
        datas = []
        global_ids = []
        for ID in range(n_cboards) :
            if ID in remaining_cluster_ids and ID != pinned_id :
                datas.append( (pinned_cdf, cdfs[ID]) )
                global_ids.append(ID)

        print "len datas", len(datas)

        #find other joints/clusters which are also close
        cluster = [pinned_id]
        dists = p.map( cdfEMD, datas )
        #dists = p.map( avgEMDFast, datas )
        for ID, dist in zip(global_ids, dists) :
            if dist<thresh :
                if ID in clusters :
                    print "CLOSE TO A GROUP, MERGING"
                    cluster.extend( clusters[ID] )
                    del clusters[ID]
                else:
                    cluster.append( ID )

                if ID in remaining_unexamined_ids :
                    remaining_unexamined_ids.remove(ID)

                remaining_cluster_ids.remove(ID)


        clusters[pinned_id] = cluster 
        print "size cluster: ", len(cluster)
        print "remaining unexamined", len(remaining_unexamined_ids)

        #if a new member member(s) got added to it last time
        #recompute the working CDF
        print "recomputing CDF for pinned_id:", pinned_id
        #setup an empty joint into which to add up and average values
        #avg_joint = []
        #for dummy in range(n_buckets) :
            #avg_joint.append([0]*n_bucketsp)
        avg_joint = [0]*(n_bucketsp*n_buckets)
        for member_id in clusters[pinned_id] :
            addJoints( avg_joint, joints[member_id] )
        averageJoint( avg_joint, len(clusters[pinned_id]) )

        #cdfs[pinned_id] = normalize( avg_joint, make_cdf=True )
        cdfs[pinned_id] = np.cumsum(avg_joint)


    #end while len(remaining_unexaminde) > 0

    #insert computed groups into the DB
    db_cluster_id = 1
    for cluster_id in clusters :
        print "\n\nGroup: ", cluster_id
        print len(clusters[cluster_id])

        #avg_joint = []
        #for dummy in range(n_buckets) :
            #avg_joint.append([0]*n_bucketsp)
        avg_joint = [0]*(n_bucketsp*n_buckets)
        for member_id in clusters[cluster_id] :
            addJoints( avg_joint, joints[member_id] )
        averageJoint( avg_joint, len(clusters[cluster_id]) )
        #for hist in avg_joint :
            #print hist

        for ID in clusters[cluster_id] :
            #print "    ", all_cboards[ID]

            #plus one is a BIG DEAL.  Python uses 0-index, DB starts auto-inc
            #from 1
            conn.insert( "CLUSTER_MAP_%s" % streetp.upper(), \
                         [all_cboards[ID], ID+1, db_cluster_id] )

        conn.insert( "CLUSTERS_%s" % streetp.upper(), \
                     [db_cluster_id, stringifyJoint(avg_joint,n_bucketsp)] )
        db_cluster_id += 1

    print  "nclusters:" , len(clusters)

    #average group sizes
    #print out groups in some fashion( if do IDs, remember +1 to make it jive
    #with DB ordering
    #want a reverse lookup:
        #cboards : group_id
    #then another table with group_id: joint

    #print "avg nut:", num_under_thresh / float(len(joints))

#cluster the P(k'|k,cboards), for a fixed k, of the clustered joints
#have cboards|k|cond_cluster_id
#and  cond_cluster_id|conditional_distribution
def clusterConditionals(conn, streetp) :
    q = """select joint
           from CLUSTERS_%s""" % streetp.upper()
    rows = conn.query(q)
    cond0s = [parse_old(row[0])[0] for row in rows]
    pinned_id = 6 
    pinned_cdf = np.cumsum( cond0s[pinned_id] )
    for i in range(pinned_id + 1,len(cond0s)) :
        compare_cdf = np.cumsum(cond0s[i])
        dist = cdfEMD( (pinned_cdf, compare_cdf) )
        if dist < .2 :
            print dist

#avg distance 
def avgIntraClusterDistance( conn, streetp ) :
    q = """select count(*)
           from CLUSTERS_%s""" % streetp.upper()
    n_clusters = conn.queryScalar( q, int )
    print n_clusters
    num = 0
    den = 0
    for cluster_id in range(1,n_clusters+1) :
        (n,d) = avgDistanceToCentroid( conn, streetp, cluster_id )
        print "cluster: ", cluster_id, " distance:", d, " num:", n
        if d > 1 :
            print "Over interCluster dist: ", cluster_id, " with dist:", d
            assert False
        num += n*d
        den += n
    return num/den


def avgInterClusterDistance( conn, streetp ) :
    summ = 0
    q = "select count(*) from CLUSTERS_%s" % streetp.upper()
    nclusters = conn.queryScalar(q,int)
    for cluster_id in range(1,nclusters) :
        print "===============\ncluster_id"
        q = """select joint from CLUSTERS_%s""" % streetp.upper()
        rows = conn.query(q)

        rix = 0
        num = 0
        den = 0
        for row in rows :
            rix += 1
            if rix < cluster_id : continue
            elif rix == cluster_id :
                pinned_cdf = np.cumsum(parse(row[0]))
            else :
                cdf = np.cumsum(parse(row[0]))
                d = cdfEMD( (pinned_cdf,cdf) )

                num += d
                den += 1
        t = num / den
        print t
        summ += t
    return summ / nclusters

def avgDistanceToCentroid( conn, streetp, cluster_id ) :
    q = """select joint 
           from CLUSTERS_%s
           where cluster_id = %d""" % (streetp.upper(), cluster_id)
    centroid_joint = conn.queryScalar(q,parse)
    centroid_cdf = np.cumsum( centroid_joint )

    q = """select member_id 
           from CLUSTER_MAP_%s
           where cluster_id = %d""" % (streetp.upper(), cluster_id )
    rows = conn.query( q ) 
    dists = []
    for row in rows :
        member_id = int(row[0])
        #print "member_id", member_id
        q2 = """select dist
                from TRANSITIONS_%s
                where id = %d""" % (streetp.upper(), member_id)

        member_joint = conn.queryScalar( q2, parse )
        assert len(member_joint) == len(centroid_joint)

        member_cdf = np.cumsum( member_joint )
        dist = cdfEMD( (centroid_cdf, member_cdf) )
        #print dist
        dists.append( dist )

    return [len(dists),  sum(dists) / float(len(dists))]

def printTransitions( conn, street, streetp ) :
    q = """select id, cboards, dist
           from TRANSITIONS_%s
           order by id""" % (streetp.upper())
    rows = conn.query( q )
    fout = open( "joints.txt", 'w' )
    for row in rows :
        fout.write( row[2] + "\n" )
    fout.close()

#distance using the legit, weighted EMD distance
def distBetween( conn, cboards1, cboards2, street, streetp  ) :
    #n_buckets = len(globles.BUCKET_PERCENTILES[street])
    n_bucketsp = len(globles.BUCKET_PERCENTILES[streetp])
    F1 = [(1,i) for i in range(n_bucketsp)]
    F2 = [(1,i) for i in range(n_bucketsp)]

    q1 =  """select dist 
             from TRANSITIONS_%s
             where cboards = '%s' """ % (streetp.upper(), cboards1 )
    q2 = """select dist 
            from TRANSITIONS_%s
            where cboards = '%s' """ % (streetp.upper(), cboards2 )

    joint1 = normalize( parse_old( conn.queryScalar( q1, str ) ) )
    joint2 = normalize( parse_old( conn.queryScalar( q2, str ) ) )

    return avgEMD( (joint1, joint2, F1, F2, streetp ) )

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
    #print distBetween( conn, "569_h_r|5569_p_r", "24A_h_r|224A_p_r", "flop","turn" )
    #print distBetween( conn, "569_h_r|5569_p_r", "678_s_r|6789_s_2fooxx", "flop","turn" )
    #print distBetween( conn, "569_h_r|5569_p_r", "8JQ_h_r|88JQ_p_r", "flop","turn" )
    clusterJoints( conn, "turn", "river" )
    #clusterConditionals(conn,"turn")

    #print avgDistanceToCentroid( conn, "river", 226 )
    #print avgIntraClusterDistance( conn, "turn" )
    #print avgInterClusterDistance( conn, "turn" )
