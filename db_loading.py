import db
from yaml import load, dump
from os import listdir

dr = False
conn = db.Conn( "localhost", dry_run = dr )

fin = open("preflop_ehs2.txt")
d_pocket_ehs2 = load( fin.read() )
buffer = []
for pocket in d_pocket_ehs2 :
    ehs2 = d_pocket_ehs2[pocket]
    buffer.append( "dummy,%s,%s" % (pocket,ehs2) )

fin.close()
fout = open( "/var/lib/mysql/toby/preflop_ehs2_bulk_load.csv",'w')
fout.write( '\n'.join(buffer) )
fout.close()

assert False

street_names = ["river"] #,'turn','river']
for street_name in street_names :
    fout = open("/var/lib/mysql/toby/%s_ehs2_bulk_load.csv" % street_name, 'w' )
    dirname = "hsdists/%ss" % street_name
    count = 0
    for listing in listdir(dirname) :
        if not listing.endswith('hsdist') :
            continue
        [cboard,ext] = listing.rsplit('.',1)

        buffer = []
        fin = open( "%s/%s" % (dirname,listing) )
        d_pocket_ehs2 = load( fin.read() )
        for pocket in d_pocket_ehs2 :
            ehs2 = d_pocket_ehs2[pocket]
            buffer.append( "%s,%s,%s" % (cboard,pocket,ehs2) )
            #conn.insert('EHS2_RIVER', [cboard,street_name,pocket,ehs2], skip_dupes=True )
        fout.write( '\n'.join(buffer) + '\n' )
        buffer = []
        fin.close()
        if count % 100 == 0 :
            print count
        count +=1

    fout.close()
