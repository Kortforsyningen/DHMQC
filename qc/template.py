######################################################################################
##  TEMPLATE FOR A TEST TO BE WRAPPED 
##  FILL IN AND DELETE BELOW...
######################################################################################
import sys,os,time
#import some relevant modules...
from thatsDEM import pointcloud, vector_io, array_geometry, report
import numpy as np
import  thatsDEM.dhmqc_constants as constants
from utils.osutils import ArgumentParser
z_min=1.0
cut_to=constants.terrain
#To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__)

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Write something here",prog=progname)
parser.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
#add some arguments below
parser.add_argument("-class",type=int,default=cut_to,help="Inspect points of this class - defaults to 'terrain'")
parser.add_argument("-zlim",type=float,default=z_min,help="Specify the minial z-size of a steep triangle.")
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("ref_file",help="input reference data.")


#
def usage():
	parser.print_help()
	

def main(args):
	pargs=parser.parse_args(args[1:])

#to be able to call the script 'stand alone'
if __name__=="__main__":
	main(sys.argv)