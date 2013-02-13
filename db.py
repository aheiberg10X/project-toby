import MySQLdb
import warnings
#import globes
import simplejson as json

endOfIteration = -1

#makes MySQLdb.Warning raise an Exception, rather than printing to stdout
#this lets us log
warnings.simplefilter("error", MySQLdb.Warning)

class Conn :
    #if dry_run : print out PUT queries without executing
    def __init__(self, switch, warning_file="warning.txt", dry_run=False) :
        #fconn = open( "%s/connections.js" % globes.ROOT_DIR )
        fconn = open( "connections.js" )
        burn = fconn.readline()
        self.connections =  json.loads( fconn.read() )
        self.connection = self.connect( *self.connections[switch] )
        self.cur = self.connection.cursor()
        self.fwarning = open(warning_file,'wb')
        self.dry_run = dry_run

    def __del__(self) :
        self.fwarning.close()
        self.cur.close()
        self.connection.close()

    def connect( self, host, user, password, db ) :
        return MySQLdb.connect( host=host, \
                                user=user, \
                                passwd=password, \
                                db=db,
                                connect_timeout = 5)

    #there are two classes of database interactions:
    #GETs (queries/reads) and PUTs (updates/inserts/deletes/writes)
    def get(self, query ) :
        self.cur.execute(query)

    def put( self, query ) :
        try :
            if self.dry_run :
                print query
                pass
            else :
                self.cur.execute( query )
        except Exception, (e) :
            exc = refineException( repr(e), query )
            if type(exc) == SQLWarning :
                string = "Warning: %s \n Query: %s\n\n\n" % (exc.error, exc.query)
                self.fwarning.write( string )
                print string

            else :
                raise exc

    def getColumns(self,table) :
        rs = self.query("SHOW COLUMNS FROM %s" % table)
        return [r[0] for r in rs]

    def query(self,query) :
        self.get( query )
        return self.cur.fetchall()

    def iterateQuery(self, query, size=10000, no_stop=False) :
        self.get( query )

        goon = True
        while goon :
            rows = self.cur.fetchmany( size )
            # print "iSQL: new set of %d rows" % len(rows)
            goon = len(rows) > 0
            if goon :
                for row in rows : yield row
            else :
                if no_stop :
                    while True : yield endOfIteration
                else :
                    raise StopIteration

    def queryToFile(self, query, fname ) :
        fout = open(fname,'wb')
        for row in self.iterateQuery(query) :
            fout.write( '%s\n' % '\t'.join([str(t) for t in row]) )
        fout.close()

    def queryScalar( self, query, cast ) :
        try :
            q = self.query(query)
            if len(q) == 0 : return False
            if len(q) > 1 :
                raise SQLError("iqueryScalar getting more than one row")
            w = q[0][0]
            return cast( w )
        except IndexError : 
            return False
        except TypeError : 
            return False

    def getNextID( self, table ) :
        nid = self.queryScalar('''select max(id) from %s''' % table, int)
        if not nid and not nid == 0 : return 0
        else : return nid+1

    #should never return a StopIteration
    #DEPRECATED?
    def iterate( self, table, cols=['*'], order_by=[] ) :
        columns = ','.join(cols)
        order_clause = ""
        if order_by :
            order_clause = "ORDER BY %s" % ','.join(order_by)
        query =  "select %s from %s %s" % (columns,table,order_clause)
        return self.iterateQuery( query, no_stop = True )

    def sanitizeValue( self, value ):
        #quote wrap everything except NULL
        if value == 'NULL' or value == '' : return 'NULL'
        else : return "'%s'" % str(value).replace("'","\\'")

    def insert(self, table, values, columns=[], skip_dupes=False ) :
        values = ','.join( map( self.sanitizeValue, values ) )
        if not columns :
            ins = """INSERT INTO %s VALUES( %s );""" \
                  % (table, values)
        else :
            columns = ','.join(['`%s`' % c for c in columns])
            ins = "INSERT INTO %s (%s) VALUES( %s );" \
                   % (table, columns, values)
        try :
            self.put(ins)
        except SQLDuplicate, (e) :
            if skip_dupes : pass
            else : raise e

    def update( self, table, values, columns, eyeD) :
        values = map( self.sanitizeValue, values )
        eqpairs = ["%s = %s" % (c,v) for (c,v) in zip(columns,values)]
        string = ', '.join(eqpairs)
        update = '''update %s set %s where id = %d''' % (table,string,eyeD)
        self.put( update )

    def wipe(self, table) :
        self.put("delete from %s" % table)

##############################################################################
###############      Exception Handling   ####################################
##############################################################################

# If an Exception is caught doing a SQL operation, we refine it to figure out
# what is actually going wrong
def refineException( message, query ) :
    if "integrity" in message.lower() :
        return SQLDuplicate(message,query)
    elif "warning" in message.lower() :
        return SQLWarning(message,query)
    else :
        return SQLError(message,query)

# the general, unrefined Error.  Can print the error message and the query that
# caused it
class SQLError(Exception) :
    def __init__(self, e, query) :
        self.error = e
        self.query = query
    def __str__(self) :
        return "\nError: %s\n----------------\nQuery: %s\n" \
                % (repr(self.error), self.query)

#If we are doing a duplicate insertion
class SQLDuplicate(SQLError) :
     pass

#for warnings
class SQLWarning(SQLError) :
    pass

#the db modules internal functions can throw some variation of SQLError
#this decorator lets external functions easily catch these errors
def catch(func) :
    def inner(*args, **kwargs) :
        try :
            return func(*args, **kwargs)
        except SQLError, (mse):
            print mse
            assert False
    return inner


if __name__=='__main__' :
    dbc = Conn()
    #dbc.update("Variants",["plateIIII",1],["sourc","chrom"],0)
    r = dbc.query( "select name,description from Genes where id = 0" )
    if not r[0][0] : print "whoopie"

