###########################
## beginnings of building zcheck...
#########################
import sys,os
import numpy as np
from thatsDEM import pointcloud,vector_io,array_geometry,report
from utils.names import get_1km_name
from utils.stats import get_dz_stats
DEBUG="-debug" in sys.argv

unclassified=1
xy_tolerance=1.0
z_tolerance=1.0
angle_tolerance=60






def main(args):
	lasname=args[1]
	buildname=args[2]
	kmname=get_1km_name(lasname)
	pc=pointcloud.fromLAS(lasname)
	polygons=vector_io.get_geometries(buildname)
	pcs=dict()
	for id in pc.get_pids():
		print("%s\n" %("+"*70))
		print("Strip id: %d" %id)
		pc_=pc.cut_to_strip(id).cut_to_class(unclassified)
		if pc_.get_size()>50:
			pcs[id]=pc_
			pcs[id].triangulate()
			pcs[id].calculate_validity_mask(angle_tolerance,xy_tolerance,z_tolerance)
		else:
			print("Not enough points....")
		
	del pc
	done=[]
	for id1 in pcs:
		pc1=pcs[id1]
		if pc1.get_size<100:
			if DEBUG:
				print("Few points in strip %d. Continuing..." %id1)
			continue
		for id2 in pcs:
			if id1==id2:
				continue
			ml="-"*70
			print("%s\nChecking strip %d against strip %d\n%s" %(ml,id1,id2,ml))
			pc2=pcs[id2]
			if not pc1.might_overlap(pc2):
				if DEBUG:
					print("Strip %d and strip %d does not seem to overlap. Continuing..." %(id1,id2))
					print("DEBUG: Strip1 bounds:\n%s\nStrip2 bounds:\n%s" %(pc1.get_bounds(),pc2.get_bounds())) 
				continue
			fn=0
			for polygon in polygons:
				fn+=1
				a_polygon=array_geometry.ogrpoly2array(polygon)
				if DEBUG:
					print("----- building: %d ------" %fn)
				bbox=array_geometry.get_bounds(a_polygon)
				if  not (pc1.might_intersect_box(bbox) and pc2.might_intersect_box(bbox)):
					if DEBUG:
						print("Polygon not in strip overlap. Continuing...")
						print("DEBUG: Strip1 bounds:\n%s\nStrip2 bounds:\n%s\nPolygon bounds:\n%s" %(pc1.get_bounds(),pc2.get_bounds(),bbox)) 
					continue
				pc2_in_poly=pc2.cut_to_polygon(a_polygon)
				if pc2_in_poly.get_size()<5:
					if DEBUG:
						print("Not enough points ( %d ) from strip %d in building." %(pc2_in_poly.get_size(),id2))
					continue
				z_out=pc1.controlled_interpolation(pc2_in_poly.xy,nd_val=-999)
				M=(z_out!=-999)
				if not M.any():
					continue
				z_good=pc2_in_poly.z[M]
				dz=z_out[M]-z_good
				#TODO calculate mean slope for triangles used - easy enough....
				print("(%d,%d,%d):" %(id1,id2,fn))
				print("Statistics for check of strip %d against strip %d, feature %d" %(id1,id2,fn))
				m,sd,l1,n=get_dz_stats(dz)
				if not DEBUG:
					report.report_zcheck_building(kmname,id1,id2,m,sd,n,ogr_geom=polygon)
					

if __name__=="__main__":
	main(sys.argv)
				
				
				
				
		
	
	